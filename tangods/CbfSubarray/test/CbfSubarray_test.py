#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
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
from datetime import datetime
import json
import logging

# Path
file_path = os.path.dirname(os.path.abspath(__file__))
# insert base package directory to import global_enum 
# module in commons folder
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)
from global_enum import freq_band_dict

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, os.path.abspath(path))

# Tango imports
import tango
from tango import DevState
import pytest

# SKA specific imports
from CbfSubarray.CbfSubarray import CbfSubarray
from ska_tango_base.control_model import LoggingLevel, HealthState
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_base.base_device import _DEBUGGER_PORT

@pytest.mark.usefixtures("proxies", "input_test_data")
class TestCbfSubarray:

    def test_AddRemoveReceptors_valid(self, proxies):
        """
        Test valid AddReceptors and RemoveReceptors commands
        """

        timeout_millis = proxies.subarray[1].get_timeout_millis()
        log_msg = "timeout_millis = {} ".format(timeout_millis)
        #logging.info(log_msg)
        #logging.info("start_time = {}".format(time.time()))
        logging.info("start datetime = {}".format(datetime.now()))
        
        if proxies.debug_device_is_on:
            port = proxies.subarray[1].DebugDevice()

        try:
            proxies.clean_proxies()
            if proxies.master.State() == DevState.OFF:
                proxies.master.Init()
                proxies.wait_timeout_dev([proxies.master], DevState.STANDBY, 3, 1)
                proxies.master.On()
                proxies.wait_timeout_dev([proxies.master], DevState.ON, 3, 1)
            proxies.clean_proxies()

            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(4)])

            input_receptors = [1, 3, 4]
            # add some receptors
            proxies.subarray[1].AddReceptors(input_receptors)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert [proxies.subarray[1].receptors[i] for i in range(3)] == input_receptors
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in input_receptors])
            assert proxies.subarray[1].obsState == ObsState.IDLE

            # add more receptors...
            proxies.subarray[1].AddReceptors([2])
            time.sleep(1)
            assert [proxies.subarray[1].receptors[i] for i in range(4)] == [1, 3, 4, 2]
            assert proxies.vcc[proxies.receptor_to_vcc[2]].subarrayMembership == 1

            # remove some receptors
            proxies.subarray[1].RemoveReceptors([2, 1, 4])
            time.sleep(1)
            assert proxies.subarray[1].receptors == ([3])
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 0 for i in [1, 2, 4]])
            assert proxies.vcc[proxies.receptor_to_vcc[3]].subarrayMembership == 1

            # remove remaining receptors
            proxies.subarray[1].RemoveReceptors([3])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 1)
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.vcc[proxies.receptor_to_vcc[3]].subarrayMembership == 0
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 1)

        except AssertionError as ae: 
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_AddRemoveReceptors_invalid_single(self, proxies):
        """
        Test invalid AddReceptors commands involving a single subarray:
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(4)])

            # add some receptors to subarray 1
            proxies.subarray[1].AddReceptors([1, 3])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[1].receptors[0] == 1
            assert proxies.subarray[1].receptors[1] == 3
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in [1, 3]])
            assert proxies.subarray[1].obsState == ObsState.IDLE

            # TODO: fix this
            # try adding an invalid receptor ID
            # with pytest.raises(tango.DevFailed) as df:
            #     proxies.subarray[1].AddReceptors([5])
            # time.sleep(1)
            # assert "Invalid receptor ID" in str(df.value.args[0].desc)

            # try removing a receptor not assigned to subarray 1
            # doing this doesn't actually throw an error
            proxies.subarray[1].RemoveReceptors([2])
            assert proxies.subarray[1].receptors[0] == 1
            assert proxies.subarray[1].receptors[1] == 3
            proxies.subarray[1].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 1)
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 1)

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e
        
    @pytest.mark.skip(reason="Since there's only a single subarray, this test is currently broken.")
    def test_AddRemoveReceptors_invalid_multiple(self, proxies):
        """

        Test invalid AddReceptors commands involving multiple subarrays:
            - when a receptor to be added is already in use by a different subarray
        """
        # for proxy in vcc_proxies:
        #     proxy.Init()
        # proxies.subarray[1].set_timeout_millis(60000)
        # subarray_2_proxy.set_timeout_millis(60000)
        # proxies.subarray[1].Init()
        # subarray_2_proxy.Init()
        # time.sleep(3)
        # cbf_master_proxy.set_timeout_millis(60000)
        # cbf_master_proxy.Init()
        # time.sleep(60)  # takes pretty long for CBF Master to initialize

        # receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
        #                        cbf_master_proxy.receptorToVcc)

        # cbf_master_proxy.On()
        # time.sleep(3)

        # # receptor list should be empty right after initialization
        # assert proxies.subarray[1].receptors == ()
        # assert subarray_2_proxy.receptors == ()
        # assert all([proxy.subarrayMembership == 0 for proxy in vcc_proxies])
        # assert proxies.subarray[1].State() == DevState.OFF
        # assert subarray_2_proxy.State() == DevState.OFF

        # # add some receptors to subarray 1
        # proxies.subarray[1].AddReceptors([1, 3])
        # time.sleep(1)
        # assert proxies.subarray[1].receptors == (1, 3)
        # assert all([vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3]])
        # assert proxies.subarray[1].State() == DevState.ON

        # # try adding some receptors (including an invalid one) to subarray 2
        # with pytest.raises(tango.DevFailed) as df:
        #     subarray_2_proxy.AddReceptors([1, 2, 4])
        # time.sleep(1)
        # assert "already in use" in str(df.value.args[0].desc)
        # assert subarray_2_proxy.receptors == (2, 4)
        # assert all([vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3]])
        # assert all([vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 2 for i in [2, 4]])
        # assert subarray_2_proxy.State() == DevState.ON

    def test_RemoveAllReceptors(self, proxies):
        """
        Test RemoveAllReceptors command
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(4)])

            # add some receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in [1, 3, 4]])
            assert proxies.subarray[1].obsState == ObsState.IDLE

            # remove all receptors
            proxies.subarray[1].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 1)
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 0 for i in [1, 3, 4]])
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 1)
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    #TODO: fix; currently tests break if multiple scan configurations are tested
    def test_ConfigureScan_basic(self, proxies):
        """
        Test a successful scan configuration
        """

        proxies.subarray[1].loggingLevel = LoggingLevel.DEBUG
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)

            # check initial value of attributes of CBF subarray
            vcc_index = proxies.receptor_to_vcc[4]
            
            logging.info("vcc_index  = {}".format( vcc_index ))

            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.subarray[1].configID == ''
            # TODO in CbfSubarray, at end of scan, clear all private data
            #assert proxies.subarray[1].frequencyBand == 0
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            config_file_name = "/test_json/ConfigureScan_basic.json"
            f = open(file_path + config_file_name)
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 15, 1)

            # check configured attributes of CBF subarray
            assert proxies.subarray[1].configID == "band:5a, fsp1, 744 channels average factor 8"
            assert proxies.subarray[1].frequencyBand == 4 # means 5a
            assert proxies.subarray[1].obsState == ObsState.READY

            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(4)], ObsState.READY, 1, 1)

            # check frequency band of VCCs, including states of 
            # frequency band capabilities

            logging.info( ("proxies.vcc[vcc_index].frequencyBand  = {}".
            format( proxies.vcc[vcc_index].frequencyBand)) )

            vcc_band_proxies = proxies.vccBand[vcc_index - 1]

            assert proxies.vcc[proxies.receptor_to_vcc[4]].frequencyBand == 4
            assert proxies.vcc[proxies.receptor_to_vcc[1]].frequencyBand == 4

            for proxy in proxies.vccBand[proxies.receptor_to_vcc[4] - 1]:
                logging.info("VCC proxy.State() = {}".format(proxy.State()))

            assert [proxy.State() for proxy in proxies.vccBand[proxies.receptor_to_vcc[4] - 1]] == [
                DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
            assert [proxy.State() for proxy in proxies.vccBand[proxies.receptor_to_vcc[1] - 1]] == [
                DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

            # check the rest of the configured attributes of VCCs
            # first for VCC belonging to receptor 10...
            assert proxies.vcc[proxies.receptor_to_vcc[4]].subarrayMembership == 1
            assert proxies.vcc[proxies.receptor_to_vcc[4]].band5Tuning[0] == 5.85
            assert proxies.vcc[proxies.receptor_to_vcc[4]].band5Tuning[1] == 7.25
            assert proxies.vcc[proxies.receptor_to_vcc[4]].frequencyBandOffsetStream1 == 0
            assert proxies.vcc[proxies.receptor_to_vcc[4]].frequencyBandOffsetStream2 == 0
            assert proxies.vcc[proxies.receptor_to_vcc[4]].rfiFlaggingMask == "{}"
            # then for VCC belonging to receptor 1...
            assert proxies.vcc[proxies.receptor_to_vcc[1]].subarrayMembership == 1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].band5Tuning[0] == 5.85
            assert proxies.vcc[proxies.receptor_to_vcc[1]].band5Tuning[1] == 7.25

            # check configured attributes of search windows
            # first for search window 1...
            
            # TODO - SearchWidow device test is disabled since the same 
            # functionality is implemented by the VccSearchWindow device; 
            # to be decide which one to keep.

            # print("proxies.sw[1].State() = {}".format(proxies.sw[1].State()))
            # print("proxies.sw[2].State() = {}".format(proxies.sw[2].State()))

            # assert proxies.sw[1].State() == DevState.ON
            # assert proxies.sw[1].searchWindowTuning == 6000000000
            # assert proxies.sw[1].tdcEnable == True
            # assert proxies.sw[1].tdcNumBits == 8
            # assert proxies.sw[1].tdcPeriodBeforeEpoch == 5
            # assert proxies.sw[1].tdcPeriodAfterEpoch == 25
            # assert "".join(proxies.sw[1].tdcDestinationAddress.split()) in [
            #     "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            #     "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            #     "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            #     "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            # ]
            # # then for search window 2...
            # assert proxies.sw[2].State() == DevState.DISABLE
            # assert proxies.sw[2].searchWindowTuning == 7000000000
            # assert proxies.sw[2].tdcEnable == False

            time.sleep(1)
            # check configured attributes of VCC search windows
            # first for search window 1 of VCC belonging to receptor 10...
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].State() == DevState.ON
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcEnable == True
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcNumBits == 8
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25

            # TODO - re-enable and debug!
            # assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
            #     "foo", "bar", "8080"
            # )
            # then for search window 1 of VCC belonging to receptor 1...
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].State() == DevState.ON
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcEnable == True
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcNumBits == 8
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25

            # TODO - re-enable and debug!
            # assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
            #     "fizz", "buzz", "80"
            # )

            # then for search window 2 of VCC belonging to receptor 10...
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][1].State() == DevState.DISABLE
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][1].searchWindowTuning == 7000000000
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][1].tdcEnable == False
            # and lastly for search window 2 of VCC belonging to receptor 1...
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][1].State() == DevState.DISABLE
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][1].tdcEnable == False

            # check configured attributes of FSPs, including states of function mode capabilities
            assert proxies.fsp[1].functionMode == 1
            assert 1 in proxies.fsp[1].subarrayMembership
            assert [proxy.State() for proxy in proxies.fsp1FunctionMode] == [
                DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
            ]

            # TODO - 
            # assert [proxy.State() for proxy in fsp_2_function_mode_proxy] == [
            #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
            # ]

            # check configured attributes of FSP subarrays
            # first for FSP 3 ... (this is a PSS fsp device)
            assert proxies.fspSubarray[3].receptors[0] == 3
            assert proxies.fspSubarray[3].receptors[1] == 1
            assert proxies.fspSubarray[3].searchWindowID == 2
            assert proxies.fspSubarray[3].searchBeamID[0] == 300
            assert proxies.fspSubarray[3].searchBeamID[1] == 400

            # TODO: currently searchBeams is stored by the device
            #       as a json string ( via attribute 'searchBeams');  
            #       this has to be updated in FspPssSubarray
            #       to read/write individual members
            searchBeam = proxies.fspSubarray[3].searchBeams
            searchBeam0 = json.loads(searchBeam[0])
            searchBeam1 = json.loads(searchBeam[1])
            assert searchBeam0["search_beam_id"] == 300
            assert searchBeam0["receptor_ids"][0] == 3
            assert searchBeam0["enable_output"] == True
            assert searchBeam0["averaging_interval"] == 4

            # TODO - this does not pass - to debug & fix
            #assert searchBeam0["searchBeamDestinationAddress"] == "10.05.1.1"

            assert searchBeam1["search_beam_id"] == 400
            assert searchBeam1["receptor_ids"][0] == 1
            assert searchBeam1["enable_output"] == True
            assert searchBeam1["averaging_interval"] == 2

            # TODO - this does not pass - to debug & fix
            #assert searchBeam1["searchBeamDestinationAddress"] == "10.05.2.1"

            # check configured attributes of FSP subarrays
            # first for FSP 1... (this is a CORR fsp device)
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[1].receptors == 4
            assert proxies.fspSubarray[1].frequencyBand == 4
            assert proxies.fspSubarray[1].band5Tuning[0] == 5.85
            assert proxies.fspSubarray[1].band5Tuning[1] == 7.25
            assert proxies.fspSubarray[1].frequencyBandOffsetStream1 == 0
            assert proxies.fspSubarray[1].frequencyBandOffsetStream2 == 0
            assert proxies.fspSubarray[1].frequencySliceID == 1
            assert proxies.fspSubarray[1].corrBandwidth == 1
            assert proxies.fspSubarray[1].zoomWindowTuning == 4700000
            assert proxies.fspSubarray[1].integrationTime == 1
            assert proxies.fspSubarray[1].fspChannelOffset == 14880

            assert proxies.fspSubarray[1].channelAveragingMap[0][0] == 0
            assert proxies.fspSubarray[1].channelAveragingMap[0][1] == 8
            assert proxies.fspSubarray[1].channelAveragingMap[1][0] == 744
            assert proxies.fspSubarray[1].channelAveragingMap[1][1] == 8
            assert proxies.fspSubarray[1].channelAveragingMap[2][0] == 1488
            assert proxies.fspSubarray[1].channelAveragingMap[2][1] == 8
            assert proxies.fspSubarray[1].channelAveragingMap[3][0] == 2232
            assert proxies.fspSubarray[1].channelAveragingMap[3][1] == 8
            assert proxies.fspSubarray[1].channelAveragingMap[4][0] == 2976

            assert proxies.fspSubarray[1].outputLinkMap[0][0] == 0
            assert proxies.fspSubarray[1].outputLinkMap[0][1] == 4
            assert proxies.fspSubarray[1].outputLinkMap[1][0] == 744
            assert proxies.fspSubarray[1].outputLinkMap[1][1] == 8      
            assert proxies.fspSubarray[1].outputLinkMap[2][0] == 1488
            assert proxies.fspSubarray[1].outputLinkMap[2][1] == 12
            assert proxies.fspSubarray[1].outputLinkMap[3][0] == 2232
            assert proxies.fspSubarray[1].outputLinkMap[3][1] == 16

            assert str(proxies.fspSubarray[1].visDestinationAddress).replace('"',"'") == \
                str({"outputHost": [[0, "192.168.0.1"], [8184, "192.168.0.2"]], 
                "outputMac": [[0, "06-00-00-00-00-01"]], 
                "outputPort": [[0, 9000, 1], [8184, 9000, 1]]}).replace('"',"'")

            # Clean Up
            proxies.clean_proxies()
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    @pytest.mark.skip(reason="pst not currently supported")
    def test_ConfigureScan_onlyPst_basic(self, proxies):
        """
        Test a successful PST-BF scan configuration
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
            for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                if proxy.State() == DevState.OFF:
                    proxy.On()
                    proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                proxy.loggingLevel = "DEBUG"
                if proxy.State() == DevState.OFF:
                    proxy.On()
                    proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            # check initial value of attributes of CBF subarray
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.subarray[1].configID == ''
            assert proxies.subarray[1].frequencyBand == 0
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([4, 1, 3, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(4), [4, 1, 3, 2])])

            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 15, 1)

            # check configured attributes of CBF subarray
            assert proxies.subarray[1].configID == "band:5a, fsp1, 744 channels average factor 8"
            assert proxies.subarray[1].frequencyBand == 4
            assert proxies.subarray[1].obsState == ObsState.READY

            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(4)], ObsState.READY, 1, 1)

            # check frequency band of VCCs, including states of frequency band capabilities
            assert proxies.vcc[proxies.receptor_to_vcc[2]].frequencyBand == 4
            assert [proxy.State() for proxy in proxies.vccBand[proxies.receptor_to_vcc[2] - 1]] == [
                DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

            # check the rest of the configured attributes of VCCs
            # first for VCC belonging to receptor 2...
            assert proxies.vcc[proxies.receptor_to_vcc[2]].subarrayMembership == 1
            assert proxies.vcc[proxies.receptor_to_vcc[2]].frequencyBandOffsetStream1 == 0
            assert proxies.vcc[proxies.receptor_to_vcc[2]].frequencyBandOffsetStream2 == 0
            assert proxies.vcc[proxies.receptor_to_vcc[2]].rfiFlaggingMask == "{}"

            # check configured attributes of FSPs, including states of function mode capabilities
            assert proxies.fsp[2].State() == DevState.ON
            assert proxies.fsp[2].functionMode == 3
            assert 1 in proxies.fsp[2].subarrayMembership
            assert [proxy.State() for proxy in proxies.fsp2FunctionMode] == [
                DevState.DISABLE, DevState.DISABLE, DevState.ON, DevState.DISABLE
            ]

            # check configured attributes of FSP subarrays
            # FSP 2
            assert proxies.fspSubarray[6].obsState == ObsState.READY
            assert all([proxies.fspSubarray[6].receptors[i] == j for i, j in zip(range(1), [2])])
            assert all([proxies.fspSubarray[6].timingBeamID[i] == j for i, j in zip(range(1), [10])])

            # Clean Up
            proxies.clean_proxies()
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    @pytest.mark.skip(reason="pst not currently supported")
    def test_ConfigureScan_onlyPst_basic_FSP_scan_parameters(self, proxies):
        """
        Test a successful transmission of PST-BF parameters to FSP
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            # check initial value of attributes of CBF subarray
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.subarray[1].configID == ''
            assert proxies.subarray[1].frequencyBand == 0
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([4, 1, 3, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(4), [4, 1, 3, 2])])

            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 15, 1)
            
            # update jones matrices from tm emulator
            f = open(file_path + "/test_json/jonesmatrix_fsp.json")
            jones_matrix = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for matrix in jones_matrix["jonesMatrix"]:
                matrix["epoch"] = epoch
                if matrix["destinationType"] == "fsp":
                    epoch = str(int(epoch) + 10)

            # update Jones Matrix
            proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

            for matrix in jones_matrix["jonesMatrix"]:
                if matrix["destinationType"] == "fsp":
                    for receptor in matrix["matrixDetails"]:
                        rec_id = int(receptor["receptor"])
                        fs_id = receptor["receptorMatrix"][0]["fsid"]
                        for index, value in enumerate(receptor["receptorMatrix"][0]["matrix"]):
                            try:
                                assert proxies.fsp[fs_id].jonesMatrix[rec_id - 1][index] == value
                            except AssertionError as ae:
                                raise ae
                            except Exception as e:
                                raise e
                    time.sleep(10)
            

            # update delay models from tm emulator
            f = open(file_path + "/test_json/delaymodel_fsp.json")
            delay_model = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for model in delay_model["delayModel"]:
                model["epoch"] = epoch
                if model["destinationType"] == "fsp":
                    epoch = str(int(epoch) + 10)
            
            # update delay model
            proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)

            for model in delay_model["delayModel"]:
                if model["destinationType"] == "fsp":
                    for receptor in model["delayDetails"]:
                        rec_id = int(receptor["receptor"])
                        fs_id = receptor["receptorDelayDetails"][0]["fsid"]
                        for index, value in enumerate(receptor["receptorDelayDetails"][0]["delayCoeff"]):
                            try:
                                assert proxies.fsp[fs_id].delayModel[rec_id - 1][index] == value
                            except AssertionError as ae:
                                raise ae
                            except Exception as e:
                                raise e
                    time.sleep(10)

            # update timing beam weights from tm emulator
            f = open(file_path + "/test_json/timingbeamweights.json")
            timing_beam_weights = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for weights in timing_beam_weights["beamWeights"]:
                weights["epoch"] = epoch
                epoch = str(int(epoch) + 10)
            
            # update delay model
            proxies.tm.beamWeights = json.dumps(timing_beam_weights)
            time.sleep(1)

            for weights in timing_beam_weights["beamWeights"]:
                for receptor in weights["beamWeightsDetails"]:
                    rec_id = int(receptor["receptor"])
                    fs_id = receptor["receptorWeightsDetails"][0]["fsid"]
                    for index, value in enumerate(receptor["receptorWeightsDetails"][0]["weights"]):
                        try:
                            assert proxies.fsp[fs_id].timingBeamWeights[rec_id - 1][index] == value
                        except AssertionError as ae:
                            raise ae
                        except Exception as e:
                            raise e
                time.sleep(10)

            # Clean Up
            proxies.clean_proxies()
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_EndScan(self, proxies, input_test_data):
        """
        Test the EndScan command
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # Input test data:
            input_receptors  = input_test_data[0] 
            config_file_name = input_test_data[1]

            subarr_index = 1;
            logging.info( "input_receptors  = {}".format(input_receptors) )
            logging.info( "config_file_name = {}".format(config_file_name) )

            num_receptors = len(input_receptors)

            vcc_ids = [None for _ in range(num_receptors)]
            for receptor_id, ii in zip(input_receptors, range(num_receptors)):
                vcc_ids[ii] = proxies.receptor_to_vcc[receptor_id]

            proxies.subarray[subarr_index].AddReceptors(input_receptors)
            proxies.wait_timeout_obs([proxies.subarray[subarr_index]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[subarr_index].receptors[i] == j for i, j in zip(range(num_receptors), input_receptors)])
            assert proxies.subarray[subarr_index].obsState == ObsState.IDLE

            # Check fsp obsState BEFORE scan configuration:
            assert proxies.fspCorrSubarray[subarr_index-1].obsState == ObsState.IDLE
            assert proxies.fspPssSubarray[subarr_index-1].obsState == ObsState.IDLE
            assert proxies.fspPstSubarray[subarr_index-1].obsState == ObsState.IDLE

            logging.info( "First vcc obsState BEFORE ConfigureScan = {}".
            format(proxies.vcc[vcc_ids[0]].obsState) )

            f = open(file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            input_config_dict = json.loads(json_string)
            proxies.subarray[subarr_index].ConfigureScan(json_string)
            f.close()

            proxies.wait_timeout_obs([proxies.subarray[subarr_index]], ObsState.READY, 15, 1)

            logging.info( "First vcc obsState AFTER ConfigureScan = {}".
            format(proxies.vcc[vcc_ids[0]].obsState) )

            # check some configured attributes of CBF subarray           
            frequency_band   = input_config_dict["common"]["frequency_band"]
            input_band_index = freq_band_dict()[frequency_band]

            assert proxies.subarray[subarr_index].configID == input_config_dict["common"]["config_id"]
            assert proxies.subarray[subarr_index].frequencyBand == input_band_index
            assert proxies.subarray[subarr_index].obsState == ObsState.READY

            # Send the Scan command
            f2 = open(file_path + "/test_json/Scan1_basic.json")
            json_string = f2.read().replace("\n", "")
            input_scan_dict = json.loads(json_string)
            proxies.subarray[subarr_index].Scan(json_string)
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[subarr_index]], ObsState.SCANNING, 1, 1)

            # Note: scan_id is 1-based and of 'string' type 
            #       scan_index is an index into an array, therefore 0-based       
            scan_index = int(input_scan_dict["scan_id"]) - 1
            logging.info( "proxies.fspCorrSubarray[subarr_index-1].obsState = {}".
            format(proxies.fspCorrSubarray[subarr_index-1].obsState) )
            logging.info( "proxies.fspPssSubarray[subarr_index-1].obsState = {}".
            format(proxies.fspPssSubarray[subarr_index-1].obsState) )
            logging.info( "proxies.fspPstSubarray[subarr_index-1].obsState = {}".
            format(proxies.fspPstSubarray[subarr_index-1].obsState) )

            # Check obsStates BEFORE the EndScan() command
            assert proxies.subarray[subarr_index].obsState == ObsState.SCANNING
            assert proxies.vcc[vcc_ids[0]].obsState == ObsState.SCANNING
            assert proxies.vcc[vcc_ids[num_receptors-1]].obsState == ObsState.SCANNING

            for fsp in input_config_dict["cbf"]["fsp"]:
                if fsp["function_mode"] == "CORR":
                   assert proxies.fspCorrSubarray[subarr_index-1].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    assert proxies.fspPssSubarray[subarr_index-1].obsState == ObsState.SCANNING
                # TODO: this check does not pass, to fix
                #elif fsp["function_mode"] == "PST-BF":
                #    assert proxies.fspPstSubarray[subarr_index-1].obsState == ObsState.SCANNING

            proxies.subarray[subarr_index].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[subarr_index]], ObsState.READY, 1, 1)

            # Check obsStates AFTER the EndScan() command
            assert proxies.subarray[subarr_index].obsState  == ObsState.READY
            assert proxies.vcc[vcc_ids[0]].obsState         == ObsState.READY
            assert proxies.vcc[vcc_ids[num_receptors -1]].obsState == ObsState.READY
            assert proxies.fspCorrSubarray[subarr_index-1].obsState == ObsState.READY

            for fsp in input_config_dict["cbf"]["fsp"]:
                if fsp["function_mode"] == "CORR":
                   assert proxies.fspCorrSubarray[subarr_index-1].obsState == ObsState.READY 
                elif fsp["function_mode"] == "PSS-BF":
                    assert proxies.fspPssSubarray[subarr_index-1].obsState == ObsState.READY
                # TODO: this check does not pass, to  fix
                #elif fsp["function_mode"] == "PST-BF":
                #    assert proxies.fspPstSubarray[subarr_index-1].obsState == ObsState.READY

            proxies.clean_proxies()

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e
    
    #TODO refactor to verify delay model values against input json
    @pytest.mark.skip(reason="test needs to be refactored")
    def test_ConfigureScan_delayModel(self, proxies):
        """
        Test the reception of delay models
        """
        
        # Read delay model data from file
        f = open(file_path + "/test_json/delaymodel.json")
        delay_model = json.loads(f.read().replace("\n", ""))
        f.close()

        aa = delay_model["delayModel"][0]["delayDetails"][0]["receptorDelayDetails"]
        num_fsp_IDs = len(aa)
        for jj in range(num_fsp_IDs):      
            logging.info( "delayCoeff = {}".format( aa[jj]["delayCoeff"]) )

        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)

            assert proxies.subarray[1].obsState == ObsState.READY

            # create a delay model
            
            # Insert the epoch
            delay_model["delayModel"][0]["epoch"] = str(int(time.time()) + 20)
            delay_model["delayModel"][1]["epoch"] = "0"
            delay_model["delayModel"][2]["epoch"] = str(int(time.time()) + 10)

            # update delay model
            proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)

            for jj in range(4):
                logging.info((" proxies.vcc[{}].receptorID = {}".
                format(jj+1, proxies.vcc[jj+1].receptorID)))

            logging.info( ("Vcc, receptor 1, ObsState = {}".
            format(proxies.vcc[proxies.receptor_to_vcc[1]].ObsState)) )

            #proxies.vcc[0].receptorID

            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][0] == 1.1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][1] == 1.2
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][2] == 1.3
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][3] == 1.4
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][4] == 1.5
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][5] == 1.6

            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][0] == 1.7
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][1] == 1.8
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][2] == 1.9
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][3] == 2.0
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][4] == 2.1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][5] == 2.2

            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][0] == 2.3
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][1] == 2.4
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][2] == 2.5
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][3] == 2.6
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][4] == 2.7
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][5] == 2.8

            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][0] == 2.9
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][1] == 3.0
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][2] == 3.1
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][3] == 3.2
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][4] == 3.3
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][5] == 3.4

            # transition to obsState=SCANNING
            f2 = open(file_path + "/test_json/Scan1_basic.json")
            proxies.subarray[1].Scan(f2.read().replace("\n", ""))
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.SCANNING

            time.sleep(10)
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][0] == 2.1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][1] == 2.2
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][2] == 2.3
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][3] == 2.4
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][4] == 2.5
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][5] == 2.6

            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][0] == 2.7
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][1] == 2.8
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][2] == 2.9
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][3] == 3.0
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][4] == 3.1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][5] == 3.2

            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][0] == 3.3
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][1] == 3.4
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][2] == 3.5
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][3] == 3.6
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][4] == 3.7
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][5] == 3.8

            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][0] == 3.9
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][1] == 4.0
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][2] == 4.1
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][3] == 4.2
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][4] == 4.3
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][5] == 4.4

            time.sleep(10)
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][0] == 0.1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][1] == 0.2
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][2] == 0.3
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][3] == 0.4
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][4] == 0.5
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[0][5] == 0.6

            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][0] == 0.7
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][1] == 0.8
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][2] == 0.9
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][3] == 1.0
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][4] == 1.1
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][5] == 1.2

            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][0] == 1.3
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][1] == 1.4
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][2] == 1.5
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][3] == 1.6
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][4] == 1.7
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[0][5] == 1.8

            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][0] == 1.9
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][1] == 2.0
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][2] == 2.1
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][3] == 2.2
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][4] == 2.3
            assert proxies.vcc[proxies.receptor_to_vcc[4]].delayModel[1][5] == 2.4

            proxies.subarray[1].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 1)

            proxies.clean_proxies()

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_ConfigureScan_jonesMatrix(self, proxies):
        """
        Test the reception of Jones matrices
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)

            assert proxies.subarray[1].obsState == ObsState.READY

            #create a Jones matrix
            f = open(file_path + "/test_json/jonesmatrix.json")
            jones_matrix = json.loads(f.read().replace("\n", ""))
            f.close()

            jones_matrix["jonesMatrix"][0]["epoch"] = str(int(time.time()) + 20)
            jones_matrix["jonesMatrix"][1]["epoch"] = "0"
            jones_matrix["jonesMatrix"][2]["epoch"] = str(int(time.time()) + 10)

            # update Jones Matrix
            proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(5)

            for receptor in jones_matrix["jonesMatrix"][1]["matrixDetails"]:
                for frequency_slice in receptor["receptorMatrix"]:
                    for index, value in enumerate(frequency_slice["matrix"]):
                        vcc_id = proxies.receptor_to_vcc[receptor["receptor"]]
                        fs_id = frequency_slice["fsid"]
                        try:
                            assert proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                        except AssertionError as ae:
                            logging.error("AssertionError; incorrect Jones matrix entry: epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format(
                                jones_matrix["jonesMatrix"][1]["epoch"], vcc_id, index, fs_id-1, proxies.vcc[vcc_id].jonesMatrix[fs_id-1])
                            )
                            raise ae
                        except Exception as e:
                            raise e

            # transition to obsState == SCANNING
            f2 = open(file_path + "/test_json/Scan1_basic.json")
            proxies.subarray[1].Scan(f2.read().replace("\n", ""))
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            
            time.sleep(10)
            for receptor in jones_matrix["jonesMatrix"][2]["matrixDetails"]:
                for frequency_slice in receptor["receptorMatrix"]:
                    for index, value in enumerate(frequency_slice["matrix"]):
                        vcc_id = proxies.receptor_to_vcc[receptor["receptor"]]
                        fs_id = frequency_slice["fsid"]
                        try:
                            assert proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                        except AssertionError as ae:
                            logging.error("AssertionError; incorrect Jones matrix entry: epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format(
                                jones_matrix["jonesMatrix"][1]["epoch"], vcc_id, index, fs_id-1, proxies.vcc[vcc_id].jonesMatrix[fs_id-1])
                            )
                            raise ae
                        except Exception as e:
                            raise e
            
            time.sleep(10)
            for receptor in jones_matrix["jonesMatrix"][0]["matrixDetails"]:
                for frequency_slice in receptor["receptorMatrix"]:
                    for index, value in enumerate(frequency_slice["matrix"]):
                        vcc_id = proxies.receptor_to_vcc[receptor["receptor"]]
                        fs_id = frequency_slice["fsid"]
                        try:
                            assert proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                        except AssertionError as ae:
                            logging.error("AssertionError; incorrect Jones matrix entry: epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format(
                                jones_matrix["jonesMatrix"][1]["epoch"], vcc_id, index, fs_id-1, proxies.vcc[vcc_id].jonesMatrix[fs_id-1])
                            )
                            raise ae
                        except Exception as e:
                            raise e

            proxies.subarray[1].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 1)

            proxies.clean_proxies()

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_Scan(self, proxies):
        """
        Test the Scan command
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f1 = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f1.read().replace("\n", ""))
            f1.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)

            # check initial states
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY

            # send the Scan command
            f2 = open(file_path + "/test_json/Scan1_basic.json")
            proxies.subarray[1].Scan(f2.read().replace("\n", ""))
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 1)

            # check scanID on VCC and FSP
            assert proxies.fspSubarray[1].scanID == 1
            assert proxies.vcc[proxies.receptor_to_vcc[4]].scanID ==1

            # check states
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[1].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[3].obsState == ObsState.SCANNING
            proxies.subarray[1].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.READY

            # Clean Up
            proxies.clean_proxies()

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_Abort_Reset(self, proxies):
        """
        Test abort reset
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            
            ############################# abort from READY ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            # ObsReset
            proxies.subarray[1].ObsReset()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.IDLE
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE


            ############################# abort from SCANNING ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)
            # scan
            f2 = open(file_path + "/test_json/Scan2_basic.json")
            proxies.subarray[1].Scan(f2.read().replace("\n", ""))
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.subarray[1].scanID == 2
            assert proxies.fspSubarray[1].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[3].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # ObsReset
            proxies.subarray[1].ObsReset()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.IDLE
            assert proxies.subarray[1].scanID == 0
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE

            # Clean Up
            proxies.clean_proxies()
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_Abort_Restart(self, proxies):
        """
        Test abort restart
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            
            ############################# abort from IDLE ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.IDLE
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            # Restart: receptors should be empty
            proxies.subarray[1].Restart()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE




            ############################# abort from READY ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            # ObsReset
            proxies.subarray[1].Restart()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE


            ############################# abort from SCANNING ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4, 2])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            # configure scan
            f = open(file_path + "/test_json/ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 1)
            # scan
            f2 = open(file_path + "/test_json/Scan2_basic.json")
            proxies.subarray[1].Scan(f2.read().replace("\n", ""))
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.subarray[1].scanID == 2
            assert proxies.fspSubarray[1].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[3].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # ObsReset
            proxies.subarray[1].Restart()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE

            proxies.clean_proxies()
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_ConfigureScan_minimal(self, proxies):
        try:
            sub_id = 1
            #TODO currently only support for 1 receptor per fsp
            test_receptor_ids = [4, 1]
            #test_receptor_ids = [1]
            vcc_index = proxies.receptor_to_vcc[test_receptor_ids[0]]
            logging.info("vcc_index  = {}".format(vcc_index))
            vcc_band_proxies = proxies.vccBand[vcc_index - 1]

            # turn on Subarray
            if proxies.subarray[sub_id].State() != DevState.ON:
                proxies.subarray[sub_id].On()
                proxies.wait_timeout_dev([proxies.subarray[sub_id]], DevState.ON, 3, 1)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 1)

            # check initial value of attributes of CBF subarray
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert proxies.subarray[sub_id].configID == ''
            # TODO in CbfSubarray, at end of scan, clear all private data
            #assert proxies.subarray[sub_id].frequencyBand == 0
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[sub_id].AddReceptors(test_receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                       for i, j in zip(range(len(test_receptor_ids)), test_receptor_ids)])

            # configure scan 
            f = open(file_path + "/test_json/Configure_TM-CSP_v2.json")
            configuration = f.read().replace("\n", "")
            f.close()
            proxies.subarray[sub_id].ConfigureScan(configuration)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 15, 1)
            configuration = json.loads(configuration)

            band_index = freq_band_dict()[configuration["common"]["frequency_band"]]

            # check configured attributes of CBF subarray
            assert sub_id == int(configuration["common"]["subarray_id"])
            assert proxies.subarray[sub_id].configID == configuration["common"]["config_id"]
            assert proxies.subarray[sub_id].frequencyBand == band_index
            assert proxies.subarray[sub_id].obsState == ObsState.READY

            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(4)], ObsState.READY, 1, 1)

            # check frequency band of VCCs, including states of 
            # frequency band capabilities
            logging.info( ("proxies.vcc[vcc_index].frequencyBand  = {}".
            format( proxies.vcc[vcc_index].frequencyBand)) )

            assert proxies.vcc[vcc_index].configID == configuration["common"]["config_id"]
            assert proxies.vcc[vcc_index].frequencyBand == band_index
            assert proxies.vcc[vcc_index].subarrayMembership == sub_id

            #TODO fix these tests; issue with VccBand devices either not reconfiguring in between
            #     configurations or causing a fault within the Vcc device
            # for proxy in vcc_band_proxies:
            #     logging.info("VCC proxy.State() = {}".format(proxy.State()))
            # for i in range(4):
            #     if (i == 0 and band_index == 0) or (i == (band_index - 1)):
            #         assert vcc_band_proxies[i].State() == DevState.ON
            #     else:
            #         assert vcc_band_proxies[i].State() == DevState.DISABLE

            # check configured attributes of FSPs, including states of function mode capabilities
            fsp_function_mode_proxies = [proxies.fsp1FunctionMode, proxies.fsp2FunctionMode, 
                                         proxies.fsp3FunctionMode, proxies.fsp4FunctionMode]
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("{}".format(fsp_id))
                #TODO add function mode to enum or edit attribute to accept string in FSP
                if fsp["function_mode"] == "CORR": function_mode = 1
                elif fsp["function_mode"] == "PSS-BF": function_mode = 2
                elif fsp["function_mode"] == "PST-BF": function_mode = 3
                elif fsp["function_mode"] == "VLBI": function_mode = 4
                assert proxies.fsp[fsp_id].functionMode == function_mode
                assert sub_id in proxies.fsp[fsp_id].subarrayMembership
                assert [proxy.State() for proxy in fsp_function_mode_proxies[fsp_id-1]] == [
                    DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
                ]
                # check configured attributes of FSP subarray
                #TODO align IDs of fspSubarrays to fsp_id in conftest; currently works for fsps 1 and 2
                assert proxies.fspSubarray[fsp_id].obsState == ObsState.READY
                assert proxies.fspSubarray[fsp_id].receptors == test_receptor_ids[0]
                assert proxies.fspSubarray[fsp_id].frequencyBand == band_index
                assert proxies.fspSubarray[fsp_id].frequencySliceID == fsp["frequency_slice_id"]
                assert proxies.fspSubarray[fsp_id].integrationTime == fsp["integration_factor"]
                assert proxies.fspSubarray[fsp_id].corrBandwidth == fsp["zoom_factor"]
                if fsp["zoom_factor"] > 0:
                    assert proxies.fspSubarray[fsp_id].zoomWindowTuning == fsp["zoom_window_tuning"]
                assert proxies.fspSubarray[fsp_id].fspChannelOffset == fsp["channel_offset"]

                for i in range(len(fsp["channel_averaging_map"])):
                    for j in range(len(fsp["channel_averaging_map"][i])):
                        assert proxies.fspSubarray[fsp_id].channelAveragingMap[i][j] == fsp["channel_averaging_map"][i][j]

                for i in range(len(fsp["output_link_map"])):
                    for j in range(len(fsp["output_link_map"][i])):
                        assert proxies.fspSubarray[fsp_id].outputLinkMap[i][j] == fsp["output_link_map"][i][j]
                
            proxies.clean_proxies()

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

'''    
    def test_ConfigureScan_onlyPss_basic(
            self,
            cbf_master_proxy,
            proxies.subarray[1],
            sw_1_proxy,
            sw_2_proxy,
            vcc_proxies,
            vcc_band_proxies,
            vcc_tdc_proxies,
            fsp_1_proxy,
            fsp_2_proxy,
            fsp_1_function_mode_proxy,
            fsp_2_function_mode_proxy,
            fsp_3_proxies.subarray[1],
            tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in vcc_proxies:
            proxy.Init()
        fsp_3_proxies.subarray[1].Init()
        fsp_1_proxy.Init()
        fsp_2_proxy.Init()
        proxies.subarray[1].set_timeout_millis(60000)  # since the command takes a while
        proxies.subarray[1].Init()
        time.sleep(3)
        cbf_master_proxy.set_timeout_millis(60000)
        cbf_master_proxy.Init()
        time.sleep(60)  # takes pretty long for CBF Master to initialize
        tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               cbf_master_proxy.receptorToVcc)

        cbf_master_proxy.On()
        time.sleep(3)

        # check initial value of attributes of CBF subarray
        # assert proxies.subarray[1].receptors == ()
        # assert proxies.subarray[1].configID == 0
        assert proxies.subarray[1].frequencyBand == 0
        assert proxies.subarray[1].obsState.value == ObsState.IDLE.value
        # assert tm_telstate_proxy.visDestinationAddress == "{}"
        assert tm_telstate_proxy.receivedOutputLinks == False

        # add receptors
        proxies.subarray[1].RemoveAllReceptors()
        proxies.subarray[1].AddReceptors([1, 3, 4])
        time.sleep(1)
        assert proxies.subarray[1].receptors[0] == 1
        assert proxies.subarray[1].receptors[1] == 3
        assert proxies.subarray[1].receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_onlyPss_basic.json")
        proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check configured attributes of CBF subarray    # def test_ConfigureScan_basic(
    #         self,
    #         cbf_master_proxy,
    #         proxies.subarray[1],
    #         sw_1_proxy,
    #         sw_2_proxy,
    #         vcc_proxies,
    #         vcc_band_proxies,
    #         vcc_tdc_proxies,
    #         fsp_1_proxy,
    #         fsp_2_proxy,
    #         fsp_1_function_mode_proxy,
    #         fsp_2_function_mode_proxy,
    #         fsp_1_proxies.subarray[1],
    #         fsp_2_proxies.subarray[1],
    #         fsp_3_proxies.subarray[1],
    #         tm_telstate_proxy
    # ):
    #     """
    #     Test a minimal successful configuration
    #     """
    #     for proxy in vcc_proxies:
    #         proxy.Init()
    #     fsp_1_proxies.subarray[1].Init()
    #     fsp_2_proxies.subarray[1].Init()
    #     fsp_3_proxies.subarray[1].Init()
    #     fsp_1_proxy.Init()
    #     fsp_2_proxy.Init()
    #     proxies.subarray[1].set_timeout_millis(60000)  # since the command takes a while
    #     proxies.subarray[1].Init()
    #     time.sleep(3)
    #     cbf_master_proxy.set_timeout_millis(60000)
    #     cbf_master_proxy.Init()
    #     time.sleep(60)  # takes pretty long for CBF Master to initialize
    #     tm_telstate_proxy.Init()
    #     time.sleep(1)

    #     receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
    #                            cbf_master_proxy.receptorToVcc)

        
    #     cbf_master_proxy.On()
    #     time.sleep(60)

    #     # turn on Subarray
    #     assert proxies.subarray[1].state()==DevState.OFF
    #     proxies.subarray[1].On()
    #     time.sleep(10)
    #     # check initial value of attributes of CBF subarray
    #     assert len(proxies.subarray[1].receptors) == 0
    #     assert proxies.subarray[1].configID == 0
    #     assert proxies.subarray[1].frequencyBand == 0
    #     assert proxies.subarray[1].State() == DevState.ON
    #     assert proxies.subarray[1].ObsState == ObsState.EMPTY
    #     # assert tm_telstate_proxy.visDestinationAddress == "{}"
    #     assert tm_telstate_proxy.receivedOutputLinks == False

    #     # add receptors
    #     proxies.subarray[1].RemoveAllReceptors()
    #     proxies.subarray[1].AddReceptors([1, 3, 4])
    #     time.sleep(1)
    #     assert proxies.subarray[1].receptors[0] == 1
    #     assert proxies.subarray[1].receptors[1] == 3
    #     assert proxies.subarray[1].receptors[2] == 4

    #     # configure scan
    #     f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
    #     proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
    #     f.close()
    #     time.sleep(15)

    #     # check configured attributes of CBF subarray
    #     assert proxies.subarray[1].configID == "band:5a, fsp1, 744 channels average factor 8"
    #     assert proxies.subarray[1].frequencyBand == 4 # means 5a?
    #     assert proxies.subarray[1].obsState.value == ObsState.READY.value

    #     # check frequency band of VCCs, including states of frequency band capabilities
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 4
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 4
    #     assert [proxy.State() for proxy in vcc_band_proxies[receptor_to_vcc[4] - 1]] == [
    #         DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
    #     assert [proxy.State() for proxy in vcc_band_proxies[receptor_to_vcc[1] - 1]] == [
    #         DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

    #     # check the rest of the configured attributes of VCCs
    #     # first for VCC belonging to receptor 10...
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[0] == 5.85
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[1] == 7.25
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream1 == 0
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream2 == 0
    #     assert vcc_proxies[receptor_to_vcc[4] - 1].rfiFlaggingMask == "{}"
    #     # then for VCC belonging to receptor 1...
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[0] == 5.85
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[1] == 7.25
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream1 == 0
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream2 == 0
    #     assert vcc_proxies[receptor_to_vcc[1] - 1].rfiFlaggingMask == "{}"

    #     # check configured attributes of search windows
    #     # first for search window 1...
    #     assert sw_1_proxy.State() == DevState.ON
    #     assert sw_1_proxy.searchWindowTuning == 6000000000
    #     assert sw_1_proxy.tdcEnable == True
    #     assert sw_1_proxy.tdcNumBits == 8
    #     assert sw_1_proxy.tdcPeriodBeforeEpoch == 5
    #     assert sw_1_proxy.tdcPeriodAfterEpoch == 25
    #     assert "".join(sw_1_proxy.tdcDestinationAddress.split()) in [
    #         "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
    #         "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
    #         "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
    #         "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
    #     ]
    #     # then for search window 2...
    #     assert sw_2_proxy.State() == DevState.DISABLE
    #     assert sw_2_proxy.searchWindowTuning == 7000000000
    #     assert sw_2_proxy.tdcEnable == False

    #     # check configured attributes of VCC search windows
    #     # first for search window 1 of VCC belonging to receptor 10...
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].State() == DevState.ON
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcEnable == True
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcNumBits == 8
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
    #         "foo", "bar", "8080"
    #     )
    #     # then for search window 1 of VCC belonging to receptor 1...
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].State() == DevState.ON
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcEnable == True
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcNumBits == 8
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
    #         "fizz", "buzz", "80"
    #     )
    #     # then for search window 2 of VCC belonging to receptor 10...
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].State() == DevState.DISABLE
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].searchWindowTuning == 7000000000
    #     assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].tdcEnable == False
    #     # and lastly for search window 2 of VCC belonging to receptor 1...
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].State() == DevState.DISABLE
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
    #     assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].tdcEnable == False

    #     # check configured attributes of FSPs, including states of function mode capabilities
    #     assert fsp_1_proxy.functionMode == 1
    #     assert 1 in fsp_1_proxy.subarrayMembership
    #     # assert 1 in fsp_2_proxy.subarrayMembership
    #     assert [proxy.State() for proxy in fsp_1_function_mode_proxy] == [
    #         DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
    #     ]
    #     # assert [proxy.State() for proxy in fsp_2_function_mode_proxy] == [
    #     #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
    #     # ]

    #     # check configured attributes of FSP subarrays
    #     # first for FSP 1...
    #     assert fsp_1_proxies.subarray[1].obsState == ObsState.EMPTY
    #     assert fsp_1_proxies.subarray[1].receptors == 4
    #     assert fsp_1_proxies.subarray[1].frequencyBand == 4
    #     assert fsp_1_proxies.subarray[1].band5Tuning[0] == 5.85
    #     assert fsp_1_proxies.subarray[1].band5Tuning[1] == 7.25
    #     assert fsp_1_proxies.subarray[1].frequencyBandOffsetStream1 == 0
    #     assert fsp_1_proxies.subarray[1].frequencyBandOffsetStream2 == 0
    #     assert fsp_1_proxies.subarray[1].frequencySliceID == 1
    #     assert fsp_1_proxies.subarray[1].corrBandwidth == 1
    #     assert fsp_1_proxies.subarray[1].zoomWindowTuning == 4700000
    #     assert fsp_1_proxies.subarray[1].integrationTime == 140
    #     assert fsp_1_proxies.subarray[1].fspChannelOffset == 14880
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[0][0] == 0
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[0][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[1][0] == 744
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[1][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[2][0] == 1488
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[2][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[3][0] == 2232
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[3][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[4][0] == 2976
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[4][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[5][0] == 3720
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[5][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[6][0] == 4464
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[6][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[7][0] == 5208
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[7][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[8][0] == 5952
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[8][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[9][0] == 6696
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[9][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[10][0] == 7440
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[10][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[11][0] == 8184
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[11][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[12][0] == 8928
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[12][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[13][0] == 9672
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[13][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[14][0] == 10416
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[14][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[15][0] == 11160
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[15][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[16][0] == 11904
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[16][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[17][0] == 12648
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[17][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[18][0] == 13392
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[18][1] == 8
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[19][0] == 14136
    #     # assert fsp_1_proxies.subarray[1].channelAveragingMap[19][1] == 8
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[0][0] == 0
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[0][1] == 4
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[1][0] == 744
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[1][1] == 8        
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[2][0] == 1488
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[2][1] == 12
    #     assert fsp_1_proxies.subarray[1].outputLinkMap[3][0] == 2232
    #     assert fsp_1_subarray_1_proroxy.receptors[2] == 4
    #     # assert fsp_2_proxies.subarray[1].frequencyBand == 4
    #     # assert fsp_2_proxies.subarray[1].band5Tuning[0] == 5.85
    #     # assert fsp_2_proxies.subarray[1].band5Tuning[1] == 7.25
    #     # assert fsp_2_proxies.subarray[1].frequencyBandOffsetStream1 == 0
    #     # assert fsp_2_proxies.subarray[1].frequencyBandOffsetStream2 == 0
    #     # assert fsp_2_proxies.subarray[1].frequencySliceID == 20
    #     # assert fsp_2_proxies.subarray[1].corrBandwidth == 0
    #     # assert fsp_2_proxies.subarray[1].integrationTime == 1400
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[0][0] == 1
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[0][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[1][0] == 745
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[1][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[2][0] == 1489
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[2][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[3][0] == 2233
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[3][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[4][0] == 2977
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[4][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[5][0] == 3721
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[5][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[6][0] == 4465
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[6][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[7][0] == 5209
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[7][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[8][0] == 5953
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[8][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[9][0] == 6697
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[9][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[10][0] == 7441
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[10][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[11][0] == 8185
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[11][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[12][0] == 8929
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[12][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[13][0] == 9673
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[13][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[14][0] == 10417
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[14][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[15][0] == 11161
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[15][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[16][0] == 11905
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[16][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[17][0] == 12649
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[17][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[18][0] == 13393
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[18][1] == 0
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[19][0] == 14137
    #     # assert fsp_2_proxies.subarray[1].channelAveragingMap[19][1] == 0

    #     # then for FSP 3...
    #     assert fsp_3_proxies.subarray[1].receptors[0] == 3
    #     assert fsp_3_proxies.subarray[1].receptors[1] == 1
    #     assert fsp_3_proxies.subarray[1].searchWindowID == 2
    #     assert fsp_3_proxies.subarray[1].searchBeamID[0] == 300
    #     assert fsp_3_proxies.subarray[1].searchBeamID[1] == 400


    #     searchBeam = fsp_3_proxies.subarray[1].searchBeams
    #     searchBeam300 = json.loads(searchBeam[0])
    #     searchBeam400 = json.loads(searchBeam[1])
    #     assert searchBeam300["searchBeamID"] == 300
    #     assert searchBeam300["receptors"][0] == 3
    #     assert searchBeam300["outputEnable"] == True
    #     assert searchBeam300["averagingInterval"] == 4
    #     assert searchBeam300["searchBeamDestinationAddress"] == "10.05.1.1"

    #     assert searchBeam400["searchBeamID"] == 400
    #     assert searchBeam400["receptors"][0] == 1
    #     assert searchBeam400["outputEnable"] == True
    #     assert searchBeam400["averagingInterval"] == 2
    #     assert searchBeam400["searchBeamDestinationAddress"] == "10.05.2.1"

    #     proxies.subarray[1].GoToIdle()
    #     time.sleep(3)
    #     assert proxies.subarray[1].obsState == ObsState.IDLE
    #     proxies.subarray[1].RemoveAllReceptors()
    #     time.sleep(3)
    #     assert proxies.subarray[1].state() == tango.DevState.OFFequency band capabilities
        assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 4
        assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 4
        assert [proxy.State() for proxy in vcc_band_proxies[receptor_to_vcc[4] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
        assert [proxy.State() for proxy in vcc_band_proxies[receptor_to_vcc[1] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

        # check the rest of the configured attributes of VCCs
        # first for VCC belonging to receptor 10...
        assert vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1
        assert vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[0] == 5.85
        assert vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[1] == 7.25
        assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream1 == 0
        assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream2 == 0
        assert vcc_proxies[receptor_to_vcc[4] - 1].rfiFlaggingMask == "{}"
        # then for VCC belonging to receptor 1...
        assert vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1
        assert vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[0] == 5.85
        assert vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[1] == 7.25
        assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream1 == 0
        assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream2 == 0
        assert vcc_proxies[receptor_to_vcc[1] - 1].rfiFlaggingMask == "{}"

        # check configured attributes of search windows
        # first for search window 1...
        assert sw_1_proxy.State() == DevState.ON
        assert sw_1_proxy.searchWindowTuning == 6000000000
        assert sw_1_proxy.tdcEnable == True
        assert sw_1_proxy.tdcNumBits == 8
        assert sw_1_proxy.tdcPeriodBeforeEpoch == 5
        assert sw_1_proxy.tdcPeriodAfterEpoch == 25
        assert "".join(sw_1_proxy.tdcDestinationAddress.split()) in [
            "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
        ]
        # then for search window 2...
        assert sw_2_proxy.State() == DevState.DISABLE
        assert sw_2_proxy.searchWindowTuning == 7000000000
        assert sw_2_proxy.tdcEnable == False

        # check configured attributes of VCC search windows
        # first for search window 1 of VCC belonging to receptor 10...
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].State() == DevState.ON
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcEnable == True
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcNumBits == 8
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
            "foo", "bar", "8080"
        )
        # then for search window 1 of VCC belonging to receptor 1...
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].State() == DevState.ON
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcEnable == True
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcNumBits == 8
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
            "fizz", "buzz", "80"
        )
        # then for search window 2 of VCC belonging to receptor 10...
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].State() == DevState.DISABLE
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].searchWindowTuning == 7000000000
        assert vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].tdcEnable == False
        # and lastly for search window 2 of VCC belonging to receptor 1...
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].State() == DevState.DISABLE
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
        assert vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].tdcEnable == False

        assert fsp_3_proxies.subarray[1].receptors[0] == 3
        assert fsp_3_proxies.subarray[1].receptors[1] == 1
        assert fsp_3_proxies.subarray[1].searchWindowID == 2
        assert fsp_3_proxies.subarray[1].searchBeamID[0] == 300
        assert fsp_3_proxies.subarray[1].searchBeamID[1] == 400


        searchBeam = fsp_3_proxies.subarray[1].searchBeams
        searchBeam300 = json.loads(searchBeam[0])
        searchBeam400 = json.loads(searchBeam[1])
        assert searchBeam300["searchBeamID"] == 300
        assert searchBeam300["receptors"][0] == 3
        assert searchBeam300["outputEnable"] == True
        assert searchBeam300["averagingInterval"] == 4
        assert searchBeam300["searchBeamDestinationAddress"] == "10.05.1.1"

        assert searchBeam400["searchBeamID"] == 400
        assert searchBeam400["receptors"][0] == 1
        assert searchBeam400["outputEnable"] == True
        assert searchBeam400["averagingInterval"] == 2
        assert searchBeam400["searchBeamDestinationAddress"] == "10.05.2.1"

        proxies.subarray[1].GoToIdle()
        time.sleep(3)
        assert proxies.subarray[1].obsState == ObsState.IDLE
        proxies.subarray[1].RemoveAllReceptors()
        time.sleep(3)
        assert proxies.subarray[1].state() == tango.DevState.OFF

    def test_band1(
            self,
            cbf_master_proxy,
            proxies.subarray[1],
            sw_1_proxy,
            sw_2_proxy,
            vcc_proxies,
            vcc_band_proxies,
            vcc_tdc_proxies,
            fsp_1_proxy,
            fsp_2_proxy,
            fsp_1_function_mode_proxy,
            fsp_2_function_mode_proxy,
            fsp_1_proxies.subarray[1],
            fsp_2_proxies.subarray[1],
            fsp_3_proxies.subarray[1],
            tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in vcc_proxies:
            proxy.Init()
        fsp_1_proxies.subarray[1].Init()
        fsp_2_proxies.subarray[1].Init()
        fsp_3_proxies.subarray[1].Init()
        fsp_1_proxy.Init()
        fsp_2_proxy.Init()

        time.sleep(3)
        cbf_master_proxy.set_timeout_millis(60000)
        cbf_master_proxy.Init()
        time.sleep(60)  # takes pretty long for CBF Master to initialize
        tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               cbf_master_proxy.receptorToVcc)

        cbf_master_proxy.On()
        time.sleep(3)

        # check initial value of attributes of CBF subarray
        assert len(proxies.subarray[1].receptors) == 0
        assert proxies.subarray[1].configID == ''
        assert proxies.subarray[1].frequencyBand == 0
        assert proxies.subarray[1].obsState.value == ObsState.IDLE.value
        # assert tm_telstate_proxy.visDestinationAddress == "{}"
        assert tm_telstate_proxy.receivedOutputLinks == False

        # add receptors
        proxies.subarray[1].AddReceptors([1, 3, 4])
        time.sleep(1)
        assert proxies.subarray[1].receptors[0] == 1
        assert proxies.subarray[1].receptors[1] == 3
        assert proxies.subarray[1].receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/data_model_confluence.json")
        proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check configured attributes of CBF subarray
        assert proxies.subarray[1].configID == "sbi-mvp01-20200325-00001-science_A"
        assert proxies.subarray[1].frequencyBand == 0 # means 1
        assert proxies.subarray[1].obsState.value == ObsState.READY.value

        # check frequency band of VCCs, including states of frequency band capabilities
        assert vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 0
        assert vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 0


        # check the rest of the configured attributes of VCCs
        # first for VCC belonging to receptor 10...
        assert vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1

        # then for VCC belonging to receptor 1...
        assert vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1



        # check configured attributes of FSPs, including states of function mode capabilities
        assert fsp_1_proxy.functionMode == 1
        assert 1 in fsp_1_proxy.subarrayMembership
        # assert 1 in fsp_2_proxy.subarrayMembership
        assert [proxy.State() for proxy in fsp_1_function_mode_proxy] == [
            DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        ]
        # assert [proxy.State() for proxy in fsp_2_function_mode_proxy] == [
        #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        # ]

        # check configured attributes of FSP subarrays
        # first for FSP 1...
        assert fsp_1_proxies.subarray[1].obsState == ObsState.READY
        assert fsp_1_proxies.subarray[1].frequencyBand == 0
        assert fsp_1_proxies.subarray[1].frequencySliceID == 1
        assert fsp_1_proxies.subarray[1].corrBandwidth == 0
        assert fsp_1_proxies.subarray[1].integrationTime == 1400

        assert fsp_1_proxies.subarray[1].outputLinkMap[0][0] == 1
        assert fsp_1_proxies.subarray[1].outputLinkMap[0][1] == 0
        assert fsp_1_proxies.subarray[1].outputLinkMap[1][0] == 201
        assert fsp_1_proxies.subarray[1].outputLinkMap[1][1] == 1



        proxies.subarray[1].GoToIdle()
        time.sleep(3)
        assert proxies.subarray[1].obsState == ObsState.IDLE
        proxies.subarray[1].RemoveAllReceptors()
        time.sleep(1)
        proxies.subarray[1].Off()
        assert proxies.subarray[1].state() == tango.DevState.OFF
'''


