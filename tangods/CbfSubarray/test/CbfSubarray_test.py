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

@pytest.mark.usefixtures("proxies")

class TestCbfSubarray:
    
    def test_AddRemoveReceptors_valid(self, proxies):
        """
        Test valid AddReceptors and RemoveReceptors commands
        """
        try:
            proxies.clean_proxies()
            if proxies.master.State() == DevState.OFF:
                proxies.master.Init()
                proxies.wait_timeout_dev([proxies.master], DevState.STANDBY, 3, 0.05)
                proxies.master.On()
                proxies.wait_timeout_dev([proxies.master], DevState.ON, 3, 0.05)
            proxies.clean_proxies()

            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(4)])

            # add some receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert [proxies.subarray[1].receptors[i] for i in range(3)] == [1, 3, 4]
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in [1, 3, 4]])
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
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 0.05)
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.vcc[proxies.receptor_to_vcc[3]].subarrayMembership == 0
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.05)

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
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(4)])

            # add some receptors to subarray 1
            proxies.subarray[1].AddReceptors([1, 3])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
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
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 0.05)
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.05)

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
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(4)])

            # add some receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in [1, 3, 4]])
            assert proxies.subarray[1].obsState == ObsState.IDLE

            # remove all receptors
            proxies.subarray[1].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 0.05)
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 0 for i in [1, 3, 4]])
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.05)
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_ConfigureScan_basic(self, proxies):
        """
        Test a minimal successful configuration
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            # check initial value of attributes of CBF subarray
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.subarray[1].configID == ''
            assert proxies.subarray[1].frequencyBand == 0
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 15, 0.05)

            # check configured attributes of CBF subarray
            assert proxies.subarray[1].configID == "band:5a, fsp1, 744 channels average factor 8"
            assert proxies.subarray[1].frequencyBand == 4 # means 5a
            assert proxies.subarray[1].obsState == ObsState.READY

            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(4)], ObsState.READY, 1, 0.05)

            # check frequency band of VCCs, including states of frequency band capabilities
            assert proxies.vcc[proxies.receptor_to_vcc[4]].frequencyBand == 4
            assert proxies.vcc[proxies.receptor_to_vcc[1]].frequencyBand == 4
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
            assert proxies.sw[1].State() == DevState.ON
            assert proxies.sw[1].searchWindowTuning == 6000000000
            assert proxies.sw[1].tdcEnable == True
            assert proxies.sw[1].tdcNumBits == 8
            assert proxies.sw[1].tdcPeriodBeforeEpoch == 5
            assert proxies.sw[1].tdcPeriodAfterEpoch == 25
            assert "".join(proxies.sw[1].tdcDestinationAddress.split()) in [
                "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
                "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
                "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
                "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            ]
            # then for search window 2...
            assert proxies.sw[2].State() == DevState.DISABLE
            assert proxies.sw[2].searchWindowTuning == 7000000000
            assert proxies.sw[2].tdcEnable == False

            # check configured attributes of VCC search windows
            # first for search window 1 of VCC belonging to receptor 10...
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].State() == DevState.ON
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].searchWindowTuning == 6000000000
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcEnable == True
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcNumBits == 8
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcPeriodBeforeEpoch == 5
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcPeriodAfterEpoch == 25
            assert proxies.vccTdc[proxies.receptor_to_vcc[4] - 1][0].tdcDestinationAddress == (
                "foo", "bar", "8080"
            )
            # then for search window 1 of VCC belonging to receptor 1...
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].State() == DevState.ON
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcEnable == True
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcNumBits == 8
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
            assert proxies.vccTdc[proxies.receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
                "fizz", "buzz", "80"
            )
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
            # assert [proxy.State() for proxy in fsp_2_function_mode_proxy] == [
            #     DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
            # ]

            # check configured attributes of FSP subarrays
            # first for FSP 1...
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
            assert proxies.fspSubarray[1].integrationTime == 140
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
                str({"outputHost": [[0, "192.168.0.1"], [8184, "192.168.0.2"]], "outputMac": [[0, "06-00-00-00-00-01"]], "outputPort": [[0, 9000, 1], [8184, 9000, 1]]}).replace('"',"'")
            
            # Clean Up
            proxies.clean_proxies()
        
        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e

    def test_EndScan(self, proxies):
        """
        Test the EndScan command
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])
            assert proxies.subarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE

            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 15, 0.05)

            # check configured attributes of CBF subarray
            assert proxies.subarray[1].configID == "band:5a, fsp1, 744 channels average factor 8"
            assert proxies.subarray[1].frequencyBand == 4
            assert proxies.subarray[1].obsState == ObsState.READY

            # send the Scan command
            proxies.subarray[1].Scan(1)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 0.05)

            # check initial states
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[1].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[3].obsState == ObsState.SCANNING

            # send the EndScan command
            proxies.subarray[1].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 0.05)

            # check states
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY

            # check scanID to zero
            assert proxies.fspSubarray[1].scanID == 0

            proxies.clean_proxies()

        except AssertionError as ae:
            proxies.clean_proxies()
            raise ae
        except Exception as e:
            proxies.clean_proxies()
            raise e
    
    def test_ConfigureScan_delayModel(self, proxies):
        """
        Test the reception of delay models
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)

            assert proxies.subarray[1].obsState == ObsState.READY

            # create a delay model
            f = open(file_path + "/test_json/delaymodel.json")
            delay_model = json.loads(f.read().replace("\n", ""))
            delay_model["delayModel"][0]["epoch"] = str(int(time.time()) + 20)
            delay_model["delayModel"][1]["epoch"] = "0"
            delay_model["delayModel"][2]["epoch"] = str(int(time.time()) + 10)

            # update delay model
            proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)
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
            proxies.subarray[1].Scan(1)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 0.05)
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
            assert proxies.vcc[proxies.receptor_to_vcc[1]].delayModel[1][2] == 2.9    #     assert fsp_1_proxies.subarray[1].obsState == ObsState.IDLE
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
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 0.05)

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
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)

            assert proxies.subarray[1].obsState == ObsState.READY

            #create a Jones matrix
            f = open(file_path + "/test_json/jonesmatrix.json")
            jones_matrix = json.loads(f.read().replace("\n", ""))
            jones_matrix["jonesMatrix"][0]["epoch"] = str(int(time.time()) + 20)
            jones_matrix["jonesMatrix"][1]["epoch"] = "0"
            jones_matrix["jonesMatrix"][2]["epoch"] = str(int(time.time()) + 10)

            # update Jones Matrix
            proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

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

            proxies.subarray[1].Scan(1)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 0.05)
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
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 0.05)

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
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])

            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)

            # check initial states
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY

            # send the Scan command
            proxies.subarray[1].Scan(1)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 0.05)

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
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 1, 0.05)
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
        Test a minimal successful configuration
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            
            ############################# abort from READY ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            # ObsReset
            proxies.subarray[1].ObsReset()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.IDLE
            assert all([proxies.subarray[1].receptors[i] == j for i, j in zip(range(3), [1, 3, 4])])
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE


            ############################# abort from SCANNING ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)
            # scan
            proxies.subarray[1].Scan(2)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.subarray[1].scanID == 2
            assert proxies.fspSubarray[1].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[3].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # ObsReset
            proxies.subarray[1].ObsReset()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
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
        Test a minimal successful configuration
        """
        try:
            # turn on Subarray
            if proxies.subarray[1].State() != DevState.ON:
                proxies.subarray[1].On()
                proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.05)
                for proxy in [proxies.vcc[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
                for proxy in [proxies.fsp[i + 1] for i in range(4)]:
                    if proxy.State() == DevState.OFF:
                        proxy.On()
                        proxies.wait_timeout_dev([proxy], DevState.ON, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            
            ############################# abort from IDLE ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.IDLE
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            # Restart: receptors should be empty
            proxies.subarray[1].Restart()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE




            ############################# abort from READY ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)
            assert proxies.subarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            # ObsReset
            proxies.subarray[1].Restart()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.EMPTY, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.EMPTY
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.fspSubarray[1].obsState == ObsState.IDLE
            assert proxies.fspSubarray[3].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE


            ############################# abort from SCANNING ###########################
            # add receptors
            proxies.subarray[1].AddReceptors([1, 3, 4])
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
            # configure scan
            f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
            proxies.subarray[1].ConfigureScan(f.read().replace("\n", ""))
            f.close()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 30, 0.05)
            # scan
            proxies.subarray[1].Scan(2)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.subarray[1].scanID == 2
            assert proxies.fspSubarray[1].obsState == ObsState.SCANNING
            assert proxies.fspSubarray[3].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            # abort
            proxies.subarray[1].Abort()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.ABORTED, 1, 0.05)
            assert proxies.subarray[1].obsState == ObsState.ABORTED
            assert proxies.fspSubarray[1].obsState == ObsState.READY
            assert proxies.fspSubarray[3].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.READY
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.READY
            # ObsReset
            proxies.subarray[1].Restart()
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 0.05)
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


