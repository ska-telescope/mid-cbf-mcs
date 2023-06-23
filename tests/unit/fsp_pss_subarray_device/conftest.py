# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import unittest

# Standard imports
from typing import Dict, Optional, Type

import pytest
import pytest_mock

# Tango imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.fsp.fsp_pss_subarray_device import FspPssSubarray
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
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
    return tango_harness.get_device("mid_csp_cbf/fspPssSubarray/01_01")


@pytest.fixture()
def device_to_load(
    patched_fsp_pss_subarray_device_class: Type[FspPssSubarray],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/fsp_pss_subarray_device/devicetoload.json",
        "package": "ska_mid_cbf_mcs.fsp.fsp_pss_subarray_device",
        "device": "fsp-01",
        "device_class": "FspPssSubarray",
        "proxy": CbfDeviceProxy,
        "patch": patched_fsp_pss_subarray_device_class,
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

    def _on(mock: unittest.mock.Mock) -> None:
        mock.message = "FspPssSubarray On command completed OK"
        return (ResultCode.OK, mock.message)

    def _off(mock: unittest.mock.Mock) -> None:
        mock.message = "FspPssSubarray Off command completed OK"
        return (ResultCode.OK, mock.message)

    def _configure_scan(mock: unittest.mock.Mock, argin: str) -> None:
        mock.message = "FspPssSubarray ConfigureScan command completed OK"
        return (ResultCode.OK, mock.message)

    def _scan(mock: unittest.mock.Mock, argin: int) -> None:
        mock.message = "FspPssSubarray Scan command completed OK"
        return (ResultCode.OK, mock.message)

    def _end_scan(mock: unittest.mock.Mock) -> None:
        mock.message = "FspPssSubarray EndScan command completed OK"
        return (ResultCode.OK, mock.message)

    def _go_to_idle(mock: unittest.mock.Mock) -> None:
        mock.message = "FspPssSubarray GoToIdle command completed OK"
        return (ResultCode.OK, mock.message)

    mock.on.side_effect = lambda: _on(mock)
    mock.off.side_effect = lambda: _off(mock)
    mock.configure_scan.side_effect = lambda mock_config: _configure_scan(
        mock, mock_config
    )
    mock.scan.side_effect = lambda mock_scan_id: _scan(mock, mock_scan_id)
    mock.end_scan.side_effect = lambda: _end_scan(mock)
    mock.go_to_idle.side_effect = lambda: _go_to_idle(mock)
    mock.start_communicating.side_effect = lambda: _start_communicating(mock)

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock


@pytest.fixture()
def patched_fsp_pss_subarray_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[FspPssSubarray]:
    """
    Return a device that is patched with a mock component manager.

    :param mock_component_manager: the mock component manager with
        which to patch the device

    :return: a device that is patched with a mock component
        manager.
    """

    class PatchedFspPssSubarray(FspPssSubarray):
        """A device patched with a mock component manager."""

        def create_component_manager(
            self: PatchedFspPssSubarray,
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

    return PatchedFspPssSubarray


@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    # Mock the Vcc subarrayMembership attribute
    # The subarray ID for this unit test is hardcoded to 1
    builder.add_attribute("subarrayMembership", 1)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_controller: a mock CbfController.
    :param mock_vcc: a mock Vcc.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/sub_elt/controller": mock_controller,
        "mid_csp_cbf/vcc/001": mock_vcc,
    }
