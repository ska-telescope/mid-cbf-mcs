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
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy to device under test
    """
    return test_context.get_device("mid_csp_cbf/vcc/001")


@pytest.fixture(name="event_tracer", autouse=True)
def tango_event_tracer(
    device_under_test: context.DeviceProxy,
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :param device_under_test: the DeviceProxy to device under test
    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    change_event_attr_list = [
        "longRunningCommandResult",
        "frequencyBand",
        "obsState",
        "subarrayMembership",
        "adminMode",
        "state",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


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
def initial_mocks(
    mock_vcc_controller: unittest.mock.Mock,
    mock_vcc_band: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_controller: mock for the vcc_controller device
    :param mock_vcc_band: mock for the vcc_band device
    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "talondx-001/vcc-app/vcc-controller": mock_vcc_controller,
        "talondx-001/vcc-app/vcc-band-1-and-2": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-3": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-4": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-5": mock_vcc_band,
    }
