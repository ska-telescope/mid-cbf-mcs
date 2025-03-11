#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the TalonBoard."""
from __future__ import annotations

from ska_control_model import LoggingLevel
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, SimulationMode

# Tango imports
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState


class TestTalonBoard:
    """
    Test class for TalonBoard device class integration testing.
    """

    def test_Online(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating
        """
        # after init devices should be in DISABLE state, but just in case...
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.loggingLevel = LoggingLevel.DEBUG

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

    def test_On(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "On" command
        """
        # send the On command
        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "On completed OK"]',
            )
        )

        change_event_callbacks["State"].assert_change_event(DevState.ON)

    def test_FPGA_Die_Temperature_Read(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test reading the FPGA Die Temperature Attributes
        See talon_board_simulator.py for the values expected
        """
        assert device_under_test.fpgaDieTemperature == 50.0

    def test_FPGA_Die_Voltage_Read(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test reading the 7 FPGA Die Voltage Attributes
        See talon_board_simulator.py for the values expected
        """
        assert device_under_test.fpgaDieVoltage0 == 12.0
        assert device_under_test.fpgaDieVoltage1 == 2.5
        assert device_under_test.fpgaDieVoltage2 == 0.87
        assert device_under_test.fpgaDieVoltage3 == 1.8
        assert device_under_test.fpgaDieVoltage4 == 1.8
        assert device_under_test.fpgaDieVoltage5 == 0.9
        assert device_under_test.fpgaDieVoltage6 == 1.8

    def test_Off(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "Off" command
        """
        # if controller is already off, we must turn it On before turning off.
        if device_under_test.State() == DevState.OFF:
            self.test_On(device_under_test, change_event_callbacks)

        # send the Off command
        result_code, message = device_under_test.Off()
        assert result_code == [ResultCode.OK]
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

    def test_Offline(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Verify the component manager can stop communicating
        """
        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE
        change_event_callbacks["State"].assert_change_event(DevState.DISABLE)
