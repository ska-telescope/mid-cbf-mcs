# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

# Standard imports
from typing import Callable, Type, Dict, Tuple, Optional
import pytest
import pytest_mock
import unittest

# Tango imports
import tango
from tango import DevState
from tango.server import command

#Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

from ska_mid_cbf_mcs.vcc.vcc_device import Vcc
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode


# TODO implement commented items in base class v0.11
@pytest.fixture()
def mock_component_manager(
    mocker: pytest_mock.mocker,
    # unique_id: str,
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
    # mock.is_communicating = False
    mock.connected = False

    def _start_communicating(mock: unittest.mock.Mock) -> None:
        # mock.is_communicating = True
        mock.connected = True
        # mock._communication_status_changed_callback(CommunicationStatus.NOT_ESTABLISHED)
        # mock._communication_status_changed_callback(CommunicationStatus.ESTABLISHED)
        # mock._component_power_mode_changed_callback(PowerMode.OFF)
    
    def _turn_on_band_device(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "Vcc On command completed OK")
    
    def _turn_off_band_device(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "Vcc Off command completed OK")
    
    def _deconfigure(mock: unittest.mock.Mock) -> None: return None

    def _configure_search_window(mock: unittest.mock.Mock) -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "Vcc ConfigureSearchWindow command completed OK")


    mock.start_communicating.side_effect = lambda: _start_communicating(mock)
    mock.turn_on_band_device.side_effect = lambda: _turn_on_band_device(mock)
    mock.turn_off_band_device.side_effect = lambda: _turn_off_band_device(mock)
    mock.deconfigure.side_effect = lambda: _deconfigure(mock)
    mock.configure_search_window.side_effect = lambda: _configure_search_window(mock)

    return mock

@pytest.fixture()
def patched_vcc_device_class(
    mock_component_manager: unittest.mock.Mock
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
            #TODO implement in base class v0.11
            #self._communication_status: Optional[CommunicationStatus] = None
            #self._component_power_mode: Optional[PowerMode] = None

            mock_component_manager._communication_status_changed_callback = (
                self._communication_status_changed
            )
            mock_component_manager._component_power_mode_changed_callback = (
                self._component_power_mode_changed
            )

            return mock_component_manager

        @command(dtype_in=int)
        def FakeSubservientDevicesObsState(
            self,
            obs_state: ObsState
        ) -> None:
            obs_state = ObsState(obs_state)

            # for fqdn in self.component_manager._device_obs_states:
            #     self.component_manager._device_obs_state_changed(fqdn, obs_state)

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
def device_to_load(
    patched_vcc_device_class: Type[Vcc]
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs.vcc.vcc_device",
        "device": "vcc-001",
        "device_class": "Vcc",
        "proxy": CbfDeviceProxy,
        "patch": patched_vcc_device_class
    }

@pytest.fixture()
def mock_vcc_band12() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_band3() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_band4() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_band5() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_vcc_band12: unittest.mock.Mock,
    mock_vcc_band3: unittest.mock.Mock,
    mock_vcc_band4: unittest.mock.Mock,
    mock_vcc_band5: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_band12: a mock VccBand1And2 that is powered off.
    :param mock_vcc_band3: a mock VccBand3 that is powered off.
    :param mock_vcc_band4: a mock VccBand4 that is powered off.
    :param mock_vcc_band5: a mock VccBand5 that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/vcc_band12/001": mock_vcc_band12,
        "mid_csp_cbf/vcc_band3/001": mock_vcc_band3,
        "mid_csp_cbf/vcc_band4/001": mock_vcc_band4,
        "mid_csp_cbf/vcc_band5/001": mock_vcc_band5,
    }
