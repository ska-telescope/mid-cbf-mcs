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

import pytest
import time

# Tango imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, SimulationMode
from tango import DevState


@pytest.mark.usefixtures("test_proxies")
class TestTalonBoard:
    """
    Test class for TalonBoard device class integration testing.
    """

    def test_Connect(self, test_proxies):
        """
        Test the initial states and verify the component manager
        can start communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # after init devices should be in DISABLE state
        assert test_proxies.talon_board.State() == DevState.DISABLE

        # trigger start_communicating by setting the AdminMode to ONLINE
        test_proxies.talon_board.adminMode = AdminMode.ONLINE

        # controller device should be in OFF state after start_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.talon_board], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.talon_board.State() == DevState.OFF

    def test_On(self, test_proxies):
        """
        Test the "On" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # send the On command
        test_proxies.talon_board.On()

        test_proxies.wait_timeout_dev(
            [test_proxies.talon_board], DevState.ON, wait_time_s, sleep_time_s
        )
        assert test_proxies.talon_board.State() == DevState.ON
        
        # Turn on Simulation Mode
        test_proxies.talon_board.simulationMode = SimulationMode.TRUE
        assert test_proxies.talon_board.simulationMode == SimulationMode.TRUE
        
    
    def test_FPGA_Die_Voltage_Readings(self, test_proxies):
        """
        Test reading the 7 FPGA Die Voltage Attributes
        See talon_board_simulator.py for the values expected
        """

        # There seems to be some delay with callbacks to turn on SimulationMode on the Component Manager
        time.sleep(5)
        assert test_proxies.talon_board.FpgaDieVoltage0 == 12.0
        assert test_proxies.talon_board.FpgaDieVoltage1 == 2.5
        assert test_proxies.talon_board.FpgaDieVoltage2 == 0.87
        assert test_proxies.talon_board.FpgaDieVoltage3 == 1.8
        assert test_proxies.talon_board.FpgaDieVoltage4 == 1.8
        assert test_proxies.talon_board.FpgaDieVoltage5 == 0.9
        assert test_proxies.talon_board.FpgaDieVoltage6 == 1.8

    def test_Off(self, test_proxies):
        """
        Test the "Off" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # if controller is already off, we must turn it On before turning off.
        if test_proxies.talon_board.State() == DevState.OFF:
            test_proxies.talon_board.On()
            test_proxies.wait_timeout_dev(
                [test_proxies.talon_board],
                DevState.ON,
                wait_time_s,
                sleep_time_s,
            )

        assert test_proxies.talon_board.State() == DevState.ON
        # send the Off command
        test_proxies.talon_board.Off()

        test_proxies.wait_timeout_dev(
            [test_proxies.talon_board], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.talon_board.State() == DevState.OFF

    def test_Disconnect(self, test_proxies):
        """
        Verify the component manager can stop communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        test_proxies.talon_board.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.talon_board],
            DevState.DISABLE,
            wait_time_s,
            sleep_time_s,
        )
