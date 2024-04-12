#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Slim."""

from __future__ import annotations

# Standard imports
import os
import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, SimulationMode
from tango import DevState
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
import tango
from ... import test_utils

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports

CONST_WAIT_TIME = 1


class TestSlim:
    """
    Test class for SLIM tests.
    """

    def test_State(self: TestSlim, device_under_test: CbfDeviceProxy) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(self: TestSlim, device_under_test: CbfDeviceProxy) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestSlim, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_adminModeOnline(
        self: TestSlim,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        # time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF
        
    def test_On(
        self: TestSlim,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        device_under_test.On()
        
        assert device_under_test.State() == DevState.ON

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_Configure(
        self: TestSlim,
        device_under_test: tango.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """
        # Put the device in simulation mode
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.adminMode = AdminMode.ONLINE

        change_event_attr_list = [
            "longRunningCommandResult",
            "longRunningCommandProgress",
        ]
        attr_event_ids = test_utils.change_event_subscriber(
            device_under_test, change_event_callbacks, change_event_attr_list
        )
        
        device_under_test.On()
        time.sleep(CONST_WAIT_TIME)
        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test.Configure(mesh_config.read())

        assert result_code == [ResultCode.QUEUED]
        for progress_point in (25,50,100):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", {progress_point}))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[0, "Configured SLIM successfully"]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        test_utils.change_event_unsubscriber(device_under_test, attr_event_ids)
        
    def test_Off(
        self: TestSlim,
        device_under_test: tango.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Off() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """
        # Put the device in simulation mode
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.adminMode = AdminMode.ONLINE

        change_event_attr_list = [
            "longRunningCommandResult",
            "longRunningCommandProgress",
        ]
        attr_event_ids = test_utils.change_event_subscriber(
            device_under_test, change_event_callbacks, change_event_attr_list
        )
        
        device_under_test.On()
        time.sleep(CONST_WAIT_TIME)
        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test.Configure(mesh_config.read())

        assert result_code == [ResultCode.QUEUED]
        for progress_point in (25,50,100):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", {progress_point}))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[0, "Configured SLIM successfully"]',
            )
        )
        
        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]
        
        for progress_point in (50,100):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", {progress_point}))
        
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[0, "SLIM shutdown successfully"]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        test_utils.change_event_unsubscriber(device_under_test, attr_event_ids)