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

import ast
import json
import pprint
from time import sleep
from typing import Any, List

import tango

# Standard imports
from ska_tango_base.commands import ResultCode

# Local imports
from ska_tango_base.control_model import AdminMode, PowerState, SimulationMode
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

from ... import test_utils


def test_TurnOnOutlet_TurnOffOutlet(
    device_under_test: tango.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
) -> None:
    """
    Tests that the outlets can be turned on and off individually.
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
        for progress_point in (10, 20, 100):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", f"{progress_point}"))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", Anything)
        )
        for j in range(0, num_outlets):
            assert device_under_test.GetOutletPowerState(str(j)) == outlets[j]

    # assert if any captured events have gone unaddressed
    change_event_callbacks.assert_not_called()
    test_utils.change_event_unsubscriber(device_under_test, attr_event_ids)


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
