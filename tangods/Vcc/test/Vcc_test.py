#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfMaster."""

# Standard imports
import sys
import os
import time
import json
import copy

import logging

# Path
file_path = os.path.dirname(os.path.abspath(__file__))
# insert base package directory to import global_enum 
# module in commons folder
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, os.path.abspath(path))

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports

from Vcc.Vcc import Vcc
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base import SKABaseDevice, DeviceStateModel
from ska_tango_base.commands import ResultCode

@pytest.mark.usefixtures(
    "debug_device_is_on",
    "create_vcc_proxy",
    "create_band_12_proxy",
    "create_band_3_proxy",
    "create_band_4_proxy",
    "create_band_5_proxy",
    "create_sw_1_proxy"
)

class TestVcc:

    def test_SetFrequencyBand(
            self,
            debug_device_is_on,
            create_vcc_proxy,
            create_band_12_proxy,
            create_band_3_proxy,
            create_band_4_proxy,
            create_band_5_proxy
    ):
        """
        Test SetFrequencyBand command state changes.
        """

        logging.info("debug_device_is_on = {}".format(debug_device_is_on))       
        if debug_device_is_on == True:
            timeout_millis = 700000 
            create_vcc_proxy.set_timeout_millis(timeout_millis)
            port = create_vcc_proxy.DebugDevice()

        # NOTE: this check is needed only while debugging this test TODO - remove
        if create_vcc_proxy.obsState  == ObsState.SCANNING:
            create_vcc_proxy.EndScan() 
        
        logging.info( ("create_band_12_proxy.State() = {}".
        format( create_band_12_proxy.State())) )

        logging.info( ("create_band_3_proxy.State() = {}".
        format( create_band_3_proxy.State())) )

        sleep_seconds = 2

        #create_band_3_proxy.Init() # may not be needed ? TODO
        # time.sleep(sleep_seconds)

        # logging.info( ("create_band_3_proxy.State() after Init() and sleep = {}".
        # format( create_band_3_proxy.State())) )

        # Can use the callable version or the 'command_inout' version of the 'On' command
        #create_band_12_proxy.On()
        create_band_12_proxy.command_inout("On")
        create_band_3_proxy.Disable()
        time.sleep(sleep_seconds)
        logging.info( ("create_band_12_proxy.State() after On() = {}".
        format( create_band_12_proxy.State())) )

        logging.info( ("create_band_3_proxy.State() after Disable() = {}".
        format( create_band_3_proxy.State())) )

        # From On, must go to Off state first:
        create_band_12_proxy.Off()
        time.sleep(sleep_seconds)
        create_band_12_proxy.Disable()
        logging.info( ("create_band_12_proxy.State() after Disable() = {}".
        format( create_band_12_proxy.State())) )

        # NOTE: this check is needed only while debugging this test TODO - remove
        if create_band_12_proxy.State() == DevState.FAULT:
            # This should not happen
            create_band_12_proxy.Reset()

            logging.info( ("create_band_12_proxy.State() after reset = {}".
            format( create_band_12_proxy.State())) )

            time.sleep(sleep_seconds)

            logging.info( ("create_band_12_proxy.State() after reset and sleep = {}".
            format( create_band_12_proxy.State())) )

        logging.info( ("vcc_proxy.State()  = {}".
        format( create_vcc_proxy.State())) )

        logging.info( ("vcc_proxy.obsState  = {}".
        format( create_vcc_proxy.obsState)) )
        time.sleep(sleep_seconds)

        create_vcc_proxy.write_attribute("scfoBand1", 1222)
        logging.info( ("vcc scfoBand1 = {}".
        format(create_vcc_proxy.scfoBand1)) )

        logging.info( ("type(create_vcc_proxy) = {}".
        format(type(create_vcc_proxy))) )

        create_vcc_proxy.On()
        
        logging.info( ("vcc_proxy.State() AFTER VCC On() = {}".
        format( create_vcc_proxy.State())) )

        time.sleep(sleep_seconds)
        logging.info( ("vcc_proxy.State() AFTER VCC On() & sleep = {}".
        format( create_vcc_proxy.State())) )

        # configure scan
        with open("test_ConfigureScan_basic.json") as json_file:
            config_scan_data = json.load(json_file)
        
        logging.info("config_scan_data type = {}".format(type(config_scan_data)))

        config_scan_data_no_fsp = copy.deepcopy(config_scan_data)
        config_scan_data_no_fsp.pop('fsp', None)

        config_scan_json_str = json.dumps(config_scan_data_no_fsp)
        #logging.info("config_scan_json_str = {}".format(config_scan_json_str))

        # config_dict = {
        #     "id": "band:1",
        #     "frequency_band": "1",
        #     "band5_tuning": [5.85, 7.25],
        #     "frequencyBandOffsetStream1": 0,
        #     "frequencyBandOffsetStream2": 0,
        #     "searchWindow": [
        #         {
        #             "searchWindowID": 1,
        #             "searchWindowTuning": 6000000000,
        #             "tdcEnable": true,
        #             "tdcNumBits": 8,
        #             "tdcPeriodBeforeEpoch": 5,
        #             "tdcPeriodAfterEpoch": 25,
        #             "tdcDestinationAddress": [
        #                 {
        #                     "receptorID": 4,
        #                     "tdcDestinationAddress": ["foo", "bar", "8080"]
        #                 },
        #                 {
        #                     "receptorID": 1,
        #                     "tdcDestinationAddress": ["fizz", "buzz", "80"]
        #                 }
        #             ]
        #         },
        #         {
        #             "searchWindowID": 2,
        #             "searchWindowTuning": 7000000000,
        #             "tdcEnable": false
        #         }
        #     ]
        # }

        config_dict = {
            "id":"vcc_unit_test",
            "frequency_band": 3,
        }

        json_str = json.dumps(config_dict)

        logging.info("json_str = {}".format(json_str))

        create_vcc_proxy.ConfigureScan(json_str)
        
        logging.info( ("vcc_proxy.obsState AFTER VCC ConfigureScan(() = {}".
        format( create_vcc_proxy.obsState)) )

        time.sleep(sleep_seconds)

        logging.info( ("vcc_proxy.obsState AFTER VCC ConfigureScan(() & sleep = {}".
        format( create_vcc_proxy.obsState)) )

        # TODO use the base class tango_change_event_helper() function
        # TODO -use the base class test  assert_calls()

        scan_id = '1'

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, scan_id)

        # Use callable 'Scan'  API
        #create_vcc_proxy.Scan(scan_id_device_data)

        create_vcc_proxy.command_inout("Scan", scan_id_device_data)

        logging.info( ("vcc_proxy.obsState AFTER VCC Scan(DeviceData) = {}".
        format( create_vcc_proxy.obsState)) )
        time.sleep(sleep_seconds)
        logging.info( ("vcc_proxy.obsState AFTER VCC Scan(DeviceData) & sleep = {}".
        format( create_vcc_proxy.obsState)) )

        obs_state_is_valid = (
            create_vcc_proxy.obsState ==  ObsState.READY or
            create_vcc_proxy.obsState ==  ObsState.SCANNING )

        logging.info( (" create_vcc_proxy.scanID =  {}".
        format(create_vcc_proxy.scanID)) )

        logging.info( (" create_vcc_proxy.frequencyBand =  {}".
        format(create_vcc_proxy.frequencyBand)) )

        assert create_vcc_proxy.frequencyBand == config_dict["frequency_band"]
        
        assert create_vcc_proxy.scanID == int(scan_id)
        create_vcc_proxy.EndScan()
        time.sleep(sleep_seconds)

        logging.info( ("vcc_proxy.obsState AFTER VCC EndScan() and sleep = {}".
        format( create_vcc_proxy.obsState)) )

        create_vcc_proxy.GoToIdle()
        
        logging.info( ("vcc_proxy.obsState AFTER GoToIdle() = {}".
        format( create_vcc_proxy.obsState)) )

        # VCC Off() command
        create_vcc_proxy.Off()
        time.sleep(sleep_seconds)
        logging.info( ("vcc_proxy.State() AFTER VCC Off() & sleep = {}".
        format( create_vcc_proxy.State())) )


        """
        # all bands should be OFF after initialization
        create_band_12_proxy.Init()
        create_band_3_proxy.Init()
        create_band_4_proxy.Init()
        create_band_5_proxy.Init()

        assert create_band_12_proxy.State() == DevState.OFF
        assert create_band_3_proxy.State() == DevState.OFF
        assert create_band_4_proxy.State() == DevState.OFF
        assert create_band_5_proxy.State() == DevState.OFF

        # set frequency band to 1
        create_vcc_proxy.SetFrequencyBand("1")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.ON
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 3
        create_vcc_proxy.SetFrequencyBand("3")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.ON
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 2
        create_vcc_proxy.SetFrequencyBand("2")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.ON
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 5a
        create_vcc_proxy.SetFrequencyBand("5a")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.ON

        # set frequency band to 4
        create_vcc_proxy.SetFrequencyBand("4")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.ON
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 5b
        create_vcc_proxy.SetFrequencyBand("5b")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.ON

        """

    def test_ConfigureSearchWindow_basic(self, create_vcc_proxy, 
                                        create_sw_1_proxy):
        """
        Test a minimal successful search window configuration.
        """
        create_sw_1_proxy.Init()
        time.sleep(3)

        # check initial values of attributes
        assert create_sw_1_proxy.searchWindowTuning == 0
        assert create_sw_1_proxy.tdcEnable == False
        assert create_sw_1_proxy.tdcNumBits == 0
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 0
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 0
        assert create_sw_1_proxy.tdcDestinationAddress == ("", "", "")

        # check initial state
        assert create_sw_1_proxy.State() == DevState.DISABLE

        # set receptorID to 1 to correctly test tdcDestinationAddress
        create_vcc_proxy.receptorID = 1

        # configure search window
        f = open(file_path + "/test_json/test_ConfigureSearchWindow_basic.json")
        create_vcc_proxy.ConfigureSearchWindow(f.read().replace("\n", ""))
        f.close()
        time.sleep(1)

        # check configured values
        assert create_sw_1_proxy.searchWindowTuning == 1000000000
        assert create_sw_1_proxy.tdcEnable == True
        assert create_sw_1_proxy.tdcNumBits == 8
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 5
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 25
        assert create_sw_1_proxy.tdcDestinationAddress == ("", "", "")

        # check state
        assert create_sw_1_proxy.State() == DevState.ON
