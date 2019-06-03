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
from global_enum import HealthState, AdminMode

@pytest.mark.usefixtures(
    "create_cbf_master_proxy",
    "create_subarray_1_proxy",
    "create_subarray_2_proxy",
    "create_vcc_proxies"
)

class TestCbfMaster:
    """
    @classmethod
    def mocking(cls):
    """#Mock external libraries.
    """
        # Example : Mock numpy
        # cls.numpy = CspMaster.numpy = MagicMock()
    """

    def test_reportVCCSubarrayMembership(
            self,
            create_cbf_master_proxy,
            create_subarray_1_proxy,
            create_subarray_2_proxy,
            create_vcc_proxies
    ):
        """
        # Test the VCC subarray membership subscriptions
        """
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               create_cbf_master_proxy.receptorToVcc)
        create_subarray_1_proxy.Init()
        create_subarray_2_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # all memberships should be 0 initially
        assert create_cbf_master_proxy.reportVCCSubarrayMembership == (0,)*197

        # add receptors to each of two subarrays
        create_subarray_1_proxy.AddReceptors([197, 1])
        create_subarray_2_proxy.AddReceptors([10, 17])
        time.sleep(4)
        assert create_cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[197] - 1] == 1
        assert create_cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[1] - 1] == 1
        assert create_cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[10] - 1] == 2
        assert create_cbf_master_proxy.reportVCCSubarrayMembership[receptor_to_vcc[17] - 1] == 2

        # remove all receptors
        create_subarray_1_proxy.RemoveAllReceptors()
        create_subarray_2_proxy.RemoveAllReceptors()
        time.sleep(4)
        assert create_cbf_master_proxy.reportVCCSubarrayMembership == (0,)*197

    def test_reportVCCState(
            self,
            create_cbf_master_proxy,
            create_vcc_proxies
    ):
        """
        # Test the VCC state subscriptions
        """
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # all states should be OFF initially
        assert create_cbf_master_proxy.reportVCCState == (DevState.OFF,)*197

        # change some states
        create_vcc_proxies[10].SetState(DevState.ON)
        create_vcc_proxies[17].SetState(DevState.DISABLE)
        create_vcc_proxies[196].SetState(DevState.STANDBY)
        time.sleep(3)
        assert create_cbf_master_proxy.reportVCCState[10] == DevState.ON
        assert create_cbf_master_proxy.reportVCCState[17] == DevState.DISABLE
        assert create_cbf_master_proxy.reportVCCState[196] == DevState.STANDBY

    def test_reportVCCHealthState(
            self,
            create_cbf_master_proxy,
            create_vcc_proxies
    ):
        """
        # Test the VCC state subscriptions
        """
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # all health states should be 3 (UNKNOWN) initially
        assert create_cbf_master_proxy.reportVCCHealthState == (3,)*197

        # change some health states
        create_vcc_proxies[10].SetHealthState(1)
        create_vcc_proxies[17].SetHealthState(0)
        create_vcc_proxies[196].SetHealthState(2)
        time.sleep(3)
        assert create_cbf_master_proxy.reportVCCHealthState[10] == 1
        assert create_cbf_master_proxy.reportVCCHealthState[17] == 0
        assert create_cbf_master_proxy.reportVCCHealthState[196] == 2
