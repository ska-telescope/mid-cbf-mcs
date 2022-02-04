#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Fsp."""
from __future__ import annotations
from typing import List

# Standard imports
import sys
import os
import time
import json
from enum import Enum
import logging

file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports
from ska_tango_base.control_model import HealthState, AdminMode, ObsState

class TestFsp:
    """
    Test class for Fsp device class integration testing.
    """

    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_Connect(
        self: TestFsp,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager 
        can start communicating
        """
        
        # after init devices should be in DISABLE state
        assert test_proxies.fsp[fsp_id].State() == DevState.DISABLE

        # trigger start_communicating by setting the AdminMode to ONLINE
        test_proxies.fsp[fsp_id].adminMode = AdminMode.ONLINE

        # fsp device should be in OFF state after start_communicating 
        test_proxies.wait_timeout_dev([test_proxies.fsp[fsp_id]], DevState.OFF, 3, 0.1)
        assert test_proxies.fsp[fsp_id].State() == DevState.OFF

    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_On(
        self: TestFsp,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:
        """
        Test the "On" command
        """

        # send the On command
        test_proxies.fsp[fsp_id].On()

        test_proxies.wait_timeout_dev([test_proxies.fsp[fsp_id]], DevState.ON, 3, 0.1)
        assert test_proxies.fsp[fsp_id].State() == DevState.ON

    
    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_Off(
        self: TestFsp,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:
        """
        Test the "Off" command
        """

        # send the Off command
        test_proxies.fsp[fsp_id].Off()

        test_proxies.wait_timeout_dev([test_proxies.fsp[fsp_id]], DevState.OFF, 3, 0.1)
        assert test_proxies.fsp[fsp_id].State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_Standby(
        self: TestFsp,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:
        """
        Test the "Standby" command
        """
        # send the Standby command
        test_proxies.fsp[fsp_id].Standby()

        test_proxies.wait_timeout_dev([test_proxies.fsp[fsp_id]], DevState.STANDBY, 3, 0.1)
        assert test_proxies.fsp[fsp_id].State() == DevState.STANDBY
    
    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_SetFunctionMode(
        self,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:
        """
        Test SetFunctionMode command state changes.
        """

        test_proxies.fsp[fsp_id].On()

        test_proxies.wait_timeout_dev([test_proxies.fsp[fsp_id]], DevState.ON, 3, 0.1)
        assert test_proxies.fsp[fsp_id].State() == DevState.ON

        # all function modes should be disabled after initialization
        assert test_proxies.fspFunctionMode[
            fsp_id]["corr"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pss"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pst"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["vlbi"].State() == DevState.DISABLE

        # set function mode to CORR
        test_proxies.fsp[fsp_id].SetFunctionMode("CORR")
        time.sleep(1)
        assert test_proxies.fspFunctionMode[
            fsp_id]["corr"].State() == DevState.ON
        assert test_proxies.fspFunctionMode[
            fsp_id]["pss"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pst"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["vlbi"].State() == DevState.DISABLE

        # set function mode to PSS
        test_proxies.fsp[fsp_id].SetFunctionMode("PSS-BF")
        time.sleep(1)
        assert test_proxies.fspFunctionMode[
            fsp_id]["corr"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pss"].State() == DevState.ON
        assert test_proxies.fspFunctionMode[
            fsp_id]["pst"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["vlbi"].State() == DevState.DISABLE

        # set function mode to PST
        test_proxies.fsp[fsp_id].SetFunctionMode("PST-BF")
        time.sleep(1)
        assert test_proxies.fspFunctionMode[ 
            fsp_id]["corr"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pss"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pst"].State() == DevState.ON
        assert test_proxies.fspFunctionMode[
            fsp_id]["vlbi"].State() == DevState.DISABLE

        # set function mode to VLBI
        test_proxies.fsp[fsp_id].SetFunctionMode("VLBI")
        time.sleep(1)
        assert test_proxies.fspFunctionMode[
            fsp_id]["corr"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pss"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pst"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["vlbi"].State() == DevState.ON

        # set function mode to IDLE
        test_proxies.fsp[fsp_id].SetFunctionMode("IDLE")
        time.sleep(1)
        assert test_proxies.fspFunctionMode[
            fsp_id]["corr"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pss"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["pst"].State() == DevState.DISABLE
        assert test_proxies.fspFunctionMode[
            fsp_id]["vlbi"].State() == DevState.DISABLE
    
    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_AddRemoveSubarrayMembership(
        self,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:

        # subarray membership should be empty
        assert test_proxies.fsp[fsp_id].subarrayMembership == None

        # add FSP to some subarrays
        test_proxies.fsp[fsp_id].AddSubarrayMembership(3)
        test_proxies.fsp[fsp_id].AddSubarrayMembership(4)
        time.sleep(4)
        assert list(test_proxies.fsp[fsp_id].subarrayMembership) == [3, 4]

        # remove from a subarray
        test_proxies.fsp[fsp_id].RemoveSubarrayMembership(3)
        time.sleep(4)
        assert list(test_proxies.fsp[fsp_id].subarrayMembership) == [4]

        # add again...
        test_proxies.fsp[fsp_id].AddSubarrayMembership(15)
        time.sleep(4)
        assert list(test_proxies.fsp[fsp_id].subarrayMembership) == [4, 15]

        # remove from all subarrays
        test_proxies.fsp[fsp_id].RemoveSubarrayMembership(4)
        test_proxies.fsp[fsp_id].RemoveSubarrayMembership(15)
        time.sleep(4)
        assert test_proxies.fsp[fsp_id].subarrayMembership == None
    
    @pytest.mark.parametrize(
        "jones_matrix_file_name, \
        pss_config_file_name, \
        pst_config_file_name, \
        sub_id, \
        valid_receptor_ids, \
        fsp_id",
        [
            (
                "/../../data/jonesmatrix_unit_test.json",
                "/../../data/FspPssSubarray_ConfigureScan_basic.json",
                "/../../data/FspPstSubarray_ConfigureScan_basic.json",
                1,
                [1, 2, 3, 4],
                1
            )
        ]
    )
    def test_UpdateJonesMatrix(
        self,
        test_proxies: pytest.fixture,
        jones_matrix_file_name: str,
        pss_config_file_name: str,
        pst_config_file_name: str,
        sub_id: int,
        valid_receptor_ids: List[int],
        fsp_id: int
    ) -> None:

        device_under_test = test_proxies.fsp[fsp_id]
        pss_proxy = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]
        pst_proxy = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
        
        device_under_test.AddSubarrayMembership(sub_id)
        time.sleep(4)
        assert device_under_test.read_attribute("subarrayMembership", \
            extract_as=tango.ExtractAs.List).value == [sub_id]

        pss_proxy.adminMode = AdminMode.ONLINE
        pst_proxy.adminMode = AdminMode.ONLINE
        test_proxies.wait_timeout_dev([pss_proxy], DevState.OFF, 3, 0.1)
        assert pss_proxy.State() == DevState.OFF
        test_proxies.wait_timeout_dev([pst_proxy], DevState.OFF, 3, 0.1)
        assert pst_proxy.State() == DevState.OFF
        
        assert pss_proxy.obsState == ObsState.IDLE
        assert pst_proxy.obsState == ObsState.IDLE
        pss_proxy.On()
        pst_proxy.On()
        test_proxies.wait_timeout_dev([pss_proxy], DevState.ON, 3, 0.1)
        assert pss_proxy.State() == DevState.ON
        test_proxies.wait_timeout_dev([pst_proxy], DevState.ON, 3, 0.1)
        assert pst_proxy.State() == DevState.ON

        f = open(file_path + pss_config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        pss_proxy.ConfigureScan(json_str)
        f = open(file_path + pst_config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        pst_proxy.ConfigureScan(json_str)
        time.sleep(5)
        assert pst_proxy.read_attribute("receptors", \
            extract_as=tango.ExtractAs.List).value == [1]
        assert pss_proxy.read_attribute("receptors", \
            extract_as=tango.ExtractAs.List).value == [1]

        # jones matrix values should be set to 0.0 after init
        num_cols = 16
        num_rows = 4
        assert device_under_test.read_attribute("jonesMatrix", \
             extract_as=tango.ExtractAs.List).value == [[0.0] * num_cols for _ in range(num_rows)]

        # read the json file
        f = open(file_path + jones_matrix_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        jones_matrix = json.loads(json_str)

        valid_function_modes = ["PSS-BF", "PST-BF"]
        for mode in valid_function_modes:
            device_under_test.SetFunctionMode(mode)
            time.sleep(0.1)
            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
            if mode == "PSS-BF":
                assert device_under_test.functionMode == FspModes.PSS_BF.value
                fs_length = 16
            elif mode == "PST-BF":
                assert device_under_test.functionMode == FspModes.PST_BF.value
                fs_length = 4

            # update the jones matrix
            for m in jones_matrix["jonesMatrix"]:
                device_under_test.UpdateJonesMatrix(json.dumps(m["matrixDetails"]))
            
            #TODO: verify correct jones matrix receieved 
            
        pss_proxy.adminMode = AdminMode.OFFLINE
        pst_proxy.adminMode = AdminMode.OFFLINE
    
    
    @pytest.mark.parametrize(
        "fsp_id", 
        [1]
    )
    def test_Disconnect(
         self,
        test_proxies: pytest.fixture,
        fsp_id: int
    ) -> None:
        """
        Verify the component manager can stop communicating
        """

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        test_proxies.fsp[fsp_id].adminMode = AdminMode.OFFLINE

        # fsp device should be in DISABLE state after stop_communicating  
        test_proxies.wait_timeout_dev([test_proxies.fsp[fsp_id]], DevState.DISABLE, 3, 0.1)
        assert test_proxies.fsp[fsp_id].State() == DevState.DISABLE

    
