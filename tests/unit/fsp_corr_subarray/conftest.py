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

from ska_mid_cbf_mcs.fsp.fsp_corr_subarray import FspCorrSubarray
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode

import logging

@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/fspCorrSubarray/01_01")

@pytest.fixture()
def device_to_load() -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs.fsp.fsp_corr_subarray",
        "device": "fsp-01",
        "device_class": "FspCorrSubarray",
        "proxy": CbfDeviceProxy,
        "patch": FspCorrSubarray
    }

@pytest.fixture()
def mock_cbf_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    # Mock the MaxCapabilities Cbf Controller property
    builder.add_property("MaxCapabilities", {'MaxCapabilities': ['VCC:4', 'FSP:4', 'Subarray:2']})
    # Mock the receptortoVcc Cbf Controller attribute
    # Note: Each receptor can only have one Vcc 
    builder.add_attribute("receptorToVcc", ["1:1", "2:2", "3:3"])
    return builder()

@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    # Mock the Vcc subarrayMembership attribute
    # The subarray ID for this unit test is hardcoded to 1
    builder.add_attribute("subarrayMembership", 1)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_cbf_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_cbf_controller: a mock CbfController.
    :param mock_vcc: a mock Vcc.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/sub_elt/controller": mock_cbf_controller,
        "mid_csp_cbf/vcc/001": mock_vcc
    }
