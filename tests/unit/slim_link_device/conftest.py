# @pytest.fixture() - indicates helper for testing
# fixture for mock component manager
# fixture to patch fixture
# fixture to mock external proxies

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import unittest
from typing import Optional, Type

import pytest
import pytest_mock

# Tango imports
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerState
from ska_tango_testing.harness import TangoTestHarness
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.slim.slim_link_device import SlimLink
from ska_mid_cbf_mcs.testing.tango_harness import (
    DeviceToLoadType,
    TangoHarness,
)

# @pytest.fixture()
# def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
#     """
#     Fixture that returns the device under test.

#     :param tango_harness: a test harness for Tango devices

#     :return: the device under test
#     """
#     return tango_harness.get_device("mid_csp_cbf/fs_links/000")


@pytest.fixture(name="device_under_test")
def slim_link_test_context() -> tango.DeviceProxy:
    harness = TangoTestHarness()
    harness.add_device(
        "mid_csp_cbf/slim_link/001",
        SlimLink,
    )

    with harness as context:
        yield context.get_device("mid_csp_cbf/slim_link/001")


@pytest.fixture(name="change_event_callbacks")
def change_event_callbacks_fixture() -> MockTangoEventCallbackGroup:
    return MockTangoEventCallbackGroup(
        "longRunningCommandResult",
        "longRunningCommandProgress",
        timeout=10,
    )


@pytest.fixture()
def device_to_load(
    patched_slim_link_device_class: Type[SlimLink],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/slim_link_device/devicetoload.json",
        "package": "ska_mid_cbf_mcs.slim.slim_link_device",
        "device": "fs-links",
        "device_class": "SlimLink",
        "proxy": CbfDeviceProxy,
        "patch": patched_slim_link_device_class,
    }


@pytest.fixture
def unique_id() -> str:
    """
    Return a unique ID used to test Tango layer infrastructure.

    :return: a unique ID
    """
    return "a unique id"


# @pytest.fixture()
# def mock_component_manager(
#     mocker: pytest_mock.mocker, unique_id: str
# ) -> unittest.mock.Mock:
#     """
#     Return a mock component manager.

#     The mock component manager is a simple mock except for one bit of
#     extra functionality: when we call start_communicating() on it, it
#     makes calls to callbacks signaling that communication is established
#     and the component is off.

#     :param mocker: pytest wrapper for unittest.mock
#     :param unique_id: a unique id used to check Tango layer functionality

#     :return: a mock component manager
#     """
#     mock = mocker.Mock()
#     mock.is_communicating = False

#     def _start_communicating(mock: unittest.mock.Mock) -> None:
#         mock.is_communicating = True
#         mock._communication_status_changed_callback(
#             CommunicationStatus.NOT_ESTABLISHED
#         )
#         mock._communication_status_changed_callback(
#             CommunicationStatus.ESTABLISHED
#         )
#         # mock._component_power_mode_changed_callback(PowerState.OFF)

#     def _connect_slim_tx_rx(mock: unittest.mock.Mock) -> None:
#         mock.message = "SlimLink ConnectTxRx command completed OK"
#         return (ResultCode.OK, mock.message)

#     def _verify_connection(mock: unittest.mock.Mock) -> None:
#         mock.message = "SlimLink VerifyConnection command completed OK"
#         return (ResultCode.OK, mock.message)

#     def _disconnect_slim_tx_rx(mock: unittest.mock.Mock) -> None:
#         mock.message = "SlimLink DisconnectTxRx command completed OK"
#         return (ResultCode.OK, mock.message)

#     def _clear_counters(mock: unittest.mock.Mock) -> None:
#         mock.message = "SlimLink ClearCounters command completed OK"
#         return (ResultCode.OK, mock.message)

#     mock.connect_slim_tx_rx.side_effect = lambda: _connect_slim_tx_rx(mock)
#     mock.verify_connection.side_effect = lambda: _verify_connection(mock)
#     mock.disconnect_slim_tx_rx.side_effect = lambda: _disconnect_slim_tx_rx(
#         mock
#     )
#     mock.clear_counters.side_effect = lambda: _clear_counters(mock)

#     mock.start_communicating.side_effect = lambda: _start_communicating(mock)

#     mock.enqueue.return_value = unique_id, ResultCode.QUEUED

#     return mock


# @pytest.fixture()
# def patched_slim_link_device_class(
#     mock_component_manager: unittest.mock.Mock,
# ) -> Type[SlimLink]:
#     """
#     Return a device that is patched with a mock component manager.

#     :param mock_component_manager: the mock component manager with
#         which to patch the device

#     :return: a device that is patched with a mock component
#         manager.
#     """

#     class PatchedSlimLink(SlimLink):
#         """A device patched with a mock component manager."""

#         def create_component_manager(
#             self: PatchedSlimLink,
#         ) -> unittest.mock.Mock:
#             """
#             Return a mock component manager instead of the usual one.

#             :return: a mock component manager
#             """
#             self._communication_status: Optional[CommunicationStatus] = None
#             self._component_power_mode: Optional[PowerState] = None

#             mock_component_manager._communication_status_changed_callback = (
#                 self._communication_status_changed
#             )
#             mock_component_manager._component_power_mode_changed_callback = (
#                 self._component_power_mode_changed
#             )

#             return mock_component_manager

#     return PatchedSlimLink
