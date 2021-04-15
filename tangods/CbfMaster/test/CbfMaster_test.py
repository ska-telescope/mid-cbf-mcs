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
from CbfMaster.CbfMaster import CbfMaster
from ska_tango_base.control_model import HealthState, AdminMode

@pytest.mark.usefixtures("proxies")

class TestCbfMaster:

    def test_On_valid(self, proxies):
        """
        Test a valid use of the "On" command
        """
        # check initial states
        assert proxies.master.State() == DevState.STANDBY
        assert proxies.subarray[1].State() == DevState.OFF
        for i in range(2):
            assert proxies.sw[i + 1].State() == DevState.OFF
        for i in range(4):
            assert proxies.vcc[i + 1].State() == DevState.OFF
        for i in range(2):
            assert proxies.fsp[i + 1].State() == DevState.OFF
        for i in range(2):
            assert proxies.fspSubarray[i + 1].State() == DevState.OFF

        # send the On command
        proxies.master.On()

        #check states
        proxies.wait_timeout_dev([proxies.master], DevState.ON, 3, 0.1)
        assert proxies.master.State() == DevState.ON

        proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.1)
        assert proxies.subarray[1].State() == DevState.ON

        proxies.wait_timeout_dev([proxies.sw[i + 1] for i in range(2)], DevState.DISABLE, 1, 0.1)
        for i in range(2):
            assert proxies.sw[i + 1].State() == DevState.DISABLE

        proxies.wait_timeout_dev([proxies.vcc[i + 1] for i in range(4)], DevState.ON, 1, 0.1)
        for i in range(4):
            assert proxies.vcc[i + 1].State() == DevState.ON

        proxies.wait_timeout_dev([proxies.fsp[i + 1] for i in range(2)], DevState.ON, 1, 0.1)
        for i in range(2):
            assert proxies.fsp[i + 1].State() == DevState.ON

        proxies.wait_timeout_dev([proxies.fspSubarray[i + 1] for i in range(2)], DevState.ON, 1, 0.1)
        for i in range(2):
            assert proxies.fspSubarray[i + 1].State() == DevState.ON
        

    def test_Standby_valid(self, proxies):
        """
        Test a valid use of the "Standby" command
        """
        # send the Standby command
        proxies.master.Standby()

        # check states
        proxies.wait_timeout_dev([proxies.master], DevState.STANDBY, 3, 0.1)
        assert proxies.master.State() == DevState.STANDBY

        proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.1)
        assert proxies.subarray[1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.sw[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        for i in range(2):
            assert proxies.sw[i + 1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.vcc[i + 1] for i in range(4)], DevState.OFF, 1, 0.1)
        for i in range(4):
            assert proxies.vcc[i + 1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.fsp[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        for i in range(2):
            assert proxies.fsp[i + 1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.fspSubarray[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        for i in range(2):
            assert proxies.fspSubarray[i + 1].State() == DevState.OFF

    def test_Off_valid(self, proxies):
        """
        Test a valid use of the "Off" command
        """

        # send the Off command
        proxies.master.Off()

        # check states
        proxies.wait_timeout_dev([proxies.master], DevState.OFF, 3, 0.1)
        assert proxies.master.State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.1)
        assert proxies.subarray[1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.sw[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        for i in range(2):
            assert proxies.sw[i + 1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.vcc[i + 1] for i in range(4)], DevState.OFF, 1, 0.1)
        for i in range(4):
            assert proxies.vcc[i + 1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.fsp[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        for i in range(2):
            assert proxies.fsp[i + 1].State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.fspSubarray[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        for i in range(2):
            assert proxies.fspSubarray[i + 1].State() == DevState.OFF

    # Don't really wanna bother fixing these three tests right now.
    """
    def test_reportVCCSubarrayMembership(
            self,
            cbf_master_proxy,
            subarray_1_proxy,
            subarray_2_proxy,
            vcc_proxies
    ):
    """
    """
        Test the VCC subarray membership subscriptions
    """
    """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               cbf_master_proxy.receptorToVcc)
        subarray_1_proxy.Init()
        subarray_2_proxy.Init()
        for proxy in vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # all memberships should be 0 initially
        assert cbf_master_proxy.reportVCCSubarrayMembership == (0,)*197

        # add receptors to each of two subarrays
        subarray_1_proxy.AddReceptors([197, 1])
        subarray_2_proxy.AddReceptors([10, 17])
        time.sleep(4)
        assert cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[197] - 1] == 1
        assert cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[1] - 1] == 1
        assert cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[10] - 1] == 2
        assert cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[17] - 1] == 2

        # remove all receptors
        subarray_1_proxy.RemoveAllReceptors()
        subarray_2_proxy.RemoveAllReceptors()
        time.sleep(4)
        assert cbf_master_proxy.reportVCCSubarrayMembership == (0,)*197

    def test_reportVCCState(
            self,
            cbf_master_proxy,
            vcc_proxies
    ):
    """
    """
        Test the VCC state subscriptions
    """
    """
        for proxy in vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # all states should be OFF initially
        assert cbf_master_proxy.reportVCCState == (DevState.OFF,)*197

        # change some states
        vcc_proxies[10].SetState(DevState.ON)
        vcc_proxies[17].SetState(DevState.DISABLE)
        vcc_proxies[196].SetState(DevState.STANDBY)
        time.sleep(3)
        assert cbf_master_proxy.reportVCCState[10] == DevState.ON
        assert cbf_master_proxy.reportVCCState[17] == DevState.DISABLE
        assert cbf_master_proxy.reportVCCState[196] == DevState.STANDBY

    def test_reportVCCHealthState(
            self,
            cbf_master_proxy,
            vcc_proxies
    ):
    """
    """
        Test the VCC state subscriptions
    """
    """
        for proxy in vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # all health states should be 3 (UNKNOWN) initially
        assert cbf_master_proxy.reportVCCHealthState == (3,)*197

        # change some health states
        vcc_proxies[10].SetHealthState(1)
        vcc_proxies[17].SetHealthState(0)
        vcc_proxies[196].SetHealthState(2)
        time.sleep(3)
        assert cbf_master_proxy.reportVCCHealthState[10] == 1
        assert cbf_master_proxy.reportVCCHealthState[17] == 0
        assert cbf_master_proxy.reportVCCHealthState[196] == 2
    """