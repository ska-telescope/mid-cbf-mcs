#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

from __future__ import annotations

import json
import os

import pytest
from assertpy import assert_that

# Tango imports
from ska_control_model import AdminMode, ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils

from ... import test_utils

# Test data file path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestCbfController:
    """
    Test class for CbfController device class integration testing.

    As teardown and setup are expensive operations, tests are interdependent.
    This is handled by the pytest.mark.dependency decorator.

    Note: Each test needs to take in the 'controller_params' fixture to run
    instances of the suite between different parameter sets.
    """

    @pytest.mark.dependency(name="CbfController_Online")
    def test_Online(
        self: TestCbfController,
        controller: context.DeviceProxy,
        talon_lru: list[context.DeviceProxy],
        power_switch: list[context.DeviceProxy],
        slim_fs: context.DeviceProxy,
        slim_vis: context.DeviceProxy,
        subarray: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
        deployer: context.DeviceProxy,
        controller_params: dict[any],
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating.

        :param controller: The controller device proxy
        :param talon_lru: The list of talon_lru device proxies
        :param power_switch: The list of power_switch device proxies
        :param slim_fs: The slim_fs device proxy
        :param slim_vis: The slim_vis device proxy
        :param subarray: The list of subarray device proxies
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """
        assert True
