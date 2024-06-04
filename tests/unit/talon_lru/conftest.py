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
from ska_control_model import ResultCode
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


@pytest.fixture(name="power_switch_1")
def power_switch_1_fixture(
    test_context: TangoTestHarnessContext,
) -> unittest.mock.Mock:
    """
    Fixture that returns the power switch mock
    """
    return test_context.get_device("mid_csp_cbf/power_switch/001")


@pytest.fixture(name="power_switch_2")
def power_switch_2_fixture(
    test_context: TangoTestHarnessContext,
) -> unittest.mock.Mock:
    """
    Fixture that returns the power switch mock
    """
    return test_context.get_device("mid_csp_cbf/power_switch/002")


@pytest.fixture(name="change_event_callbacks")
def lru_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "state",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_talon_board() -> unittest.mock.Mock:
    """
    Fixture that builds the talon board mock
    """
    builder = MockDeviceBuilder()
    builder.add_attribute("adminMode", None)
    builder.add_command("On", ResultCode.OK)
    builder.add_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture(params=["command_success", "command_fail"])
def mock_power_switch_1(request: pytest.FixtureRequest) -> unittest.mock.Mock:
    """
    Get a mock power switch device. This fixture is parameterized to
    mock different pass / failure scenarios.

    :param request: the pytest request fixture which holds information about the
                    parameterization of this fixture
    :return: a mock PowerSwitch device
    """
    return get_mock_power_switch(request.param)


@pytest.fixture(params=["command_success", "command_fail"])
def mock_power_switch_2(request: pytest.FixtureRequest) -> unittest.mock.Mock:
    """
    Get a mock power switch device. This fixture is parameterized to
    mock different pass / failure scenarios.

    :param request: the pytest request fixture which holds information about the
                    parameterization of this fixture
    :return: a mock PowerSwitch device
    """
    return get_mock_power_switch(request.param)


def get_mock_power_switch(param: str) -> unittest.mock.Mock:
    """
    Get a mock power switch device with the specified parameterization.

    :param param: parameterization string that impacts the mocked behaviour
    """
    builder = MockDeviceBuilder()
    builder.add_attribute("stimulusMode", param)
    builder.add_attribute("adminMode", None)
    builder.add_attribute("simulationMode", None)
    if param == "command_success":
        # Connection to power switch is working as expected.
        builder.add_attribute("numOutlets", 8)
        builder.add_command("GetOutletPowerState", PowerState.OFF)
        builder.add_result_command(
            "TurnOnOutlet", ResultCode.OK, "Success message"
        )
        builder.add_result_command(
            "TurnOffOutlet", ResultCode.OK, "Success message"
        )
    elif param == "command_fail":
        # Can communicate with the power switch, but the turn on/off outlet commands fail.
        builder.add_attribute("numOutlets", 8)
        builder.add_command("GetOutletPowerState", PowerState.OFF)
        builder.add_result_command(
            "TurnOnOutlet", ResultCode.FAILED, "Failed message"
        )
        builder.add_result_command(
            "TurnOffOutlet", ResultCode.FAILED, "Failed message"
        )
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_power_switch_1: unittest.mock.Mock,
    mock_power_switch_2: unittest.mock.Mock,
    mock_talon_board: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_power_switch_1: a mock power switch device that simulates both successful and failed commands
    :param mock_power_switch_2: a mock power switch device that simulates both successful and failed commands
    :param mock_talon_board: a mock talon board

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/talon_board/001": mock_talon_board,
        "mid_csp_cbf/talon_board/002": mock_talon_board,
        "mid_csp_cbf/power_switch/001": mock_power_switch_1,
        "mid_csp_cbf/power_switch/002": mock_power_switch_2,
    }
