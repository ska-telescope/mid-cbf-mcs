# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS Slim integration tests."""

from __future__ import annotations

import pytest

# Tango imports
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ... import test_utils


@pytest.fixture(name="device_under_test")
def device_under_test_fixture() -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the device under test
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/talon_board/001")


@pytest.fixture(name="change_event_callbacks")
def talon_board_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "lrcFinished",
        "State",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks
