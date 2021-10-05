# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

# Standard imports
from typing import Callable, Type, Dict
import pytest
import unittest

# Tango imports
import tango
from tango import DevState
from tango.server import command

#Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

from ska_mid_cbf_mcs.controller.controller_device import CbfController
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/sub_elt/controller")

@pytest.fixture()
def device_to_load() -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :param patched_vcc_device_class: a class for a patched Vcc
        device with extra methods for testing purposes.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs",
        "device": "controller",
        "proxy": CbfDeviceProxy,
        "patch": CbfController,
    }

@pytest.fixture()
def mock_vcc_band12() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_band3() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_band4() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_band5() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Disable", ResultCode.OK)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_vcc_band12: unittest.mock.Mock,
    mock_vcc_band3: unittest.mock.Mock,
    mock_vcc_band4: unittest.mock.Mock,
    mock_vcc_band5: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc_band12: a mock VccBand1And2 that is powered off.
    :param mock_vcc_band3: a mock VccBand3 that is powered off.
    :param mock_vcc_band4: a mock VccBand4 that is powered off.
    :param mock_vcc_band5: a mock VccBand5 that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/vcc_band12/001": mock_vcc_band12,
        "mid_csp_cbf/vcc_band3/001": mock_vcc_band3,
        "mid_csp_cbf/vcc_band4/001": mock_vcc_band4,
        "mid_csp_cbf/vcc_band5/001": mock_vcc_band5,
    }
