#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the FspPstSubarray."""

from __future__ import annotations

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

from tango import server

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict

class TestFspPstSubarray:
    """
    Test class for FspPstSubarray tests.
    """
    def test_On_Off(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test for FspPstSubarray device.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        
        device_under_test.On()
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id", 
        [
            (
                "/../../data/FspPstSubarray_ConfigureScan_basic.json",
                1,
            ),
                        (
                "/../../data/FspPstSubarray_ConfigureScan_basic.json",
                2,
            )
        ]
    )
    def test_Scan_EndScan_GoToIdle(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_id: int
    ) -> None:
        """
        Test Scan command state changes.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        # turn on device and configure scan
        device_under_test.On()
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        device_under_test.ConfigureScan(json_string)

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, str(scan_id))

        # Use callable 'Scan'  API
        device_under_test.Scan(scan_id_device_data)
        assert device_under_test.scanID == scan_id
        assert device_under_test.obsState == ObsState.SCANNING


        device_under_test.EndScan()
        assert device_under_test.obsState == ObsState.READY

        device_under_test.GoToIdle()
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "config_file_name",
        [
            (
                "/../../data/FspPstSubarray_ConfigureScan_basic.json"
            )
        ]
    )    
    def test_ConfigureScan_basic(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        assert device_under_test.State() == tango.DevState.OFF
        # check initial values of attributes
        # TODO: device_under_test.receptors,
        #       device_under_test.timingBeams 
        #       and device_under_test.timingBeamID 
        #       should be [] after Init 
        # assert device_under_test.receptors == []
        # assert device_under_test.timingBeams == []
        # assert device_under_test.timingBeamID == [] 
        # This is a bug in the tango library: 
        # https://gitlab.com/tango-controls/pytango/-/issues/230
        assert device_under_test.outputEnable == 0
        
        device_under_test.On()
        assert device_under_test.State() == DevState.ON

        # configure search window
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_str)
        device_under_test.ConfigureScan(json_str)
        f.close()

        for i, timingBeam in enumerate(configuration["timing_beam"]):
            assert device_under_test.timingBeams[i] == json.dumps(timingBeam)
            assert device_under_test.timingBeamID[i] == int(timingBeam["timing_beam_id"])