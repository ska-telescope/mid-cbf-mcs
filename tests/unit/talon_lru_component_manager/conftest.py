# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for TalonLRU unit tests."""

from __future__ import annotations

import logging
import unittest
from typing import Callable, Dict

# Standard imports
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.talon_lru.talon_lru_component_manager import (
    TalonLRUComponentManager,
)

# Local imports
from ska_mid_cbf_mcs.talon_lru.talon_lru_device import TalonLRU
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import (
    DevicesToLoadType,
    TangoHarness,
)


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/talon_lru/001")


@pytest.fixture()
def device_to_load() -> DevicesToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/talon_lru_component_manager/devicetoload.json",
        "package": "ska_mid_cbf_mcs.talon_lru.talon_lru_device",
        "device": "talonlru-001",
        "device_class": "TalonLRU",
        "proxy": CbfDeviceProxy,
        "patch": TalonLRU,
    }


@pytest.fixture(
    params=["conn_success", "conn_fail", "invalid_start_state", "command_fail"]
)
def mock_power_switch1(request: pytest.FixtureRequest) -> unittest.mock.Mock:
    """
    Get a mock power switch device. This fixture is parameterized to
    mock different pass / failure scenarios.

    :param request: the pytest request fixture which holds information about the
                    parameterization of this fixture
    :return: a mock PowerSwitch device
    """
    return get_mock_power_switch(request.param)


@pytest.fixture(
    params=["conn_success", "conn_fail", "invalid_start_state", "command_fail"]
)
def mock_power_switch2(request: pytest.FixtureRequest) -> unittest.mock.Mock:
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
    builder.add_attribute(
        "stimulusMode", param
    )  # Attribute only used by tests

    if param == "conn_success":
        # Connection to power switch is working as expected
        builder.add_attribute("numOutlets", 8)
        builder.add_command("GetOutletPowerMode", PowerMode.OFF)
        builder.add_result_command(
            "TurnOnOutlet", ResultCode.OK, "Success msg"
        )
        builder.add_result_command(
            "TurnOffOutlet", ResultCode.OK, "Success msg"
        )

    elif param == "conn_fail":
        # Connection to power switch cannot be made
        builder.add_attribute("numOutlets", 0)
        builder.add_result_command(
            "TurnOnOutlet", ResultCode.FAILED, "Failed msg"
        )
        builder.add_result_command(
            "TurnOffOutlet", ResultCode.FAILED, "Failed msg"
        )

    elif param == "invalid_start_state":
        # Can communicate with the power switch, but one or both outlets are ON
        # when the TalonLRU device starts up
        builder.add_attribute("numOutlets", 8)
        builder.add_command("GetOutletPowerMode", PowerMode.ON)
        builder.add_result_command(
            "TurnOnOutlet", ResultCode.OK, "Success msg"
        )
        builder.add_result_command(
            "TurnOffOutlet", ResultCode.OK, "Success msg"
        )

    elif param == "command_fail":
        # Can communicate with the power switch, but the turn on/off outlet
        # commands fail
        builder.add_attribute("numOutlets", 8)
        builder.add_command("GetOutletPowerMode", PowerMode.OFF)
        builder.add_result_command(
            "TurnOnOutlet", ResultCode.FAILED, "Failed msg"
        )
        builder.add_result_command(
            "TurnOffOutlet", ResultCode.FAILED, "Failed msg"
        )

    return builder()


@pytest.fixture()
def initial_mocks(
    mock_power_switch1: unittest.mock.Mock,
    mock_power_switch2: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_power_switch1: a mock PowerSwitch device
    :param mock_power_switch2: a second mock PowerSwitch device
    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/power_switch/001": mock_power_switch1,
        "mid_csp_cbf/power_switch/002": mock_power_switch2,
    }


@pytest.fixture()
def talon_lru_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> TalonLRUComponentManager:
    return TalonLRUComponentManager(
        talons=["001", "002"],
        pdus=["001", "002"],
        pdu_outlets=["0", "AA1"],
        pdu_cmd_timeout=20,
        logger=logging.getLogger(),
        push_change_event_callback=push_change_event_callback,
        communication_status_changed_callback=communication_status_changed_callback,
        component_power_mode_changed_callback=component_power_mode_changed_callback,
        component_fault_callback=component_fault_callback,
    )


@pytest.fixture()
def communication_status_changed_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager communication status.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the communication status
        of a component manager changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def component_power_mode_changed_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component power mode change.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the component manager
        detects that the power mode of its component has changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def component_fault_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager fault.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the communication status
        of a component manager changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def check_power_mode_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager fault.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the communication status
        of a component manager changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def push_change_event_callback_factory(
    mock_change_event_callback_factory: Callable[
        [str], MockChangeEventCallback
    ],
) -> Callable[[], MockChangeEventCallback]:
    """
    Return a mock change event callback factory

    :param mock_change_event_callback_factory: fixture that provides a
        mock change event callback factory (i.e. an object that returns
        mock callbacks when called).

    :return: a mock change event callback factory
    """

    def _factory() -> MockChangeEventCallback:
        return mock_change_event_callback_factory("adminMode")

    return _factory


@pytest.fixture()
def push_change_event_callback(
    push_change_event_callback_factory: Callable[[], MockChangeEventCallback],
) -> MockChangeEventCallback:
    """
    Return a mock change event callback

    :param push_change_event_callback_factory: fixture that provides a mock
        change event callback factory

    :return: a mock change event callback
    """
    return push_change_event_callback_factory()
