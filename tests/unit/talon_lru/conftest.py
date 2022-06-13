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
from typing import Callable, Dict, Optional, Tuple, Type

# Standard imports
import pytest
import pytest_mock
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
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
def device_to_load(
    patched_talon_lru_device_class: Type[TalonLRU],
) -> DevicesToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/talon_lru/devicetoload.json",
        "package": "ska_mid_cbf_mcs.talon_lru.talon_lru_device",
        "device": "talonlru-001",
        "device_class": "TalonLRU",
        "proxy": CbfDeviceProxy,
        "patch": patched_talon_lru_device_class,
    }


@pytest.fixture
def unique_id() -> str:
    """
    Return a unique ID used to test Tango layer infrastructure.

    :return: a unique ID
    """
    return "a unique id"


@pytest.fixture()
def mock_component_manager(
    mocker: pytest_mock.mocker,
    unique_id: str,
    mock_power_switch1: unittest.mock.Mock,
    mock_power_switch2: unittest.mock.Mock,
) -> unittest.mock.Mock:
    """
    Return a mock component manager.

    The mock component manager is a simple mock except for one bit of
    extra functionality: when we call start_communicating() on it, it
    makes calls to callbacks signaling that communication is established
    and the component is off.

    :param mocker: pytest wrapper for unittest.mock
    :param unique_id: a unique id used to check Tango layer functionality

    :return: a mock component manager
    """
    mock = mocker.Mock()
    mock.is_communicating = False
    mock.connected = False

    def _start_communicating(mock: unittest.mock.Mock) -> None:
        if (
            mock_power_switch1.stimulusMode == "conn_success"
            or mock_power_switch2.stimulusMode == "conn_success"
        ):
            mock.is_communicating = True
            mock.connected = True
            mock._communication_status_changed_callback(
                CommunicationStatus.ESTABLISHED
            )
            mock._component_power_mode_changed_callback(PowerMode.OFF)
        elif (
            mock_power_switch1.stimulusMode == "command_fail"
            or mock_power_switch2.stimulusMode == "command_fail"
        ):
            mock.is_communicating = True
            mock.connected = True
            mock._communication_status_changed_callback(
                CommunicationStatus.ESTABLISHED
            )
            mock._component_power_mode_changed_callback(PowerMode.OFF)
        else:
            mock.is_communicating = False
            mock.connected = False
            mock._communication_status_changed_callback(
                CommunicationStatus.NOT_ESTABLISHED
            )
            mock._component_fault_callback(True)

    def _on(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            mock._component_fault_callback(True)
            return (ResultCode.FAILED, "On command failed")
        else:
            mock._component_power_mode_changed_callback(PowerMode.ON)
            return (ResultCode.OK, "On command completed OK")

    def _off(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            mock._component_fault_callback(True)
            return (ResultCode.FAILED, "Off command failed")
        else:
            mock._component_power_mode_changed_callback(PowerMode.OFF)
            return (ResultCode.OK, "Off command completed OK")

    def _check_power_mode(
        mock: unittest.mock.Mock, state: tango.DevState
    ) -> None:
        pass

    mock.start_communicating.side_effect = lambda: _start_communicating(mock)
    mock.on.side_effect = lambda: _on(mock)
    mock.off.side_effect = lambda: _off(mock)
    mock.check_power_mode.side_effect = lambda mock_state: _check_power_mode(
        mock, mock_state
    )

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock


@pytest.fixture()
def patched_talon_lru_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[TalonLRU]:
    """
    Return a Talon LRU device that is patched with a mock component manager.

    :param mock_component_manager: the mock component manager with
        which to patch the device

    :return: a Talon LRU device that is patched with a mock component
        manager.
    """

    class PatchedTalonLRU(TalonLRU):
        """A Talon LRU device patched with a mock component manager."""

        def create_component_manager(
            self: PatchedTalonLRU,
        ) -> unittest.mock.Mock:
            """
            Return a mock component manager instead of the usual one.

            :return: a mock component manager
            """
            self._communication_status: Optional[CommunicationStatus] = None
            self._component_power_mode: Optional[PowerMode] = None

            mock_component_manager._communication_status_changed_callback = (
                self._communication_status_changed
            )
            mock_component_manager._component_power_mode_changed_callback = (
                self._component_power_mode_changed
            )
            mock_component_manager._component_fault_callback = (
                self._component_fault
            )

            return mock_component_manager

    return PatchedTalonLRU


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
