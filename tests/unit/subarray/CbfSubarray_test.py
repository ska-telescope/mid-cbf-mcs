#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfSubarray."""

from __future__ import annotations

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestCbfSubarray:
    """
    Test class for TestCbfSubarray tests.
    """

    def test_State(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.OFF

    def test_On(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test On command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        result = device_under_test.On()
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == DevState.ON

    def test_Off(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Off command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        result = device_under_test.Off()
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == DevState.OFF

