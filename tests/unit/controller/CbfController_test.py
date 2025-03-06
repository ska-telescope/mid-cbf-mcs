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
from assertpy import assert_that
from ska_control_model import AdminMode, SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_tdc_mcs.controller.controller_device import CbfController

from ... import test_utils

# Paths
file_path = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Disable garbage collection to prevent tests hanging
gc.disable()


class TestCbfController:
    """
    Test class for CbfController.
    """

    @pytest.fixture(name="test_context", scope="function")
    def cbf_controller_test_context(
        self: TestCbfController,
        initial_mocks: dict[str, Mock],
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that creates a test context for the CbfController.

        :param initial_mocks: A dictionary of device mocks to be added to the test context.
        :return: A test context for the CbfController.
        """
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
                "mid_csp_cbf/fsp/05",
                "mid_csp_cbf/fsp/06",
                "mid_csp_cbf/fsp/07",
                "mid_csp_cbf/fsp/08",
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
            FsSLIMConfigPath="mnt/slim/fs/slim_config.yaml",
            VisSLIMConfigPath="mnt/slim/vis/slim_config.yaml",
            LRCTimeout="30",
            MaxCapabilities=["VCC:8", "FSP:8", "Subarray:1"],
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock(name))

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestCbfController, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestCbfController, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestCbfController, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_Online(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test that the devState is appropriately set after device startup.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="adminMode",
            attribute_value=AdminMode.ONLINE,
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.OFF,
        )

    @pytest.mark.parametrize(
        "sys_param_file_path",
        [
            "sys_param_4_boards.json",
            "sys_param_dup_dishid.json",
            # Test using tm_data_sources params
            "source_init_sys_param.json",
            "source_init_sys_param_invalid_source.json",
            "source_init_sys_param_invalid_file.json",
        ],
    )
    def test_InitSysParam(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        sys_param_file_path: str,
    ) -> None:
        """
        Test InitSysParam and failure cases.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param sys_param_file_path: The path to the sys_param file to be used
        """
        self.test_Online(device_under_test, event_tracer)

        with open(json_file_path + sys_param_file_path) as f:
            sp = f.read()
        result_code, command_id = device_under_test.InitSysParam(sp)
        assert result_code == [ResultCode.QUEUED]

        if (
            sys_param_file_path == "sys_param_4_boards.json"
            or sys_param_file_path == "source_init_sys_param.json"
        ):
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{command_id[0]}",
                    '[0, "InitSysParam completed OK"]',
                ),
            )
        elif (
            sys_param_file_path == "source_init_sys_param_invalid_source.json"
            or sys_param_file_path == "source_init_sys_param_invalid_file.json"
        ):
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{command_id[0]}",
                    '[3, "Retrieving the init_sys_param file failed"]',
                ),
            )
        elif sys_param_file_path == "sys_param_dup_dishid.json":
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{command_id[0]}",
                    '[3, "Duplicated Dish ID in the init_sys_param json"]',
                ),
            )

    def test_On_without_init_sys_param(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test On without InitSysParam.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    def test_Commands_all(
        self: TestCbfController,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test all of CbfController's commands, expect success.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        # Establish communication
        # TODO: mock talon configuration to test with sim mode FALSE
        # device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="adminMode",
            attribute_value=AdminMode.ONLINE,
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.OFF,
        )

        with open(json_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        command_dict["InitSysParam"] = device_under_test.InitSysParam(sp)
        command_dict["On"] = device_under_test.On()
        command_dict["Off"] = device_under_test.Off()

        attr_values = [
            ("state", DevState.ON, DevState.OFF, 1),
            ("state", DevState.OFF, DevState.ON, 1),
        ]

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )
