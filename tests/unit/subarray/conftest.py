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
from ska_mid_cbf_mcs.testing.mock.mock_attribute import MockAttributeBuilder
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

# uncomment the following after update to version 0.11.3 of base classes
# from ska_mid_cbf_mcs.subarray.subarray_device import CbfSubarray
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode


@pytest.fixture()
@pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
) 
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/sub_elt/subarray_01")

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
        "package": "ska_mid_cbf_mcs.subarray.subarray_device",
        "device": "cbfsubarray-01",
        "device_class": "CbfSubarray",
        "proxy": CbfDeviceProxy,
        "patch": CbfSubarray,
    }

@pytest.fixture()
def mock_doppler() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value([0.0, 0.0, 0.0, 0.0])
    return builder()

@pytest.fixture()
def mock_delay() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value("")
    return builder()

@pytest.fixture()
def mock_jones() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value("")
    return builder()

@pytest.fixture()
def mock_beam() -> unittest.mock.Mock:
    builder = MockAttributeBuilder()
    builder.add_value("")
    return builder()

@pytest.fixture()
def mock_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("receptorToVcc", ["1:1", "2:2", "3:3", "4:4"])
    builder.add_property(
        "MaxCapabilities", {'MaxCapabilities': ['VCC:4', 'FSP:4', 'Subarray:1']}
    )
    return builder()

@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    builder.add_command("ConfigureScan", None)
    builder.add_command("ConfigureSearchWindow", None)
    builder.add_command("GoToIdle", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_command("TurnOnBandDevice", None)
    builder.add_command("TurnOffBandDevice", None)
    builder.add_command("UpdateDelayModel", None)
    builder.add_command("UpdateJonesMatrix", None)
    return builder()

@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_fsp_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    builder.add_command("RemoveSubarrayMembership", None)
    builder.add_command("UpdateDelayModel", None)
    builder.add_command("UpdateJonesMatrix", None)
    builder.add_command("UpdateBeamWeights", None)
    return builder()

@pytest.fixture()
def mock_fsp_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("searchBeamID", None)
    builder.add_attribute("timingBeamID", None)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_command("GoToIdle", None)
    builder.add_command("Scan", None)
    builder.add_command("EndScan", None)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_fsp_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    builder.add_command("GoToIdle", None)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_doppler: unittest.mock.Mock,
    mock_delay: unittest.mock.Mock,
    mock_jones: unittest.mock.Mock,
    mock_beam: unittest.mock.Mock,
    mock_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
    mock_vcc_group: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_group: unittest.mock.Mock,
    mock_fsp_subarray: unittest.mock.Mock,
    mock_fsp_subarray_group: unittest.mock.Mock
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of proxy mocks to pre-register.

    :param mock_doppler: a mock dopplerPhaseCorrection attribute
    :param mock_delay: a mock delayModel attribute
    :param mock_jones: a mock jonesMatrix attribute
    :param mock_beam: a mock beamWeights attribute
    :param mock_controller: a mock CbfController that is powered on.
    :param mock_vcc: a mock Vcc that is powered on.
    :param mock_vcc_group: a mock Vcc tango.Group.
    :param mock_fsp: a mock Fsp that is powered off.
    :param mock_fsp_group: a mock Fsp tango.Group.
    :param mock_fsp_subarray: a mock Fsp function mode subarray that is powered on.
    :param mock_fsp_subarray_group: a mock Fsp function mode subarray tango.Group.

    :return: a dictionary of proxy mocks to pre-register.
    """
    return {
        "ska_mid/tm_leaf_node/csp_subarray_01/dopplerPhaseCorrection": mock_doppler,
        "ska_mid/tm_leaf_node/csp_subarray_01/delayModel": mock_delay,
        "ska_mid/tm_leaf_node/csp_subarray_01/jonesMatrix": mock_jones,
        "ska_mid/tm_leaf_node/csp_subarray_01/beamWeights": mock_beam,
        "mid_csp_cbf/sub_elt/controller": mock_controller,
        "mid_csp_cbf/vcc/001": mock_vcc,
        "mid_csp_cbf/vcc/002": mock_vcc,
        "mid_csp_cbf/vcc/003": mock_vcc,
        "mid_csp_cbf/vcc/004": mock_vcc,
        "mid_csp_cbf/fsp/01": mock_fsp,
        "mid_csp_cbf/fsp/02": mock_fsp,
        "mid_csp_cbf/fsp/03": mock_fsp,
        "mid_csp_cbf/fsp/04": mock_fsp,
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/04_01": mock_fsp_subarray,
        "VCC": mock_vcc_group,
        "FSP": mock_fsp_group,
        "FSP Subarray Corr": mock_fsp_subarray_group,
        "FSP Subarray Pss": mock_fsp_subarray_group,
        "FSP Subarray Pst": mock_fsp_subarray_group,
    }
