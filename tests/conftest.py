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

from typing import Dict, List, Set, cast

import pytest

# Tango imports
import tango
import yaml


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


# @pytest.fixture(name="test_proxies", scope="session")
# def init_proxies_fixture():
#     """
#     Return a proxy connection to all devices under test.

#     :return: a TestProxies object containing device proxies to all devices covered
#         under integration testing scope, with methods for resetting subarray ObsState
#         and waits with timeout for device DevState and ObsState.
#     """

#     class TestProxies:
#         def __init__(self: TestProxies) -> None:
#             """
#             Initialize all device proxies needed for integration testing.

#             Currently supported capabilities:
#             - 1 CbfController
#             - 1 CbfSubarray
#             - 4 Fsp
#             - 8 Vcc
#             - 1 Slim
#             - 4 SlimLink
#             """
#             # NOTE: set debug_device_is_on to True in order
#             #       to allow device debugging under VScode
#             self.debug_device_is_on = False
#             if self.debug_device_is_on:
#                 # Increase the timeout in order to allow  time for debugging
#                 timeout_millis = 500000
#             else:
#                 timeout_millis = 60000

#             # Load in system params
#             sys_param = load_data("sys_param_4_boards")
#             self.dish_utils = DISHUtils(sys_param)

#             # TmCspSubarrayLeafNodeTest
#             self.tm = CbfDeviceProxy(
#                 fqdn="ska_mid/tm_leaf_node/csp_subarray_01",
#                 logger=logging.getLogger(),
#             )

#             # CbfController
#             self.controller = CbfDeviceProxy(
#                 fqdn="mid_csp_cbf/sub_elt/controller",
#                 logger=logging.getLogger(),
#             )
#             self.controller.set_timeout_millis(timeout_millis)
#             self.wait_timeout_dev([self.controller], DevState.DISABLE, 3, 1)

#             self.max_capabilities = dict(
#                 pair.split(":")
#                 for pair in self.controller.get_property("MaxCapabilities")[
#                     "MaxCapabilities"
#                 ]
#             )
#             self.num_sub = int(self.max_capabilities["Subarray"])
#             self.num_fsp = int(self.max_capabilities["FSP"])
#             self.num_vcc = int(self.max_capabilities["VCC"])

#             # CbfSubarray
#             self.subarray = [None]
#             for proxy in [
#                 CbfDeviceProxy(
#                     fqdn=f"mid_csp_cbf/sub_elt/subarray_{i:02}",
#                     logger=logging.getLogger(),
#                 )
#                 for i in range(1, self.num_sub + 1)
#             ]:
#                 proxy.set_timeout_millis(timeout_millis)
#                 self.subarray.append(proxy)
#                 proxy.loggingLevel = LoggingLevel.DEBUG

#             # Fsp
#             # index == fspID
#             self.fsp = [None]
#             for proxy in [
#                 CbfDeviceProxy(
#                     fqdn=f"mid_csp_cbf/fsp/{j:02}", logger=logging.getLogger()
#                 )
#                 for j in range(1, self.num_fsp + 1)
#             ]:
#                 self.fsp.append(proxy)

#             # currently support for just one subarray, CORR/PSS-BF/PST-BF only
#             # fspSubarray[function mode (str)][subarray id (int)][fsp id (int)]
#             self.fspSubarray = {
#                 "CORR": {1: [None]},
#                 "PSS-BF": {1: [None]},
#                 "PST-BF": {1: [None]},
#             }

#             for proxy in [
#                 CbfDeviceProxy(
#                     fqdn=f"mid_csp_cbf/fspCorrSubarray/{j:02}_01",
#                     logger=logging.getLogger(),
#                 )
#                 for j in range(1, self.num_fsp + 1)
#             ]:
#                 self.fspSubarray["CORR"][1].append(proxy)

#             for proxy in [
#                 CbfDeviceProxy(
#                     fqdn=f"mid_csp_cbf/fspPssSubarray/{j:02}_01",
#                     logger=logging.getLogger(),
#                 )
#                 for j in range(1, self.num_fsp + 1)
#             ]:
#                 self.fspSubarray["PSS-BF"][1].append(proxy)

#             for proxy in [
#                 CbfDeviceProxy(
#                     fqdn=f"mid_csp_cbf/fspPstSubarray/{j:02}_01",
#                     logger=logging.getLogger(),
#                 )
#                 for j in range(1, self.num_fsp + 1)
#             ]:
#                 self.fspSubarray["PST-BF"][1].append(proxy)

#             # Vcc
#             # index == vccID
#             self.vcc = [None]
#             for proxy in [
#                 CbfDeviceProxy(
#                     fqdn=f"mid_csp_cbf/vcc/{i:03}", logger=logging.getLogger()
#                 )
#                 for i in range(1, self.num_vcc + 1)
#             ]:
#                 self.vcc.append(proxy)

#             # TODO: CIP-1470 removed VCC SW
#             # self.vccSw = [None]
#             # for i in range(1, self.num_vcc + 1):
#             #     sw = [None]
#             #     for j in range(1, 3):  # 2 search windows
#             #         sw.append(
#             #             CbfDeviceProxy(
#             #                 fqdn=f"mid_csp_cbf/vcc_sw{j}/{i:03}",
#             #                 logger=logging.getLogger(),
#             #             )
#             #         )
#             #     self.vccSw.append(sw)

#             # Talon LRU
#             self.talon_lru = []
#             for i in range(1, 5):  # 4 Talon LRUs for now
#                 self.talon_lru.append(
#                     CbfDeviceProxy(
#                         fqdn=f"mid_csp_cbf/talon_lru/{i:03}",
#                         logger=logging.getLogger(),
#                     )
#                 )

#             # Power switch
#             self.power_switch = []
#             for i in range(1, 4):  # 3 Power Switches
#                 self.power_switch.append(
#                     CbfDeviceProxy(
#                         fqdn=f"mid_csp_cbf/power_switch/{i:03}",
#                         logger=logging.getLogger(),
#                     )
#                 )

#             # Slim
#             self.slim = [
#                 CbfDeviceProxy(
#                     fqdn="mid_csp_cbf/slim/slim-fs",
#                     logger=logging.getLogger(),
#                 )
#             ]

#             # SlimLink
#             self.slim_link = []
#             for i in range(0, 3):  # 4 SlimLinks
#                 self.slim_link.append(
#                     CbfDeviceProxy(
#                         fqdn=f"mid_csp_cbf/fs_links/{i:03}",
#                         logger=logging.getLogger(),
#                     )
#                 )

#         def wait_timeout_dev(
#             self: TestProxies,
#             proxy_list: List[CbfDeviceProxy],
#             state: DevState,
#             time_s: float,
#             sleep_time_s: float,
#         ) -> None:
#             """
#             Periodically check proxy DevState until it is either the specified
#             value or the time limit has elapsed.

#             :param proxy_list: list of proxies to wait on
#             :param state: proxy DevState to wait for
#             :param time_s: time to timeout in seconds
#             :param sleep_time_s: sleep time cycle in seconds
#             """
#             timeout = time.time_ns() + (time_s * 1_000_000_000)
#             while time.time_ns() < timeout:
#                 for proxy in proxy_list:
#                     if proxy.State() == state:
#                         break
#                 time.sleep(sleep_time_s)

#         def wait_timeout_obs(
#             self: TestProxies,
#             proxy_list: List[CbfDeviceProxy],
#             state: ObsState,
#             time_s: float,
#             sleep_time_s: float,
#         ) -> None:
#             """
#             Periodically check proxy ObsState until it is either the specified
#             value or the time limit has elapsed.

#             :param proxy_list: list of proxies to wait on
#             :param state: proxy ObsState to wait for
#             :param time_s: time to timeout in seconds
#             :param sleep_time_s: sleep time cycle in seconds
#             """
#             timeout = time.time_ns() + (time_s * 1_000_000_000)
#             while time.time_ns() < timeout:
#                 for proxy in proxy_list:
#                     if proxy.obsState == state:
#                         break
#                 time.sleep(sleep_time_s)

#         def clean_test_proxies(self: TestProxies) -> None:
#             """
#             Reset subarray to DevState.ON, ObsState.EMPTY
#             """
#             wait_time_s = 3
#             sleep_time_s_long = 1
#             sleep_time_s_short = 0.05

#             for proxy in [
#                 self.subarray[i] for i in range(1, self.num_sub + 1)
#             ]:
#                 if proxy.State() != DevState.ON:
#                     proxy.On()
#                     self.wait_timeout_dev(
#                         [proxy], DevState.ON, wait_time_s, sleep_time_s_long
#                     )

#                 if proxy.obsState != ObsState.EMPTY:
#                     if proxy.obsState not in [
#                         ObsState.FAULT,
#                         ObsState.ABORTED,
#                     ]:
#                         proxy.Abort()
#                         self.wait_timeout_obs(
#                             [proxy],
#                             ObsState.ABORTED,
#                             wait_time_s,
#                             sleep_time_s_short,
#                         )

#                     proxy.Restart()
#                     self.wait_timeout_obs(
#                         [proxy],
#                         ObsState.EMPTY,
#                         wait_time_s,
#                         sleep_time_s_short,
#                     )

#         def on(self: TestProxies) -> None:
#             """
#             Controller device command sequence to turn on subarrays, FSPs, VCCs
#             Used for resetting starting state duing subarray integration testing.
#             """
#             wait_time_s = 3
#             sleep_time_s = 1

#             if self.controller.adminMode == AdminMode.OFFLINE:
#                 self.controller.adminMode = AdminMode.ONLINE

#             # ensure On command sent in OFF state
#             if self.controller.State() != DevState.OFF:
#                 self.controller.Off()
#                 self.wait_timeout_dev(
#                     [self.controller], DevState.OFF, wait_time_s, sleep_time_s
#                 )

#             # Run InitSysParam command before turning on the MCS
#             data_file_path = (
#                 os.path.dirname(os.path.abspath(__file__)) + "/data/"
#             )
#             with open(data_file_path + "sys_param_4_boards.json") as f:
#                 sp = f.read()
#             self.controller.InitSysParam(sp)

#             self.controller.On()
#             self.wait_timeout_dev(
#                 [self.controller], DevState.ON, wait_time_s, sleep_time_s
#             )

#         def off(self: TestProxies) -> None:
#             """
#             Controller device command sequence to turn off subarrays, FSPs, VCCs
#             Used for resetting starting state duing subarray integration testing.
#             """
#             wait_time_s = 3
#             sleep_time_s = 1

#             if self.controller.adminMode == AdminMode.OFFLINE:
#                 self.controller.adminMode = AdminMode.ONLINE

#             # ensure Off command not sent in OFF state
#             if self.controller.State() == DevState.OFF:
#                 self.controller.On()
#                 self.wait_timeout_dev(
#                     [self.controller], DevState.ON, wait_time_s, sleep_time_s
#                 )

#             self.controller.Off()
#             self.wait_timeout_dev(
#                 [self.controller], DevState.OFF, wait_time_s, sleep_time_s
#             )

#             # self.controller.adminMode = AdminMode.OFFLINE
#             # self.wait_timeout_dev(
#             #     [self.controller], DevState.DISABLE, wait_time_s, sleep_time_s
#             # )

#     return TestProxies()


# @pytest.fixture(scope="class")
# def debug_device_is_on() -> bool:
#     # NOTE: set debug_device_is_on to True in order
#     #       to allow device debugging under VScode
#     debug_device_is_on = False
#     if debug_device_is_on:
#         # Increase the timeout in order to allow  time for debugging
#         timeout_millis = 500000  # noqa: F841
#     return debug_device_is_on


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
            receptors_under_test: list[int],
        ) -> dict:
            dm_num_entries = len(delay_model_all_obj)
            # TODO: receptor values are hardcoded
            receptors_to_remove = list(
                set(["SKA001", "SKA100", "SKA036", "SKA063"])
                - set(receptors_under_test)
            )

            if receptors_to_remove:
                for i_dm in range(dm_num_entries):
                    # Remove the entries from the delay models that are NOT
                    # among receptors_under_test:
                    for i_rec in receptors_to_remove:
                        for jj, entry in enumerate(
                            delay_model_all_obj[i_dm]["receptor_delays"]
                        ):
                            if entry["receptor"] == i_rec:
                                delay_model_all_obj[i_dm][
                                    "receptor_delays"
                                ].pop(jj)

            return delay_model_all_obj

    return DelayModelTest()
