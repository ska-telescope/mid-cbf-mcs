#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Vcc."""

from __future__ import annotations
from typing import List

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# Path
file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

from ska_tango_base.control_model import HealthState, AdminMode, ObsState, LoggingLevel
from ska_tango_base.commands import ResultCode

CONST_WAIT_TIME = 4

class TestVccBand:
    """
    Test class for VccBand tests.
    """

    def test_On_Off(
        self: TestVccBand,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.state() == DevState.OFF

        (result_code, msg) = device_under_test.On()
        assert result_code == ResultCode.OK
        assert device_under_test.state() == DevState.ON
        (result_code, msg) = device_under_test.Off()
        assert result_code == ResultCode.OK
        assert device_under_test.state() == DevState.OFF


