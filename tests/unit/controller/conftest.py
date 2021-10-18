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
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_group() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_group_command("On", ResultCode.OK)
    builder.add_group_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_fsp_group() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_group_command("On", ResultCode.OK)
    builder.add_group_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_subarray_group() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_group_command("On", ResultCode.OK)
    builder.add_group_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_vcc: unittest.mock.Mock,
    mock_vcc_group: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_group: unittest.mock.Mock,
    mock_subarray: unittest.mock.Mock,
    mock_subarray_group: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc: a mock Vcc that is powered off.
    :param mock_fsp: a mock VccBand3 that is powered off.
    :param mock_subarray: a mock VccBand4 that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    vcc = [
        "mid_csp_cbf/vcc/001",
        "mid_csp_cbf/vcc/002",
        "mid_csp_cbf/vcc/003",
        "mid_csp_cbf/vcc/004",
    ]
    fsp = [
        "mid_csp_cbf/fsp/01",
        "mid_csp_cbf/fsp/02",
        "mid_csp_cbf/fsp/03",
        "mid_csp_cbf/fsp/04",
    ]
    subarray = [
        "mid_csp_cbf/sub_elt/subarray_01",
        "mid_csp_cbf/sub_elt/subarray_02",
        "mid_csp_cbf/sub_elt/subarray_03",
    ]
    return {
        vcc[0]: mock_vcc,
        vcc[1]: mock_vcc,
        vcc[2]: mock_vcc,
        vcc[3]: mock_vcc,
        fsp[0]: mock_fsp,
        fsp[1]: mock_fsp,
        fsp[2]: mock_fsp,
        fsp[3]: mock_fsp,
        subarray[0]: mock_subarray,
        subarray[1]: mock_subarray,
        subarray[2]: mock_subarray,
        ''.join(vcc): mock_vcc_group,
        ''.join(fsp): mock_fsp_group,
        ''.join(subarray): mock_subarray_group,
    }
