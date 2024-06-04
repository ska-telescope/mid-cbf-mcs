# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import os
import unittest

# Standard imports
from typing import Dict

import pytest
import tango

# Tango imports
from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, HealthState
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

from ... import test_utils


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/cbf_controller/001")


@pytest.fixture(name="change_event_callbacks")
def lru_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "longRunningCommandProgress",
        "state",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    builder.add_property("DeviceID", {"DeviceID": ["1"]})
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
def mock_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("obsState", ObsState.EMPTY)
    json_file_path = (
        os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
    )
    with open(json_file_path + "sys_param_4_boards.json") as f:
        sp = f.read()
    builder.add_attribute("sysParam", sp)
    with open(json_file_path + "source_init_sys_param.json") as f:
        sp = f.read()
    builder.add_attribute("sourceSysParam", sp)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
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
def mock_talon_board() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_property(
        "TalonDxBoardAddress", {"TalonDxBoardAddress": ["192.168.6.2"]}
    )
    return builder()


@pytest.fixture()
def mock_power_switch() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    return builder()


@pytest.fixture()
def mock_slim_mesh() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    builder.add_result_command("Configure", ResultCode.OK)
    return builder()


@pytest.fixture()
def initial_device_mocks(
    mock_vcc: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_subarray: unittest.mock.Mock,
    mock_talon_lru: unittest.mock.Mock,
    mock_talon_board: unittest.mock.Mock,
    mock_power_switch: unittest.mock.Mock,
    mock_slim_mesh: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of proxy mocks to pre-register.

    :param mock_vcc: a mock Vcc that is powered off.
    :param mock_fsp: a mock Fsp that is powered off.
    :param mock_subarray: a mock CbfSubarray that is powered off.
    :param mock_talon_lru: a mock TalonLRU that is powered off.
    :param mock_slim_mesh: a mock SLIM Mesh that is powered off.

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
        "mid_csp_cbf/talon_lru/002": mock_talon_lru,
        "mid_csp_cbf/talon_lru/003": mock_talon_lru,
        "mid_csp_cbf/talon_lru/004": mock_talon_lru,
        "mid_csp_cbf/talon_board/001": mock_talon_board,
        "mid_csp_cbf/talon_board/002": mock_talon_board,
        "mid_csp_cbf/talon_board/003": mock_talon_board,
        "mid_csp_cbf/talon_board/004": mock_talon_board,
        "mid_csp_cbf/talon_board/005": mock_talon_board,
        "mid_csp_cbf/talon_board/006": mock_talon_board,
        "mid_csp_cbf/talon_board/007": mock_talon_board,
        "mid_csp_cbf/talon_board/008": mock_talon_board,
        "mid_csp_cbf/power_switch/001": mock_power_switch,
        "mid_csp_cbf/power_switch/002": mock_power_switch,
        "mid_csp_cbf/slim/slim-fs": mock_slim_mesh,
        "mid_csp_cbf/slim/slim-vis": mock_slim_mesh,
    }
