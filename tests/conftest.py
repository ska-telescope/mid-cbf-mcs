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

from __future__ import absolute_import
from __future__ import annotations

import logging
from typing import Any, Callable, Generator, Set, cast
import pytest
import unittest
import yaml
import time
import json

# Tango imports
import tango
from tango import DevState
from tango import DeviceProxy

# SKA imports
from ska_tango_base.control_model import LoggingLevel, ObsState, AdminMode

from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import (
    ClientProxyTangoHarness,
    DevicesToLoadType,
    CbfDeviceInfo,
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
    _testbeds: dict[str, set[str]] = yaml.safe_load(stream)


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
    config: pytest.config.Config, items: list[pytest.Item]
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
            tag[len(prefix) :] for tag in item.keywords if tag.startswith(prefix)
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
def initial_mocks() -> dict[str, unittest.mock.Mock]:
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
        dict[str, Any],
        DevicesToLoadType,
        Callable[[], unittest.mock.Mock],
        dict[str, unittest.mock.Mock],
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

        pass

    testbed = request.config.getoption("--testbed")

    def build_harness(
        tango_config: dict[str, Any],
        devices_to_load: DevicesToLoadType,
        mock_factory: Callable[[], unittest.mock.Mock],
        initial_mocks: dict[str, unittest.mock.Mock],
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
            tango_harness = _CPTCTangoHarness(device_info, logger, **tango_config)
        else:
            tango_harness = ClientProxyTangoHarness(device_info, logger)

        starting_state_harness = StartingStateTangoHarness(tango_harness)

        mocking_harness = MockingTangoHarness(
            starting_state_harness, mock_factory, initial_mocks
        )

        return mocking_harness

    return build_harness


@pytest.fixture()
def tango_config() -> dict[str, Any]:
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
            dict[str, Any],
            DevicesToLoadType,
            Callable[[], unittest.mock.Mock],
            dict[str, unittest.mock.Mock],
        ],
        TangoHarness,
    ],
    tango_config: dict[str, str],
    devices_to_load: DevicesToLoadType,
    mock_factory: Callable[[], unittest.mock.Mock],
    initial_mocks: dict[str, unittest.mock.Mock],
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
def mock_change_event_callback_factory() -> Callable[[str], MockChangeEventCallback]:
    """
    Return a factory that returns a new mock change event callback each call.

    :return: a factory that returns a new mock change event callback
        each time it is called with the name of a device attribute.
    """
    return MockChangeEventCallback


@pytest.fixture(name="proxies", scope="session")
def init_proxies_fixture():

    class Proxies:
        def __init__(self):
            # NOTE: set debug_device_is_on to True in order
            #       to allow device debugging under VScode
            self.debug_device_is_on = False
            if self.debug_device_is_on:
                # Increase the timeout in order to allow  time for debugging
                timeout_millis = 500000
            else:
                timeout_millis = 60000

            self.vcc = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/vcc/" + str(j + 1).zfill(3)) for j in range(4)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.vcc[i + 1] = proxy

            band_tags = ["12", "3", "4", "5"]
            self.vccBand = [[DeviceProxy("mid_csp_cbf/vcc_band{0}/{1:03d}".format(j, k + 1)) for j in band_tags] for k in range(4)]
            self.vccTdc = [[DeviceProxy("mid_csp_cbf/vcc_sw{0}/{1:03d}".format(j, i + 1)) for j in ["1", "2"]] for i in range(4)] 
            
            self.fspSubarray = {} # index 1, 2 = corr (01_01, 02_01); index 3, 4 = pss (03_01, 04_01); index 5, 6 = pst (01_01, 02_01)
            self.fspCorrSubarray = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/fspCorrSubarray/" + str(j + 1).zfill(2) + "_01") for j in range(2)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.fspSubarray[i + 1] = proxy
                self.fspCorrSubarray[i] = proxy

            self.fspPssSubarray = {}    
            for i ,proxy in enumerate([DeviceProxy("mid_csp_cbf/fspPssSubarray/" + str(j + 3).zfill(2) + "_01") for j in range(2)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.fspSubarray[i + 3] = proxy
                self.fspPssSubarray[i] = proxy

            self.fspPstSubarray = {}      
            for i ,proxy in enumerate([DeviceProxy("mid_csp_cbf/fspPstSubarray/" + str(j + 1).zfill(2) + "_01") for j in range(2)]):
                self.fspSubarray[i + 5] = proxy
                self.fspPstSubarray[i] = proxy

            self.fsp1FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/01".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp2FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/02".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp3FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/03".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp4FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/04".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

            self.fsp = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/fsp/" + str(j + 1).zfill(2)) for j in range(4)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.fsp[i + 1] = proxy
            
            self.controller = DeviceProxy("mid_csp_cbf/sub_elt/controller")
            self.controller.loggingLevel = LoggingLevel.DEBUG
            self.controller.set_timeout_millis(timeout_millis)
            self.wait_timeout_dev([self.controller], DevState.STANDBY, 3, 0.05)
            
            self.receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in self.controller.receptorToVcc)
            
            self.subarray = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/sub_elt/subarray_" + str(i + 1).zfill(2)) for i in range(3)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.subarray[i + 1] = proxy
                self.subarray[i + 1].set_timeout_millis(timeout_millis)

            self.tm = DeviceProxy("ska_mid/tm_leaf_node/csp_subarray_01")

        def clean_proxies(self):
            self.receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in self.controller.receptorToVcc)
            for proxy in [self.subarray[i + 1] for i in range(1)]:
                if proxy.obsState == ObsState.FAULT:
                    proxy.Restart()
                if proxy.obsState == ObsState.SCANNING:
                    proxy.EndScan()
                    self.wait_timeout_obs([proxy], ObsState.READY, 3, 0.05)
                if proxy.obsState == ObsState.READY:
                    proxy.GoToIdle()
                    self.wait_timeout_obs([proxy], ObsState.IDLE, 3, 0.05)
                if proxy.obsState == ObsState.IDLE:
                    if len(proxy.receptors) > 0:
                        proxy.RemoveAllReceptors()
                        self.wait_timeout_obs([proxy], ObsState.EMPTY, 3, 0.05)
                if proxy.obsState == ObsState.EMPTY:
                    proxy.Off()
                    self.wait_timeout_dev([proxy], DevState.OFF, 3, 0.05)
                    for vcc_proxy in [self.vcc[i + 1] for i in range(4)]:
                        if vcc_proxy.State() == DevState.ON:
                            vcc_proxy.Off()
                            self.wait_timeout_dev([vcc_proxy], DevState.OFF, 1, 0.05)
                    for fsp_proxy in [self.fsp[i + 1] for i in range(4)]:
                        if fsp_proxy.State() == DevState.ON:
                            fsp_proxy.Off()
                            self.wait_timeout_dev([fsp_proxy], DevState.OFF, 1, 0.05)
        
        def wait_timeout_dev(self, proxygroup, state, time_s, sleep_time_s):
            #time.sleep(time_s)
            timeout = time.time_ns() + (time_s * 1_000_000_000)
            while time.time_ns() < timeout:
                for proxy in proxygroup:
                    if proxy.State() == state: break
                time.sleep(sleep_time_s)

        def wait_timeout_obs(self, proxygroup, state, time_s, sleep_time_s):
            #time.sleep(time_s)
            timeout = time.time_ns() + (time_s * 1_000_000_000)
            while time.time_ns() < timeout:
                for proxy in proxygroup:
                    if proxy.obsState == state: break
                time.sleep(sleep_time_s)
    
    return Proxies()

@pytest.fixture(scope="class")
def debug_device_is_on():
    # NOTE: set debug_device_is_on to True in order
    #       to allow device debugging under VScode
    debug_device_is_on = False
    if debug_device_is_on:
        # Increase the timeout in order to allow  time for debugging
        timeout_millis = 500000
    return debug_device_is_on

@pytest.fixture(scope="class")
def create_vcc_proxy():
    dp = DeviceProxy("mid_csp_cbf/vcc/001")
    dp.loggingLevel = LoggingLevel.DEBUG
    return dp

@pytest.fixture(scope="class")
def create_band_12_proxy():
    #return DeviceTestContext(VccBand1And2)
    return DeviceProxy("mid_csp_cbf/vcc_band12/001")

@pytest.fixture(scope="class")
def create_band_3_proxy():
    #return DeviceTestContext(VccBand3)
    return DeviceProxy("mid_csp_cbf/vcc_band3/001")

@pytest.fixture(scope="class")
def create_band_4_proxy():
    #return DeviceTestContext(VccBand4)
    return DeviceProxy("mid_csp_cbf/vcc_band4/001")

@pytest.fixture(scope="class")
def create_band_5_proxy():
    #return DeviceTestContext(VccBand5)
    return DeviceProxy("mid_csp_cbf/vcc_band5/001")

@pytest.fixture(scope="class")
def create_sw_1_proxy():
    #return DeviceTestContext(VccSearchWindow)
    return DeviceProxy("mid_csp_cbf/vcc_sw1/001")

@pytest.fixture(scope="class")
def create_fsp_corr_subarray_1_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspCorrSubarray/01_01")

@pytest.fixture(scope="class")
def create_fsp_pss_subarray_2_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspPssSubarray/02_01")

@pytest.fixture(scope="class")
def create_corr_proxy():
    return DeviceProxy("mid_csp_cbf/fsp_corr/01")

@pytest.fixture(scope="class")
def create_pss_proxy():
    return DeviceProxy("mid_csp_cbf/fsp_pss/01")

def load_data(name):
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
