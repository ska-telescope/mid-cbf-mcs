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

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestFsp:
    """
    Test class for CbfController tests.
    """

    def test_On_Off(
        self: TestFsp,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test for Fsp device.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
    
        assert device_under_test.State() == DevState.OFF

        device_under_test.On()
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()
        assert device_under_test.State() == DevState.OFF