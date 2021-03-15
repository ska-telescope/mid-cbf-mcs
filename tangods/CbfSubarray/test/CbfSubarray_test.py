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
import json
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

from CbfSubarray.CbfSubarray import CbfSubarray
from ska_tango_base.control_model import HealthState, AdminMode, ObsState

@pytest.mark.usefixtures(
    "create_cbf_master_proxy",
    "create_subarray_1_proxy",
    "create_subarray_2_proxy",
    "create_sw_1_proxy",
    "create_sw_2_proxy",
    "create_vcc_proxies",
    "create_vcc_band_proxies",
    "create_vcc_tdc_proxies",
    "create_fsp_1_proxy",
    "create_fsp_2_proxy",
    "create_fsp_1_function_mode_proxy",
    "create_fsp_2_function_mode_proxy",
    "create_fsp_1_subarray_1_proxy",
    "create_fsp_2_subarray_1_proxy",
    "create_tm_telstate_proxy"
)

class TestCbfSubarray:
    
    def test_AddRemoveReceptors_valid(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies
    ):
        """
        Test valid AddReceptors and RemoveReceptors commands
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        # receptor list should be empty right after initialization
        assert len(create_subarray_1_proxy.receptors) == 0
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        

        # turn on Subarray
        if create_subarray_1_proxy.State() != DevState.ON:
            create_subarray_1_proxy.On()
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.ON
        assert create_subarray_1_proxy.ObsState == ObsState.EMPTY

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3, 4]])
        assert create_subarray_1_proxy.ObsState == ObsState.IDLE

        # add more receptors...
        create_subarray_1_proxy.AddReceptors([2])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4
        assert create_subarray_1_proxy.receptors[3] == 2
        assert create_vcc_proxies[receptor_to_vcc[2] - 1].subarrayMembership == 1

        # remove some receptors
        create_subarray_1_proxy.RemoveReceptors([2, 1, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == ([3])
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 2, 4]])
        assert create_vcc_proxies[receptor_to_vcc[3] - 1].subarrayMembership == 1

        # remove remaining receptors
        create_subarray_1_proxy.RemoveReceptors([3])
        time.sleep(1)
        assert len(create_subarray_1_proxy.receptors) == 0
        assert create_vcc_proxies[receptor_to_vcc[3] - 1].subarrayMembership == 0
        assert create_subarray_1_proxy.ObsState == ObsState.EMPTY
        create_subarray_1_proxy.Off()
        time.sleep(1)

    def test_AddRemoveReceptors_invalid_single(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies
    ):
        """
        Test invalid AddReceptors commands involving a single subarray:
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        # receptor list should be empty right after initialization
        assert len(create_subarray_1_proxy.receptors) == 0
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])

        # turn on Subarray
        if create_subarray_1_proxy.State() != DevState.ON:
            create_subarray_1_proxy.On()
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.ON
        assert create_subarray_1_proxy.ObsState == ObsState.EMPTY

        # add some receptors to subarray 1
        create_subarray_1_proxy.AddReceptors([1, 3])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3]])
        assert create_subarray_1_proxy.ObsState == ObsState.IDLE

        # TODO: fix this
        # try adding an invalid receptor ID
        # with pytest.raises(tango.DevFailed) as df:
        #     create_subarray_1_proxy.AddReceptors([5])
        time.sleep(1)
        # assert "Invalid receptor ID" in str(df.value.args[0].desc)

        # try removing a receptor not assigned to subarray 1
        # doing this doesn't actually throw an error
        create_subarray_1_proxy.RemoveReceptors([2])
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        create_subarray_1_proxy.RemoveAllReceptors()
        create_subarray_1_proxy.Off()
        

    # Since there's only a single subarray, this test is currently broken.
    """
    def test_AddRemoveReceptors_invalid_multiple(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_subarray_2_proxy,
            create_vcc_proxies
    ):
    """
    """
        Test invalid AddReceptors commands involving multiple subarrays:
            - when a receptor to be added is already in use by a different subarray
    """
    """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)
        create_subarray_2_proxy.set_timeout_millis(60000)
        create_subarray_1_proxy.Init()
        create_subarray_2_proxy.Init()
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(60)  # takes pretty long for CBF Master to initialize

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_2_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        assert create_subarray_1_proxy.State() == DevState.OFF
        assert create_subarray_2_proxy.State() == DevState.OFF

        # add some receptors to subarray 1
        create_subarray_1_proxy.AddReceptors([1, 3])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (1, 3)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3]])
        assert create_subarray_1_proxy.State() == DevState.ON

        # try adding some receptors (including an invalid one) to subarray 2
        with pytest.raises(tango.DevFailed) as df:
            create_subarray_2_proxy.AddReceptors([1, 2, 4])
        time.sleep(1)
        assert "already in use" in str(df.value.args[0].desc)
        assert create_subarray_2_proxy.receptors == (2, 4)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3]])
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 2 for i in [2, 4]])
        assert create_subarray_2_proxy.State() == DevState.ON
    """

    def test_RemoveAllReceptors(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies
    ):
        """
        Test RemoveAllReceptors command
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(5)


        
        # receptor list should be empty right after initialization
        assert len(create_subarray_1_proxy.receptors) == 0
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])

        # turn on Subarray
        if create_subarray_1_proxy.State() != DevState.ON:
            create_subarray_1_proxy.On()
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.ON
        assert create_subarray_1_proxy.ObsState == ObsState.EMPTY

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 3, 4]])
        assert create_subarray_1_proxy.ObsState == ObsState.IDLE

        # remove all receptors
        create_subarray_1_proxy.RemoveAllReceptors()
        time.sleep(1)
        assert len(create_subarray_1_proxy.receptors) == 0
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 3, 4]])
        assert create_subarray_1_proxy.ObsState == ObsState.EMPTY
        create_subarray_1_proxy.Off()



    def test_ConfigureScan_basic(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_sw_1_proxy,
            create_sw_2_proxy,
            create_vcc_proxies,
            create_vcc_band_proxies,
            create_vcc_tdc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_function_mode_proxy,
            create_fsp_2_function_mode_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)  # since the command takes a while
        # create_subarray_1_proxy.Init()
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        # turn on Subarray
        if create_subarray_1_proxy.State() != DevState.ON:
            create_subarray_1_proxy.On()
        time.sleep(1)
        # check initial value of attributes of CBF subarray
        assert len(create_subarray_1_proxy.receptors) == 0
        assert create_subarray_1_proxy.configID == ''
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState.value == ObsState.EMPTY.value

        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check configured attributes of CBF subarray
        assert create_subarray_1_proxy.configID == "band:5a, fsp1, 744 channels average factor 8"
        assert create_subarray_1_proxy.frequencyBand == 4 # means 5a
        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value

        # check frequency band of VCCs, including states of frequency band capabilities
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 4
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 4
        assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[4] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
        assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[1] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

        # check the rest of the configured attributes of VCCs
        # first for VCC belonging to receptor 10...
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[0] == 5.85
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[1] == 7.25
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream1 == 0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream2 == 0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].rfiFlaggingMask == "{}"
        # then for VCC belonging to receptor 1...
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[0] == 5.85
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[1] == 7.25
       

        # check configured attributes of search windows
        # first for search window 1...
        assert create_sw_1_proxy.State() == DevState.ON
        assert create_sw_1_proxy.searchWindowTuning == 6000000000
        assert create_sw_1_proxy.tdcEnable == True
        assert create_sw_1_proxy.tdcNumBits == 8
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 5
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 25
        assert "".join(create_sw_1_proxy.tdcDestinationAddress.split()) in [
            "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
        ]
        # then for search window 2...
        assert create_sw_2_proxy.State() == DevState.DISABLE
        assert create_sw_2_proxy.searchWindowTuning == 7000000000
        assert create_sw_2_proxy.tdcEnable == False

        # check configured attributes of VCC search windows
        # first for search window 1 of VCC belonging to receptor 10...
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].State() == DevState.ON
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcEnable == True
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcNumBits == 8
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
            "foo", "bar", "8080"
        )
        # then for search window 1 of VCC belonging to receptor 1...
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].State() == DevState.ON
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcEnable == True
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcNumBits == 8
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
            "fizz", "buzz", "80"
        )
        # then for search window 2 of VCC belonging to receptor 10...
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].State() == DevState.DISABLE
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].searchWindowTuning == 7000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].tdcEnable == False
        # and lastly for search window 2 of VCC belonging to receptor 1...
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].State() == DevState.DISABLE
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].tdcEnable == False

        # check configured attributes of FSPs, including states of function mode capabilities
        assert create_fsp_1_proxy.functionMode == 1
        assert 1 in create_fsp_1_proxy.subarrayMembership
        assert [proxy.State() for proxy in create_fsp_1_function_mode_proxy] == [
            DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        ]
        # assert [proxy.State() for proxy in create_fsp_2_function_mode_proxy] == [
        #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        # ]

        # check configured attributes of FSP subarrays
        # first for FSP 1...
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_1_subarray_1_proxy.receptors == 4
        assert create_fsp_1_subarray_1_proxy.frequencyBand == 4
        assert create_fsp_1_subarray_1_proxy.band5Tuning[0] == 5.85
        assert create_fsp_1_subarray_1_proxy.band5Tuning[1] == 7.25
        assert create_fsp_1_subarray_1_proxy.frequencyBandOffsetStream1 == 0
        assert create_fsp_1_subarray_1_proxy.frequencyBandOffsetStream2 == 0
        assert create_fsp_1_subarray_1_proxy.frequencySliceID == 1
        assert create_fsp_1_subarray_1_proxy.corrBandwidth == 1
        assert create_fsp_1_subarray_1_proxy.zoomWindowTuning == 4700000
        assert create_fsp_1_subarray_1_proxy.integrationTime == 140
        assert create_fsp_1_subarray_1_proxy.fspChannelOffset == 14880

        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[0][0] == 0
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[0][1] == 8
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[1][0] == 744
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[1][1] == 8
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[2][0] == 1488
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[2][1] == 8
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[3][0] == 2232
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[3][1] == 8
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap[4][0] == 2976

        assert create_fsp_1_subarray_1_proxy.outputLinkMap[0][0] == 0
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[0][1] == 4
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[1][0] == 744
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[1][1] == 8        
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[2][0] == 1488
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[2][1] == 12
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[3][0] == 2232
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[3][1] == 16
        assert str(create_fsp_1_subarray_1_proxy.visDestinationAddress).replace('"',"'") == \
            str({"outputHost": [[0, "192.168.0.1"], [8184, "192.168.0.2"]], "outputMac": [[0, "06-00-00-00-00-01"]], "outputPort": [[0, 9000, 1], [8184, 9000, 1]]}).replace('"',"'")
         


        # Clean Up
        create_subarray_1_proxy.GoToIdle()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()     
        time.sleep(1)
        if create_subarray_1_proxy.obsState!=ObsState.EMPTY:
            create_subarray_1_proxy.Off()
            assert create_subarray_1_proxy.state() == tango.DevState.OFF
        else: 
            assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
            time.sleep(1)
            create_subarray_1_proxy.Off()
            assert create_subarray_1_proxy.state() == tango.DevState.OFF

    


 


    def test_EndScan(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test the EndScan command
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        assert create_tm_telstate_proxy.state() == tango.DevState.STANDBY
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        assert create_subarray_1_proxy.obsState.value == ObsState.EMPTY.value

        # turn on Subarray
        if create_subarray_1_proxy.State() != DevState.ON:
            create_subarray_1_proxy.On()
        time.sleep(1)

        # add receptors

        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(6)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4


        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.IDLE
        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check configured attributes of CBF subarray
        assert create_subarray_1_proxy.configID == "band:5a, fsp1, 744 channels average factor 8"
        assert create_subarray_1_proxy.frequencyBand == 4
        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value

        # send the Scan command
        create_subarray_1_proxy.Scan(1)
        time.sleep(1)

        # check initial states
        assert create_subarray_1_proxy.obsState.value == ObsState.SCANNING
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.SCANNING.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.SCANNING.value
        assert create_fsp_1_subarray_1_proxy.obsState.value == ObsState.SCANNING.value
        assert create_fsp_3_subarray_1_proxy.obsState.value == ObsState.SCANNING.value

        # send the EndScan command
        create_subarray_1_proxy.EndScan()
        time.sleep(1)

        # check states
        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.READY.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.READY.value
        assert create_fsp_1_subarray_1_proxy.obsState.value == ObsState.READY.value
        assert create_fsp_3_subarray_1_proxy.obsState.value == ObsState.READY.value

        # check scanID to zero
        assert create_fsp_1_subarray_1_proxy.scanID == 0

        # Clean Up
        create_subarray_1_proxy.GoToIdle()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()     
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF

    def test_ConfigureScan_delayModel(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test the reception of delay models
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(80000)  # since the command takes a while
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)


        assert create_subarray_1_proxy.obsState.value == ObsState.EMPTY.value

        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(30)

        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value

        # create a delay model
        f = open(file_path + "/test_json/delaymodel.json")
        delay_model = json.loads(f.read().replace("\n", ""))
        delay_model["delayModel"][0]["epoch"] = str(int(time.time()) + 20)
        delay_model["delayModel"][1]["epoch"] = "0"
        delay_model["delayModel"][2]["epoch"] = str(int(time.time()) + 10)

        # update delay model
        create_tm_telstate_proxy.delayModel = json.dumps(delay_model)
        time.sleep(1)
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][0] == 1.1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][1] == 1.2
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][2] == 1.3
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][3] == 1.4
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][4] == 1.5
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][5] == 1.6

        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][0] == 1.7
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][1] == 1.8
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][2] == 1.9
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][3] == 2.0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][4] == 2.1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][5] == 2.2

        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][0] == 2.3
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][1] == 2.4
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][2] == 2.5
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][3] == 2.6
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][4] == 2.7
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][5] == 2.8

        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][0] == 2.9
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][1] == 3.0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][2] == 3.1
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][3] == 3.2
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][4] == 3.3
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][5] == 3.4

        # transition to obsState=SCANNING
        create_subarray_1_proxy.Scan(1)
        time.sleep(1)
        assert create_subarray_1_proxy.obsState.value == ObsState.SCANNING.value

        time.sleep(10)
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][0] == 2.1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][1] == 2.2
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][2] == 2.3
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][3] == 2.4
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][4] == 2.5
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][5] == 2.6

        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][0] == 2.7
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][1] == 2.8
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][2] == 2.9    #     assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][3] == 3.0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][4] == 3.1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][5] == 3.2

        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][0] == 3.3
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][1] == 3.4
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][2] == 3.5
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][3] == 3.6
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][4] == 3.7
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][5] == 3.8

        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][0] == 3.9
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][1] == 4.0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][2] == 4.1
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][3] == 4.2
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][4] == 4.3
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][5] == 4.4

        time.sleep(10)
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][0] == 0.1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][1] == 0.2
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][2] == 0.3
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][3] == 0.4
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][4] == 0.5
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[0][5] == 0.6

        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][0] == 0.7
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][1] == 0.8
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][2] == 0.9
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][3] == 1.0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][4] == 1.1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].delayModel[1][5] == 1.2

        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][0] == 1.3
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][1] == 1.4
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][2] == 1.5
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][3] == 1.6
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][4] == 1.7
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[0][5] == 1.8

        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][0] == 1.9
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][1] == 2.0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][2] == 2.1
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][3] == 2.2
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][4] == 2.3
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].delayModel[1][5] == 2.4

        create_subarray_1_proxy.EndScan()
        time.sleep(1)

        # Clean Up
        create_subarray_1_proxy.GoToIdle()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()     
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF

    def test_ConfigureScan_jonesMatrix(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test the reception of Jones matrices
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(80000)  # since the command takes a while
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        #reveal debug level logging in Vcc, CbfSubarray
        for proxy in create_vcc_proxies:
            proxy.loggingLevel = "DEBUG"
        create_subarray_1_proxy.loggingLevel = "DEBUG"

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        assert create_subarray_1_proxy.obsState.value == ObsState.EMPTY.value

        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(30)

        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value

        #create a Jones matrix
        f = open(file_path + "/test_json/jonesmatrix.json")
        jones_matrix = json.loads(f.read().replace("\n", ""))
        jones_matrix["jonesMatrix"][0]["epoch"] = str(int(time.time()) + 20)
        jones_matrix["jonesMatrix"][1]["epoch"] = "0"
        jones_matrix["jonesMatrix"][2]["epoch"] = str(int(time.time()) + 10)

        # update Jones Matrix
        create_tm_telstate_proxy.jonesMatrix = json.dumps(jones_matrix)
        time.sleep(1)

        for receptor in jones_matrix["jonesMatrix"][1]["matrixDetails"]:
            for frequency_slice in receptor["receptorMatrix"]:
                for i in frequency_slice["matrix"]:
                    try:
                        assert create_vcc_proxies[receptor_to_vcc[receptor["receptor"]]-1].jonesMatrix[frequency_slice["fsid"]-1][i] == i
                    except AssertionError:
                        logging.error("AssertionError; incorrect Jones matrix entry: epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format(jones_matrix["jonesMatrix"][1]["epoch"], receptor_to_vcc[receptor["receptor"]], i, frequency_slice["fsid"]-1, create_vcc_proxies[receptor_to_vcc[receptor["receptor"]]-1].jonesMatrix[frequency_slice["fsid"]-1]))
                        return AssertionError
                    except Exception:
                        pass

        create_subarray_1_proxy.Scan(1)
        time.sleep(1)
        assert create_subarray_1_proxy.obsState.value == ObsState.SCANNING.value
        
        time.sleep(10)
        for receptor in jones_matrix["jonesMatrix"][2]["matrixDetails"]:
            for frequency_slice in receptor["receptorMatrix"]:
                for i in frequency_slice["matrix"]:
                    try:
                        assert create_vcc_proxies[receptor_to_vcc[receptor["receptor"]]-1].jonesMatrix[frequency_slice["fsid"]-1][i] == i
                    except AssertionError:
                        logging.error("AssertionError; incorrect Jones matrix entry: epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format(jones_matrix["jonesMatrix"][2]["epoch"], receptor_to_vcc[receptor["receptor"]], i, frequency_slice["fsid"]-1, create_vcc_proxies[receptor_to_vcc[receptor["receptor"]]-1].jonesMatrix[frequency_slice["fsid"]-1]))
                        return AssertionError
                    except Exception:
                        pass
        
        time.sleep(10)
        for receptor in jones_matrix["jonesMatrix"][0]["matrixDetails"]:
            for frequency_slice in receptor["receptorMatrix"]:
                for i in frequency_slice["matrix"]:
                    try:
                        assert create_vcc_proxies[receptor_to_vcc[receptor["receptor"]]-1].jonesMatrix[frequency_slice["fsid"]-1][i] == i
                    except AssertionError:
                        logging.error("AssertionError; incorrect Jones matrix entry: epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format(jones_matrix["jonesMatrix"][0]["epoch"], receptor_to_vcc[receptor["receptor"]], i, frequency_slice["fsid"]-1, create_vcc_proxies[receptor_to_vcc[receptor["receptor"]]-1].jonesMatrix[frequency_slice["fsid"]-1]))
                        return AssertionError
                    except Exception:
                        pass

        create_subarray_1_proxy.EndScan()
        time.sleep(1)

        # Clean Up
        create_subarray_1_proxy.GoToIdle()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()     
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF

    def test_Scan(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test the Scan command
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(80000)  # since the command takes a while

        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)
        if create_subarray_1_proxy.state() != DevState.ON:
            create_subarray_1_proxy.On()
        create_subarray_1_proxy.set_timeout_millis(60000)
        time.sleep(3)
        assert create_subarray_1_proxy.obsState.value == ObsState.EMPTY.value

        
        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check initial states
        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.READY.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.READY.value
        assert create_fsp_1_subarray_1_proxy.obsState.value == ObsState.READY.value
        assert create_fsp_3_subarray_1_proxy.obsState.value == ObsState.READY.value

        # send the Scan command
        create_subarray_1_proxy.Scan(1)
        time.sleep(1)

        # check scanID on VCC and FSP
        assert create_fsp_1_subarray_1_proxy.scanID == 1
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].scanID ==1

        # check states
        assert create_subarray_1_proxy.obsState.value == ObsState.SCANNING
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.SCANNING.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.SCANNING.value
        assert create_fsp_1_subarray_1_proxy.obsState.value == ObsState.SCANNING.value
        assert create_fsp_3_subarray_1_proxy.obsState.value == ObsState.SCANNING.value
        create_subarray_1_proxy.EndScan()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState.value == ObsState.READY

        # Clean Up
        create_subarray_1_proxy.GoToIdle()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()     
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF

    def test_Abort_Reset(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_sw_1_proxy,
            create_sw_2_proxy,
            create_vcc_proxies,
            create_vcc_band_proxies,
            create_vcc_tdc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_function_mode_proxy,
            create_fsp_2_function_mode_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)  # since the command takes a while
        # create_subarray_1_proxy.Init()
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)
        # # turn on Subarray
        # create_subarray_1_proxy.On()
        # time.sleep(1)

        ############################# abort from READY ###########################
        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(5)
        assert create_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.READY
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.READY.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.READY.value
        # abort
        create_subarray_1_proxy.Abort()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.ABORTED
        # ObsReset
        create_subarray_1_proxy.ObsReset()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.IDLE.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.IDLE.value


        ############################# abort from SCANNING ###########################
        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(5)
        # scan
        create_subarray_1_proxy.Scan(2)
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.SCANNING
        assert create_subarray_1_proxy.scanID == 2
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.SCANNING
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.SCANNING
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.SCANNING
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.SCANNING
        # abort
        create_subarray_1_proxy.Abort()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.ABORTED
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.READY
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.READY.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.READY.value
        # ObsReset
        create_subarray_1_proxy.ObsReset()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_subarray_1_proxy.scanID == 0
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.IDLE.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.IDLE.value

        # Clean Up
        create_subarray_1_proxy.RemoveAllReceptors()     
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
        time.sleep(1)
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF


    def test_Abort_Restart(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_sw_1_proxy,
            create_sw_2_proxy,
            create_vcc_proxies,
            create_vcc_band_proxies,
            create_vcc_tdc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_function_mode_proxy,
            create_fsp_2_function_mode_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)  # since the command takes a while
        # create_subarray_1_proxy.Init()
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(5)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)
        # # turn on Subarray
        # create_subarray_1_proxy.On()
        # time.sleep(1)

        ############################# abort from IDLE ###########################
        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        # abort
        create_subarray_1_proxy.Abort()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.ABORTED
        # Restart: receptors should be empty
        create_subarray_1_proxy.Restart()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY
        assert len(create_subarray_1_proxy.receptors) == 0
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.IDLE.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.IDLE.value




        ############################# abort from READY ###########################
        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(5)
        assert create_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.READY
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.READY
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.READY
        # abort
        create_subarray_1_proxy.Abort()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.ABORTED
        # ObsReset
        create_subarray_1_proxy.Restart()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY
        assert len(create_subarray_1_proxy.receptors) == 0
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.IDLE.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.IDLE.value


        ############################# abort from SCANNING ###########################
        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(5)
        # scan
        create_subarray_1_proxy.Scan(2)
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.SCANNING
        assert create_subarray_1_proxy.scanID == 2
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.SCANNING
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.SCANNING
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.SCANNING
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.SCANNING
        # abort
        create_subarray_1_proxy.Abort()
        time.sleep(1)
        assert create_subarray_1_proxy.obsState == ObsState.ABORTED
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.READY
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.READY
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.READY
        # ObsReset
        create_subarray_1_proxy.Restart()
        time.sleep(1)
        assert len(create_subarray_1_proxy.receptors) == 0
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_fsp_3_subarray_1_proxy.obsState == ObsState.IDLE
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].obsState.value == ObsState.IDLE.value
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].obsState.value == ObsState.IDLE.value


        # Clean Up
        assert create_subarray_1_proxy.obsState == ObsState.EMPTY  
        time.sleep(1)
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF
'''    
    def test_ConfigureScan_onlyPss_basic(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_sw_1_proxy,
            create_sw_2_proxy,
            create_vcc_proxies,
            create_vcc_band_proxies,
            create_vcc_tdc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_function_mode_proxy,
            create_fsp_2_function_mode_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()
        create_subarray_1_proxy.set_timeout_millis(60000)  # since the command takes a while
        create_subarray_1_proxy.Init()
        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(60)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        # check initial value of attributes of CBF subarray
        # assert create_subarray_1_proxy.receptors == ()
        # assert create_subarray_1_proxy.configID == 0
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState.value == ObsState.IDLE.value
        # assert create_tm_telstate_proxy.visDestinationAddress == "{}"
        assert create_tm_telstate_proxy.receivedOutputLinks == False

        # add receptors
        create_subarray_1_proxy.RemoveAllReceptors()
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_onlyPss_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check configured attributes of CBF subarray    # def test_ConfigureScan_basic(
    #         self,
    #         create_cbf_master_proxy,
    #         create_subarray_1_proxy,
    #         create_sw_1_proxy,
    #         create_sw_2_proxy,
    #         create_vcc_proxies,
    #         create_vcc_band_proxies,
    #         create_vcc_tdc_proxies,
    #         create_fsp_1_proxy,
    #         create_fsp_2_proxy,
    #         create_fsp_1_function_mode_proxy,
    #         create_fsp_2_function_mode_proxy,
    #         create_fsp_1_subarray_1_proxy,
    #         create_fsp_2_subarray_1_proxy,
    #         create_fsp_3_subarray_1_proxy,
    #         create_tm_telstate_proxy
    # ):
    #     """
    #     Test a minimal successful configuration
    #     """
    #     for proxy in create_vcc_proxies:
    #         proxy.Init()
    #     create_fsp_1_subarray_1_proxy.Init()
    #     create_fsp_2_subarray_1_proxy.Init()
    #     create_fsp_3_subarray_1_proxy.Init()
    #     create_fsp_1_proxy.Init()
    #     create_fsp_2_proxy.Init()
    #     create_subarray_1_proxy.set_timeout_millis(60000)  # since the command takes a while
    #     create_subarray_1_proxy.Init()
    #     time.sleep(3)
    #     create_cbf_master_proxy.set_timeout_millis(60000)
    #     create_cbf_master_proxy.Init()
    #     time.sleep(60)  # takes pretty long for CBF Master to initialize
    #     create_tm_telstate_proxy.Init()
    #     time.sleep(1)

    #     receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
    #                            create_cbf_master_proxy.receptorToVcc)

        
    #     create_cbf_master_proxy.On()
    #     time.sleep(60)

    #     # turn on Subarray
    #     assert create_subarray_1_proxy.state()==DevState.OFF
    #     create_subarray_1_proxy.On()
    #     time.sleep(10)
    #     # check initial value of attributes of CBF subarray
    #     assert len(create_subarray_1_proxy.receptors) == 0
    #     assert create_subarray_1_proxy.configID == 0
    #     assert create_subarray_1_proxy.frequencyBand == 0
    #     assert create_subarray_1_proxy.State() == DevState.ON
    #     assert create_subarray_1_proxy.ObsState == ObsState.EMPTY
    #     # assert create_tm_telstate_proxy.visDestinationAddress == "{}"
    #     assert create_tm_telstate_proxy.receivedOutputLinks == False

    #     # add receptors
    #     create_subarray_1_proxy.RemoveAllReceptors()
    #     create_subarray_1_proxy.AddReceptors([1, 3, 4])
    #     time.sleep(1)
    #     assert create_subarray_1_proxy.receptors[0] == 1
    #     assert create_subarray_1_proxy.receptors[1] == 3
    #     assert create_subarray_1_proxy.receptors[2] == 4

    #     # configure scan
    #     f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
    #     create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
    #     f.close()
    #     time.sleep(15)

    #     # check configured attributes of CBF subarray
    #     assert create_subarray_1_proxy.configID == "band:5a, fsp1, 744 channels average factor 8"
    #     assert create_subarray_1_proxy.frequencyBand == 4 # means 5a?
    #     assert create_subarray_1_proxy.obsState.value == ObsState.READY.value

    #     # check frequency band of VCCs, including states of frequency band capabilities
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 4
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 4
    #     assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[4] - 1]] == [
    #         DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
    #     assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[1] - 1]] == [
    #         DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

    #     # check the rest of the configured attributes of VCCs
    #     # first for VCC belonging to receptor 10...
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[0] == 5.85
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[1] == 7.25
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream1 == 0
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream2 == 0
    #     assert create_vcc_proxies[receptor_to_vcc[4] - 1].rfiFlaggingMask == "{}"
    #     # then for VCC belonging to receptor 1...
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[0] == 5.85
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[1] == 7.25
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream1 == 0
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream2 == 0
    #     assert create_vcc_proxies[receptor_to_vcc[1] - 1].rfiFlaggingMask == "{}"

    #     # check configured attributes of search windows
    #     # first for search window 1...
    #     assert create_sw_1_proxy.State() == DevState.ON
    #     assert create_sw_1_proxy.searchWindowTuning == 6000000000
    #     assert create_sw_1_proxy.tdcEnable == True
    #     assert create_sw_1_proxy.tdcNumBits == 8
    #     assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 5
    #     assert create_sw_1_proxy.tdcPeriodAfterEpoch == 25
    #     assert "".join(create_sw_1_proxy.tdcDestinationAddress.split()) in [
    #         "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
    #         "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
    #         "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
    #         "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
    #     ]
    #     # then for search window 2...
    #     assert create_sw_2_proxy.State() == DevState.DISABLE
    #     assert create_sw_2_proxy.searchWindowTuning == 7000000000
    #     assert create_sw_2_proxy.tdcEnable == False

    #     # check configured attributes of VCC search windows
    #     # first for search window 1 of VCC belonging to receptor 10...
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].State() == DevState.ON
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcEnable == True
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcNumBits == 8
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
    #         "foo", "bar", "8080"
    #     )
    #     # then for search window 1 of VCC belonging to receptor 1...
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].State() == DevState.ON
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcEnable == True
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcNumBits == 8
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
    #         "fizz", "buzz", "80"
    #     )
    #     # then for search window 2 of VCC belonging to receptor 10...
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].State() == DevState.DISABLE
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].searchWindowTuning == 7000000000
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].tdcEnable == False
    #     # and lastly for search window 2 of VCC belonging to receptor 1...
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].State() == DevState.DISABLE
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
    #     assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].tdcEnable == False

    #     # check configured attributes of FSPs, including states of function mode capabilities
    #     assert create_fsp_1_proxy.functionMode == 1
    #     assert 1 in create_fsp_1_proxy.subarrayMembership
    #     # assert 1 in create_fsp_2_proxy.subarrayMembership
    #     assert [proxy.State() for proxy in create_fsp_1_function_mode_proxy] == [
    #         DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
    #     ]
    #     # assert [proxy.State() for proxy in create_fsp_2_function_mode_proxy] == [
    #     #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
    #     # ]

    #     # check configured attributes of FSP subarrays
    #     # first for FSP 1...
    #     assert create_fsp_1_subarray_1_proxy.obsState == ObsState.EMPTY
    #     assert create_fsp_1_subarray_1_proxy.receptors == 4
    #     assert create_fsp_1_subarray_1_proxy.frequencyBand == 4
    #     assert create_fsp_1_subarray_1_proxy.band5Tuning[0] == 5.85
    #     assert create_fsp_1_subarray_1_proxy.band5Tuning[1] == 7.25
    #     assert create_fsp_1_subarray_1_proxy.frequencyBandOffsetStream1 == 0
    #     assert create_fsp_1_subarray_1_proxy.frequencyBandOffsetStream2 == 0
    #     assert create_fsp_1_subarray_1_proxy.frequencySliceID == 1
    #     assert create_fsp_1_subarray_1_proxy.corrBandwidth == 1
    #     assert create_fsp_1_subarray_1_proxy.zoomWindowTuning == 4700000
    #     assert create_fsp_1_subarray_1_proxy.integrationTime == 140
    #     assert create_fsp_1_subarray_1_proxy.fspChannelOffset == 14880
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[0][0] == 0
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[0][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[1][0] == 744
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[1][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[2][0] == 1488
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[2][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[3][0] == 2232
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[3][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[4][0] == 2976
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[4][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[5][0] == 3720
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[5][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[6][0] == 4464
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[6][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[7][0] == 5208
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[7][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[8][0] == 5952
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[8][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[9][0] == 6696
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[9][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[10][0] == 7440
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[10][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[11][0] == 8184
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[11][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[12][0] == 8928
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[12][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[13][0] == 9672
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[13][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[14][0] == 10416
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[14][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[15][0] == 11160
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[15][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[16][0] == 11904
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[16][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[17][0] == 12648
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[17][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[18][0] == 13392
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[18][1] == 8
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[19][0] == 14136
    #     # assert create_fsp_1_subarray_1_proxy.channelAveragingMap[19][1] == 8
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[0][0] == 0
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[0][1] == 4
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[1][0] == 744
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[1][1] == 8        
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[2][0] == 1488
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[2][1] == 12
    #     assert create_fsp_1_subarray_1_proxy.outputLinkMap[3][0] == 2232
    #     assert create_fsp_1_subarray_1_proroxy.receptors[2] == 4
    #     # assert create_fsp_2_subarray_1_proxy.frequencyBand == 4
    #     # assert create_fsp_2_subarray_1_proxy.band5Tuning[0] == 5.85
    #     # assert create_fsp_2_subarray_1_proxy.band5Tuning[1] == 7.25
    #     # assert create_fsp_2_subarray_1_proxy.frequencyBandOffsetStream1 == 0
    #     # assert create_fsp_2_subarray_1_proxy.frequencyBandOffsetStream2 == 0
    #     # assert create_fsp_2_subarray_1_proxy.frequencySliceID == 20
    #     # assert create_fsp_2_subarray_1_proxy.corrBandwidth == 0
    #     # assert create_fsp_2_subarray_1_proxy.integrationTime == 1400
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[0][0] == 1
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[0][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[1][0] == 745
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[1][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[2][0] == 1489
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[2][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[3][0] == 2233
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[3][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[4][0] == 2977
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[4][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[5][0] == 3721
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[5][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[6][0] == 4465
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[6][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[7][0] == 5209
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[7][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[8][0] == 5953
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[8][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[9][0] == 6697
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[9][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[10][0] == 7441
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[10][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[11][0] == 8185
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[11][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[12][0] == 8929
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[12][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[13][0] == 9673
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[13][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[14][0] == 10417
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[14][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[15][0] == 11161
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[15][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[16][0] == 11905
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[16][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[17][0] == 12649
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[17][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[18][0] == 13393
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[18][1] == 0
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[19][0] == 14137
    #     # assert create_fsp_2_subarray_1_proxy.channelAveragingMap[19][1] == 0

    #     # then for FSP 3...
    #     assert create_fsp_3_subarray_1_proxy.receptors[0] == 3
    #     assert create_fsp_3_subarray_1_proxy.receptors[1] == 1
    #     assert create_fsp_3_subarray_1_proxy.searchWindowID == 2
    #     assert create_fsp_3_subarray_1_proxy.searchBeamID[0] == 300
    #     assert create_fsp_3_subarray_1_proxy.searchBeamID[1] == 400


    #     searchBeam = create_fsp_3_subarray_1_proxy.searchBeams
    #     searchBeam300 = json.loads(searchBeam[0])
    #     searchBeam400 = json.loads(searchBeam[1])
    #     assert searchBeam300["searchBeamID"] == 300
    #     assert searchBeam300["receptors"][0] == 3
    #     assert searchBeam300["outputEnable"] == True
    #     assert searchBeam300["averagingInterval"] == 4
    #     assert searchBeam300["searchBeamDestinationAddress"] == "10.1.1.1"

    #     assert searchBeam400["searchBeamID"] == 400
    #     assert searchBeam400["receptors"][0] == 1
    #     assert searchBeam400["outputEnable"] == True
    #     assert searchBeam400["averagingInterval"] == 2
    #     assert searchBeam400["searchBeamDestinationAddress"] == "10.1.2.1"

    #     create_subarray_1_proxy.GoToIdle()
    #     time.sleep(3)
    #     assert create_subarray_1_proxy.obsState == ObsState.IDLE
    #     create_subarray_1_proxy.RemoveAllReceptors()
    #     time.sleep(3)
    #     assert create_subarray_1_proxy.state() == tango.DevState.OFFequency band capabilities
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 4
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 4
        assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[4] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
        assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[1] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

        # check the rest of the configured attributes of VCCs
        # first for VCC belonging to receptor 10...
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[0] == 5.85
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].band5Tuning[1] == 7.25
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream1 == 0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBandOffsetStream2 == 0
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].rfiFlaggingMask == "{}"
        # then for VCC belonging to receptor 1...
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[0] == 5.85
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning[1] == 7.25
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream1 == 0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream2 == 0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].rfiFlaggingMask == "{}"

        # check configured attributes of search windows
        # first for search window 1...
        assert create_sw_1_proxy.State() == DevState.ON
        assert create_sw_1_proxy.searchWindowTuning == 6000000000
        assert create_sw_1_proxy.tdcEnable == True
        assert create_sw_1_proxy.tdcNumBits == 8
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 5
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 25
        assert "".join(create_sw_1_proxy.tdcDestinationAddress.split()) in [
            "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
        ]
        # then for search window 2...
        assert create_sw_2_proxy.State() == DevState.DISABLE
        assert create_sw_2_proxy.searchWindowTuning == 7000000000
        assert create_sw_2_proxy.tdcEnable == False

        # check configured attributes of VCC search windows
        # first for search window 1 of VCC belonging to receptor 10...
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].State() == DevState.ON
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcEnable == True
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcNumBits == 8
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
            "foo", "bar", "8080"
        )
        # then for search window 1 of VCC belonging to receptor 1...
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].State() == DevState.ON
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcEnable == True
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcNumBits == 8
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
            "fizz", "buzz", "80"
        )
        # then for search window 2 of VCC belonging to receptor 10...
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].State() == DevState.DISABLE
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].searchWindowTuning == 7000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[4] - 1][1].tdcEnable == False
        # and lastly for search window 2 of VCC belonging to receptor 1...
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].State() == DevState.DISABLE
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].tdcEnable == False

        assert create_fsp_3_subarray_1_proxy.receptors[0] == 3
        assert create_fsp_3_subarray_1_proxy.receptors[1] == 1
        assert create_fsp_3_subarray_1_proxy.searchWindowID == 2
        assert create_fsp_3_subarray_1_proxy.searchBeamID[0] == 300
        assert create_fsp_3_subarray_1_proxy.searchBeamID[1] == 400


        searchBeam = create_fsp_3_subarray_1_proxy.searchBeams
        searchBeam300 = json.loads(searchBeam[0])
        searchBeam400 = json.loads(searchBeam[1])
        assert searchBeam300["searchBeamID"] == 300
        assert searchBeam300["receptors"][0] == 3
        assert searchBeam300["outputEnable"] == True
        assert searchBeam300["averagingInterval"] == 4
        assert searchBeam300["searchBeamDestinationAddress"] == "10.1.1.1"

        assert searchBeam400["searchBeamID"] == 400
        assert searchBeam400["receptors"][0] == 1
        assert searchBeam400["outputEnable"] == True
        assert searchBeam400["averagingInterval"] == 2
        assert searchBeam400["searchBeamDestinationAddress"] == "10.1.2.1"

        create_subarray_1_proxy.GoToIdle()
        time.sleep(3)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()
        time.sleep(3)
        assert create_subarray_1_proxy.state() == tango.DevState.OFF







    def test_band1(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_sw_1_proxy,
            create_sw_2_proxy,
            create_vcc_proxies,
            create_vcc_band_proxies,
            create_vcc_tdc_proxies,
            create_fsp_1_proxy,
            create_fsp_2_proxy,
            create_fsp_1_function_mode_proxy,
            create_fsp_2_function_mode_proxy,
            create_fsp_1_subarray_1_proxy,
            create_fsp_2_subarray_1_proxy,
            create_fsp_3_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test a minimal successful configuration
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        create_fsp_1_subarray_1_proxy.Init()
        create_fsp_2_subarray_1_proxy.Init()
        create_fsp_3_subarray_1_proxy.Init()
        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()

        time.sleep(3)
        create_cbf_master_proxy.set_timeout_millis(60000)
        create_cbf_master_proxy.Init()
        time.sleep(60)  # takes pretty long for CBF Master to initialize
        create_tm_telstate_proxy.Init()
        time.sleep(1)

        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_cbf_master_proxy.On()
        time.sleep(3)

        # check initial value of attributes of CBF subarray
        assert len(create_subarray_1_proxy.receptors) == 0
        assert create_subarray_1_proxy.configID == ''
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState.value == ObsState.IDLE.value
        # assert create_tm_telstate_proxy.visDestinationAddress == "{}"
        assert create_tm_telstate_proxy.receivedOutputLinks == False

        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 3, 4])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors[0] == 1
        assert create_subarray_1_proxy.receptors[1] == 3
        assert create_subarray_1_proxy.receptors[2] == 4

        # configure scan
        f = open(file_path + "/test_json/data_model_confluence.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(15)

        # check configured attributes of CBF subarray
        assert create_subarray_1_proxy.configID == "sbi-mvp01-20200325-00001-science_A"
        assert create_subarray_1_proxy.frequencyBand == 0 # means 1
        assert create_subarray_1_proxy.obsState.value == ObsState.READY.value

        # check frequency band of VCCs, including states of frequency band capabilities
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].frequencyBand == 0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 0


        # check the rest of the configured attributes of VCCs
        # first for VCC belonging to receptor 10...
        assert create_vcc_proxies[receptor_to_vcc[4] - 1].subarrayMembership == 1

        # then for VCC belonging to receptor 1...
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1



        # check configured attributes of FSPs, including states of function mode capabilities
        assert create_fsp_1_proxy.functionMode == 1
        assert 1 in create_fsp_1_proxy.subarrayMembership
        # assert 1 in create_fsp_2_proxy.subarrayMembership
        assert [proxy.State() for proxy in create_fsp_1_function_mode_proxy] == [
            DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        ]
        # assert [proxy.State() for proxy in create_fsp_2_function_mode_proxy] == [
        #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        # ]

        # check configured attributes of FSP subarrays
        # first for FSP 1...
        assert create_fsp_1_subarray_1_proxy.obsState == ObsState.READY
        assert create_fsp_1_subarray_1_proxy.frequencyBand == 0
        assert create_fsp_1_subarray_1_proxy.frequencySliceID == 1
        assert create_fsp_1_subarray_1_proxy.corrBandwidth == 0
        assert create_fsp_1_subarray_1_proxy.integrationTime == 1400

        assert create_fsp_1_subarray_1_proxy.outputLinkMap[0][0] == 1
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[0][1] == 0
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[1][0] == 201
        assert create_fsp_1_subarray_1_proxy.outputLinkMap[1][1] == 1



        create_subarray_1_proxy.GoToIdle()
        time.sleep(3)
        assert create_subarray_1_proxy.obsState == ObsState.IDLE
        create_subarray_1_proxy.RemoveAllReceptors()
        time.sleep(1)
        create_subarray_1_proxy.Off()
        assert create_subarray_1_proxy.state() == tango.DevState.OFF
'''


