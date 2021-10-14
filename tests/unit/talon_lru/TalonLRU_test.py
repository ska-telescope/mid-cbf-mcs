#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the TalonLRU device."""

# Standard imports
import pytest
from ska_mid_cbf_mcs.commons.global_enum import PowerMode

# Tango imports
from tango import DevState

# Local imports
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

def test_startup_state(
    tango_harness: TangoHarness,
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the state of the TalonLRU device when it starts up is correct.
    """
    mock_power_switch1 = tango_harness.get_device("mid_csp_cbf/power_switch/001")
    mock_power_switch2 = tango_harness.get_device("mid_csp_cbf/power_switch/002")

    # Check the device state and PDU1PowerMode based on mock_power_switch1 behaviour
    power_switch1_valid = False
    if mock_power_switch1.stimulusMode == "conn_fail":
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU1PowerMode == PowerMode.UNKNOWN
    elif mock_power_switch1.stimulusMode == "invalid_start_state":
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU1PowerMode == mock_power_switch1.GetOutletPowerMode()
    else:
        assert device_under_test.PDU1PowerMode == PowerMode.OFF
        power_switch1_valid = True
    
    # Check the device state and PDU2PowerMode based on mock_power_switch2 behaviour
    power_switch2_valid = False
    if mock_power_switch2.stimulusMode == "conn_fail":
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU2PowerMode == PowerMode.UNKNOWN
    elif mock_power_switch2.stimulusMode == "invalid_start_state":
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU2PowerMode == mock_power_switch2.GetOutletPowerMode()
    else:
        assert device_under_test.PDU2PowerMode == PowerMode.OFF
        power_switch2_valid = True

    # If both power switches are valid, the device should be in the OFF state
    if power_switch1_valid and power_switch2_valid:
        assert device_under_test.State() == DevState.OFF

def test_On(
    tango_harness: TangoHarness,
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the On command behaves appropriately.
    """
    mock_power_switch1 = tango_harness.get_device("mid_csp_cbf/power_switch/001")
    mock_power_switch2 = tango_harness.get_device("mid_csp_cbf/power_switch/002")

    # Skip this test for certain configurations
    if (mock_power_switch1.stimulusMode == "conn_fail" or 
        mock_power_switch1.stimulusMode == "invalid_start_state" or
        mock_power_switch2.stimulusMode == "conn_fail" or 
        mock_power_switch2.stimulusMode == "invalid_start_state"):
        pytest.skip("TalonLRU device is not in a valid startup state for this test")

    # Send the On command
    result = device_under_test.On()

    # Check the command result, device state and PDU power modes
    if (mock_power_switch1.stimulusMode == "command_fail" and 
        mock_power_switch2.stimulusMode == "command_fail"):
        assert result[0][0] == ResultCode.FAILED
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU1PowerMode == PowerMode.OFF
        assert device_under_test.PDU2PowerMode == PowerMode.OFF
    else:
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == DevState.ON

        if mock_power_switch1.stimulusMode == "command_fail":
            assert device_under_test.PDU1PowerMode == PowerMode.OFF
        else:
            assert device_under_test.PDU1PowerMode == PowerMode.ON

        if mock_power_switch2.stimulusMode == "command_fail":
            assert device_under_test.PDU2PowerMode == PowerMode.OFF
        else:
            assert device_under_test.PDU2PowerMode == PowerMode.ON

def test_Off(
    tango_harness: TangoHarness,
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the Off command behaves appropriately.
    """
    mock_power_switch1 = tango_harness.get_device("mid_csp_cbf/power_switch/001")
    mock_power_switch2 = tango_harness.get_device("mid_csp_cbf/power_switch/002")

    # Skip this test for certain configurations
    if (mock_power_switch1.stimulusMode == "conn_fail" or 
        mock_power_switch1.stimulusMode == "invalid_start_state" or
        mock_power_switch2.stimulusMode == "conn_fail" or 
        mock_power_switch2.stimulusMode == "invalid_start_state"):
        pytest.skip("TalonLRU device is not in a valid startup state for this test")

    # Get the initial device state and power modes
    initial_pdu1_power_mode = device_under_test.PDU1PowerMode
    initial_pdu2_power_mode = device_under_test.PDU2PowerMode

    # Send the Off command
    result = device_under_test.Off()

    # Check the command result, device state and PDU power modes
    if mock_power_switch1.stimulusMode == "command_fail":
        assert result[0][0] == ResultCode.FAILED
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU1PowerMode == initial_pdu1_power_mode
    else:
        assert device_under_test.PDU1PowerMode == PowerMode.OFF

    if mock_power_switch2.stimulusMode == "command_fail":
        assert result[0][0] == ResultCode.FAILED
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU2PowerMode == initial_pdu2_power_mode
    else:
        assert device_under_test.PDU2PowerMode == PowerMode.OFF

    if (mock_power_switch1.stimulusMode != "command_fail" and
        mock_power_switch2.stimulusMode != "command_fail"):
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == DevState.OFF

def test_OnOff(
    tango_harness: TangoHarness,
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the On command followed by the Off command works appropriately.
    """
    mock_power_switch1 = tango_harness.get_device("mid_csp_cbf/power_switch/001")
    mock_power_switch2 = tango_harness.get_device("mid_csp_cbf/power_switch/002")

    # Skip this test for certain configurations
    if (mock_power_switch1.stimulusMode == "command_fail" and
        mock_power_switch2.stimulusMode == "command_fail"):
        pytest.skip("Test sequence is not valid for this configuration of stimulus")

    test_On(tango_harness, device_under_test)
    test_Off(tango_harness, device_under_test)