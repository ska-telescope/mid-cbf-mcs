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
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, HealthState, PowerMode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.controller.controller_device import CbfController

# Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
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
    return tango_harness.get_device("mid_csp_cbf/sub_elt/controller")


@pytest.fixture()
def device_to_load(
    patched_controller_device_class: Type[CbfController],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/controller/devicetoload.json",
        "package": "ska_mid_cbf_mcs.controller.controller_device",
        "device": "controller",
        "device_class": "CbfController",
        "proxy": CbfDeviceProxy,
        "patch": patched_controller_device_class,
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
        mock.message = "CbfController On command completed OK"
        return (ResultCode.OK, mock.message)

    def _off(mock: unittest.mock.Mock) -> None:
        mock.message = "CbfController Off command completed OK"
        return (ResultCode.OK, mock.message)

    def _standby(mock: unittest.mock.Mock) -> None:
        mock.message = "CbfController On command completed OK"
        return (ResultCode.OK, mock.message)

    mock.on.side_effect = lambda: _on(mock)
    mock.off.side_effect = lambda: _off(mock)
    mock.standby.side_effect = lambda: _standby(mock)
    mock.start_communicating.side_effect = lambda: _start_communicating(mock)

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock


@pytest.fixture()
def patched_controller_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[CbfController]:
    """
    Return a controller device that is patched with a mock component manager.

    :param mock_component_manager: the mock component manager with
        which to patch the device

    :return: a controller device that is patched with a mock component
        manager.
    """

    class PatchedCbfController(CbfController):
        """A controller device patched with a mock component manager."""

        def create_component_manager(
            self: PatchedCbfController,
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

    return PatchedCbfController


@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture()
def mock_vcc_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()


@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture()
def mock_fsp_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()


@pytest.fixture()
def mock_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture()
def mock_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()


@pytest.fixture()
def mock_talon_lru() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_vcc: unittest.mock.Mock,
    mock_vcc_group: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_group: unittest.mock.Mock,
    mock_subarray: unittest.mock.Mock,
    mock_subarray_group: unittest.mock.Mock,
    mock_talon_lru: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of proxy mocks to pre-register.

    :param mock_vcc: a mock Vcc that is powered off.
    :param mock_vcc_group: a mock Vcc tango.Group.
    :param mock_fsp: a mock Fsp that is powered off.
    :param mock_fsp_group: a mock Fsp tango.Group.
    :param mock_subarray: a mock CbfSubarray that is powered off.
    :param mock_subarray_group: a mock CbfSubarray tango.Group.
    :param mock_talon_lru: a mock TalonLRU that is powered off.

    :return: a dictionary of proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/vcc/001": mock_vcc,
        "mid_csp_cbf/vcc/002": mock_vcc,
        "mid_csp_cbf/vcc/003": mock_vcc,
        "mid_csp_cbf/vcc/004": mock_vcc,
        "mid_csp_cbf/vcc/005": mock_vcc,
        "mid_csp_cbf/vcc/006": mock_vcc,
        "mid_csp_cbf/vcc/007": mock_vcc,
        "mid_csp_cbf/vcc/008": mock_vcc,
        "mid_csp_cbf/fsp/01": mock_fsp,
        "mid_csp_cbf/fsp/02": mock_fsp,
        "mid_csp_cbf/fsp/03": mock_fsp,
        "mid_csp_cbf/fsp/04": mock_fsp,
        "mid_csp_cbf/sub_elt/subarray_01": mock_subarray,
        "mid_csp_cbf/sub_elt/subarray_02": mock_subarray,
        "mid_csp_cbf/sub_elt/subarray_03": mock_subarray,
        "mid_csp_cbf/talon_lru/001": mock_talon_lru,
        "VCC": mock_vcc_group,
        "FSP": mock_fsp_group,
        "CBF Subarray": mock_subarray_group,
    }
