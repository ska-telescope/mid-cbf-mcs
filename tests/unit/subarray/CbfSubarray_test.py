#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfSubarray."""

from __future__ import annotations

import gc
import json
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_control_model import AdminMode, ObsState, ResultCode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.subarray.subarray_device import CbfSubarray

from ...test_utils import device_online_and_on

# Data file path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Disable garbage collection to prevent tests hanging
gc.disable()


class TestCbfSubarray:
    """
    Test class for TestCbfSubarray tests.
    """

    @pytest.fixture(name="test_context")
    def subarray_test_context(
        self: TestCbfSubarray, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/sub_elt/subarray_01",
            device_class=CbfSubarray,
            CbfControllerAddress="mid_csp_cbf/sub_elt/controller",
            VCC=[
                "mid_csp_cbf/vcc/001",
                "mid_csp_cbf/vcc/002",
                "mid_csp_cbf/vcc/003",
                "mid_csp_cbf/vcc/004",
            ],
            FSP=[
                "mid_csp_cbf/fsp/01",
                "mid_csp_cbf/fsp/02",
                "mid_csp_cbf/fsp/03",
                "mid_csp_cbf/fsp/04",
            ],
            FspCorrSubarray=[
                "mid_csp_cbf/fspCorrSubarray/01_01",
                "mid_csp_cbf/fspCorrSubarray/02_01",
                "mid_csp_cbf/fspCorrSubarray/03_01",
                "mid_csp_cbf/fspCorrSubarray/04_01",
            ],
            TalonBoard=[
                "mid_csp_cbf/talon_board/001",
                "mid_csp_cbf/talon_board/002",
                "mid_csp_cbf/talon_board/003",
                "mid_csp_cbf/talon_board/004",
            ],
            DeviceID="1",
        )
        for name, mock in initial_mocks.items():
            # subarray requires unique VCC mocks to be generated
            if "mid_csp_cbf/vcc/" in name:
                harness.add_mock_device(device_name=name, device_mock=mock())
            else:
                harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestCbfSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestCbfSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestCbfSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        command: str,
    ) -> None:
        """
        Test the On/Off/Standby commands
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param command: the command to test (one of On/Off/Standby)
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF

        if command == "On":
            expected_result = ResultCode.OK
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            expected_result = ResultCode.REJECTED
            expected_state = DevState.OFF
            result = device_under_test.Off()
        elif command == "Standby":
            expected_result = ResultCode.REJECTED
            expected_state = DevState.OFF
            result = device_under_test.Standby()

        assert result[0][0] == expected_result
        assert device_under_test.State() == expected_state

    @pytest.mark.parametrize(
        "receptors, \
        remove_all, \
        receptors_to_remove",
        [
            (
                ["SKA001", "SKA063", "SKA100", "SKA036"],
                False,
                ["SKA063", "SKA036", "SKA001"],
            ),
            (["SKA100", "SKA036", "SKA001"], False, ["SKA036", "SKA100"]),
            (["SKA100", "SKA036", "SKA001"], True, []),
        ],
    )
    def test_Add_Remove_Receptors_valid(
        self: TestCbfSubarray,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        receptors: list[str],
        remove_all: bool,
        receptors_to_remove: list[str],
    ) -> None:
        """
        Test valid use of Add/RemoveReceptors command.

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param receptors: list of DISH IDs to assign to subarray
        :param remove_all: False to use RemoveReceptors, True for RemoveAllReceptors
        :param receptors_to_remove: list of DISH IDs to remove from subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param
        assert device_under_test.sysParam == sys_param

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # add receptors in 2 stages
        curr_rec = set()
        for input_rec in [receptors[:-1], receptors[-1:]]:
            (return_value, command_id) = device_under_test.AddReceptors(
                input_rec
            )

            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
                )
            )

            # check obsState transitions
            for obs_state in [
                ObsState.RESOURCING,
                ObsState.IDLE,
            ]:
                change_event_callbacks["obsState"].assert_change_event(
                    obs_state.value
                )

            # assert receptors attribute updated
            curr_rec.update(input_rec)
            receptors_push_val = list(curr_rec.copy())
            receptors_push_val.sort()
            change_event_callbacks["receptors"].assert_change_event(
                attribute_value=tuple(receptors_push_val)
            )

        if remove_all:
            (return_value, command_id) = device_under_test.RemoveAllReceptors()

            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
                )
            )
        else:
            # remove receptors in 2 stages
            for input_rec in [
                receptors_to_remove[:-1],
                receptors_to_remove[-1:],
            ]:
                (return_value, command_id) = device_under_test.RemoveReceptors(
                    input_rec
                )

                # check that the command was successfully queued
                assert return_value[0] == ResultCode.QUEUED

                # check that the queued command succeeded
                change_event_callbacks[
                    "longRunningCommandResult"
                ].assert_change_event(
                    (
                        f"{command_id[0]}",
                        f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
                    )
                )

                # check obsState transitions
                for obs_state in [
                    ObsState.RESOURCING,
                    ObsState.IDLE,
                ]:
                    change_event_callbacks["obsState"].assert_change_event(
                        obs_state.value
                    )

                # assert receptors attribute updated
                curr_rec.difference_update(input_rec)
                receptors_push_val = list(curr_rec.copy())
                receptors_push_val.sort()
                change_event_callbacks["receptors"].assert_change_event(
                    attribute_value=tuple(receptors_push_val)
                )

            # remove remaining receptor
            (return_value, command_id) = device_under_test.RemoveReceptors(
                list(curr_rec)
            )

            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
                )
            )

        # check obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.EMPTY,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert receptors attribute updated
        change_event_callbacks["receptors"].assert_change_event(
            attribute_value=()
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "invalid_receptor",
        [["SKA200"], ["MKT100"]],
    )
    def test_AddReceptors_invalid(
        self: TestCbfSubarray,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        invalid_receptor: list[str],
    ) -> None:
        """
        Test invalid use of AddReceptors commands when a receptor ID is out of
        valid range.

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param invalid_receptor: invalid DISH ID
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param
        assert device_under_test.sysParam == sys_param

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # add receptors
        (return_value, command_id) = device_under_test.AddReceptors(
            invalid_receptor
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command failed
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f"[{ResultCode.FAILED.value}, "
                + f'"DISH ID {invalid_receptor[0]} is not valid. '
                + "It must be SKA001-SKA133 or MKT000-MKT063. "
                + 'Spaces before, after, or in the middle of the ID are not accepted."]',
            )
        )

        # check obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.EMPTY,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert if any captured events have gone unaddressed
        # we should not have gotten a change event from the receptors attribute
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "receptors, \
        unassigned_receptors",
        [
            (["SKA036", "SKA063"], ["SKA100"]),
            (["SKA100", "SKA001"], ["SKA063", "SKA036"]),
        ],
    )
    def test_RemoveReceptors_not_assigned(
        self: TestCbfSubarray,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        receptors: list[str],
        unassigned_receptors: list[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors command when a receptor to be removed
        is not assigned to the subarray.

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param receptors: list of DISH IDs to assign to subarray
        :param unassigned_receptors: unassigned DISH IDs
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param
        assert device_under_test.sysParam == sys_param

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # add receptors
        (return_value, command_id) = device_under_test.AddReceptors(receptors)

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command succeeded
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
            )
        )

        # check obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert receptors attribute updated
        receptors.sort()
        change_event_callbacks["receptors"].assert_change_event(
            attribute_value=tuple(receptors)
        )

        # try removing a receptor not assigned to subarray
        (return_value, command_id) = device_under_test.RemoveReceptors(
            unassigned_receptors
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command succeeded
        # unassigned receptors will raise warning logs, but will not fail command
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
            )
        )

        # check obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert if any captured events have gone unaddressed
        # we should not have gotten a change event from the receptors attribute
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "receptors, \
        invalid_receptor",
        [
            (["SKA036", "SKA063"], ["SKA000"]),
            (["SKA100", "SKA001"], [" MKT163"]),
        ],
    )
    def test_RemoveReceptors_invalid(
        self: TestCbfSubarray,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        receptors: list[str],
        invalid_receptor: list[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors command when a receptor ID to be removed
        is not in valid range.

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param receptors: list of DISH IDs to assign to subarray
        :param invalid_receptor: invalid DISH ID
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param
        assert device_under_test.sysParam == sys_param

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # add receptors
        (return_value, command_id) = device_under_test.AddReceptors(receptors)

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command succeeded
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
            )
        )

        # check obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert receptors attribute updated
        receptors.sort()
        change_event_callbacks["receptors"].assert_change_event(
            attribute_value=tuple(receptors)
        )

        # try to remove invalid receptors
        (return_value, command_id) = device_under_test.RemoveReceptors(
            invalid_receptor
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command failed
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f"[{ResultCode.FAILED.value}, "
                + f'"DISH ID {invalid_receptor[0]} is not valid. '
                + "It must be SKA001-SKA133 or MKT000-MKT063. "
                + 'Spaces before, after, or in the middle of the ID are not accepted."]',
            )
        )

        # check obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert if any captured events have gone unaddressed
        # we should not have gotten a change event from the receptors attribute
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "receptors",
        [["SKA036", "SKA063"], ["SKA100", "SKA001"]],
    )
    def test_RemoveAllReceptors_invalid(
        self: TestCbfSubarray,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        receptors: list[str],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands, when, subarray is in ObsState.EMPTY

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param receptors: list of DISH IDs to remove from subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param
        assert device_under_test.sysParam == sys_param

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # try to remove receptors
        (return_value, command_id) = device_under_test.RemoveReceptors(
            receptors
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command failed
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
            )
        )

        # try to remove allreceptors
        (return_value, command_id) = device_under_test.RemoveAllReceptors()

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # check that the queued command failed
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
            )
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "config_file_name, receptors, scan_file_name",
        [("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan1_basic.json")],
    )
    def test_Scan(
        self: TestCbfSubarray,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        config_file_name: str,
        receptors: list[int],
        scan_file_name: str,
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param config_file_name: JSON file for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        :param scan_file_name: JSON file for the scan ID
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            config_str = f.read().replace("\n", "")
            configuration = json.loads(config_str)
        with open(test_data_path + scan_file_name) as f:
            scan_str = f.read().replace("\n", "")
            scan = json.loads(scan_str)

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param
        assert device_under_test.sysParam == sys_param

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # add receptors
        command_dict["AddReceptors"] = device_under_test.AddReceptors(
            receptors
        )
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            config_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_str)

        change_event_callbacks.assert_not_called()
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.RESOURCING,
            ObsState.IDLE,
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert receptors attribute updated
        receptors.sort()
        change_event_callbacks["receptors"].assert_change_event(
            attribute_value=tuple(receptors)
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA063", "SKA100", "SKA036"],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA100", "SKA001", "SKA036", "SKA063"],
    #         ),
    #     ],
    # )
    # def test_Scan(
    #     self: TestCbfSubarray,
    #     device_under_test: context.DeviceProxy,
    #     config_file_name: str,
    #     scan_file_name: str,
    #     receptors: List[int],
    # ) -> None:
    #     """
    #     Test the Scan command
    #     """
    #     self.test_ConfigureScan_basic(
    #         device_under_test, config_file_name, receptors
    #     )

    #     # scan command is only allowed in op state ON
    #     device_under_test.On()
    #     sleep(CONST_WAIT_TIME)
    #     assert device_under_test.State() == DevState.ON

    #     # send the Scan command
    #     f = open(test_data_path + scan_file_name)
    #     device_under_test.Scan(f.read().replace("\n", ""))
    #     f.close()

    #     assert device_under_test.obsState == ObsState.SCANNING

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA063", "SKA100", "SKA036"],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA100", "SKA001", "SKA036", "SKA063"],
    #         ),
    #     ],
    # )
    # def test_EndScan(
    #     self: TestCbfSubarray,
    #     device_under_test: context.DeviceProxy,
    #     config_file_name: str,
    #     scan_file_name: str,
    #     receptors: List[int],
    # ) -> None:
    #     """
    #     Test the EndScan command
    #     """
    #     self.test_Scan(
    #         device_under_test, config_file_name, scan_file_name, receptors
    #     )

    #     # send the EndScan command
    #     device_under_test.EndScan()

    #     assert device_under_test.obsState == ObsState.READY

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA063", "SKA100", "SKA036"],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA100", "SKA001", "SKA036", "SKA063"],
    #         ),
    #     ],
    # )
    # def test_Abort(
    #     self: TestCbfSubarray,
    #     device_under_test: context.DeviceProxy,
    #     config_file_name: str,
    #     scan_file_name: str,
    #     receptors: List[int],
    # ) -> None:
    #     """
    #     Test the Abort command
    #     """
    #     self.test_Scan(
    #         device_under_test, config_file_name, scan_file_name, receptors
    #     )

    #     # send the Abort command
    #     device_under_test.Abort()

    #     assert device_under_test.obsState == ObsState.ABORTED

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA063", "SKA100", "SKA036"],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA100", "SKA001", "SKA036", "SKA063"],
    #         ),
    #     ],
    # )
    # def test_ObsReset(
    #     self: TestCbfSubarray,
    #     device_under_test: context.DeviceProxy,
    #     config_file_name: str,
    #     scan_file_name: str,
    #     receptors: List[int],
    # ) -> None:
    #     """
    #     Test the ObsReset command
    #     """
    #     self.test_Abort(
    #         device_under_test, config_file_name, scan_file_name, receptors
    #     )

    #     # send the ObsReset command
    #     device_under_test.ObsReset()

    #     assert device_under_test.obsState == ObsState.IDLE

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA063", "SKA100", "SKA036"],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA100", "SKA001", "SKA036", "SKA063"],
    #         ),
    #     ],
    # )
    # def test_Restart(
    #     self: TestCbfSubarray,
    #     device_under_test: context.DeviceProxy,
    #     config_file_name: str,
    #     scan_file_name: str,
    #     receptors: List[int],
    # ) -> None:
    #     """
    #     Test the Restart command
    #     """
    #     self.test_Abort(
    #         device_under_test, config_file_name, scan_file_name, receptors
    #     )

    #     # send the Restart command
    #     device_under_test.Restart()

    #     assert device_under_test.obsState == ObsState.EMPTY

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             ["SKA001", "SKA063", "SKA100", "SKA036"],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             ["SKA100", "SKA001", "SKA036", "SKA063"],
    #         ),
    #     ],
    # )
    # def test_GoToIdle(
    #     self: TestCbfSubarray,
    #     device_under_test: context.DeviceProxy,
    #     config_file_name: str,
    #     receptors: List[int],
    # ) -> None:
    #     # End the scan block.
    #     self.test_ConfigureScan_basic(
    #         device_under_test, config_file_name, receptors
    #     )

    #     # end command is only permitted in Op state ON
    #     device_under_test.On()
    #     assert device_under_test.State() == DevState.ON

    #     device_under_test.GoToIdle()

    #     assert device_under_test.obsState == ObsState.IDLE
