# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for ControllerComponentManager unit tests."""

from __future__ import annotations

# Standard imports
import logging
import pytest
import unittest
from typing import Dict, Callable

import tango

import os

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
file_path = os.path.dirname(os.path.abspath(__file__))
import json
import functools

# Local imports

from ska_mid_cbf_mcs.controller.controller_component_manager import ControllerComponentManager 
from ska_tango_base.control_model import PowerMode, SimulationMode
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback

@pytest.fixture(scope="function")
def controller_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness # sets the connection_factory
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
            pass

        def configure_talons(self: MockTalonDxComponentManager) -> ResultCode:
            return ResultCode.OK
    
    f = open(file_path + "/../../data/controller_component_manager.json")
    json_string = f.read().replace("\n", "")
    f.close()
    configuration = json.loads(json_string)

    vcc = configuration["fqdn_vcc"]
    fsp = configuration["fqdn_fsp"]
    subarray = configuration["fqdn_subarray"]
    talon_lru = configuration["fqdn_talon_lru"]

    def mock_get_num_capabilities():
        num_capbilities = {
                            "VCC": 4,
                            "FSP": 4,
                            "Subarray": 1 
                        }
        return num_capbilities
    
    def mock_communication_status_changed_callback(communication_status: CommunicationStatus):
        pass

    def mock_component_power_mode_changed_callback(power_mode: PowerMode):
        pass

    talondx_component_manager = MockTalonDxComponentManager()

    return ControllerComponentManager( 
            mock_get_num_capabilities,
            vcc,
            fsp,
            subarray,
            talon_lru,
            talondx_component_manager,
            logger,
            mock_change_event_callback_factory,
            mock_communication_status_changed_callback,
            mock_component_power_mode_changed_callback,
        )

@pytest.fixture()
def mock_change_event_callback_factory(
    mock_callback_called_timeout: float,
    mock_callback_not_called_timeout: float,
) -> Callable[[str], MockChangeEventCallback]:
    """
    Return a factory that returns a new mock change event callback each call.

    :param mock_callback_called_timeout: the time to wait for a mock
        callback to be called when a call is expected
    :param mock_callback_not_called_timeout: the time to wait for a mock
        callback to be called when a call is unexpected

    :return: a factory that returns a new mock change event callback
        each time it is called with the name of a device attribute.
    """
    return functools.partial(
        MockChangeEventCallback,
        called_timeout=mock_callback_called_timeout,
        not_called_timeout=mock_callback_not_called_timeout,
    )

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
    mock_talon_lru: unittest.mock.Mock
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