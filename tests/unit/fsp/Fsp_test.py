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
    
    @pytest.mark.parametrize(
        "sub_ids", 
        [
            (
                [3, 4, 15]
            ),
            (
                [5, 1, 2]
            )
        ]
    )
    def test_AddRemoveSubarrayMembership(
        self: TestFsp,
        device_under_test: CbfDeviceProxy,
        sub_ids: List[int]
    ) -> None:

        device_under_test.On()
        assert device_under_test.State() == DevState.ON

        # subarray membership should be empty
        assert device_under_test.subarrayMembership == None

        # add fsp to all but last test subarray
        for sub_id in sub_ids[:-1]:
            device_under_test.AddSubarrayMembership(sub_id)
        time.sleep(5)
        for idx, sub_id in enumerate(sub_ids[:-1]):
            assert device_under_test.read_attribute("subarrayMembership", \
                extract_as=tango.ExtractAs.List).value[idx] == sub_ids[:-1][idx]

        # remove fsp from first test subarray
        device_under_test.RemoveSubarrayMembership(sub_ids[0])
        time.sleep(5)
        for idx, sub_id in enumerate(sub_ids[1:-1]):
            assert device_under_test.read_attribute("subarrayMembership", \
                extract_as=tango.ExtractAs.List).value[idx] == sub_ids[1:-1][idx]
        
        # add fsp to last test subarray
        device_under_test.AddSubarrayMembership(sub_ids[-1])
        time.sleep(5)
        for idx, sub_id in enumerate(sub_ids[1:]):
            assert device_under_test.read_attribute("subarrayMembership", \
                extract_as=tango.ExtractAs.List).value[idx] == sub_ids[1:][idx]
       
        # remove fsp from all subarrays
        for sub_id in sub_ids:
            device_under_test.RemoveSubarrayMembership(sub_id)
        time.sleep(5)
        assert device_under_test.subarrayMembership == None
