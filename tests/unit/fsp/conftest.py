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
from ska_control_model import ResultCode
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder


@pytest.fixture(name="device_under_test")
def fsp_device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the DeviceProxy to device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/fsp/01")


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
        "functionMode",
        "subarrayMembership",
        "adminMode",
        "state",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


@pytest.fixture()
def mock_fsp_corr_subarray_device() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_command("On", (ResultCode.OK, "test"))
    builder.add_command("Off", (ResultCode.OK, "test"))
    return builder()


@pytest.fixture()
def mock_fsp_pst_subarray_device() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    # add vccIDs to the mock pst subarray
    # (this is required for test_UpdateBeamWeights)
    builder.add_attribute("vccIDs", [1, 2, 3, 4])
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_fsp_corr_subarray_device: unittest.mock.Mock,
    mock_fsp_pst_subarray_device: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_fsp_corr_subarray_device: a mock FspCorrSubarray.
    :param mock_fsp_pst_subarray_device: a mock FspPstSubarray.
    :return: a dictionary of device proxy mocks to pre-register.
    """
    mocks = {}
    for sub_id in range(1, const.MAX_SUBARRAY + 1):
        mocks[
            f"mid_csp_cbf/fspCorrSubarray/01_{sub_id:02}"
        ] = mock_fsp_corr_subarray_device
        mocks[
            f"mid_csp_cbf/fspPstSubarray/01_{sub_id:02}"
        ] = mock_fsp_pst_subarray_device
    return mocks
