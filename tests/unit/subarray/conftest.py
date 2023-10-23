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
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    ObsState,
    PowerMode,
    SimulationMode,
)
from tango.server import command

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.subarray.subarray_component_manager import (
    CbfSubarrayComponentManager,
)
from ska_mid_cbf_mcs.subarray.subarray_device import CbfSubarray
from ska_mid_cbf_mcs.testing.mock.mock_attribute import MockAttributeBuilder
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import (
    DeviceToLoadType,
    TangoHarness,
)


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
    mock.connected = False
    mock.receptors = []
    mock._ready = False

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

    def _raise_configure_scan_fatal_error() -> None:
        tango.Except.throw_exception(
            "Command failed ConfigureScan execution", tango.ErrSeverity.ERR
        )

    def _deconfigure(mock) -> Tuple[ResultCode, str]:
        if mock._ready:
            mock._component_configured_callback(False)
        mock._ready = False
        return (ResultCode.OK, "Deconfiguration completed OK")

    def _validate_input() -> Tuple[bool, str]:
        return (True, "Scan configuration is valid.")

    def _configure_scan(mock) -> Tuple[ResultCode, str]:
        if not mock._ready:
            mock._component_configured_callback(True)
        mock._ready = True
        return (ResultCode.OK, "ConfigureScan command completed OK")

    def _remove_receptor(
        mock: unittest.mock.Mock, receptor_id: int
    ) -> Tuple[ResultCode, str]:
        if receptor_id in mock.receptors:
            mock.receptors.remove(receptor_id)
            if len(mock.receptors) == 0:
                mock._component_resourced_callback(False)
            return (ResultCode.OK, "RemoveReceptors completed OK")
        else:
            return (
                ResultCode.FAILED,
                f"Error in CbfSubarrayComponentManager; receptor {receptor_id} not found.",
            )

    def _remove_all_receptors(
        mock: unittest.mock.Mock,
    ) -> Tuple[ResultCode, str]:
        if mock.receptors == []:
            return (ResultCode.FAILED, "RemoveAllReceptors failed")
        mock.receptors = []
        mock._component_resourced_callback(False)
        return (ResultCode.OK, "RemoveAllReceptors completed OK")

    def _add_receptor(
        mock: unittest.mock.Mock, receptor_id: int
    ) -> Tuple[ResultCode, str]:
        if receptor_id not in mock.receptors:
            if len(mock.receptors) == 0:
                mock._component_resourced_callback(True)
            mock.receptors.append(receptor_id)
            return (ResultCode.OK, "AddReceptors completed OK")
        else:
            mock._component_fault_callback(True)
            return (
                ResultCode.FAILED,
                f"Receptor {receptor_id} already assigned to subarray component manager.",
            )

    def _scan() -> Tuple[ResultCode, str]:
        return (ResultCode.STARTED, "Scan command successful")

    def _end_scan() -> Tuple[ResultCode, str]:
        return (ResultCode.OK, "EndScan command completed OK")

    def _update_sys_param() -> None:
        return

    mock.start_communicating.side_effect = lambda: _start_communicating(mock)
    mock.on.side_effect = lambda: mock._component_power_mode_changed_callback(
        PowerMode.ON
    )
    mock.off.side_effect = lambda: mock._component_power_mode_changed_callback(
        PowerMode.OFF
    )
    mock.standby.side_effect = (
        lambda: mock._component_power_mode_changed_callback(PowerMode.STANDBY)
    )
    mock.raise_configure_scan_fatal_error.side_effect = (
        lambda: _raise_configure_scan_fatal_error()
    )
    mock.deconfigure.side_effect = lambda: _deconfigure(mock)
    mock.validate_input.side_effect = lambda argin: _validate_input()
    mock.configure_scan.side_effect = lambda argin: _configure_scan(mock)
    mock.remove_receptor.side_effect = lambda receptor_id: _remove_receptor(
        mock, receptor_id
    )
    mock.remove_all_receptors.side_effect = lambda: _remove_all_receptors(mock)
    mock.add_receptor.side_effect = lambda receptor_id: _add_receptor(
        mock, receptor_id
    )
    mock.scan.side_effect = lambda argin: _scan()
    mock.end_scan.side_effect = lambda: _end_scan()
    mock.update_sys_param.side_effect = lambda argin: _update_sys_param()

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock


@pytest.fixture()
def patched_subarray_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[CbfSubarray]:
    """
    Return a CbfSubarray device class, patched with extra methods for testing.

    :return: a patched CbfSubarray device class, patched with extra methods
        for testing
    """

    class PatchedCbfSubarray(CbfSubarray):
        """
        CbfSubarray patched with extra commands for testing purposes.

        The extra commands allow us to mock the receipt of obs state
        change events from subservient devices.
        """

        def create_component_manager(
            self: PatchedCbfSubarray,
        ) -> unittest.mock.Mock:
            """
            Return a mock component manager instead of the usual one.

            :return: a mock component manager
            """
            self._communication_status: Optional[CommunicationStatus] = None
            self._component_power_mode: Optional[PowerMode] = None

            mock_component_manager._component_resourced_callback = (
                self._component_resourced
            )
            mock_component_manager._component_configured_callback = (
                self._component_configured
            )
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

        @command(dtype_in=int)
        def FakeSubservientDevicesObsState(
            self: PatchedCbfSubarray, obs_state: ObsState
        ) -> None:
            obs_state = ObsState(obs_state)

            # for fqdn in self.component_manager._device_obs_states:
            #     self.component_manager._device_obs_state_changed(fqdn, obs_state)

    return PatchedCbfSubarray


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/sub_elt/subarray_01")


@pytest.fixture()
def device_to_load(
    patched_subarray_device_class: Type[CbfSubarray],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :param patched_vcc_device_class: a class for a patched CbfSubarray
        device with extra methods for testing purposes.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/subarray/devicetoload.json",
        "package": "ska_mid_cbf_mcs.subarray.subarray_device",
        "device": "cbfsubarray-01",
        "device_class": "CbfSubarray",
        "proxy": CbfDeviceProxy,
        "patch": None,
    }


@pytest.fixture()
def mock_doppler() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value([0.0, 0.0, 0.0, 0.0])
    return builder()


@pytest.fixture()
def mock_delay() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value("")
    return builder()


@pytest.fixture()
def mock_jones() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value("")
    return builder()


@pytest.fixture()
def mock_beam() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value("")
    return builder()


@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
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
    builder.add_command("ConfigureScan", None)
    builder.add_command("ConfigureSearchWindow", None)
    builder.add_command("GoToIdle", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_command("ConfigureBand", None)
    builder.add_command("UpdateDelayModel", None)
    builder.add_command("UpdateJonesMatrix", None)
    return builder()


@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
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
    builder.add_command("RemoveSubarrayMembership", None)
    builder.add_command("UpdateDelayModel", None)
    builder.add_command("UpdateJonesMatrix", None)
    builder.add_command("UpdateBeamWeights", None)
    return builder()


@pytest.fixture()
def mock_fsp_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("searchBeamID", None)
    builder.add_attribute("timingBeamID", None)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_command("GoToIdle", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()


@pytest.fixture()
def mock_fsp_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    builder.add_command("GoToIdle", None)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_doppler: unittest.mock.Mock,
    mock_delay: unittest.mock.Mock,
    mock_jones: unittest.mock.Mock,
    mock_beam: unittest.mock.Mock,
    mock_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
    mock_vcc_group: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_group: unittest.mock.Mock,
    mock_fsp_subarray: unittest.mock.Mock,
    mock_fsp_subarray_group: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of proxy mocks to pre-register.

    :param mock_doppler: a mock dopplerPhaseCorrection attribute
    :param mock_delay: a mock delayModel attribute
    :param mock_jones: a mock jones_matrix attribute
    :param mock_beam: a mock beam_weights attribute
    :param mock_controller: a mock CbfController that is powered on.
    :param mock_vcc: a mock Vcc that is powered on.
    :param mock_vcc_group: a mock Vcc tango.Group.
    :param mock_fsp: a mock Fsp that is powered off.
    :param mock_fsp_group: a mock Fsp tango.Group.
    :param mock_fsp_subarray: a mock Fsp function mode subarray that is powered on.
    :param mock_fsp_subarray_group: a mock Fsp function mode subarray tango.Group.

    :return: a dictionary of proxy mocks to pre-register.
    """
    return {
        "ska_mid/tm_leaf_node/csp_subarray_01/dopplerPhaseCorrection": mock_doppler,
        "ska_mid/tm_leaf_node/csp_subarray_01/delayModel": mock_delay,
        "ska_mid/tm_leaf_node/csp_subarray_01/jonesMatrix": mock_jones,
        "ska_mid/tm_leaf_node/csp_subarray_01/timingBeamWeights": mock_beam,
        "mid_csp_cbf/sub_elt/controller": mock_controller,
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
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/04_01": mock_fsp_subarray,
        "VCC": mock_vcc_group,
        "FSP": mock_fsp_group,
        "FSP Subarray Corr": mock_fsp_subarray_group,
        "FSP Subarray Pss": mock_fsp_subarray_group,
        "FSP Subarray Pst": mock_fsp_subarray_group,
    }


@pytest.fixture()
def subarray_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    component_callback: MockCallable,
) -> CbfSubarrayComponentManager:
    """Return a subarray component manager."""
    return CbfSubarrayComponentManager(
        subarray_id=1,
        controller="mid_csp_cbf/sub_elt/controller",
        vcc=[
            "mid_csp_cbf/vcc/001",
            "mid_csp_cbf/vcc/002",
            "mid_csp_cbf/vcc/003",
            "mid_csp_cbf/vcc/004",
            "mid_csp_cbf/vcc/005",
            "mid_csp_cbf/vcc/006",
            "mid_csp_cbf/vcc/007",
            "mid_csp_cbf/vcc/008",
        ],
        fsp=[
            "mid_csp_cbf/fsp/01",
            "mid_csp_cbf/fsp/02",
            "mid_csp_cbf/fsp/03",
            "mid_csp_cbf/fsp/04",
        ],
        fsp_corr_sub=[
            "mid_csp_cbf/fspCorrSubarray/01_01",
            "mid_csp_cbf/fspCorrSubarray/02_01",
            "mid_csp_cbf/fspCorrSubarray/03_01",
            "mid_csp_cbf/fspCorrSubarray/04_01",
        ],
        fsp_pss_sub=[
            "mid_csp_cbf/fspPssSubarray/01_01",
            "mid_csp_cbf/fspPssSubarray/02_01",
            "mid_csp_cbf/fspPssSubarray/03_01",
            "mid_csp_cbf/fspPssSubarray/04_01",
        ],
        fsp_pst_sub=[
            "mid_csp_cbf/fspPstSubarray/01_01",
            "mid_csp_cbf/fspPstSubarray/02_01",
            "mid_csp_cbf/fspPstSubarray/03_01",
            "mid_csp_cbf/fspPstSubarray/04_01",
        ],
        logger=logger,
        simulation_mode=SimulationMode.TRUE,
        push_change_event_callback=push_change_event_callback,
        component_resourced_callback=component_callback,
        component_configured_callback=component_callback,
        component_scanning_callback=component_callback,
        communication_status_changed_callback=component_callback,
        component_power_mode_changed_callback=component_callback,
        component_fault_callback=component_callback,
        component_obs_fault_callback=component_callback,
    )


@pytest.fixture()
def component_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager use.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called.
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
