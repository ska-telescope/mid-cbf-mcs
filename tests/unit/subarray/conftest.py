# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import unittest

import pytest
import tango
from ska_control_model import (
    AdminMode,
    HealthState,
    ObsState,
    ResultCode,
    SimulationMode,
)
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

    :param test_context: the context in which the tests run

    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/sub_elt/subarray_01")


@pytest.fixture(name="change_event_callbacks")
def vcc_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "obsState",
        "receptors",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_tm() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_attribute("delayModel", "")
    return builder()


@pytest.fixture()
def mock_vcc_builder() -> unittest.mock.Mock:
    """Subarray requires unique Vcc mocks, so we return the mock builder"""
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("simulationMode", SimulationMode.TRUE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    builder.add_result_command("ConfigureScan", ResultCode.OK)
    builder.add_command("GoToIdle", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_result_command("ConfigureBand", ResultCode.OK)
    builder.add_result_command("UpdateDelayModel", ResultCode.OK)
    builder.add_command("Abort", None)
    builder.add_command("ObsReset", None)
    return builder


@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("simulationMode", SimulationMode.TRUE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("functionMode", 0)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    builder.add_result_command("AddSubarrayMembership", ResultCode.OK)
    builder.add_result_command("SetFunctionMode", ResultCode.OK)
    builder.add_result_command("RemoveSubarrayMembership", ResultCode.OK)
    builder.add_result_command("UpdateDelayModel", ResultCode.OK)
    return builder()


@pytest.fixture()
def mock_fsp_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("simulationMode", SimulationMode.TRUE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_command("GoToIdle", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_command("Abort", None)
    builder.add_command("ObsReset", None)
    builder.add_property("FspID", {"FspID": [1]})
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    builder.add_result_command("ConfigureScan", ResultCode.OK)
    return builder()


@pytest.fixture()
def mock_talon_board() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayID", "")
    builder.add_attribute("dishID", "")
    builder.add_attribute("vccID", "")
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_tm: unittest.mock.Mock,
    mock_controller: unittest.mock.Mock,
    mock_vcc_builder: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_subarray: unittest.mock.Mock,
    mock_talon_board: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of proxy mocks to pre-register.

    :param mock_delay: a mock delayModel attribute
    :param mock_controller: a mock CbfController that is powered on.
    :param mock_vcc_builder: a builder for a mock Vcc that is powered on.
    :param mock_fsp: a mock Fsp that is powered off.
    :param mock_fsp_subarray: a mock Fsp function mode subarray that is powered on.
    :param mock_talon_board: a mock talon board device

    :return: a dictionary of proxy mocks to pre-register.
    """
    return {
        "ska_mid/tm_leaf_node/csp_subarray_01": mock_tm,
        "mid_csp_cbf/sub_elt/controller": mock_controller,
        "mid_csp_cbf/vcc/001": mock_vcc_builder,
        "mid_csp_cbf/vcc/002": mock_vcc_builder,
        "mid_csp_cbf/vcc/003": mock_vcc_builder,
        "mid_csp_cbf/vcc/004": mock_vcc_builder,
        "mid_csp_cbf/fsp/01": mock_fsp,
        "mid_csp_cbf/fsp/02": mock_fsp,
        "mid_csp_cbf/fsp/03": mock_fsp,
        "mid_csp_cbf/fsp/04": mock_fsp,
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/talon_board/001": mock_talon_board,
        "mid_csp_cbf/talon_board/002": mock_talon_board,
        "mid_csp_cbf/talon_board/003": mock_talon_board,
        "mid_csp_cbf/talon_board/004": mock_talon_board,
    }
