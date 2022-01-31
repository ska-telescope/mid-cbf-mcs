#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.
"""Contain the tests for the FspSubarray."""
from __future__ import annotations

import pytest
import time
import os
import copy
import json

data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

import tango
from tango import DevState

from ska_tango_base.control_model import AdminMode, ObsState
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

class TestFspPssSubarray:
    """
    Test class for FspPssSubarray device class integration testing.
    """

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Connect(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager 
        can start communicating
        """
        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]

        assert device_under_test.State() == DevState.DISABLE 

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE

        # device should be in OFF state after start_communicating 
        test_proxies.wait_timeout_dev([device_under_test], DevState.OFF, 3, 0.1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_On(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test a valid use of the "On" command
        """
        
        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]

        device_under_test.On()

        test_proxies.wait_timeout_dev([device_under_test], DevState.ON, 3, 0.1)
        assert device_under_test.State() == DevState.ON
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Off(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test a valid use of the "Off" command
        """
        
        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]

        device_under_test.Off()

        test_proxies.wait_timeout_dev([device_under_test], DevState.OFF, 3, 0.1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Standby(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test a valid use of the "Standby" command
        """
        
        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]

        device_under_test.Standby()

        test_proxies.wait_timeout_dev([device_under_test], DevState.STANDBY, 3, 0.1)
        assert device_under_test.State() == DevState.STANDBY
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_ConfigureScan(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:

        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]
        wait_time_s = 1
        sleep_time_s = 1

        assert device_under_test.adminMode == AdminMode.ONLINE

        device_under_test.On()

        test_proxies.wait_timeout_dev([device_under_test], DevState.ON, wait_time_s, sleep_time_s)
        assert device_under_test.State() == DevState.ON

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].subarrayMembership == 0
        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.vcc[i].subarrayMembership = sub_id
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].subarrayMembership == sub_id

        config_file_name = "FspPssSubarray_ConfigureScan_basic.json"
        f = open(data_file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = copy.deepcopy(json.loads(json_str))
        f.close()

        assert device_under_test.obsState == ObsState.IDLE
        
        device_under_test.ConfigureScan(json_str)

        time.sleep(10)
        assert device_under_test.obsState == ObsState.READY
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Scan(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:

        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]
        wait_time_s = 1
        sleep_time_s = 1

        assert device_under_test.adminMode == AdminMode.ONLINE

        test_proxies.wait_timeout_dev([device_under_test], DevState.ON, wait_time_s, sleep_time_s)
        assert device_under_test.State() == DevState.ON

        scan_id = 1
        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, str(scan_id))

        device_under_test.Scan(scan_id_device_data)

        test_proxies.wait_timeout_obs([device_under_test], ObsState.SCANNING, wait_time_s, sleep_time_s)
        assert device_under_test.obsState == ObsState.SCANNING

        assert device_under_test.scanID == scan_id

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_EndScan(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:

        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]
        wait_time_s = 1
        sleep_time_s = 1

        assert device_under_test.adminMode == AdminMode.ONLINE

        test_proxies.wait_timeout_dev([device_under_test], DevState.ON, wait_time_s, sleep_time_s)
        assert device_under_test.State() == DevState.ON

        device_under_test.EndScan()
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Disconnect(
        self: TestFspPssSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Verify the component manager can stop communicating
        """

        device_under_test = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE

        # device should be in DISABLE state after stop_communicating  
        test_proxies.wait_timeout_dev([device_under_test], DevState.DISABLE, 3, 0.1)
        assert device_under_test.State() == DevState.DISABLE