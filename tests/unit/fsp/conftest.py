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
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

from ... import test_utils


@pytest.fixture(name="device_under_test")
def fsp_device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run

    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/fsp/01")


@pytest.fixture(name="change_event_callbacks")
def fsp_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "functionMode",
        "state",
        "subarrayMembership",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_fsp_corr_subarray_device() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_fsp_corr_subarray_device: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_fsp_corr_subarray_device: a mock FspCorrSubarray.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_corr_subarray_device,
        "mid_csp_cbf/fspCorrSubarray/01_02": mock_fsp_corr_subarray_device,
        "mid_csp_cbf/fspCorrSubarray/01_03": mock_fsp_corr_subarray_device,
        "mid_csp_cbf/fspCorrSubarray/01_04": mock_fsp_corr_subarray_device,
    }
