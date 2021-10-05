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

# TODO: see TODO in src/ska_mid_cbf_mcs/testing/tango_harness.py
@pytest.fixture()
def device_to_load() -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs",
        "device": "fsp-01",
        "proxy": CbfDeviceProxy,
        "patch": FspCorrSubarray
    }

#TODO mock controller max capabilities
@pytest.fixture()
def mock_cbf_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_property({'MaxCapabilities': ['VCC:4', 'FSP:4', 'Subarray:2']})
    builder.add_attribute("receptorToVcc", ["1:2", "1:1", "2:1"])
    return builder()

@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_attribute("subarrayMembership", 1)
    return builder()

@pytest.fixture()
def mock_cbf_subarray_1() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    return builder()

@pytest.fixture()
def mock_fsp_pss_subarray_2_1() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_cbf_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
    mock_cbf_subarray_1: unittest.mock.Mock,
    mock_fsp_pss_subarray_2_1: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_cbf_controller: a mock CbfController.
    :param mock_vcc: a mock Vcc.
    :param mock_cbf_subarray_1: a mock CbfSubarray.
    :param mock_fsp_pss_subarray_2_1: a mock FspPssSubarray.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/sub_elt/controller": mock_cbf_controller,
        "mid_csp_cbf/vcc/001": mock_vcc,
        "mid_csp_cbf/sub_elt/subarray_01": mock_cbf_subarray_1,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_pss_subarray_2_1,
    }
