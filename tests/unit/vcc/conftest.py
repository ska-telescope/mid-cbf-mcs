# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import logging
import unittest
# Standard imports
from typing import Callable, Dict, Optional, Tuple, Type

import pytest
import pytest_mock
# Tango imports
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable, MockChangeEventCallback)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import (DeviceToLoadType,
                                                   TangoHarness)
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager
# Local imports
from ska_mid_cbf_mcs.vcc.vcc_device import Vcc


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
    mock.connected = False
    mock.receptor_id = 1

    def _start_communicating(mock: unittest.mock.Mock) -> None:
        mock.is_communicating = True
        mock.connected = True
        mock._communication_status_changed_callback(
            CommunicationStatus.NOT_ESTABLISHED
        )
        mock._component_power_mode_changed_callback(PowerMode.ON)
        mock._communication_status_changed_callback(
            CommunicationStatus.ESTABLISHED
        )

    def _on(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        mock._component_power_mode_changed_callback(PowerMode.ON)
        return (ResultCode.OK, "On command completed OK")

    def _off(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        mock._component_power_mode_changed_callback(PowerMode.OFF)
        return (ResultCode.OK, "Off command completed OK")

    def _standby(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        mock._component_power_mode_changed_callback(PowerMode.STANDBY)
        return (ResultCode.OK, "Standby command completed OK")

    def _configure_scan() -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "ConfigureScan command completed OK")

    def _scan() -> Tuple[ResultCode, str]:
        return (ResultCode.STARTED, "Scan command started")

    def _end_scan() -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "EndScan command completed OK")

    def _configure_band(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "ConfigureBand command completed OK")

    def _deconfigure() -> None:
        pass

    def _configure_search_window() -> Tuple[ResultCode, str]:
        return (
            ResultCode.OK,
            "Vcc ConfigureSearchWindow command completed OK",
        )

    mock.start_communicating.side_effect = lambda: _start_communicating(mock)
    mock.on.side_effect = lambda: _on(mock)
    mock.off.side_effect = lambda: _off(mock)
    mock.standby.side_effect = lambda: _standby(mock)
    mock.configure_scan.side_effect = lambda argin: _configure_scan()
    mock.scan.side_effect = lambda argin: _scan()
    mock.end_scan.side_effect = lambda: _end_scan()
    mock.configure_band.side_effect = lambda argin: _configure_band(mock)
    mock.deconfigure.side_effect = lambda: _deconfigure()
    mock.configure_search_window.side_effect = (
        lambda argin: _configure_search_window()
    )

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock


@pytest.fixture()
def patched_vcc_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[Vcc]:
    """
    Return a Vcc device class, patched with extra methods for testing.

    :return: a patched Vcc device class, patched with extra methods
        for testing
    """

    class PatchedVcc(Vcc):
        """
        Vcc patched with extra commands for testing purposes.

        The extra commands allow us to mock the receipt of obs state
        change events from subservient devices.
        """

        def create_component_manager(
            self: PatchedVcc,
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

    return PatchedVcc


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/vcc/001")


@pytest.fixture()
def device_to_load(patched_vcc_device_class: Type[Vcc]) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf-mcs/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs.vcc.vcc_device",
        "device": "vcc-001",
        "device_class": "Vcc",
        "proxy": CbfDeviceProxy,
        "patch": patched_vcc_device_class,
    }


@pytest.fixture()
def mock_talon_lru() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_attribute("PDU1PowerMode", PowerMode.OFF)
    builder.add_attribute("PDU2PowerMode", PowerMode.OFF)
    return builder()


@pytest.fixture()
def mock_vcc_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_command("InitCommonParameters", None)
    builder.add_command("ConfigureBand", None)
    builder.add_command("Unconfigure", None)
    return builder()


@pytest.fixture()
def mock_vcc_band() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_command("SetInternalParameters", None)
    builder.add_command("ConfigureScan", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_command("Abort", None)
    builder.add_command("ObsReset", None)
    return builder()


@pytest.fixture()
def mock_sw() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("searchWindowTuning", 0)
    builder.add_attribute("tdcEnable", False)
    builder.add_attribute("tdcNumBits", 0)
    builder.add_attribute("tdcPeriodBeforeEpoch", 0)
    builder.add_attribute("tdcPeriodAfterEpoch", 0)
    builder.add_attribute("tdcDestinationAddress", ["", "", ""])
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_talon_lru: unittest.mock.Mock,
    mock_vcc_controller: unittest.mock.Mock,
    mock_vcc_band: unittest.mock.Mock,
    mock_sw: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_band: a mock VccBand device that is powered off.
    :param mock_sw: a mock VccSearchWindow that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/talon_lru/001": mock_talon_lru,
        "talondx-001/vcc-app/vcc-controller": mock_vcc_controller,
        "talondx-001/vcc-app/vcc-band-1-and-2": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-3": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-4": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-5": mock_vcc_band,
        "mid_csp_cbf/vcc_sw1/001": mock_sw,
        "mid_csp_cbf/vcc_sw2/001": mock_sw,
    }


@pytest.fixture()
def vcc_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> VccComponentManager:
    """Return a VCC component manager."""
    return VccComponentManager(
        talon_lru="mid_csp_cbf/talon_lru/001",
        vcc_controller="talondx-001/vcc-app/vcc-controller",
        vcc_band=[
            "talondx-001/vcc-app/vcc-band-1-and-2",
            "talondx-001/vcc-app/vcc-band-3",
            "talondx-001/vcc-app/vcc-band-4",
            "talondx-001/vcc-app/vcc-band-5",
        ],
        search_window=["mid_csp_cbf/vcc_sw1/001", "mid_csp_cbf/vcc_sw2/001"],
        logger=logger,
        push_change_event_callback=push_change_event_callback,
        communication_status_changed_callback=communication_status_changed_callback,
        component_power_mode_changed_callback=component_power_mode_changed_callback,
        component_fault_callback=component_fault_callback,
        simulation_mode=SimulationMode.FALSE,
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
    Return a mock callback for component fault.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the component manager
        detects that the power mode of its component has changed.
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
