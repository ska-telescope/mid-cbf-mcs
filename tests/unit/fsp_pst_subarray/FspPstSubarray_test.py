#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the FspPssSubarray."""

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
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()
        time.sleep(3)
        assert device_under_test.State() == DevState.OFF
    
    def test_Scan_EndScan_GoToIdle(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Scan command state changes.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        # turn on device and configure scan
        device_under_test.On()
        time.sleep(1)
        config_file_name = "/../../data/FspPstSubarray_ConfigureScan_basic.json"
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        device_under_test.ConfigureScan(json_str)
        time.sleep(1)

        scan_id = '1'
        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, scan_id)

        # Use callable 'Scan'  API
        device_under_test.Scan(scan_id_device_data)
        time.sleep(0.1)
        assert device_under_test.scanID == int(scan_id)
        assert device_under_test.obsState == ObsState.SCANNING

        device_under_test.EndScan()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.READY

        device_under_test.GoToIdle()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

    def test_ConfigureScan_basic(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy
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
        assert device_under_test.outputEnable == 0
        
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        # configure search window
        config_file_name = "/../../data/FspPstSubarray_ConfigureScan_basic.json"
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_str)
        device_under_test.ConfigureScan(json_str)
        f.close()

        for i, timingBeam in enumerate(configuration["timing_beam"]):
            assert device_under_test.timingBeams[i] == json.dumps(timingBeam)
            assert device_under_test.timingBeamID[i] == int(timingBeam["timing_beam_id"])
    
    def test_AddRemoveReceptors_valid(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test valid AddReceptors and RemoveReceptors commands
        """

        time.sleep(3)

        # receptor list should be empty right after initialization
        #TODO: this assert should pass
        # assert device_under_test.receptors == []

        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        # add a receptor
        time.sleep(1)
        device_under_test.AddReceptors([1])
        assert device_under_test.receptors[0] == 1

        # remove the receptor
        device_under_test.RemoveReceptors([1])
        #TODO: this assert should pass
        # assert device_under_test.receptors == []

    def test_AddRemoveReceptors_invalid(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test invalid AddReceptors and RemoveReceptors commands:
            - when a receptor to be added is not in use by the subarray
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        """

        time.sleep(3)

        # receptor list should be empty right after initialization
        #TODO: this assert should pass
        # assert device_under_test.receptors == []

        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        # add some receptors
        time.sleep(1)
        device_under_test.AddReceptors([1])
        assert device_under_test.receptors[0] == 1

        # try adding an invalid receptor ID
        with pytest.raises(tango.DevFailed) as df:
            device_under_test.AddReceptors([200])
        time.sleep(1)
        assert "Invalid receptor ID" in str(df.value.args[0].desc)

        # try removing a receptor not assigned to subarray 2
        # doing this doesn't actually throw an error
        device_under_test.RemoveReceptors([5])
        assert device_under_test.receptors[0] == 1

        # remove all receptors
        device_under_test.RemoveReceptors([1])
        #TODO: this assert should pass
        # assert device_under_test.receptors == []

    def test_RemoveAllReceptors(
        self: TestFspPstSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test RemoveAllReceptors command
        """

        time.sleep(3)

        # receptor list should be empty right after initialization
        #TODO: this assert should pass
        # assert device_under_test.receptors == []

        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        # add some receptors
        time.sleep(1)
        device_under_test.AddReceptors([1])
        assert device_under_test.receptors[0] == 1

        # remove all receptors
        device_under_test.RemoveAllReceptors()
        #TODO: this assert should pass
        # assert device_under_test.receptors == []