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
from typing import Optional, Tuple,  Type

import pytest
import pytest_mock

# Tango imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.slim.slim_device import Slim
from ska_mid_cbf_mcs.testing.tango_harness import (
    DeviceToLoadType,
    TangoHarness,
)


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/slim/slim-fs")


@pytest.fixture()
def device_to_load(
    patched_slim_device_class: Type[Slim],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/slim_device/devicetoload.json",
        "package": "ska_mid_cbf_mcs.slim.slim_device",
        "device": "mesh",
        "device_class": "Slim",
        "proxy": CbfDeviceProxy,
        "patch": patched_slim_device_class,
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
    mocker: pytest_mock.mocker, unique_id: str
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

    def _start_communicating(mock: unittest.mock.Mock) -> None:
        mock.is_communicating = True
        mock._communication_status_changed_callback(
            CommunicationStatus.NOT_ESTABLISHED
        )
        mock._communication_status_changed_callback(
            CommunicationStatus.ESTABLISHED
        )
        mock._component_power_mode_changed_callback(PowerMode.OFF)
        
    def _on(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        mock.message = "Slim On command completed OK"
        return (ResultCode.OK, mock.message)

    def _off(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        mock.message = "Slim Off command completed OK"
        return (ResultCode.OK, mock.message)
    
    def _configure(mock: unittest.mock.Mock, argin: str) -> Tuple[ResultCode, str]:
        mock.message = "Slim Configure command completed OK"
        return (ResultCode.OK, mock.message)

    mock.on.side_effect = lambda: _on(mock)
    mock.off.side_effect = lambda: _off(mock)
    mock.configure.side_effect = lambda argin: _configure(mock, argin)

    mock.start_communicating.side_effect = lambda: _start_communicating(mock)

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock


@pytest.fixture()
def patched_slim_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[Slim]:
    """
    Return a device that is patched with a mock component manager.

    :param mock_component_manager: the mock component manager with
        which to patch the device

    :return: a device that is patched with a mock component
        manager.
    """

    class PatchedSlim(Slim):
        """A device patched with a mock component manager."""

        def create_component_manager(
            self: PatchedSlim,
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

            return mock_component_manager

    return PatchedSlim
