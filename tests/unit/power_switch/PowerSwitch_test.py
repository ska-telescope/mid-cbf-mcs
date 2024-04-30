#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the power switch device."""

from typing import List

import pytest
import tango

# Standard imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, PowerState, SimulationMode
from ska_tango_testing.harness import TangoTestHarness
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.power_switch.power_switch_device import PowerSwitch
from ska_mid_cbf_mcs.testing import context
from tango import DevState

from ... import test_utils

# Local imports

@pytest.fixture(name="device_under_test")
def power_switch_test_context() -> tango.DeviceProxy:
    harness = TangoTestHarness()
    harness.add_device(
        "mid_csp_cbf/power_switch/001",
        PowerSwitch,
        PowerSwitchIp="192.168.0.100",
        PowerSwitchLogin="admin",
        PowerSwitchModel="DLI LPC9",
        PowerSwitchPassword="1234",
    )

    with harness as context:
        yield context.get_device("mid_csp_cbf/power_switch/001")


def test_TurnOnOutlet_TurnOffOutlet(
    device_under_test: context.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
) -> None:
    """
    Tests that the outlets can be turned on and off individually.
    """
    device_under_test.simulationMode = SimulationMode.FALSE
    device_under_test.adminMode = AdminMode.ONLINE
    assert device_under_test.State() == DevState.ON

    num_outlets = device_under_test.numOutlets
    assert num_outlets == 8

    # Check initial state
    outlets: List[PowerState] = []
    for i in range(0, num_outlets):
        outlets.append(device_under_test.GetOutletPowerState(str(i)))
        # assert device_under_test.GetOutletPowerState(str(j)) == PowerState.UNKNOWN

    # Turn outlets off and check the state again
    for i in range(0, num_outlets):
        result_code, command_id = device_under_test.TurnOffOutlet(str(i))
        assert result_code == [ResultCode.QUEUED]
        outlets[i] = PowerState.OFF

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", f'[0, "TurnOffOutlet completed OK"]')
        )
        for j in range(0, num_outlets):
            assert device_under_test.GetOutletPowerState(str(j)) == outlets[j]
            
    # Turn on outlets and check the state again
    for i in range(0, num_outlets):
        result_code, command_id = device_under_test.TurnOnOutlet(str(i))
        assert result_code == [ResultCode.QUEUED]
        outlets[i] = PowerState.ON

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", f'[0, "TurnOnOutlet completed OK"]')
        )
        for j in range(0, num_outlets):
            assert device_under_test.GetOutletPowerState(str(j)) == outlets[j]
    
    # assert if any captured events have gone unaddressed
    change_event_callbacks.assert_not_called()


def test_connection_failure(device_under_test: CbfDeviceProxy) -> None:
    """
    Tests that the device can respond to requests even when the power
    switch is not communicating.
    """
    device_under_test.adminMode = AdminMode.ONLINE
    # Take device out of simulation mode
    device_under_test.simulationMode = SimulationMode.FALSE

    # Check that the device is not communicating
    assert device_under_test.isCommunicating is False

    # Check that numOutlets is 0 since we cannot talk to the power switch
    assert device_under_test.numOutlets == 0
