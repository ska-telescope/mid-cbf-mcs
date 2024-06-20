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
ska-mid-cbf-mcs integration tests.
"""

from __future__ import absolute_import, annotations

import json
import logging

# Path
import os
import time

import pytest

# SKA imports
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from tango import DevState
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils

def load_data(name: str) -> dict[any, any]:
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
            - 8 Vcc
            - 1 Slim
            - 4 SlimLink
            """
            # NOTE: set debug_device_is_on to True in order
            #       to allow device debugging under VScode
            self.debug_device_is_on = False
            if self.debug_device_is_on:
                # Increase the timeout in order to allow  time for debugging
                timeout_millis = 500000
            else:
                timeout_millis = 60000

            # Load in system params
            sys_param = load_data("sys_param_4_boards")
            self.dish_utils = DISHUtils(sys_param)

            # TmCspSubarrayLeafNodeTest
            self.tm = context.DeviceProxy(
                device_name="ska_mid/tm_leaf_node/csp_subarray_01",
            )

            # CbfController
            self.controller = context.DeviceProxy(
                device_name="mid_csp_cbf/sub_elt/controller",
            )
            self.controller.set_timeout_millis(timeout_millis)
            self.wait_timeout_dev([self.controller], DevState.DISABLE, 3, 1)

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
                context.DeviceProxy(
                    device_name=f"mid_csp_cbf/sub_elt/subarray_{i:02}",
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
                context.DeviceProxy(
                    device_name=f"mid_csp_cbf/fsp/{j:02}",
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fsp.append(proxy)

            # currently support for just one subarray, CORR/PSS-BF/PST-BF only
            # fspSubarray[function mode (str)][subarray id (int)][fsp id (int)]
            self.fspSubarray = {
                "CORR": {1: [None]},
            }

            for proxy in [
                context.DeviceProxy(
                    device_name=f"mid_csp_cbf/fspCorrSubarray/{j:02}_01",
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fspSubarray["CORR"][1].append(proxy)

            # Vcc
            # index == vccID
            self.vcc = [None]
            for proxy in [
                context.DeviceProxy(
                    device_name=f"mid_csp_cbf/vcc/{i:03}",
                )
                for i in range(1, self.num_vcc + 1)
            ]:
                self.vcc.append(proxy)

            # Talon LRU
            self.talon_lru = []
            for i in range(1, 5):  # 4 Talon LRUs for now
                self.talon_lru.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/talon_lru/{i:03}",
                    )
                )

            # Power switch
            self.power_switch = []
            for i in range(1, 4):  # 3 Power Switches
                self.power_switch.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/power_switch/{i:03}",
                    )
                )

            # Slim
            self.slim = [
                context.DeviceProxy(
                    device_name="mid_csp_cbf/slim/slim-fs",
                )
            ]

            # SlimLink
            self.slim_link = []
            for i in range(0, 3):  # 4 SlimLinks
                self.slim_link.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/fs_links/{i:03}",
                    )
                )

        def wait_timeout_dev(
            self: TestProxies,
            proxy_list: list[context.DeviceProxy],
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
            proxy_list: list[context.DeviceProxy],
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
                    proxy.On()
                    self.wait_timeout_dev(
                        [proxy], DevState.ON, wait_time_s, sleep_time_s_long
                    )

                if proxy.obsState != ObsState.EMPTY:
                    if proxy.obsState not in [
                        ObsState.FAULT,
                        ObsState.ABORTED,
                    ]:
                        proxy.Abort()
                        self.wait_timeout_obs(
                            [proxy],
                            ObsState.ABORTED,
                            wait_time_s,
                            sleep_time_s_short,
                        )

                    proxy.Restart()
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

            # Run InitSysParam command before turning on the MCS
            data_file_path = (
                os.path.dirname(os.path.abspath(__file__)) + "/data/"
            )
            with open(data_file_path + "sys_param_4_boards.json") as f:
                sp = f.read()
            self.controller.InitSysParam(sp)

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

            self.controller.adminMode = AdminMode.OFFLINE
            self.wait_timeout_dev(
                [self.controller], DevState.DISABLE, wait_time_s, sleep_time_s
            )

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

