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
from ska_tango_base.control_model import PowerState
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
    return test_context.get_device("mid_csp_cbf/vcc/001")


@pytest.fixture(name="change_event_callbacks")
def vcc_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "longRunningCommandProgress",
        "frequencyBand",
        "obsState",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_talon_lru() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_attribute("LRUPowerState", PowerState.OFF)
    return builder()


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
    mock_talon_lru: unittest.mock.Mock,
    mock_vcc_controller: unittest.mock.Mock,
    mock_vcc_band: unittest.mock.Mock,
    mock_sw: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_band: a mock VccBand device that is powered off.
    :param mock_sw: a mock VccSearchWindow that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/talon_lru/001": mock_talon_lru,
        "talondx-001/vcc-app/vcc-controller": mock_vcc_controller,
        "talondx-001/vcc-app/vcc-band-1-and-2": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-3": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-4": mock_vcc_band,
        "talondx-001/vcc-app/vcc-band-5": mock_vcc_band,
    }
