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

@pytest.fixture()
def patched_fsp_corr_subarray_class() -> Type[FspCorrSubarray]:
    """
    Return a FspCorrSubarray device class, patched with extra methods for testing.

    :return: a patched FspCorrSubarray device class, patched with extra methods
        for testing
    """

    class PatchedFspCorrSubarrayDevice(FspCorrSubarray):
        """
        FspCorrSubarray patched with extra commands for testing purposes.

        The extra commands allow us to mock the receipt of obs state
        change events from subservient devices.
        """

        @command(dtype_in=int)
        def FakeSubservientDevicesObsState(
            self,
            obs_state: ObsState
        ) -> None:
            obs_state = ObsState(obs_state)

            # for fqdn in self.component_manager._device_obs_states:
            #     self.component_manager._device_obs_state_changed(fqdn, obs_state)

    return PatchedFspCorrSubarrayDevice


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/fspCorrSubarray/01_01")

@pytest.fixture()
def device_to_load(
    patched_fsp_corr_subarray_class: Type[FspCorrSubarray],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :param patched_fsp_corr_subarray_class: a class for a patched FspCorrSubarray
        device with extra methods for testing purposes.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs",
        "device": "fsp-01",
        "proxy": CbfDeviceProxy,
        "patch": patched_fsp_corr_subarray_class,
    }

@pytest.fixture()
def mock_cbf_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    return builder()

@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    return builder()

@pytest.fixture()
def mock_cbf_subarray_1() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("receptors", ())
    return builder()

@pytest.fixture()
def mock_fsp_pss_subarray_2_1() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("receptors", ())
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
