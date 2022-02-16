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

# Standard imports
import pytest
from typing import List
from ska_tango_base.control_model import PowerMode

# Local imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import SimulationMode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

@pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
)
def test_TurnOnOutlet_TurnOffOutlet(
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the outlets can be turned on and off individually.
    """
    # Put the device in simulation mode
    device_under_test.simulationMode = SimulationMode.TRUE

    num_outlets = device_under_test.numOutlets
    assert num_outlets == 8

    # Check initial state
    outlets: List[PowerMode] = []
    for i in range(0, num_outlets):
        outlets.append(device_under_test.GetOutletPowerMode(i))

    # Turn outlets off and check the state again
    for i in range(0, num_outlets):
        assert device_under_test.TurnOffOutlet(i) == [
            [ResultCode.OK], [f"Outlet {i} power off"]]
        outlets[i] = PowerMode.OFF

        for j in range(0, num_outlets):
            assert device_under_test.GetOutletPowerMode(j) == outlets[j]

    # Turn on outlets and check the state again
    for i in range(0, num_outlets):
        assert device_under_test.TurnOnOutlet(i) == [
            [ResultCode.OK], [f"Outlet {i} power on"]]
        outlets[i] = PowerMode.ON

        for j in range(0, num_outlets):
            assert device_under_test.GetOutletPowerMode(j) == outlets[j]

@pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
)
def test_connection_failure(
    device_under_test: CbfDeviceProxy
) -> None:
    """
    Tests that the device can respond to requests even when the power
    switch is not communicating.
    """
    # Take device out of simulation mode
    device_under_test.simulationMode = SimulationMode.FALSE

    # Check that the device is not communicating
    assert device_under_test.isCommunicating == False

    # Check that numOutlets is 0 since we cannot talk to the power switch
    assert device_under_test.numOutlets == 0
