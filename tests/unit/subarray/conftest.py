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
from typing import Generator

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
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

# Paths
file_path = os.path.dirname(os.path.abspath(__file__))
vis_slim_config_path = file_path + "/../../../mnt/slim/vis/slim_config.yaml"


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/sub_elt/subarray_01")


@pytest.fixture(name="event_tracer", autouse=True)
def tango_event_tracer(
    device_under_test: context.DeviceProxy,
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :param device_under_test: the DeviceProxy for the device under test
    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    change_event_attr_list = [
        "lrcFinished",
        "obsState",
        "receptors",
        "sysParam",
        "adminMode",
        "state",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


@pytest.fixture()
def mock_tm() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_attribute("delayModel", "")
    return builder


@pytest.fixture()
def mock_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("validateSupportedConfiguration", True)
    builder.add_attribute("receptorToVcc", ["1:1", "36:2", "63:3", "100:4"])
    builder.add_attribute("maxCapabilities", ["VCC:4", "FSP:4", "Subarray:1"])
    builder.add_property(
        "MaxCapabilities",
        {"MaxCapabilities": ["VCC:4", "FSP:4", "Subarray:1"]},
    )
    return builder


@pytest.fixture()
def mock_vcc_builder() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("simulationMode", SimulationMode.TRUE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("lrcFinished", ("", ""))
    builder.add_lrc(
        name="ConfigureBand",
        result_code=ResultCode.OK,
        message="ConfigureBand completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="ConfigureScan",
        result_code=ResultCode.OK,
        message="ConfigureScan completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="Scan",
        result_code=ResultCode.OK,
        message="Scan completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="EndScan",
        result_code=ResultCode.OK,
        message="EndScan completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="GoToIdle",
        result_code=ResultCode.OK,
        message="GoToIdle completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="Abort",
        result_code=ResultCode.OK,
        message="Abort completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="ObsReset",
        result_code=ResultCode.OK,
        message="ObsReset completed OK",
        queued=True,
    )
    return builder


@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("simulationMode", SimulationMode.TRUE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("functionMode", 0)
    builder.add_attribute("subarrayMembership", [])
    builder.add_lrc(
        name="AddSubarrayMembership",
        result_code=ResultCode.OK,
        message="AddSubarrayMembership completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="RemoveSubarrayMembership",
        result_code=ResultCode.OK,
        message="RemoveSubarrayMembership completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="SetFunctionMode",
        result_code=ResultCode.OK,
        message="SetFunctionMode completed OK",
        queued=True,
    )
    return builder


@pytest.fixture()
def mock_fsp_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("simulationMode", SimulationMode.TRUE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_property("FspID", {"FspID": [1]})
    builder.add_result_command("UpdateDelayModel", ResultCode.OK)
    builder.add_lrc(
        name="ConfigureScan",
        result_code=ResultCode.OK,
        message="ConfigureScan completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="Scan",
        result_code=ResultCode.OK,
        message="Scan completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="EndScan",
        result_code=ResultCode.OK,
        message="EndScan completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="GoToIdle",
        result_code=ResultCode.OK,
        message="GoToIdle completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="Abort",
        result_code=ResultCode.OK,
        message="Abort completed OK",
        queued=True,
    )
    builder.add_lrc(
        name="ObsReset",
        result_code=ResultCode.OK,
        message="ObsReset completed OK",
        queued=True,
    )
    return builder


@pytest.fixture()
def mock_talon_board() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayID", "")
    builder.add_attribute("dishID", "SKA001")
    builder.add_attribute("vccID", "1")
    return builder


@pytest.fixture()
def mock_vis_mesh() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    with open(vis_slim_config_path) as f:
        mesh_config_str = f.read()
    builder.add_attribute("meshConfiguration", mesh_config_str)
    return builder


@pytest.fixture()
def mock_host_lut_s1() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("host_lut_stage_2_device_name", "")
    builder.add_attribute("channel_offset", 0)
    builder.add_command("connectToHostLUTStage2", ResultCode.OK)
    builder.add_command("Program", ResultCode.OK)
    builder.add_command("Unprogram", ResultCode.OK)
    return builder


@pytest.fixture()
def mock_host_lut_s2() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("host_lut_s1_chan_offsets", [0])
    builder.add_command("Program", ResultCode.OK)
    builder.add_command("Unprogram", ResultCode.OK)
    return builder


@pytest.fixture()
def mock_spead_desc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_command("StartScan", ResultCode.OK)
    builder.add_command("EndScan", ResultCode.OK)
    return builder


@pytest.fixture()
def initial_mocks(
    mock_tm: unittest.mock.Mock,
    mock_controller: unittest.mock.Mock,
    mock_vcc_builder: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_subarray: unittest.mock.Mock,
    mock_talon_board: unittest.mock.Mock,
    mock_vis_mesh: unittest.mock.Mock,
    mock_host_lut_s1: unittest.mock.Mock,
    mock_host_lut_s2: unittest.mock.Mock,
    mock_spead_desc: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of proxy mocks to pre-register.

    :param mock_tm: a mock TM.
    :param mock_controller: a mock CbfController.
    :param mock_vcc_builder: a mock Vcc builder.
    :param mock_fsp: a mock Fsp.
    :param mock_fsp_subarray: a mock FspCorrSubarray.
    :param mock_talon_board: a mock TalonBoard.
    :param mock_vis_mesh: a mock SlimMesh.
    :param mock_host_lut_s1: a mock HostLutStage1.
    :param mock_host_lut_s2: a mock HostLutStage2.
    :param mock_spead_desc: a mock SpeadDescriptor.

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
        "mid_csp_cbf/slim/slim-vis": mock_vis_mesh,
        "talondx-001/dshostlutstage1/host_lut_s1": mock_host_lut_s1,
        "talondx-002/dshostlutstage1/host_lut_s1": mock_host_lut_s1,
        "talondx-003/dshostlutstage1/host_lut_s1": mock_host_lut_s1,
        "talondx-004/dshostlutstage1/host_lut_s1": mock_host_lut_s1,
        "talondx-001/dshostlutstage2/host_lut_s2": mock_host_lut_s2,
        "talondx-001/dsspeaddescriptor/spead": mock_spead_desc,
    }
