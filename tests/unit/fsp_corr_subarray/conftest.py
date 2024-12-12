# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import unittest
from typing import Generator

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder


@pytest.fixture(name="device_under_test")
def fsp_corr_device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the DeviceProxy to device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/fspCorrSubarray/01_01")


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
        "longRunningCommandResult",
        "obsState",
        "adminMode",
        "state",
        "delayModel",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


@pytest.fixture()
def mock_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("receptorToVcc", ["1:1", "36:2", "63:3", "100:4"])
    builder.add_attribute("maxCapabilities", ["VCC:4", "FSP:4", "Subarray:1"])
    builder.add_property(
        "MaxCapabilities",
        {"MaxCapabilities": ["VCC:4", "FSP:4", "Subarray:1"]},
    )
    return builder()


@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    # Mock the Vcc subarrayMembership attribute
    # The subarray ID for this unit test is hardcoded to 1
    builder.add_attribute("subarrayMembership", 1)
    return builder()


@pytest.fixture()
def mock_hps_fsp_corr_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    # TODO: Update this with an appropriate string from fsp app return
    builder.add_command("SetInternalParameters", (ResultCode.OK, "Nice"))
    builder.add_command("ConfigureScan", (ResultCode.OK, "Nice"))
    builder.add_command("Scan", (ResultCode.OK, "Nice"))
    builder.add_command("EndScan", (ResultCode.OK, "Nice"))
    builder.add_command("Abort", (ResultCode.OK, "Nice"))
    builder.add_command("ObsReset", (ResultCode.OK, "Nice"))
    builder.add_command("UpdateDelayModels", (ResultCode.OK, "Nice"))
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
    mock_hps_fsp_corr_controller: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_controller: a mock CbfController.
    :param mock_vcc: a mock Vcc.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/sub_elt/controller": mock_controller,
        "mid_csp_cbf/vcc/001": mock_vcc,
        "mid_csp_cbf/talon_lru/001": mock_hps_fsp_corr_controller,
    }
