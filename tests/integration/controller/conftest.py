# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS Controller integration tests."""

from __future__ import annotations

import json

import pytest

# Tango imports
from ska_control_model import SimulationMode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils

from ... import test_utils


@pytest.fixture(name="device_under_test")
def device_under_test_fixture() -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :return: the device under test
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/sub_elt/controller")


@pytest.fixture(name="test_proxies")
def test_proxies_fixture() -> pytest.fixture:
    """
    Fixture that returns the device proxies required for this scope.

    :return: a TestProxies object containing device proxies to all devices required in this module's scope of integration testing
    """

    class TestProxies:
        def __init__(self: TestProxies) -> None:
            """
            Initialize all device proxies needed for integration testing the DUT.

            Includes:
            - 1 CbfSubarray
            - 1 TalonBoard
            - 4 Fsp
            - 8 Vcc
            - 1 Slim
            - 4 SlimLink
            """
            # NOTE: set debug_device_is_on to True in order
            #       to allow device debugging under VScode
            #       by increasing the timeout_millis
            self.debug_device_is_on = False
            timeout_millis = 500000 if self.debug_device_is_on else 60000

            with open(f"tests/data/sys_param_4_boards.json", "r") as json_file:
                sys_param = json.load(json_file)
            self.dish_utils = DISHUtils(sys_param)

            # TmCspSubarrayLeafNodeTest
            self.tm = context.DeviceProxy(
                device_name="ska_mid/tm_leaf_node/csp_subarray_01"
            )

            # TODO: Move MaxCapabilities out and remove redundant controller
            self.controller = context.DeviceProxy(
                device_name="mid_csp_cbf/sub_elt/controller",
            )
            # Max Capabilities
            self.max_capabilities = dict(
                pair.split(":")
                for pair in self.controller.get_property("MaxCapabilities")[
                    "MaxCapabilities"
                ]
            )
            self.num_sub = int(self.max_capabilities["Subarray"])
            self.num_fsp = int(self.max_capabilities["FSP"])
            self.num_vcc = int(self.max_capabilities["VCC"])

            # TalonBoard : single board is enough for integration testing
            self.talon_board = context.DeviceProxy(
                device_name="mid_csp_cbf/talon_board/001",
            )
            self.talon_board.set_timeout_millis(timeout_millis)

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

            # Fsp : index == fspID
            self.fsp = [None]
            for proxy in [
                context.DeviceProxy(device_name=f"mid_csp_cbf/fsp/{j:02}")
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fsp.append(proxy)

            # Currently support for just one subarray, CORR/PSS-BF/PST-BF only
            # fspSubarray[function mode (str)][subarray id (int)][fsp id (int)]
            self.fspSubarray = {
                "CORR": {1: [None]},
                "PSS-BF": {1: [None]},
                "PST-BF": {1: [None]},
            }

            for proxy in [
                context.DeviceProxy(
                    device_name=f"mid_csp_cbf/fspCorrSubarray/{j:02}_01",
                )
                for j in range(1, self.num_fsp + 1)
            ]:
                self.fspSubarray["CORR"][1].append(proxy)

            # for proxy in [
            #     context.DeviceProxy(
            #         device_name=f"mid_csp_cbf/fspPssSubarray/{j:02}_01",
            #     )
            #     for j in range(1, self.num_fsp + 1)
            # ]:
            #     self.fspSubarray["PSS-BF"][1].append(proxy)

            # for proxy in [
            #     context.DeviceProxy(
            #         device_name=f"mid_csp_cbf/fspPstSubarray/{j:02}_01",
            #     )
            #     for j in range(1, self.num_fsp + 1)
            # ]:
            #     self.fspSubarray["PST-BF"][1].append(proxy)

            # Vcc : index == vccID
            self.vcc = [None]
            for proxy in [
                context.DeviceProxy(device_name=f"mid_csp_cbf/vcc/{i:03}")
                for i in range(1, self.num_vcc + 1)
            ]:
                self.vcc.append(proxy)

            # self.vccSw = [None]
            # for i in range(1, self.num_vcc + 1):
            #     sw = [None]
            #     for j in range(1, 3):  # 2 search windows
            #         sw.append(
            #             context.DeviceProxy(
            #                 device_name=f"mid_csp_cbf/vcc_sw{j}/{i:03}",
            #             )
            #         )
            #     self.vccSw.append(sw)

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

    return TestProxies()


@pytest.fixture(name="change_event_callbacks")
def controller_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    """
    Fixture that returns the device under test's change event callback group.

    :param device_under_test: the device whose change events will be subscribed to.
    :return: the change event callback object
    """
    change_event_attr_list = [
        "longRunningCommandResult",
        "State",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks
