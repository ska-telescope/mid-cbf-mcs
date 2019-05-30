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
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.OFF

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.ON

        # add more receptors...
        create_subarray_1_proxy.AddReceptors([17, 197])
        assert create_subarray_1_proxy.receptors == (1, 10, 197, 17)
        assert create_vcc_proxies[receptor_to_vcc[17] - 1].subarrayMembership == 1

        # remove some receptors
        create_subarray_1_proxy.RemoveReceptors([17, 1, 197])
        assert create_subarray_1_proxy.receptors == (10,)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 17, 197]])
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].subarrayMembership == 1

        # remove remaining receptors
        create_subarray_1_proxy.RemoveReceptors([10])
        assert create_subarray_1_proxy.receptors == ()
        assert create_vcc_proxies[receptor_to_vcc[10] - 1].subarrayMembership == 0
        time.sleep(1)
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
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()
        create_subarray_2_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_2_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.OFF
        assert create_subarray_2_proxy.State() == DevState.OFF

        # add some receptors to subarray 1
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.ON

        # try adding some receptors (including an invalid one) to subarray 2
        with pytest.raises(tango.DevFailed) as df:
            create_subarray_2_proxy.AddReceptors([17, 100, 197])
        assert "already in use" in str(df.value.args[0].desc)
        assert create_subarray_2_proxy.receptors == (17, 100)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 2 for i in [17, 100]])
        time.sleep(1)
        assert create_subarray_2_proxy.State() == DevState.ON

        # try adding an invalid receptor ID to subarray 2
        with pytest.raises(tango.DevFailed) as df:
            create_subarray_2_proxy.AddReceptors([200])
        assert "Invalid receptor ID" in str(df.value.args[0].desc)

        # try removing a receptor not assigned to subarray 2
        # doing this doesn't actually throw an error
        create_subarray_2_proxy.RemoveReceptors([5])
        assert create_subarray_2_proxy.receptors == (17, 100)

        # remove all receptors
        create_subarray_1_proxy.RemoveReceptors([1, 10, 197])
        create_subarray_2_proxy.RemoveReceptors([17, 100])
        assert create_subarray_1_proxy.receptors == ()
        assert create_subarray_2_proxy.receptors == ()
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 10, 17, 100, 197]])
        time.sleep(1)
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
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               create_cbf_master_proxy.receptorToVcc)

        create_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        # receptor list should be empty right after initialization
        assert create_subarray_1_proxy.receptors == ()
        assert all([proxy.subarrayMembership == 0 for proxy in create_vcc_proxies])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.OFF

        # add some receptors
        create_subarray_1_proxy.AddReceptors([1, 10, 197])
        assert create_subarray_1_proxy.receptors == (1, 10, 197)
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 1 for i in [1, 10, 197]])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.ON

        # remove all receptors
        create_subarray_1_proxy.RemoveAllReceptors()
        assert create_subarray_1_proxy.receptors == ()
        assert all([create_vcc_proxies[receptor_to_vcc[i] - 1].subarrayMembership == 0 for i in [1, 10, 197]])
        time.sleep(1)
        assert create_subarray_1_proxy.State() == DevState.OFF

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

        f = open(file_path + "/test_json/test_ConfigureScan_basic.json")
        create_subarray_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()

        assert create_subarray_1_proxy.receptors == (1,)
        assert create_subarray_1_proxy.scanID == 1
        assert create_subarray_1_proxy.frequencyBand == 0
        assert create_subarray_1_proxy.obsState == ObsState.READY.value
