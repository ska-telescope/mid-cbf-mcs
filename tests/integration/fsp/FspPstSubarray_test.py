#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.
"""Contain the tests for the FspPstSubarray."""
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

class TestFspPstSubarray:
    """
    Test class for FspPstSubarray device class integration testing.
    """

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(2, 1)]
    )
    def test_Connect(
        self: TestFspPstSubarray, 
        test_proxies: pytest.fixture,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager 
        can start communicating

        :param test_proxies: the proxies test fixture
        :param fsp_id: the fsp id
        :param sub_id: the subarray id
        """
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]

        assert device_under_test.State() == DevState.DISABLE 

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE

        # device should be in OFF state after start_communicating 
        test_proxies.wait_timeout_dev([device_under_test], DevState.OFF, 3, 0.1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(2, 1)]
    )
    def test_On(
        self: TestFspPstSubarray, 
        test_proxies: pytest.fixture,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        :param fsp_id: the fsp id
        :param sub_id: the subarray id
        """
        
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]

        device_under_test.On()

        test_proxies.wait_timeout_dev([device_under_test], DevState.ON, 3, 0.1)
        assert device_under_test.State() == DevState.ON
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(2, 1)]
    )
    def test_Off(
        self: TestFspPstSubarray, 
        test_proxies: pytest.fixture,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test the "Off" command

        :param test_proxies: the proxies test fixture
        :param fsp_id: the fsp id
        :param sub_id: the subarray id
        """
        
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]

        device_under_test.Off()

        test_proxies.wait_timeout_dev([device_under_test], DevState.OFF, 3, 0.1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(2, 1)]
    )
    def test_Standby(
        self: TestFspPstSubarray, 
        test_proxies: pytest.fixture,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test the "Standby" command

        :param test_proxies: the proxies test fixture
        :param fsp_id: the fsp id
        :param sub_id: the subarray id
        """
        
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]

        device_under_test.Standby()

        test_proxies.wait_timeout_dev([device_under_test], DevState.STANDBY, 3, 0.1)
        assert device_under_test.State() == DevState.STANDBY

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(2, 1)]
    )
    def test_Disconnect(
        self: TestFspPstSubarray, 
        test_proxies: pytest.fixture,         
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        :param fsp_id: the fsp id
        :param sub_id: the subarray id
        """

        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE

        # device should be in DISABLE state after stop_communicating  
        test_proxies.wait_timeout_dev([device_under_test], DevState.DISABLE, 3, 0.1)
        assert device_under_test.State() == DevState.DISABLE