#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

from __future__ import annotations

# Standard imports
import os
import pytest
import unittest
import time

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
from tango import DevState
from tango.server import command

#SKA imports
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import AdminMode

CONST_WAIT_TIME = 5

class TestCbfController:
    """
    Test class for CbfController tests.
    """
    
    def test_State(
        self: TestCbfController,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE
    
    def test_Status(
        self: TestCbfController,
        device_under_test: CbfDeviceProxy,
    ) -> None:

        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestCbfController,
        device_under_test: CbfDeviceProxy,
    ) -> None:

        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize(
        "command",
        [
            "On",
            "Off",
            "Standby"
        ]
    )
    def test_Commands(
        self: TestCbfController,
        device_under_test: CbfDeviceProxy,
        command: str
    ) -> None:
        """
        Test On command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF

        if command == "On":
            state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            state = DevState.OFF
            result = device_under_test.Off()
        elif command == "Standby":
            state = DevState.STANDBY
            result = device_under_test.Standby()

        time.sleep(CONST_WAIT_TIME)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == state