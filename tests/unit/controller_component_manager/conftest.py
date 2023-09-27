# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for ControllerComponentManager unit tests."""

from __future__ import annotations

import json

# Standard imports
import logging
import os
import unittest
from typing import Callable, Dict

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    ObsState,
    SimulationMode,
)

from ska_mid_cbf_mcs.controller.controller_component_manager import (
    ControllerComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

file_path = os.path.dirname(os.path.abspath(__file__))


# Local imports


CONST_TEST_NUM_VCC = 8
CONST_TEST_NUM_FSP = 4
CONST_TEST_NUM_SUBARRAY = 1


@pytest.fixture()
def controller_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> ControllerComponentManager:
    """
    Return a Controller component manager.

    :param logger: the logger fixture

    :return: a Controller component manager.
    """

    class MockTalonDxComponentManager:
        """
        Class to mock the TalonDxComponentManager.
        """

        def __init__(self: MockTalonDxComponentManager) -> None:
            self.simulation_mode = SimulationMode.TRUE
            pass

        def configure_talons(self: MockTalonDxComponentManager) -> ResultCode:
            return ResultCode.OK

        def shutdown(
            self: MockTalonDxComponentManager, argin: int
        ) -> ResultCode:
            return ResultCode.OK

    f = open(file_path + "/../../data/test_fqdns.json")
    json_string = f.read().replace("\n", "")
    f.close()
    configuration = json.loads(json_string)

    vcc = configuration["fqdn_vcc"]
    fsp = configuration["fqdn_fsp"]
    subarray = configuration["fqdn_subarray"]
    talon_lru = configuration["fqdn_talon_lru"]
    talon_board = configuration["fqdn_talon_board"]
    power_switch = configuration["fqdn_power_switch"]

    def mock_get_num_capabilities():
        num_capabilities = {
            "VCC": CONST_TEST_NUM_VCC,
            "FSP": CONST_TEST_NUM_FSP,
        }
        return num_capabilities

    talondx_component_manager = MockTalonDxComponentManager()

    talondx_config_path = "mnt/talondx-config/"
    hw_config_path = "mnt/hw_config/hw_config.yaml"

    component_manager = ControllerComponentManager(
        get_num_capabilities=mock_get_num_capabilities,
        subarray_fqdns_all=subarray,
        vcc_fqdns_all=vcc,
        fsp_fqdns_all=fsp,
        talon_lru_fqdns_all=talon_lru,
        talon_board_fqdns_all=talon_board,
        power_switch_fqdns_all=power_switch,
        lru_timeout=20,
        talondx_component_manager=talondx_component_manager,
        talondx_config_path=talondx_config_path,
        hw_config_path=hw_config_path,
        logger=logger,
        push_change_event=push_change_event_callback,
        communication_status_changed_callback=communication_status_changed_callback,
        component_power_mode_changed_callback=component_power_mode_changed_callback,
        component_fault_callback=component_fault_callback,
    )
    component_manager._vcc_to_receptor = {1: 1, 2: 36, 3: 63, 4: 100}
    return component_manager


@pytest.fixture()
def component_fault_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock]
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


@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("frequencyOffsetF", 0)
    builder.add_attribute("frequencyOffsetDeltaK", 0)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_property("VccID", {"VccID": ["1"]})
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
    builder.add_attribute("obsState", ObsState.EMPTY)
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
def mock_talon_board() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
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
def mock_power_switch() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_vcc: unittest.mock.Mock,
    mock_vcc_group: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_group: unittest.mock.Mock,
    mock_subarray: unittest.mock.Mock,
    mock_subarray_group: unittest.mock.Mock,
    mock_talon_board: unittest.mock.Mock,
    mock_talon_lru: unittest.mock.Mock,
    mock_power_switch: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc: a mock Vcc that is powered off.
    :param mock_fsp: a mock VccBand3 that is powered off.
    :param mock_subarray: a mock VccBand4 that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
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
        "mid_csp_cbf/talon_board/001": mock_talon_board,
        "mid_csp_cbf/talon_board/002": mock_talon_board,
        "mid_csp_cbf/talon_board/003": mock_talon_board,
        "mid_csp_cbf/talon_board/004": mock_talon_board,
        "mid_csp_cbf/talon_board/005": mock_talon_board,
        "mid_csp_cbf/talon_board/006": mock_talon_board,
        "mid_csp_cbf/talon_board/007": mock_talon_board,
        "mid_csp_cbf/talon_board/008": mock_talon_board,
        "mid_csp_cbf/talon_lru/001": mock_talon_lru,
        "mid_csp_cbf/talon_lru/002": mock_talon_lru,
        "mid_csp_cbf/talon_lru/003": mock_talon_lru,
        "mid_csp_cbf/talon_lru/004": mock_talon_lru,
        "mid_csp_cbf/power_switch/001": mock_power_switch,
        "mid_csp_cbf/power_switch/002": mock_power_switch,
        "VCC": mock_vcc_group,
        "FSP": mock_fsp_group,
        "CBF Subarray": mock_subarray_group,
    }
