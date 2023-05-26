# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Partially ported from the SKA Low MCCS project:
# https://gitlab.com/ska-telescope/ska-low-mccs/-/blob/main/testing/src/tests/conftest.py
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""
A module defining a list of fixture functions that are shared across all the
ska-mid-cbf-mcs tests.
"""

from __future__ import absolute_import, annotations

import json
import logging
import time
import unittest
from typing import Any, Callable, Dict, Generator, List, Set, cast

import pytest

# Tango imports
import tango
import yaml

# SKA imports
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from tango import DevState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import (
    CbfDeviceInfo,
    ClientProxyTangoHarness,
    DevicesToLoadType,
    MockingTangoHarness,
    StartingStateTangoHarness,
    TangoHarness,
    TestContextTangoHarness,
)


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Pytest hook; prints info about tango version.

    :param session: a pytest Session object
    """
    print(tango.utils.info())


with open("tests/testbeds.yaml", "r") as stream:
    _testbeds: Dict[str, Set[str]] = yaml.safe_load(stream)


def pytest_configure(config: pytest.config.Config) -> None:
    """
    Register custom markers to avoid pytest warnings.

    :param config: the pytest config object
    """
    all_tags: Set[str] = cast(Set[str], set()).union(*_testbeds.values())
    for tag in all_tags:
        config.addinivalue_line("markers", f"needs_{tag}")


def pytest_addoption(parser: pytest.config.ArgumentParser) -> None:
    """
    Pytest hook; implemented to add the `--testbed` option, used to specify the context
    in which the test is running. This could be used, for example, to skip tests that
    have requirements not met by the context.

    :param parser: the command line options parser
    """
    parser.addoption(
        "--testbed",
        choices=_testbeds.keys(),
        default="test",
        help="Specify the testbed on which the tests are running.",
    )


def pytest_collection_modifyitems(
    config: pytest.config.Config, items: List[pytest.Item]
) -> None:
    """
    Modify the list of tests to be run, after pytest has collected them.

    This hook implementation skips tests that are marked as needing some
    tag that is not provided by the current test context, as specified
    by the "--testbed" option.

    For example, if we have a hardware test that requires the presence
    of a real TPM, we can tag it with "@needs_tpm". When we run in a
    "test" context (that is, with "--testbed test" option), the test
    will be skipped because the "test" context does not provide a TPM.
    But when we run in "pss" context, the test will be run because the
    "pss" context provides a TPM.

    :param config: the pytest config object
    :param items: list of tests collected by pytest
    """
    testbed = config.getoption("--testbed")
    available_tags = _testbeds.get(testbed, set())

    prefix = "needs_"
    for item in items:
        needs_tags = set(
            tag[len(prefix) :]  # noqa: E203
            for tag in item.keywords
            if tag.startswith(prefix)
        )
        unmet_tags = list(needs_tags - available_tags)
        if unmet_tags:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        f"Testbed '{testbed}' does not meet test needs: "
                        f"{unmet_tags}."
                    )
                )
            )


@pytest.fixture()
def initial_mocks() -> Dict[str, unittest.mock.Mock]:
    """
    Fixture that registers device proxy mocks prior to patching.

    By default no initial mocks are registered, but this fixture can be
    overridden by test modules/classes that need to register initial
    mocks.

    :return: an empty dictionary
    """
    return {}


@pytest.fixture()
def mock_factory() -> Callable[[], unittest.mock.Mock]:
    """
    Fixture that provides a mock factory for device proxy mocks. This default factory
    provides vanilla mocks, but this fixture can be overridden by test modules/classes
    to provide mocks with specified behaviours.

    :return: a factory for device proxy mocks
    """
    return MockDeviceBuilder()


@pytest.fixture()
def tango_harness_factory(
    request: pytest.FixtureRequest, logger: logging.Logger
) -> Callable[
    [
        Dict[str, Any],
        DevicesToLoadType,
        Callable[[], unittest.mock.Mock],
        Dict[str, unittest.mock.Mock],
    ],
    TangoHarness,
]:
    """
    Returns a factory for creating a test harness for testing Tango devices. The Tango
    context used depends upon the context in which the tests are being run, as specified
    by the `--testbed` option.

    If the context is "test", then this harness deploys the specified
    devices into a
    :py:class:`tango.test_context.MultiDeviceTestContext`.

    Otherwise, this harness assumes that devices are already running;
    that is, we are testing a deployed system.

    This fixture is implemented as a factory so that the actual
    `tango_harness` fixture can vary in scope: unit tests require test
    isolation, so will want to build a new harness every time. But
    functional tests assume a single harness that maintains state
    across multiple tests, so they will want to instantiate the harness
    once and then use it for multiple tests.

    :param request: A pytest object giving access to the requesting test
        context.
    :param logger: the logger to be used by this object.

    :return: a tango harness factory
    """

    class _CPTCTangoHarness(ClientProxyTangoHarness, TestContextTangoHarness):
        """
        A Tango test harness with the client proxy functionality of
        :py:class:`~ska_mid_cbf_mcs.testing.tango_harness.ClientProxyTangoHarness`
        within the lightweight test context provided by
        :py:class:`~ska_mid_cbf_mcs.testing.tango_harness.TestContextTangoHarness`.
        """

    testbed = request.config.getoption("--testbed")

    def build_harness(
        tango_config: Dict[str, Any],
        devices_to_load: DevicesToLoadType,
        mock_factory: Callable[[], unittest.mock.Mock],
        initial_mocks: Dict[str, unittest.mock.Mock],
    ) -> TangoHarness:
        """
        Builds the Tango test harness.

        :param tango_config: basic configuration information for a tango
            test harness
        :param devices_to_load: fixture that provides a specification of the
            devices that are to be included in the devices_info dictionary
        :param mock_factory: the factory to be used to build mocks
        :param initial_mocks: a pre-build dictionary of mocks to be used
            for particular

        :return: a tango test harness
        """
        if devices_to_load is None:
            device_info = None
        else:
            device_info = CbfDeviceInfo(**devices_to_load)

        tango_harness: TangoHarness  # type hint only
        if testbed == "test":
            tango_harness = _CPTCTangoHarness(
                device_info, logger, **tango_config
            )
        else:
            tango_harness = ClientProxyTangoHarness(device_info, logger)

        starting_state_harness = StartingStateTangoHarness(tango_harness)

        mocking_harness = MockingTangoHarness(
            starting_state_harness, mock_factory, initial_mocks
        )

        return mocking_harness

    return build_harness


@pytest.fixture()
def tango_config() -> Dict[str, Any]:
    """
    Fixture that returns basic configuration information for a Tango test harness, such
    as whether or not to run in a separate process.

    :return: a dictionary of configuration key-value pairs
    """
    return {"process": False}


@pytest.fixture()
def tango_harness(
    tango_harness_factory: Callable[
        [
            Dict[str, Any],
            DevicesToLoadType,
            Callable[[], unittest.mock.Mock],
            Dict[str, unittest.mock.Mock],
        ],
        TangoHarness,
    ],
    tango_config: Dict[str, str],
    devices_to_load: DevicesToLoadType,
    mock_factory: Callable[[], unittest.mock.Mock],
    initial_mocks: Dict[str, unittest.mock.Mock],
) -> Generator[TangoHarness, None, None]:
    """
    Creates a test harness for testing Tango devices.

    :param tango_harness_factory: a factory that provides a test harness
        for testing tango devices
    :param tango_config: basic configuration information for a tango
        test harness
    :param devices_to_load: fixture that provides a specification of the
        devices that are to be included in the devices_info dictionary
    :param mock_factory: the factory to be used to build mocks
    :param initial_mocks: a pre-build dictionary of mocks to be used
        for particular

    :yields: a tango test harness
    """
    with tango_harness_factory(
        tango_config, devices_to_load, mock_factory, initial_mocks
    ) as harness:
        yield harness


@pytest.fixture(scope="session")
def logger() -> logging.Logger:
    """
    Fixture that returns a default logger.

    :return: a logger
    """
    return logging.getLogger()


@pytest.fixture()
def mock_change_event_callback_factory() -> (
    Callable[[str], MockChangeEventCallback]
):
    """
    Return a factory that returns a new mock change event callback each call.

    :return: a factory that returns a new mock change event callback
        each time it is called with the name of a device attribute.
    """
    return MockChangeEventCallback


@pytest.fixture(name="test_proxies", scope="session")
def init_proxies_fixture():
    """
    Return a proxy connection to all devices under test.

    :return: a TestProxies object containing device proxies to all devices covered
        under integration testing scope, with methods for resetting subarray ObsState
        and waits with timeout for device DevState and ObsState.
    """

    class TestProxies:
        def __init__(self: TestProxies) -> None:
            """
            Initialize all device proxies needed for integration testing.

            Currently supported capabilities:
            - 1 CbfController
            - 1 CbfSubarray
            - 4 Fsp
            - 4 Vcc
            """
            # NOTE: set debug_device_is_on to True in order
            #       to allow device debugging under VScode
            self.debug_device_is_on = False
            if self.debug_device_is_on:
                # Increase the timeout in order to allow  time for debugging
                timeout_millis = 500000
            else:
                timeout_millis = 60000

            # TmCspSubarrayLeafNodeTest
            self.tm = CbfDeviceProxy(
                fqdn="ska_mid/tm_leaf_node/csp_subarray_01",
                logger=logging.getLogger(),
            )

            # CbfController
            self.controller = CbfDeviceProxy(
                fqdn="mid_csp_cbf/sub_elt/controller",
                logger=logging.getLogger(),
            )
            self.controller.set_timeout_millis(timeout_millis)
            self.wait_timeout_dev([self.controller], DevState.DISABLE, 3, 1)

            self.receptor_to_vcc = dict(
                [*map(int, pair.split(":"))]
                for pair in self.controller.receptorToVcc
            )

            self.max_capabilities = dict(
                pair.split(":")
                for pair in self.controller.get_property("MaxCapabilities")[
                    "MaxCapabilities"
                ]
            )
            self.num_sub = int(self.max_capabilities["Subarray"])
            self.num_fsp = int(self.max_capabilities["FSP"])
            self.num_vcc = int(self.max_capabilities["VCC"])

            # CbfSubarray
            self.subarray = [None]
            for proxy in [
                CbfDeviceProxy(
                    fqdn=f"mid_csp_cbf/sub_elt/subarray_{i:02}",
                    logger=logging.getLogger(),
                )
                for i in range(1, self.num_sub + 1)
            ]:
                proxy.set_timeout_millis(timeout_millis)
                self.subarray.append(proxy)
                proxy.loggingLevel = LoggingLevel.DEBUG

            # Fsp
            # index == fspID
            self.fsp = [None]
            for proxy in [
                CbfDeviceProxy(
                    fqdn=f"mid_csp_cbf/fsp/{j:02}", logger=logging.getLogger()
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fsp.append(proxy)

            # currently support for just one subarray, CORR/PSS-BF/PST-BF only
            # fspSubarray[function mode (str)][subarray id (int)][fsp id (int)]
            self.fspSubarray = {
                "CORR": {1: [None]},
                "PSS-BF": {1: [None]},
                "PST-BF": {1: [None]},
            }

            for proxy in [
                CbfDeviceProxy(
                    fqdn=f"mid_csp_cbf/fspCorrSubarray/{j:02}_01",
                    logger=logging.getLogger(),
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fspSubarray["CORR"][1].append(proxy)

            for proxy in [
                CbfDeviceProxy(
                    fqdn=f"mid_csp_cbf/fspPssSubarray/{j:02}_01",
                    logger=logging.getLogger(),
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fspSubarray["PSS-BF"][1].append(proxy)

            for proxy in [
                CbfDeviceProxy(
                    fqdn=f"mid_csp_cbf/fspPstSubarray/{j:02}_01",
                    logger=logging.getLogger(),
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fspSubarray["PST-BF"][1].append(proxy)

            # Vcc
            # index == vccID
            self.vcc = [None]
            for proxy in [
                CbfDeviceProxy(
                    fqdn=f"mid_csp_cbf/vcc/{i:03}", logger=logging.getLogger()
                )
                for i in range(1, self.num_vcc + 1)
            ]:
                self.vcc.append(proxy)

            self.vccSw = [None]
            for i in range(1, self.num_vcc + 1):
                sw = [None]
                for j in range(1, 3):  # 2 search windows
                    sw.append(
                        CbfDeviceProxy(
                            fqdn=f"mid_csp_cbf/vcc_sw{j}/{i:03}",
                            logger=logging.getLogger(),
                        )
                    )
                self.vccSw.append(sw)

            # Talon LRU
            self.talon_lru = []
            for i in range(1, 3):  # 2 Talon LRUs for now
                self.talon_lru.append(
                    CbfDeviceProxy(
                        fqdn=f"mid_csp_cbf/talon_lru/{i:03}",
                        logger=logging.getLogger(),
                    )
                )

            # Power switch
            self.power_switch = CbfDeviceProxy(
                fqdn="mid_csp_cbf/power_switch/001", logger=logging.getLogger()
            )

        def wait_timeout_dev(
            self: TestProxies,
            proxy_list: List[CbfDeviceProxy],
            state: DevState,
            time_s: float,
            sleep_time_s: float,
        ) -> None:
            """
            Periodically check proxy DevState until it is either the specified
            value or the time limit has elapsed.

            :param proxy_list: list of proxies to wait on
            :param state: proxy DevState to wait for
            :param time_s: time to timeout in seconds
            :param sleep_time_s: sleep time cycle in seconds
            """
            timeout = time.time_ns() + (time_s * 1_000_000_000)
            while time.time_ns() < timeout:
                for proxy in proxy_list:
                    if proxy.State() == state:
                        break
                time.sleep(sleep_time_s)

        def wait_timeout_obs(
            self: TestProxies,
            proxy_list: List[CbfDeviceProxy],
            state: ObsState,
            time_s: float,
            sleep_time_s: float,
        ) -> None:
            """
            Periodically check proxy ObsState until it is either the specified
            value or the time limit has elapsed.

            :param proxy_list: list of proxies to wait on
            :param state: proxy ObsState to wait for
            :param time_s: time to timeout in seconds
            :param sleep_time_s: sleep time cycle in seconds
            """
            timeout = time.time_ns() + (time_s * 1_000_000_000)
            while time.time_ns() < timeout:
                for proxy in proxy_list:
                    if proxy.obsState == state:
                        break
                time.sleep(sleep_time_s)

        def clean_test_proxies(self: TestProxies) -> None:
            """
            Reset subarray to DevState.ON, ObsState.EMPTY
            """
            wait_time_s = 3
            sleep_time_s_long = 1
            sleep_time_s_short = 0.05

            for proxy in [
                self.subarray[i] for i in range(1, self.num_sub + 1)
            ]:
                if proxy.State() != DevState.ON:
                    if proxy.State() != DevState.OFF:
                        proxy.Off()
                        self.wait_timeout_dev(
                            [proxy],
                            DevState.OFF,
                            wait_time_s,
                            sleep_time_s_long,
                        )
                    proxy.On()
                    self.wait_timeout_dev(
                        [proxy], DevState.ON, wait_time_s, sleep_time_s_long
                    )

                if proxy.obsState == ObsState.FAULT:
                    proxy.Restart()
                    self.wait_timeout_obs(
                        [proxy],
                        ObsState.READY,
                        wait_time_s,
                        sleep_time_s_short,
                    )

                if proxy.obsState == ObsState.SCANNING:
                    proxy.EndScan()
                    self.wait_timeout_obs(
                        [proxy],
                        ObsState.READY,
                        wait_time_s,
                        sleep_time_s_short,
                    )

                if proxy.obsState == ObsState.READY:
                    proxy.End()
                    self.wait_timeout_obs(
                        [proxy], ObsState.IDLE, wait_time_s, sleep_time_s_short
                    )

                if proxy.obsState == ObsState.IDLE:
                    proxy.RemoveAllReceptors()
                    self.wait_timeout_obs(
                        [proxy],
                        ObsState.EMPTY,
                        wait_time_s,
                        sleep_time_s_short,
                    )

        def on(self: TestProxies) -> None:
            """
            Controller device command sequence to turn on subarrays, FSPs, VCCs
            Used for resetting starting state duing subarray integration testing.
            """
            wait_time_s = 3
            sleep_time_s = 1

            if self.controller.adminMode == AdminMode.OFFLINE:
                self.controller.adminMode = AdminMode.ONLINE

            # ensure On command sent in OFF state
            if self.controller.State() != DevState.OFF:
                self.controller.Off()
                self.wait_timeout_dev(
                    [self.controller], DevState.OFF, wait_time_s, sleep_time_s
                )

            self.controller.On()
            self.wait_timeout_dev(
                [self.controller], DevState.ON, wait_time_s, sleep_time_s
            )

        def off(self: TestProxies) -> None:
            """
            Controller device command sequence to turn off subarrays, FSPs, VCCs
            Used for resetting starting state duing subarray integration testing.
            """
            wait_time_s = 3
            sleep_time_s = 1

            if self.controller.adminMode == AdminMode.OFFLINE:
                self.controller.adminMode = AdminMode.ONLINE

            # ensure Off command not sent in OFF state
            if self.controller.State() == DevState.OFF:
                self.controller.On()
                self.wait_timeout_dev(
                    [self.controller], DevState.ON, wait_time_s, sleep_time_s
                )

            self.controller.Off()
            self.wait_timeout_dev(
                [self.controller], DevState.OFF, wait_time_s, sleep_time_s
            )

            # self.controller.adminMode = AdminMode.OFFLINE
            # self.wait_timeout_dev(
            #     [self.controller], DevState.DISABLE, wait_time_s, sleep_time_s
            # )

    return TestProxies()


@pytest.fixture(scope="class")
def debug_device_is_on() -> bool:
    # NOTE: set debug_device_is_on to True in order
    #       to allow device debugging under VScode
    debug_device_is_on = False
    if debug_device_is_on:
        # Increase the timeout in order to allow  time for debugging
        timeout_millis = 500000  # noqa: F841
    return debug_device_is_on


def load_data(name: str) -> Dict[Any, Any]:
    """
    Loads a dataset by name. This implementation uses the name to find a
    JSON file containing the data to be loaded.

    :param name: name of the dataset to be loaded; this implementation
        uses the name to find a JSON file containing the data to be
        loaded.
    :type name: string
    """
    with open(f"tests/data/{name}.json", "r") as json_file:
        return json.load(json_file)


@pytest.fixture(name="delay_model_test", scope="session")
def init_delay_model_test_fixture():
    """
    Return a delay model test object.

    :return: a DelayModelTest object, with a method for creating
    the delay model input used for tests
    """

    class DelayModelTest:
        def __init__(self: DelayModelTest) -> None:
            """
            No initialization required.
            """

        def create_test_dm_obj_all(
            self: DelayModelTest,
            delay_model_all_obj: dict,
            receptors_under_test: List(int),
        ) -> dict:
            dm_num_entries = len(delay_model_all_obj)
            # TODO: receptor values are hardcoded
            receptors_to_remove = list(
                set(["MKT000", "MKT001", "MKT002", "MKT003"])
                - set(receptors_under_test)
            )

            if receptors_to_remove:
                for i_dm in range(dm_num_entries):
                    # Remove the entries from the delay models that are NOT
                    # among receptors_under_test:
                    for i_rec in receptors_to_remove:
                        for jj, entry in enumerate(
                            delay_model_all_obj[i_dm]["delay_model"]
                        ):
                            if entry["receptor"] == i_rec:
                                delay_model_all_obj[i_dm]["delay_model"].pop(
                                    jj
                                )

            return delay_model_all_obj

    return DelayModelTest()
