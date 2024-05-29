#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the CbfController."""

from __future__ import annotations

import gc
import os
import time
import unittest
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevFailed, DevState

from ska_mid_cbf_mcs.controller.controller_device import CbfController
from ska_mid_cbf_mcs.testing import context

CONST_WAIT_TIME = 4

# Path
file_path = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# To prevent tests hanging during gc.
gc.disable()


class TestCbfController:
    """
    Test class for CbfController tests.
    """

    @pytest.fixture(name="test_context", scope="function")
    def cbf_controller_test_context(
        self: TestCbfController,
        initial_device_mocks: dict[str, Mock],
        initial_group_mocks: dict[str, Mock],
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        harness.add_device(
            device_class=CbfController,
            device_name="mid_csp_cbf/cbf_controller/001",
            CbfSubarray=[
                "mid_csp_cbf/sub_elt/subarray_01",
                "mid_csp_cbf/sub_elt/subarray_02",
                "mid_csp_cbf/sub_elt/subarray_03",
            ],
            VCC=[
                "mid_csp_cbf/vcc/001",
                "mid_csp_cbf/vcc/002",
                "mid_csp_cbf/vcc/003",
                "mid_csp_cbf/vcc/004",
                "mid_csp_cbf/vcc/005",
                "mid_csp_cbf/vcc/006",
                "mid_csp_cbf/vcc/007",
                "mid_csp_cbf/vcc/008",
            ],
            FSP=[
                "mid_csp_cbf/fsp/01",
                "mid_csp_cbf/fsp/02",
                "mid_csp_cbf/fsp/03",
                "mid_csp_cbf/fsp/04",
            ],
            TalonLRU=[
                "mid_csp_cbf/talon_lru/001",
                "mid_csp_cbf/talon_lru/002",
                "mid_csp_cbf/talon_lru/003",
                "mid_csp_cbf/talon_lru/004",
            ],
            TalonBoard=[
                "mid_csp_cbf/talon_board/001",
                "mid_csp_cbf/talon_board/002",
                "mid_csp_cbf/talon_board/003",
                "mid_csp_cbf/talon_board/004",
                "mid_csp_cbf/talon_board/005",
                "mid_csp_cbf/talon_board/006",
                "mid_csp_cbf/talon_board/007",
                "mid_csp_cbf/talon_board/008",
            ],
            PowerSwitch=[
                "mid_csp_cbf/power_switch/001",
                "mid_csp_cbf/power_switch/002",
            ],
            FsSLIM="mid_csp_cbf/slim/slim-fs",
            VisSLIM="mid_csp_cbf/slim/slim-vis",
            TalonDxConfigPath="mnt/talondx-config",
            HWConfigPath="mnt/hw_config/hw_config.yaml",
            FsSLIMConfigPath="mnt/slim/fs_slim_config.yaml",
            VisSLIMConfigPath="mnt/slim/vis_slim_config.yaml",
            LruTimeout="30",
            MaxCapabilities=["VCC:8", "FSP:4", "Subarray:1"],
        )

        for name, mock in initial_device_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        for name, mock in initial_group_mocks.items():
            harness.add_mock_group(group_name=name, group_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestCbfController, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestCbfController, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestCbfController, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test adminMode

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize(
        "command",
        ["On"],
        # ["On", "Off", "Standby", "InitSysParam", "SourceInitSysParam"],
    )
    def test_Commands(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        command: str,
    ) -> None:
        """
        Test each of CbfController's commands.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF

        if command == "On":
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            # Off cannot be called from OFF state so On must be called first.
            device_under_test.On()
            time.sleep(CONST_WAIT_TIME)
            assert device_under_test.State() == DevState.ON
            expected_state = DevState.OFF
            result = device_under_test.Off()
        elif command == "Standby":
            expected_state = DevState.STANDBY
            result = device_under_test.Standby()
        elif command == "InitSysParam":
            expected_state = device_under_test.State()  # no change expected
            with open(json_file_path + "sys_param_4_boards.json") as f:
                sp = f.read()
            result = device_under_test.InitSysParam(sp)
        elif command == "SourceInitSysParam":
            expected_state = device_under_test.State()  # no change expected
            with open(json_file_path + "source_init_sys_param.json") as f:
                sp = f.read()
            result = device_under_test.InitSysParam(sp)

        time.sleep(CONST_WAIT_TIME)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state

    # @pytest.mark.parametrize(
    #     "command",
    #     ["On", "Off"],
    # )
    # def test_CommandsFail(
    #     self: TestCbfController,
    #     device_under_test: context.DeviceProxy,
    #     command: str,
    # ) -> None:
    #     """
    #     Test On/Off commands from dissallowed states.

    #     :param device_under_test: fixture that provides a
    #         :py:class:`CbfDeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     """

    #     device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
    #     assert device_under_test.adminMode == AdminMode.ONLINE

    #     assert device_under_test.State() == DevState.OFF

    #     if command == "On":
    #         # On is not allowed when controller is already on, so it must be called twice for this test.
    #         device_under_test.On()
    #         assert device_under_test.State() == DevState.ON
    #         expected_state = DevState.ON
    #         with pytest.raises(
    #             DevFailed,
    #             match="Command On not allowed when the device is in ON state",
    #         ):
    #             device_under_test.On()
    #     elif command == "Off":
    #         expected_state = DevState.OFF
    #         with pytest.raises(
    #             DevFailed,
    #             match="Command Off not allowed when the device is in OFF state",
    #         ):
    #             device_under_test.Off()

    #     assert device_under_test.State() == expected_state
