# @pytest.fixture() - indicates helper for testing
# fixture for mock component manager
# fixture to patch fixture
# fixture to mock external proxies

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

from ska_mid_cbf_tdc_mcs.testing.mock.mock_device import MockDeviceBuilder


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/fs_links/001")


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
        "state",
        "adminMode",
        "healthState",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


@pytest.fixture()
def mock_slim_tx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 123456)
    builder.add_attribute("read_counters", [6, 7, 8])

    builder.add_command("ping", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_slim_rx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 0)
    builder.add_attribute("read_counters", [0, 1, 2, 3, 0, 0])
    builder.add_attribute("bit_error_rate", 8e-12)

    builder.add_command("ping", None)
    builder.add_command("initialize_connection", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_slim_tx_regenerate() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", None)
    builder.add_attribute("read_counters", [6, 7, 8])

    builder.add_command("ping", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_slim_rx_unhealthy() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 0)
    builder.add_attribute("read_counters", [0, 1, 2, 3, 4, 5])
    builder.add_attribute("bit_error_rate", 8e-8)

    builder.add_command("ping", None)
    builder.add_command("initialize_connection", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_slim_tx: unittest.mock.Mock,
    mock_slim_rx: unittest.mock.Mock,
    mock_slim_tx_regenerate: unittest.mock.Mock,
    mock_slim_rx_unhealthy: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_slim_tx: a mock SlimTx device.
    :param mock_slim_rx: a mock SlimRx device.
    :param mock_slim_tx_regenerate: a mock SlimTx device in regenerating state.
    :param mock_slim_rx_unhealthy: a mock SlimRx device in unhealthy state.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "talon-x/slim-tx-rx/fs-tx0": mock_slim_tx,
        "talon-x/slim-tx-rx/fs-rx0": mock_slim_rx,
        "talon-x/slim-tx-rx/fs-tx1": mock_slim_tx_regenerate,
        "talon-x/slim-tx-rx/fs-rx1": mock_slim_rx_unhealthy,
    }
