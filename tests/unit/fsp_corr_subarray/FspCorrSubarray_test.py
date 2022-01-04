#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the FspCorrSubarray."""

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
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict

class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray tests.
    """

    def test_On_Off(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test for FspCorrSubarray device.

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
                "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
                1,
            ),
                        (
                "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
                2,
            )
        ]
    )
    def test_Scan_EndScan_GoToIdle(
        self: TestFspCorrSubarray,
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
        time.sleep(0.1)
        assert device_under_test.scanID == scan_id
        assert device_under_test.obsState == ObsState.SCANNING


        device_under_test.EndScan()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.READY

        device_under_test.GoToIdle()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "config_file_name",
        [
            (
                "/../../data/FspCorrSubarray_ConfigureScan_basic.json"
            )
        ]
    )
    def test_ConfigureScan_basic(
        self: TestFspCorrSubarray,
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
        # Check initial values of attributes
        # TODO: device_under_test.receptors should be [] after Init not None
        # This is a bug in the tango library: 
        # https://gitlab.com/tango-controls/pytango/-/issues/230
        assert device_under_test.receptors == None
        assert device_under_test.frequencyBand == 0
        assert [device_under_test.band5Tuning[0],
                device_under_test.band5Tuning[1]] == [0, 0]
        assert device_under_test.frequencyBandOffsetStream1 == 0
        assert device_under_test.frequencyBandOffsetStream2 == 0
        assert device_under_test.frequencySliceID == 0
        assert device_under_test.corrBandwidth == 0
        assert device_under_test.zoomWindowTuning == 0
        assert device_under_test.integrationTime == 0
        assert device_under_test.scanID == 0
        assert device_under_test.configID == ""
        for i in range(const.NUM_CHANNEL_GROUPS):
            assert device_under_test.channelAveragingMap[i][0] == int(i*const.NUM_FINE_CHANNELS/const.NUM_CHANNEL_GROUPS) + 1
            assert device_under_test.channelAveragingMap[i][1] == 0
        assert device_under_test.visDestinationAddress == json.dumps({"outputHost":[], "outputMac": [], "outputPort":[]})
        assert device_under_test.fspChannelOffset == 0
        for i in range(40):
            for j in range(2):
                assert device_under_test.outputLinkMap[i][j] == 0 

        # turn device ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON

        # run ConfigureScan
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_str)
        device_under_test.ConfigureScan(json_str)
        f.close()

        # verify correct attribute values are receieved 
        for idx, receptorID in enumerate(device_under_test.receptors):
            assert receptorID == configuration["receptor_ids"][idx]
        assert device_under_test.frequencyBand == freq_band_dict()[configuration["frequency_band"]]
        assert device_under_test.frequencySliceID == configuration["frequency_slice_id"]
        if "band_5_tuning" in configuration:
            if device_under_test.frequencyBand in [4, 5]:
                band5Tuning_config = configuration["band_5_tuning"]
                for i in range(0, len(band5Tuning_config)):
                    assert device_under_test.band5Tuning[i] == band5Tuning_config[i]
        else:
            logging.info("Attribute band5Tuning not in configuration")
        
        assert device_under_test.zoomWindowTuning == configuration["zoom_window_tuning"]
        assert device_under_test.integrationTime == configuration["integration_factor"]
        channelAveragingMap_config = configuration["channel_averaging_map"]
        logging.info(channelAveragingMap_config)
        for i, chan in enumerate(channelAveragingMap_config):
            for j in range(0,len(chan)):
                assert device_under_test.channelAveragingMap[i][j] == channelAveragingMap_config[i][j]