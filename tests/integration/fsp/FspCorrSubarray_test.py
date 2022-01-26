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

from ska_tango_base.control_model import AdminMode

class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray device class integration testing.
    """

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Connect(
        self: TestFspCorrSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager 
        can start communicating
        """
        device_under_test = test_proxies.fspSubarray["CORR"][sub_id][fsp_id]

        assert device_under_test.State() == DevState.DISABLE 

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE

        # controller device should be in OFF state after start_communicating 
        time.sleep(1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_On(
        self: TestFspCorrSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test a valid use of the "On" command
        """
        
        device_under_test = test_proxies.fspSubarray["CORR"][sub_id][fsp_id]

        device_under_test.On()

        time.sleep(1)
        assert device_under_test.State() == DevState.ON
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Off(
        self: TestFspCorrSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test a valid use of the "Off" command
        """
        
        device_under_test = test_proxies.fspSubarray["CORR"][sub_id][fsp_id]

        device_under_test.Off()

        time.sleep(1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_ConfigureScan(
        self: TestFspCorrSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:

        device_under_test = test_proxies.fspSubarray["CORR"][sub_id][fsp_id]

        config_file_name = "Vcc_ConfigureScan_basic.json"
        f = open(data_file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = copy.deepcopy(json.loads(json_str))
        f.close()
        pass
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Disconnect(
        self: TestFspCorrSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Verify the component manager can stop communicating
        """

        device_under_test = test_proxies.fspSubarray["CORR"][sub_id][fsp_id]

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating  
        time.sleep(1)
        assert device_under_test.State() == DevState.DISABLE