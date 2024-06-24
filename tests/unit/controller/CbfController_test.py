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
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.controller.controller_device import CbfController

# Paths
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
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        harness = context.ThreadedTestTangoContextManager()
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
        "sys_param_file_path",
        [
            "sys_param_4_boards.json",
            "sys_param_dup_vcc.json",
            "sys_param_invalid_rec_id.json",
            "sys_param_dup_dishid.json",
            # test using tm_data_sources params
            "source_init_sys_param.json",
            "source_init_sys_param_invalid_source.json",
            "source_init_sys_param_invalid_file.json",
            "source_init_sys_param_invalid_schema.json",
        ],
    )
    def test_InitSysParam(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        sys_param_file_path: str,
    ) -> None:
        """
        Test InitSysParam and failure cases.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        change_event_callbacks["state"].assert_change_event(DevState.OFF)

        with open(json_file_path + sys_param_file_path) as f:
            sp = f.read()
        result_code, command_id = device_under_test.InitSysParam(sp)
        assert result_code == [ResultCode.QUEUED]

        if (
            sys_param_file_path == "sys_param_4_boards.json"
            or sys_param_file_path == "source_init_sys_param.json"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "InitSysParam completed OK"]')
            )
        elif (
            sys_param_file_path == "source_init_sys_param_invalid_source.json"
            or sys_param_file_path == "source_init_sys_param_invalid_file.json"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    '[3, "Retrieving the init_sys_param file failed"]',
                )
            )
        elif sys_param_file_path == "sys_param_dup_dishid.json":
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    '[3, "Duplicated Dish ID in the init_sys_param json"]',
                )
            )
        elif (
            sys_param_file_path == "source_init_sys_param_invalid_schema.json"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    '[3, "Validating init_sys_param file retrieved from tm_data_filepath against ska-telmodel schema failed"]',
                )
            )
        else:
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    '[3, "Validating init_sys_param file against ska-telmodel schema failed"]',
                )
            )
        change_event_callbacks.assert_not_called()

    def test_On_without_init_sys_param(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test On without InitSysParam.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        change_event_callbacks["state"].assert_change_event(DevState.OFF)

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            )
        )
        change_event_callbacks.assert_not_called()

    def test_Commands_all(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test all of CbfController's commands, expect success.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        # Establish communication
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        change_event_callbacks["state"].assert_change_event(DevState.OFF)

        with open(json_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        result_code, command_id = device_under_test.InitSysParam(sp)
        assert result_code == [ResultCode.QUEUED]
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "InitSysParam completed OK"]')
        )

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "On completed OK"]')
        )
        change_event_callbacks["state"].assert_change_event(DevState.ON)

        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "Off completed OK"]')
        )
        change_event_callbacks["state"].assert_change_event(DevState.OFF)
        change_event_callbacks.assert_not_called()
