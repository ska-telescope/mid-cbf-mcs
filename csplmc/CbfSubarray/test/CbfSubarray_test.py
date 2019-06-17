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
    "create_vcc_proxies",
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

    def test_ConfigureScan_basic(self, create_subarray_1_proxy):
        """
        Test a minimal successful configuration
        """
        create_subarray_1_proxy.Init()

        # check default values
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_1_proxy.scanID == 0
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState == ObsState.IDLE.value

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()

        # check configured values
        assert create_subarray_1_proxy.receptors == (1,)
        assert create_subarray_1_proxy.scanID == 1
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState == ObsState.READY.value

    def test_ConfigureScan_subscriptions(
            self,
            create_subarray_1_proxy,
            create_tm_telstate_proxy
    ):
        """
        Test successful subscriptions to TM TelState attributes dopplerPhaseCorrection_1 and delayModel
        """
        create_subarray_1_proxy.Init()
        create_tm_telstate_proxy.Init()

        time.sleep(3)

        # check default values of attributes
        assert create_tm_telstate_proxy.dopplerPhaseCorrection_1 == (0, 0, 0, 0)
        assert create_tm_telstate_proxy.delayModel == "{}"
        assert create_subarray_1_proxy.reportDopplerPhaseCorrection == (0, 0, 0, 0)
        assert create_subarray_1_proxy.reportDelayModel == "{}"

        # configure scan
        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()

        # subscription should trigger an event, but default values are identical
        assert create_subarray_1_proxy.reportDopplerPhaseCorrection == (0, 0, 0, 0)
        assert create_subarray_1_proxy.reportDelayModel == "{}"

        # change attribute values
        create_tm_telstate_proxy.dopplerPhaseCorrection_1 = (1, 2, 3, 4)
        create_tm_telstate_proxy.delayModel = "{\"test\": 10000}"
        time.sleep(10)  # wait for next poll
        assert create_subarray_1_proxy.reportDopplerPhaseCorrection == (1, 2, 3, 4)
        assert create_subarray_1_proxy.reportDelayModel == "{\"test\": 10000}"

        create_tm_telstate_proxy.dopplerPhaseCorrection_1 = (2.789, -1, 3.141, 0)
        create_tm_telstate_proxy.delayModel = "{\"test\": [{\"foo\": \"bar\", \"fizz\": \"buzz\"}]}"
        time.sleep(10)  # wait for next poll
        assert create_subarray_1_proxy.reportDopplerPhaseCorrection == (2.789, -1, 3.141, 0)
        assert create_subarray_1_proxy.reportDelayModel == "{\"test\": [{\"foo\": \"bar\", \"fizz\": \"buzz\"}]}" or \
            create_subarray_1_proxy.reportDelayModel == "{\"test\": [{\"fizz\": \"buzz\", \"foo\": \"bar\"}]}"
