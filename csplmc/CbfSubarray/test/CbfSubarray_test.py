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
from global_enum import HealthState, AdminMode, ObsState

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
    """
    @classmethod
    def mocking(cls):
    """#Mock external libraries.
    """
        # Example : Mock numpy
        # cls.numpy = CspMaster.numpy = MagicMock()
    """

    def test_AddRemoveReceptors_valid(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies
    ):
        """
        Test valid AddReceptors and RemoveReceptors commands
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        assert create_subarray_1_proxy.State() == DevState.OFF

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        assert create_subarray_1_proxy.State() == DevState.ON

        # add more receptors...
        create_subarray_1_proxy.AddReceptors([17, 197])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (1, 10, 197, 17)
        assert create_vcc_proxies[receptor_to_vcc[17] - 1].subarrayMembership == 1

        # remove some receptors
        create_subarray_1_proxy.RemoveReceptors([17, 1, 197])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (10,)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 17, 197]])
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].subarrayMembership == 1

        # remove remaining receptors
        create_subarray_1_proxy.RemoveReceptors([10])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == ()
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].subarrayMembership == 0
        assert create_subarray_1_proxy.State() == DevState.OFF

    def test_AddRemoveReceptors_invalid(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_subarray_2_proxy,
            create_vcc_proxies
    ):
        """
        Test invalid AddReceptors and RemoveReceptors commands:
            - when a receptor to be added is already in use by a different subarray
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()
        create_subarray_2_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_2_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        assert create_subarray_1_proxy.State() == DevState.OFF
        assert create_subarray_2_proxy.State() == DevState.OFF

        # add some receptors to subarray 1
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        assert create_subarray_1_proxy.State() == DevState.ON

        # try adding some receptors (including an invalid one) to subarray 2
        with pytest.raises(tango.DevFailed) as df:
            create_subarray_2_proxy.AddReceptors([17, 100, 197])
        time.sleep(1)
        assert "already in use" in str(df.value.args[0].desc)
        assert create_subarray_2_proxy.receptors == (17, 100)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 2 for i in [17, 100]])
        assert create_subarray_2_proxy.State() == DevState.ON

        # try adding an invalid receptor ID to subarray 2
        with pytest.raises(tango.DevFailed) as df:
            create_subarray_2_proxy.AddReceptors([200])
        time.sleep(1)
        assert "Invalid receptor ID" in str(df.value.args[0].desc)

        # try removing a receptor not assigned to subarray 2
        # doing this doesn't actually throw an error
        create_subarray_2_proxy.RemoveReceptors([5])
        assert create_subarray_2_proxy.receptors == (17, 100)

        # remove all receptors
        create_subarray_1_proxy.RemoveReceptors([1, 10, 197])
        create_subarray_2_proxy.RemoveReceptors([17, 100])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_2_proxy.receptors == ()
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 10, 17, 100, 197]])
        assert create_subarray_1_proxy.State() == DevState.OFF
        assert create_subarray_2_proxy.State() == DevState.OFF

    def test_RemoveAllReceptors(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies
    ):
        """
        Test RemoveAllReceptors command
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        assert create_subarray_1_proxy.State() == DevState.OFF

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        assert create_subarray_1_proxy.State() == DevState.ON

        # remove all receptors
        create_subarray_1_proxy.RemoveAllReceptors()
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == ()
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 10, 197]])
        assert create_subarray_1_proxy.State() == DevState.OFF

    def test_AddReceptors_subscriptions(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_vcc_proxies
    ):
        """
        Test successful subscriptions to VCC state and healthState for AddReceptors command
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)
        create_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_1_proxy.vccState == None
        assert create_subarray_1_proxy.vccHealthState == None

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(3)
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        # default state is OFF
        assert create_subarray_1_proxy.vccState == (DevState.OFF, DevState.OFF, DevState.OFF)
        # default health state is 3 (UNKNOWN)
        assert create_subarray_1_proxy.vccHealthState == (3, 3, 3)

        # change states
        create_vcc_proxies[receptor_to_vcc[1] - 1].SetState(DevState.ON)
        create_vcc_proxies[receptor_to_vcc[10] - 1].SetState(DevState.DISABLE)
        create_vcc_proxies[receptor_to_vcc[197] - 1].SetState(DevState.STANDBY)
        time.sleep(4)
        assert sorted(create_subarray_1_proxy.vccState) == [DevState.ON, DevState.STANDBY, DevState.DISABLE]

        # change health states
        create_vcc_proxies[receptor_to_vcc[1] - 1].SetHealthState(1)
        create_vcc_proxies[receptor_to_vcc[10] - 1].SetHealthState(0)
        create_vcc_proxies[receptor_to_vcc[197] - 1].SetHealthState(2)
        time.sleep(4)
        assert sorted(create_subarray_1_proxy.vccHealthState) == [0, 1, 2]

        # remove a receptor
        create_subarray_1_proxy.RemoveReceptors([10])
        time.sleep(3)
        assert create_subarray_1_proxy.receptors == (1, 197)
        assert sorted(create_subarray_1_proxy.vccState) == [DevState.ON, DevState.STANDBY]
        assert sorted(create_subarray_1_proxy.vccHealthState) == [1, 2]

        # remove all receptors
        create_subarray_1_proxy.RemoveAllReceptors()
        time.sleep(3)
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_1_proxy.vccState == None
        assert create_subarray_1_proxy.vccHealthState == None

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
            create_fsp_2_subarray_1_proxy
    ):
        """
        Test a minimal successful configuration
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()

        # We actually don't want to initialize these...
        # CBF Master (for the moment at least), creates the map of receptors to VCCs and assigns
        # receptor IDs to VCCs accordingly. Initializing them sets them all back to 0.
        # I wasted a few hours trying to figure out why this test wasn't working -.-
        """
        for proxy in create_vcc_proxies:
            proxy.Init()
        """

        create_fsp_1_proxy.Init()
        create_fsp_2_proxy.Init()

        # don't bother initializing the sub-capability proxies - it takes way too long and they
        # should be configured by ConfigureScan anyway

        time.sleep(3)

        # check initial value of attributes of CBF subarray
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_1_proxy.scanID == 0
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState == ObsState.IDLE.value

        # add receptors
        create_subarray_1_proxy.AddReceptors([1, 10])
        time.sleep(1)
        assert create_subarray_1_proxy.receptors == (1, 10)

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.set_timeout_millis(60000)  # since the command takes a while
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(1)

        # check configured attributes of CBF subarray
        assert create_subarray_1_proxy.scanID == 1
        assert create_subarray_1_proxy.frequencyBand == 4
        assert create_subarray_1_proxy.obsState == ObsState.READY.value

        # check frequency band of VCCs, including states of frequency band capabilities
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].frequencyBand == 4
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBand == 4
        assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[10] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
        assert [proxy.State() for proxy in create_vcc_band_proxies[receptor_to_vcc[1] - 1]] == [
            DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

        # check the rest of the configured attributes of VCCs
        # first for VCC belonging to receptor 10...
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].subarrayMembership == 1
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].band5Tuning == (5.85, 7.25)
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].frequencyBandOffsetStream1 == 0
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].frequencyBandOffsetStream2 == 0
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].rfiFlaggingMask == "{}"
        # then for VCC belonging to receptor 1...
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].subarrayMembership == 1
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].band5Tuning == (5.85, 7.25)
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream1 == 0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].frequencyBandOffsetStream2 == 0
        assert create_vcc_proxies[receptor_to_vcc[1] - 1].rfiFlaggingMask == "{}"

        # check configured attributes of search windows
        # first for search window 1...
        assert create_sw_1_proxy.searchWindowTuning == 6000000000
        assert create_sw_1_proxy.tdcEnable == True
        assert create_sw_1_proxy.tdcNumBits == 8
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 5
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 25
        assert "".join(create_sw_1_proxy.tdcDestinationAddress.split()) in [
               "{\"10\":[\"foo\",\"bar\",\"baz\"],\"1\":[\"fizz\",\"buzz\",\"fizz-buzz\"]}",
               "{\"1\":[\"fizz\",\"buzz\",\"fizz-buzz\"],\"10\":[\"foo\",\"bar\",\"baz\"]}"
        ]
        # then for search window 2...
        assert create_sw_2_proxy.searchWindowTuning == 7000000000
        assert create_sw_2_proxy.tdcEnable == False

        # check configured attributes of VCC search windows
        # first for search window 1 of VCC belonging to receptor 10...
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][0].searchWindowTuning == 6000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][0].tdcEnable == True
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][0].tdcNumBits == 8
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][0].tdcPeriodBeforeEpoch == 5
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][0].tdcPeriodAfterEpoch == 25
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][0].tdcDestinationAddress == (
            "foo", "bar", "baz"
        )
        # then for search window 1 of VCC belonging to receptor 1...
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].searchWindowTuning == 6000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcEnable == True
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcNumBits == 8
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodBeforeEpoch == 5
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcPeriodAfterEpoch == 25
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][0].tdcDestinationAddress == (
            "fizz", "buzz", "fizz-buzz"
        )
        # then for search window 2 of VCC belonging to receptor 10...
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][1].searchWindowTuning == 7000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[10] - 1][1].tdcEnable == False
        # and lastly for search window 2 of VCC belonging to receptor 1...
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].searchWindowTuning == 7000000000
        assert create_vcc_tdc_proxies[receptor_to_vcc[1] - 1][1].tdcEnable == False

        # check configured attributes of FSPs, including states of function mode capabilities
        assert create_fsp_1_proxy.functionMode == 1
        assert create_fsp_2_proxy.functionMode == 1
        assert 1 in create_fsp_1_proxy.subarrayMembership
        assert 1 in create_fsp_2_proxy.subarrayMembership
        assert [proxy.State() for proxy in create_fsp_1_function_mode_proxy] == [
            DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        ]
        assert [proxy.State() for proxy in create_fsp_2_function_mode_proxy] == [
            DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
        ]

        # check configured attributes of FSP subarrays
        # first for FSP 1...
        assert create_fsp_1_subarray_1_proxy.receptors == (10,)
        assert create_fsp_1_subarray_1_proxy.frequencyBand == 4
        assert create_fsp_1_subarray_1_proxy.band5Tuning == (5.85, 7.25)
        assert create_fsp_1_subarray_1_proxy.frequencySliceID == 1
        assert create_fsp_1_subarray_1_proxy.corrBandwidth == 1
        assert create_fsp_1_subarray_1_proxy.zoomWindowTuning == 6000000
        assert create_fsp_1_subarray_1_proxy.integrationTime == 140
        assert create_fsp_1_subarray_1_proxy.channelAveragingMap == (
            (1, 0),
            (745, 0),
            (1489, 0),
            (2233, 0),
            (2977, 0),
            (3721, 0),
            (4465, 0),
            (5209, 0),
            (5953, 0),
            (6697, 0),
            (7441, 0),
            (8185, 0),
            (8929, 0),
            (9673, 0),
            (10417, 0),
            (11161, 0),
            (11905, 0),
            (12649, 0),
            (13393, 0),
            (14137, 0)
        )
        # then for FSP 2...
        assert create_fsp_2_subarray_1_proxy.receptors == (1, 10)
        assert create_fsp_2_subarray_1_proxy.frequencyBand == 4
        assert create_fsp_1_subarray_1_proxy.band5Tuning == (5.85, 7.25)
        assert create_fsp_2_subarray_1_proxy.frequencySliceID == 20
        assert create_fsp_2_subarray_1_proxy.corrBandwidth == 0
        assert create_fsp_2_subarray_1_proxy.integrationTime == 1400
        assert create_fsp_2_subarray_1_proxy.channelAveragingMap == ((0, 0),)*20
