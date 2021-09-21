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
import time
import json
from typing import Callable, Type
import logging
import pytest

# Tango imports
import tango
from tango import DevState
from tango.server import command
from tango.test_context import DeviceTestContext, MultiDeviceTestContext

#Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

from ska_mid_cbf_mcs.vcc.vcc_device import Vcc
from ska_mid_cbf_mcs.vcc.vcc_band_1_and_2 import VccBand1And2
from ska_mid_cbf_mcs.vcc.vcc_band_3 import VccBand3
from ska_mid_cbf_mcs.vcc.vcc_band_4 import VccBand4
from ska_mid_cbf_mcs.vcc.vcc_band_5 import VccBand5
from ska_mid_cbf_mcs.vcc.vcc_search_window import VccSearchWindow
from ska_mid_cbf_mcs.dev_factory import DevFactory
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode

@pytest.mark.usefixtures(
    "debug_device_is_on",
    "tango_context"
)

# @pytest.fixture()
# def devices_to_load():
#     return (
#         {
#             "class": Vcc,
#             "devices": [
#                 {
#                     "name": "mid_csp_cbf/vcc/001",
#                     "properties": {
#                             "Band1And2Address": [
#                                 "mid_csp_cbf/vcc_band12/001"
#                             ],
#                             "Band3Address": [
#                                 "mid_csp_cbf/vcc_band3/001"
#                             ],
#                             "Band4Address": [
#                                 "mid_csp_cbf/vcc_band4/001"
#                             ],
#                             "Band5Address": [
#                                 "mid_csp_cbf/vcc_band5/001"
#                             ],
#                             "SW1Address": [
#                                 "mid_csp_cbf/vcc_sw1/001"
#                             ],
#                             "SW2Address": [
#                                 "mid_csp_cbf/vcc_sw2/001"
#                             ],
#                             "VccID": [
#                                 "1"
#                             ],
#                     }
#                 }
#             ]
#         },
#         {
#             "class": VccBand1And2,
#             "devices": [
#                 {"name": "mid_csp_cbf/vcc_band12/001"},
#             ]
#         },
#         {
#             "class": VccBand3,
#             "devices": [
#                 {"name": "mid_csp_cbf/vcc_band3/001"},
#             ]
#         },
#         {
#             "class": VccBand4,
#             "devices": [
#                 {"name": "mid_csp_cbf/vcc_band4/001"},
#             ]
#         },
#         {
#             "class": VccBand5,
#             "devices": [
#                 {"name": "mid_csp_cbf/vcc_band5/001"},
#             ]
#         },
#         {
#             "class": VccSearchWindow,
#             "devices": [
#                 {"name": "mid_csp_cbf/vcc_sw1/001"},
#             ]
#         },
#     )

@pytest.fixture()
def patched_vcc_device_class() -> Type[Vcc]:
    """
    Return a subarray device class, patched with extra methods for testing.

    :return: a patched subarray device class, patched with extra methods
        for testing
    """

    class PatchedVccDevice(Vcc):
        """
        Vcc patched with extra commands for testing purposes.

        The extra commands allow us to mock the receipt of obs state
        change events from subservient devices.
        """

        @command(dtype_in=int)
        def FakeSubservientDevicesObsState(
            self,
            obs_state: ObsState
        ) -> None:
            obs_state = ObsState(obs_state)

            # for fqdn in self.component_manager._device_obs_states:
            #     self.component_manager._device_obs_state_changed(fqdn, obs_state)

    return PatchedVccDevice


# @pytest.fixture()
# def devices_to_load(patched_vcc_device_class: Type[Vcc]) -> DeviceToLoadType:
#     """
#     Fixture that specifies the device to be loaded for testing.

#     :param patched_tile_device_class: a device class for the tile device
#         under test, patched with extra methods for testing.

#     :return: specification of the device to be loaded
#     """
#     return {
#         "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
#         "package": "ska_mid_cbf_mcs",
#         "devices": [
#                 { "name": "vcc-001", "proxy": CbfDeviceProxy },
#                 { "name": "mid_csp_cbf/vcc_band12/001", "proxy": CbfDeviceProxy },
#                 { "name": "mid_csp_cbf/vcc_band3/001", "proxy": CbfDeviceProxy },
#                 { "name": "mid_csp_cbf/vcc_band4/001", "proxy": CbfDeviceProxy },
#                 { "name": "mid_csp_cbf/vcc_band5/001", "proxy": CbfDeviceProxy },
#                 { "name": "mid_csp_cbf/vcc_sw1/001", "proxy": CbfDeviceProxy },
#             ]
#     }

@pytest.fixture()
def device_to_load(
    patched_vcc_device_class: Type[Vcc],
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :param patched_subarray_device_class: a class for a patched subarray
        device with extra methods for testing purposes.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs",
        "device": "vcc-001",
        "proxy": CbfDeviceProxy,
        "patch": patched_vcc_device_class,
    }



class TestVcc:
    """
    Test class for Vcc tests.
    """

    @pytest.fixture()
    def device_under_test(
        self, 
        tango_harness: TangoHarness
    ) -> CbfDeviceProxy:
        """
        Fixture that returns the device under test.

        :param tango_harness: a test harness for Tango devices

        :return: the device under test
        """
        return tango_harness.get_device("mid_csp_cbf/vcc/001")


    def test_VccBand(
        self,
        tango_harness: TangoHarness,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test for VccBand device.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        mock_band12 = tango_harness.get_device("mid_csp_cbf/vcc_band12/001")
        assert device_under_test.obsState == ObsState.IDLE
    
    @pytest.mark.skip
    def test_SetFrequencyBand(
        self,
        debug_device_is_on,
        tango_context
    ):
        """
        Test SetFrequencyBand command state changes.
        """
        logging.info("%s", tango_context)
        dev_factory = DevFactory()
        logging.info("%s", dev_factory._test_context)
        vcc_proxy = dev_factory.get_device("mid_csp_cbf/vcc/001")
        band_12_proxy = dev_factory.get_device("mid_csp_cbf/vcc_band12/001")
        band_3_proxy = dev_factory.get_device("mid_csp_cbf/vcc_band3/001")

        logging.info("debug_device_is_on = {}".format(debug_device_is_on))       
        if debug_device_is_on == True:
            timeout_millis = 700000 
            vcc_proxy.set_timeout_millis(timeout_millis)
            port = vcc_proxy.DebugDevice()
        
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
        band_12_proxy.On()
        #band_12_proxy.command_inout("On")
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

        # logging.info( ("vcc_proxy.obsState  = {}".
        # format( vcc_proxy.obsState)) )
        # time.sleep(sleep_seconds)

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
        
        # logging.info( ("vcc_proxy.obsState AFTER VCC ConfigureScan(() = {}".
        # format( vcc_proxy.obsState)) )

        time.sleep(sleep_seconds)

        # logging.info( ("vcc_proxy.obsState AFTER VCC ConfigureScan(() & sleep = {}".
        # format( vcc_proxy.obsState)) )

        # TODO use the base class tango_change_event_helper() function
        # TODO -use the base class test  assert_calls()

        scan_id = '1'

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, scan_id)

        # Use callable 'Scan'  API
        #vcc_proxy.Scan(scan_id_device_data)

        vcc_proxy.command_inout("Scan", scan_id_device_data)

        # logging.info( ("vcc_proxy.obsState AFTER VCC Scan(DeviceData) = {}".
        # format( vcc_proxy.obsState)) )
        # time.sleep(sleep_seconds)
        # logging.info( ("vcc_proxy.obsState AFTER VCC Scan(DeviceData) & sleep = {}".
        # format( vcc_proxy.obsState)) )

        # obs_state_is_valid = (
        #     vcc_proxy.obsState ==  ObsState.READY or
        #     vcc_proxy.obsState ==  ObsState.SCANNING )

        logging.info( (" vcc_proxy.scanID =  {}".
        format(vcc_proxy.scanID)) )

        logging.info( (" vcc_proxy.frequencyBand =  {}".
        format(vcc_proxy.frequencyBand)) )

        #TODO fix hardcoded value
        assert vcc_proxy.frequencyBand == 2 # index 2 == freq band 3
        
        assert vcc_proxy.scanID == int(scan_id)
        vcc_proxy.EndScan()
        time.sleep(sleep_seconds)

        # logging.info( ("vcc_proxy.obsState AFTER VCC EndScan() and sleep = {}".
        # format( vcc_proxy.obsState)) )

        vcc_proxy.GoToIdle()
        
        # logging.info( ("vcc_proxy.obsState AFTER GoToIdle() = {}".
        # format( vcc_proxy.obsState)) )

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

    @pytest.mark.skip
    def test_ConfigureSearchWindow_basic(
        self,
    ):
        """
        Test a minimal successful search window configuration.
        """
        if Vcc.TEST_CONTEXT is False:
            dev_factory = DevFactory()
            logging.info("%s", dev_factory._test_context)
            vcc_proxy = dev_factory.get_device("mid_csp_cbf/vcc/001")
            sw_1_proxy = dev_factory.get_device("mid_csp_cbf/vcc_sw1/001")
            sw_1_proxy.Init()
            time.sleep(3)

            # check initial values of attributes
            assert sw_1_proxy.searchWindowTuning == 0
            assert sw_1_proxy.tdcEnable == False
            assert sw_1_proxy.tdcNumBits == 0
            assert sw_1_proxy.tdcPeriodBeforeEpoch == 0
            assert sw_1_proxy.tdcPeriodAfterEpoch == 0
            assert sw_1_proxy.tdcDestinationAddress == ("", "", "")

            # check initial state
            assert sw_1_proxy.State() == DevState.DISABLE

            # set receptorID to 1 to correctly test tdcDestinationAddress
            vcc_proxy.receptorID = 1

        
            # configure search window
            f = open(file_path + "/../data/test_ConfigureSearchWindow_basic.json")
            vcc_proxy.ConfigureSearchWindow(f.read().replace("\n", ""))
            f.close()
            time.sleep(1)

            # check configured values
            assert sw_1_proxy.searchWindowTuning == 1000000000
            assert sw_1_proxy.tdcEnable == True
            assert sw_1_proxy.tdcNumBits == 8
            assert sw_1_proxy.tdcPeriodBeforeEpoch == 5
            assert sw_1_proxy.tdcPeriodAfterEpoch == 25
            assert sw_1_proxy.tdcDestinationAddress == ("", "", "")

            # check state
            assert sw_1_proxy.State() == DevState.ON
