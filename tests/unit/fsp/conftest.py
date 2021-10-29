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
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

from ska_mid_cbf_mcs.fsp.fsp_device import Fsp
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/fsp/01")

@pytest.fixture()
def device_to_load() -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :param patched_fsp_device_class: a class for a patched Fsp
        device with extra methods for testing purposes.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs",
        "device": "fsp-01",
        "proxy": CbfDeviceProxy,
        "patch": Fsp,
    }

@pytest.fixture()
def mock_fsp_corr_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()

@pytest.fixture()
def mock_fsp_corr_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def mock_fsp_pss_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()

@pytest.fixture()
def mock_fsp_pss_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def mock_fsp_pst_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()

@pytest.fixture()
def mock_fsp_pst_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_fsp_corr_subarray: unittest.mock.Mock,
    mock_fsp_corr_subarray_group: unittest.mock.Mock,
    mock_fsp_pss_subarray: unittest.mock.Mock,
    mock_fsp_pss_subarray_group: unittest.mock.Mock,
    mock_fsp_pst_subarray: unittest.mock.Mock,
    mock_fsp_pst_subarray_group: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc: a mock Vcc that is powered off.
    :param mock_subarray: a mock VccBand4 that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspPssSubarray/01_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/03_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/04_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPstSubarray/01_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/02_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/03_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/04_01": mock_fsp_pst_subarray,
        "FSP Subarray Corr": mock_fsp_corr_subarray_group,
        "FSP Subarray Pss": mock_fsp_pss_subarray_group,
        "FSP Subarray Pst": mock_fsp_pst_subarray_group,
    }
