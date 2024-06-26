# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS Slim integration tests."""

from __future__ import annotations

import random
import unittest

import pytest
import tango
from ska_tango_base.commands import ResultCode

# Tango imports
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

from ... import test_utils

@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_proxies: pytest.fixture,
) -> list[context.DeviceProxy]:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the device under test
    """
    return test_proxies.slim

@pytest.fixture(name="change_event_callbacks")
def slim_change_event_callbacks(
    device_under_test: list[context.DeviceProxy],
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    for mesh in device_under_test:
        test_utils.change_event_subscriber(
            mesh, change_event_attr_list, change_event_callbacks
        )
    return change_event_callbacks