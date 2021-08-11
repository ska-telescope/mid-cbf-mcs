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

# Standard imports
import sys
import os
import time
import json
import copy
import logging
import pytest

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
from tango.test_context import DeviceTestContext, MultiDeviceTestContext

#Local imports

from Vcc.Vcc.Vcc import Vcc
from Vcc.VccBand1And2.VccBand1And2 import VccBand1And2
from Vcc.VccBand3.VccBand3 import VccBand3
from Vcc.VccBand4.VccBand4 import VccBand4
from Vcc.VccBand5.VccBand5 import VccBand5
from DeviceFactory.DeviceFactory import DeviceFactory
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode

@pytest.mark.usefixtures(
    "debug_device_is_on",
    "create_vcc_proxy",
    "create_band_12_proxy",
    "create_band_3_proxy",
    "create_band_4_proxy",
    "create_band_5_proxy",
    "create_sw_1_proxy",
    "proxies",
    "tango_context"
)

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": Vcc,
            "devices": [
                {
                    "name": "mid_csp_cbf/vcc/001",
                    "properties": {
                            "Band1And2Address": [
                                "mid_csp_cbf/vcc_band12/001"
                            ],
                            "Band3Address": [
                                "mid_csp_cbf/vcc_band3/001"
                            ],
                            "Band4Address": [
                                "mid_csp_cbf/vcc_band4/001"
                            ],
                            "Band5Address": [
                                "mid_csp_cbf/vcc_band5/001"
                            ],
                            "SW1Address": [
                                "mid_csp_cbf/vcc_sw1/001"
                            ],
                            "SW2Address": [
                                "mid_csp_cbf/vcc_sw2/001"
                            ],
                            "VccID": [
                                "1"
                            ],
                    }
                },
                {"name": "mid_csp_cbf/vcc/002"},
                {"name": "mid_csp_cbf/vcc/003"},
                {"name": "mid_csp_cbf/vcc/004"}
            ]
        },
        {
            "class": VccBand1And2,
            "devices": [
                {"name": "mid_csp_cbf/vcc_band12/001"},
            ]
        },
        {
            "class": VccBand3,
            "devices": [
                {"name": "mid_csp_cbf/vcc_band3/001"},
            ]
        },
        {
            "class": VccBand4,
            "devices": [
                {"name": "mid_csp_cbf/vcc_band4/001"},
            ]
        },
        {
            "class": VccBand5,
            "devices": [
                {"name": "mid_csp_cbf/vcc_band5/001"},
            ]
        },
    )

class TestVcc:

    def test_Vcc_DeviceTestContext(self, tango_context):
        logging.info("%s", tango_context)
        device_factory = DeviceFactory()
        proxy = device_factory.get_device("mid_csp_cbf/vcc/001")
        proxy.On()
        assert proxy.State() == DevState.ON

    def test_SetFrequencyBand(
            self,
            debug_device_is_on,
            tango_context
    ):
        """
        Test SetFrequencyBand command state changes.
        """
        logging.info("%s", tango_context)
        device_factory = DeviceFactory()
        vcc_proxy = device_factory.get_device("mid_csp_cbf/vcc/001")
        band_12_proxy = device_factory.get_device("mid_csp_cbf/vcc_band12/001")
        band_3_proxy = device_factory.get_device("mid_csp_cbf/vcc_band3/001")

        logging.info("debug_device_is_on = {}".format(debug_device_is_on))       
        if debug_device_is_on == True:
            timeout_millis = 700000 
            vcc_proxy.set_timeout_millis(timeout_millis)
            port = vcc_proxy.DebugDevice()

        # NOTE: this check is needed only while debugging this test TODO - remove
        if vcc_proxy.obsState  == ObsState.SCANNING:
            vcc_proxy.EndScan() 
        
        logging.info( ("band_12_proxy.State() = {}".
        format( band_12_proxy.State())) )

        logging.info( ("band_3_proxy.State() = {}".
        format( band_3_proxy.State())) )

        sleep_seconds = 2

        #band_3_proxy.Init() # may not be needed ? TODO
        # time.sleep(sleep_seconds)

        # logging.info( ("band_3_proxy.State() after Init() and sleep = {}".
        # format( band_3_proxy.State())) )

        # Can use the callable version or the 'command_inout' version of the 'On' command
        #band_12_proxy.On()
        band_12_proxy.command_inout("On")
        band_3_proxy.Disable()
        time.sleep(sleep_seconds)
        logging.info( ("band_12_proxy.State() after On() = {}".
        format( band_12_proxy.State())) )

        logging.info( ("band_3_proxy.State() after Disable() = {}".
        format( band_3_proxy.State())) )

        # From On, must go to Off state first:
        band_12_proxy.Off()
        time.sleep(sleep_seconds)
        band_12_proxy.Disable()
        logging.info( ("band_12_proxy.State() after Disable() = {}".
        format( band_12_proxy.State())) )

        # NOTE: this check is needed only while debugging this test TODO - remove
        if band_12_proxy.State() == DevState.FAULT:
            # This should not happen
            band_12_proxy.Reset()

            logging.info( ("band_12_proxy.State() after reset = {}".
            format( band_12_proxy.State())) )

            time.sleep(sleep_seconds)

            logging.info( ("band_12_proxy.State() after reset and sleep = {}".
            format( band_12_proxy.State())) )

        logging.info( ("vcc_proxy.State()  = {}".
        format( vcc_proxy.State())) )

        logging.info( ("vcc_proxy.obsState  = {}".
        format( vcc_proxy.obsState)) )
        time.sleep(sleep_seconds)

        vcc_proxy.write_attribute("scfoBand1", 1222)
        logging.info( ("vcc scfoBand1 = {}".
        format(vcc_proxy.scfoBand1)) )

        logging.info( ("type(vcc_proxy) = {}".
        format(type(vcc_proxy))) )

        vcc_proxy.On()
        
        logging.info( ("vcc_proxy.State() AFTER VCC On() = {}".
        format( vcc_proxy.State())) )

        time.sleep(sleep_seconds)
        logging.info( ("vcc_proxy.State() AFTER VCC On() & sleep = {}".
        format( vcc_proxy.State())) )

        # configure scan
        # with open("test_ConfigureScan_basic.json") as json_file:
        #     config_scan_data = json.load(json_file)
        
        # logging.info("config_scan_data type = {}".format(type(config_scan_data)))

        # config_scan_data_no_fsp = copy.deepcopy(config_scan_data)
        # config_scan_data_no_fsp.pop('fsp', None)

        # config_scan_json_str = json.dumps(config_scan_data_no_fsp)
        # logging.info("config_scan_json_str = {}".format(config_scan_json_str))

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
            "config_id": "vcc_unit_test",
            "frequency_band": "3",
        }

        json_str = json.dumps(config_dict)

        logging.info("json_str = {}".format(json_str))

        vcc_proxy.ConfigureScan(json_str)
        
        logging.info( ("vcc_proxy.obsState AFTER VCC ConfigureScan(() = {}".
        format( vcc_proxy.obsState)) )

        time.sleep(sleep_seconds)

        logging.info( ("vcc_proxy.obsState AFTER VCC ConfigureScan(() & sleep = {}".
        format( vcc_proxy.obsState)) )

        # TODO use the base class tango_change_event_helper() function
        # TODO -use the base class test  assert_calls()

        scan_id = '1'

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, scan_id)

        # Use callable 'Scan'  API
        #vcc_proxy.Scan(scan_id_device_data)

        vcc_proxy.command_inout("Scan", scan_id_device_data)

        logging.info( ("vcc_proxy.obsState AFTER VCC Scan(DeviceData) = {}".
        format( vcc_proxy.obsState)) )
        time.sleep(sleep_seconds)
        logging.info( ("vcc_proxy.obsState AFTER VCC Scan(DeviceData) & sleep = {}".
        format( vcc_proxy.obsState)) )

        obs_state_is_valid = (
            vcc_proxy.obsState ==  ObsState.READY or
            vcc_proxy.obsState ==  ObsState.SCANNING )

        logging.info( (" vcc_proxy.scanID =  {}".
        format(vcc_proxy.scanID)) )

        logging.info( (" vcc_proxy.frequencyBand =  {}".
        format(vcc_proxy.frequencyBand)) )

        assert vcc_proxy.frequencyBand == config_dict["frequency_band"]
        
        assert vcc_proxy.scanID == int(scan_id)
        vcc_proxy.EndScan()
        time.sleep(sleep_seconds)

        logging.info( ("vcc_proxy.obsState AFTER VCC EndScan() and sleep = {}".
        format( vcc_proxy.obsState)) )

        vcc_proxy.GoToIdle()
        
        logging.info( ("vcc_proxy.obsState AFTER GoToIdle() = {}".
        format( vcc_proxy.obsState)) )

        # VCC Off() command
        vcc_proxy.Off()
        time.sleep(sleep_seconds)
        logging.info( ("vcc_proxy.State() AFTER VCC Off() & sleep = {}".
        format( vcc_proxy.State())) )


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
