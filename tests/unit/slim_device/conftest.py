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

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

# Tango imports
from ska_mid_cbf_mcs.testing import context
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

from ... import test_utils

# Local imports


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/slim/001")


@pytest.fixture(name="change_event_callbacks")
def slim_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture(name="device_under_test_fail")
def device_under_test_fail_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/slim_fail/001")


@pytest.fixture(name="change_event_callbacks_fail")
def slim_change_event_callbacks_fail(
    device_under_test_fail: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test_fail, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_slim_link() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute(
        "linkName", "test/slim-tx-rx/fs-tx0->test/slim-tx-rx/fs-rx0"
    )
    builder.add_attribute("tx_link_occupancy", 0.5)
    builder.add_attribute("rx_link_occupancy", 0.5)
    builder.add_attribute("counters", [0, 0, 0, 0, 0, 0, 0, 0, 0])

    builder.add_command("set_timeout_millis", None)
    builder.add_command("poll_command", None)
    builder.add_command("stop_poll_command", None)
    builder.add_command(
        "ConnectTxRx", [[ResultCode.OK], ["ConnectTxRx Success: Mock"]]
    )
    builder.add_result_command(
        "DisconnectTxRx",
        ResultCode.OK,
        "DisconnectTxRx Success: Mock",
    )
    return builder()


@pytest.fixture()
def mock_fail_slim_link() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute(
        "linkName", "test/slim-tx-rx/fs-tx0->test/slim-tx-rx/fs-rx0"
    )
    builder.add_attribute("tx_link_occupancy", 0.5)
    builder.add_attribute("rx_link_occupancy", 0.5)
    builder.add_attribute("counters", [0, 0, 0, 0, 0, 0, 0, 0, 0])

    builder.add_command("set_timeout_millis", None)
    builder.add_command("poll_command", None)
    builder.add_command("stop_poll_command", None)
    builder.add_command(
        "ConnectTxRx", [[ResultCode.FAILED], ["ConnectTxRx Failed: Mock"]]
    )
    builder.add_result_command(
        "DisconnectTxRx",
        ResultCode.FAILED,
        "DisconnectTxRx Failed: Mock",
    )
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_slim_link: unittest.mock.Mock,
    mock_fail_slim_link: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_band: a mock VccBand device that is powered off.
    :param mock_sw: a mock VccSearchWindow that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/slim_link/001": mock_slim_link,
        "mid_csp_cbf/slim_link/002": mock_slim_link,
        "mid_csp_cbf/slim_link/003": mock_slim_link,
        "mid_csp_cbf/slim_link/004": mock_slim_link,
        "mid_csp_cbf/slim_link_fail/001": mock_fail_slim_link,
        "mid_csp_cbf/slim_link_fail/002": mock_fail_slim_link,
        "mid_csp_cbf/slim_link_fail/003": mock_fail_slim_link,
        "mid_csp_cbf/slim_link_fail/004": mock_fail_slim_link,
    }
