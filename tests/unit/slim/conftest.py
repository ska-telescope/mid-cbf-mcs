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
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
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
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/slim/001")


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
        "adminMode",
        "state",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


@pytest.fixture(name="device_under_test_fail")
def device_under_test_fail_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test. For testing failure conditions.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test for failure conditions
    """
    return test_context.get_device("mid_csp_cbf/slim_fail/001")


@pytest.fixture(name="event_tracer_fail", autouse=True)
def tango_event_tracer_fail(
    device_under_test_fail: context.DeviceProxy,
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for the device used to test failure conditions.
    Takes as parameter all required device proxy fixtures for this test module.

    :param device_under_test: the DeviceProxy for the device under test for failure conditions
    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    change_event_attr_list = [
        "longRunningCommandResult",
        "state",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test_fail, attr)

    return tracer


@pytest.fixture()
def mock_slim_link() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("adminMode", AdminMode.OFFLINE)
    builder.add_attribute(
        "linkName",
        "talondx-001/slim-tx-rx/fs-tx0->talondx-001/slim-tx-rx/fs-rx0",
    )
    builder.add_attribute("longRunningCommandResult", ("", ""))
    builder.add_attribute("txLinkOccupancy", 0.5)
    builder.add_attribute("rxLinkOccupancy", 0.5)
    builder.add_attribute(
        "counters", [1000, 100, 1000, 0, 0, 0, 1000, 100, 1000]
    )
    builder.add_attribute(
        "rxDebugAlignmentAndLockStatus", [False, True, False, True]
    )

    builder.add_command("set_timeout_millis", None)
    builder.add_command("poll_command", None)
    builder.add_command("stop_poll_command", None)
    builder.add_lrc(
        name="ConnectTxRx",
        result_code=ResultCode.OK,
        message="ConnectTxRx completed OK",
        queued=True,
        attr_values={},
    )
    builder.add_lrc(
        name="DisconnectTxRx",
        result_code=ResultCode.OK,
        message="DisconnectTxRx completed OK",
        queued=True,
        attr_values={},
    )
    return builder


@pytest.fixture()
def mock_fail_slim_link() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("adminMode", AdminMode.OFFLINE)
    builder.add_attribute(
        "linkName",
        "talondx-001/slim-tx-rx/fs-tx0->talondx-001/slim-tx-rx/fs-rx0",
    )
    builder.add_attribute("longRunningCommandResult", ("", ""))
    builder.add_attribute("tx_link_occupancy", 0.5)
    builder.add_attribute("rx_link_occupancy", 0.5)
    builder.add_attribute(
        "counters", [1000, 100, 1000, 1, 0, 0, 1000, 100, 1000]
    )
    builder.add_attribute(
        "rx_debug_alignment_and_lock_status", [False, True, False, True]
    )

    builder.add_command("set_timeout_millis", None)
    builder.add_command("poll_command", None)
    builder.add_command("stop_poll_command", None)
    builder.add_lrc(
        name="ConnectTxRx",
        queued=False,
    )
    builder.add_lrc(
        name="DisconnectTxRx",
        queued=False,
    )
    return builder


@pytest.fixture()
def mock_slim_tx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 123456)
    builder.add_attribute("read_counters", [6, 7, 8])

    builder.add_command("ping", None)
    builder.add_command("clear_read_counters", None)
    return builder


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
    return builder


@pytest.fixture()
def initial_mocks(
    mock_slim_tx: unittest.mock.Mock,
    mock_slim_rx: unittest.mock.Mock,
    mock_slim_link: unittest.mock.Mock,
    mock_fail_slim_link: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_slim_tx: a mock SlimTx device.
    :param mock_slim_rx: a mock SlimRx device.
    :param mock_slim_link: a mock SlimLink device.
    :param mock_fail_slim_link: a mock SlimLink device that rejects commands.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "talondx-001/slim-tx-rx/fs-tx0": mock_slim_tx,
        "talondx-002/slim-tx-rx/fs-tx0": mock_slim_tx,
        "talondx-003/slim-tx-rx/fs-tx0": mock_slim_tx,
        "talondx-004/slim-tx-rx/fs-tx0": mock_slim_tx,
        "talondx-001/slim-tx-rx/fs-rx0": mock_slim_rx,
        "talondx-001/slim-tx-rx/fs-rx1": mock_slim_rx,
        "talondx-001/slim-tx-rx/fs-rx2": mock_slim_rx,
        "talondx-001/slim-tx-rx/fs-rx3": mock_slim_rx,
        "mid_csp_cbf/slim_link/001": mock_slim_link,
        "mid_csp_cbf/slim_link/002": mock_slim_link,
        "mid_csp_cbf/slim_link/003": mock_slim_link,
        "mid_csp_cbf/slim_link/004": mock_slim_link,
        "mid_csp_cbf/slim_link_fail/001": mock_fail_slim_link,
        "mid_csp_cbf/slim_link_fail/002": mock_fail_slim_link,
        "mid_csp_cbf/slim_link_fail/003": mock_fail_slim_link,
        "mid_csp_cbf/slim_link_fail/004": mock_fail_slim_link,
    }
