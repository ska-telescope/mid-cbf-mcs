#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

# Standard imports
import sys
import os
import time

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports

from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode, ControlMode, HealthState, LoggingLevel, SimulationMode, TestMode
)
from ska_tango_base.base_device import (
    _DEBUGGER_PORT,
    _Log4TangoLoggingLevel,
    _PYTHON_TO_TANGO_LOGGING_LEVEL,
    LoggingUtils,
    LoggingTargetError,
    DeviceStateModel,
    TangoLoggingServiceHandler,
)
from ska_tango_base.faults import CommandError
import socket
from tango.test_context import DeviceTestContext


@pytest.mark.usefixtures("test_proxies")

class TestCbfController:

    @pytest.mark.skip(reason="enable to test DebugDevice")
    def test_DebugDevice(self, test_proxies):
        port = test_proxies.controller.DebugDevice()
        assert port == _DEBUGGER_PORT
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", _DEBUGGER_PORT))
        test_proxies.controller.On()

    def test_On_valid(self, test_proxies):
        """
        Test a valid use of the "On" command
        """
        # check initial states
        assert test_proxies.controller.State() == DevState.OFF
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.OFF
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.OFF

        # send the On command
        (result_code, message) = test_proxies.controller.On()

        #check states
        assert result_code == ResultCode.OK
        assert test_proxies.controller.State() == DevState.ON

        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.ON

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.ON

        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.ON
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.ON
        

    def test_Off_valid(self, test_proxies):
        """
        Test a valid use of the "Off" command
        """

        # send the Off command
        (result_code, message) = test_proxies.controller.Off()

        # check states
        assert result_code == ResultCode.OK
        assert test_proxies.controller.State() == DevState.OFF

        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.OFF
    
    def test_Standby_valid(self, test_proxies):
        """
        Test a valid use of the "Standby" command
        """
        # send the Standby command
        (result_code, message) = test_proxies.controller.Standby()

        # check states
        assert result_code == ResultCode.OK
        assert test_proxies.controller.State() == DevState.STANDBY

        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.OFF


    #TODO implement these tests properly?
    # def test_reportVCCSubarrayMembership(
    #         self,
    #         cbf_master_proxy,
    #         subarray_1_proxy,
    #         subarray_2_proxy,
    #         vcc_test_proxies
    # ):
    # """
    #     Test the VCC subarray membership subscriptions
    # """

    # def test_reportVCCState(
    #         self,
    #         cbf_master_proxy,
    #         vcc_test_proxies
    # ):
    # """
    #     Test the VCC state subscriptions
    # """
       
    # def test_reportVCCHealthState(
    #         self,
    #         cbf_master_proxy,
    #         vcc_test_proxies
    # ):
    # """
    #     Test the VCC state subscriptions
    # """
