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
from typing import Dict, Iterator, Optional, Tuple, Type

import pytest
import pytest_mock
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerState
from ska_tango_testing.harness import TangoTestHarness
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.slim.slim_device import Slim

# Tango imports
from ska_mid_cbf_mcs.slim.slim_link_device import SlimLink
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import (
    DeviceToLoadType,
    TangoHarness,
)
from ska_mid_cbf_mcs.testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
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
    return test_context.get_device("mid_csp_cbf/slim/001")


@pytest.fixture(name="change_event_callbacks")
def slim_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "longRunningCommandProgress",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks

@pytest.fixture()
def mock_slim_link() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_command("set_timeout_millis", None)
    builder.add_command("poll_command", None)
    builder.add_result_command(
        "ConnectTxRx", ResultCode.OK, "Connected Tx Rx successfully: Mock"
    )
    return builder()
