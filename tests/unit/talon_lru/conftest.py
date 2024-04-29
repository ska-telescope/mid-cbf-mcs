# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for TalonLRU unit tests."""

from __future__ import annotations

import unittest

import pytest
import tango
from ska_tango_base.control_model import PowerState
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

from ... import test_utils

@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:

    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run

    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/talon_lru/001")

@pytest.fixture(name="change_event_callbacks")
def lru_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "longRunningCommandProgress",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_power_switch() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_command("TurnOnOutlet", None)
    builder.add_command("TurnOffOutlet", None)
    builder.add_command("GetOutletState", PowerState.ON)
    return builder()

@pytest.fixture()
def mock_talon_lru() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_power_switch: unittest.mock.Mock,
    mock_talon_lru: unittest.mock.Mock,
    mock_sw: unittest.mock.Mock
) -> dict[str, unittest.mock.Mock]:
   """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_band: a mock VccBand device that is powered off.
    :param mock_sw: a mock VccSearchWindow that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
   return {
       "mid_csp_cbf/talon_lru/001": mock_talon_lru,
       "mid_csp_cbf/power_switch/001": mock_power_switch,
       "mid_csp_cbf/power_switch/002": mock_power_switch,
   }
   


