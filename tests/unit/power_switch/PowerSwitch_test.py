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

import json
import pprint
from time import sleep
from typing import Any, List
import ast
from ska_tango_testing.mock.placeholders import Anything

# Standard imports
from ska_tango_base.commands import ResultCode

# Local imports
from ska_tango_base.control_model import AdminMode, PowerState, SimulationMode

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from  ... import test_utils

def change_event_subscriber(dut: tango.DeviceProxy, change_attr: dict) -> dict:
    eid_dict = {}
    for key, value in change_attr.items():
        eid_dict[key] = dut.subscribe_event(key,
                                      tango.EventType.CHANGE_EVENT,
                                      value)
        value.assert_change_event(key, (Anything))
    return eid_dict

def change_event_unsubscriber(dut: tango.DeviceProxy, eid_dict: dict) -> None:
    for key, value in eid_dict.items():
        eid_dict[key] = dut.unsubscribe_event(value)

def test_TurnOnOutlet_TurnOffOutlet(device_under_test: tango.DeviceProxy,
                                    change_event_callback: MockTangoEventCallbackGroup) -> None:
    """
    Tests that the outlets can be turned on and off individually.
    """
    # Put the device in simulation mode
    device_under_test.simulationMode = SimulationMode.TRUE
    device_under_test.adminMode = AdminMode.ONLINE
    
    # Subscribe to change events
    # eid_1 = device_under_test.subscribe_event("longRunningCommandResult",
    #                                   tango.EventType.CHANGE_EVENT,
    #                                   change_event_callback["longRunningCommandResult"])
    
    # eid_dict.append(eid_1)
    # eid_2 = device_under_test.subscribe_event("longRunningCommandProgress",
    #                                   tango.EventType.CHANGE_EVENT,
    #                                   change_event_callback["longRunningCommandProgress"])
    eid_dict = change_event_subscriber(device_under_test, {"longRunningCommandResult":change_event_callback["longRunningCommandResult"],
                                                "longRunningCommandProgress":change_event_callback["longRunningCommandProgress"]})
    
    # change_event_callback.assert_change_event("longRunningCommandResult", (Anything))
    # change_event_callback.assert_change_event("longRunningCommandProgress", (Anything))
    num_outlets = device_under_test.numOutlets
    assert num_outlets == 8

    # Check initial state
    outlets: List[PowerState] = []
    for i in range(0, num_outlets):
        outlets.append(device_under_test.GetOutletPowerState(str(i)))

    # # Turn outlets off and check the state again
    # for i in range(0, num_outlets):
    #     assert device_under_test.TurnOffOutlet(str(i)) == [
    #         [ResultCode.OK],
    #         [f"Outlet {i} power off"],
    #     ]
    #     outlets[i] = PowerState.OFF

    #     for j in range(0, num_outlets):
    #         assert device_under_test.GetOutletPowerState(str(j)) == outlets[j]

    # Turn on outlets and check the state again
    for i in range(0, num_outlets):
        result_code, command_id = device_under_test.TurnOnOutlet(str(i))
        assert result_code == [ResultCode.QUEUED]
        outlets[i] = PowerState.ON
        for progress_point in (10,20,100):
            change_event_callback["longRunningCommandProgress"].assert_change_event((f'{command_id[0]}', f'{progress_point}'))

        change_event_callback["longRunningCommandResult"].assert_change_event((f'{command_id[0]}', Anything))
        for j in range(0, num_outlets):
            assert device_under_test.GetOutletPowerState(str(j)) == outlets[j]
    change_event_callback.assert_not_called()
    change_event_unsubscriber(device_under_test, eid_dict)

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
