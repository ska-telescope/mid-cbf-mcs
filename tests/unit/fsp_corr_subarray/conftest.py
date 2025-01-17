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
from ska_control_model import HealthState
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


@pytest.fixture(name="device_under_test_unhealthy")
def fsp_corr_device_under_test_unhealthy_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the DeviceProxy to the unhealthy device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/fspCorrSubarray/02_01")


@pytest.fixture(name="event_tracer_unhealthy", autouse=True)
def tango_event_tracer_unhealthy(
    device_under_test_unhealthy: context.DeviceProxy,
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
        tracer.subscribe_event(device_under_test_unhealthy, attr)

    return tracer


@pytest.fixture()
def mock_hps_fsp_corr_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_command("SetInternalParameters", None)
    builder.add_command("ConfigureScan", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_command("Abort", None)
    builder.add_command("ObsReset", None)
    builder.add_command("UpdateDelayModels", None)
    builder.add_attribute("healthState", HealthState.OK)
    return builder()


@pytest.fixture()
def mock_hps_fsp_corr_controller_unhealthy() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_command("SetInternalParameters", None)
    builder.add_command("ConfigureScan", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_command("Abort", None)
    builder.add_command("ObsReset", None)
    builder.add_command("UpdateDelayModels", None)
    builder.add_attribute("healthState", HealthState.FAILED)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_hps_fsp_corr_controller: unittest.mock.Mock,
    mock_hps_fsp_corr_controller_unhealthy: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_hps_fsp_corr_controller: a mock FspCorrController.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "talondx-001/fsp-app/fsp-corr-controller": mock_hps_fsp_corr_controller,
        "talondx-002/fsp-app/fsp-corr-controller": mock_hps_fsp_corr_controller_unhealthy,
    }
