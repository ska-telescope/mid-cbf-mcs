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
from typing import List
from ska_mid_cbf_mcs.commons.global_enum import PowerMode

# Tango imports
from tango import DevState

# Local imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import SimulationMode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceConfigType, TangoHarness

def test_startup_state(
    tango_harness: TangoHarness,
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the outlets can be turned on and off individually.
    """
    mock_power_switch1 = tango_harness.get_device("mid_csp_cbf/power_switch/001")
    mock_power_switch2 = tango_harness.get_device("mid_csp_cbf/power_switch/002")

    # Check the device state and PDU1PowerMode based on mock_power_switch1 behaviour
    power_switch1_valid = False
    if mock_power_switch1.numOutlets == 0:
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU1PowerMode == PowerMode.UNKNOWN
    elif mock_power_switch1.GetOutletPowerMode() != PowerMode.OFF:
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU1PowerMode == mock_power_switch1.GetOutletPowerMode()
    else:
        assert device_under_test.PDU1PowerMode == PowerMode.OFF
        power_switch1_valid = True
    
    # Check the device state and PDU2PowerMode based on mock_power_switch2 behaviour
    power_switch2_valid = False
    if mock_power_switch2.numOutlets == 0:
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU2PowerMode == PowerMode.UNKNOWN
    elif mock_power_switch2.GetOutletPowerMode() != PowerMode.OFF:
        assert device_under_test.State() == DevState.FAULT
        assert device_under_test.PDU2PowerMode == mock_power_switch2.GetOutletPowerMode()
    else:
        assert device_under_test.PDU2PowerMode == PowerMode.OFF
        power_switch2_valid = True

    # If both power switches are valid, the device should be in the OFF state
    if power_switch1_valid and power_switch2_valid:
        assert device_under_test.State() == DevState.OFF
