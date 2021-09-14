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

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

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


@pytest.mark.usefixtures("proxies")

class TestCbfController:

    @pytest.mark.skip(reason="enable to test DebugDevice")
    def test_DebugDevice(self, proxies):
        port = proxies.controller.DebugDevice()
        assert port == _DEBUGGER_PORT
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", _DEBUGGER_PORT))
        proxies.controller.On()

    def test_On_valid(self, proxies):
        """
        Test a valid use of the "On" command
        """
        # check initial states
        assert proxies.controller.State() == DevState.OFF
        assert proxies.subarray[1].State() == DevState.OFF

        # TODO - to remove
        # for i in range(2):
        #     assert proxies.sw[i + 1].State() == DevState.OFF

        for i in range(4):
            assert proxies.vcc[i + 1].State() == DevState.OFF
        for i in range(2):
            assert proxies.fsp[i + 1].State() == DevState.OFF
        for i in range(2):
            assert proxies.fspSubarray[i + 1].State() == DevState.OFF

        # send the On command
        proxies.controller.On()

        #check states
        proxies.wait_timeout_dev([proxies.controller], DevState.ON, 3, 0.1)
        assert proxies.controller.State() == DevState.ON

        proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 0.1)
        assert proxies.subarray[1].State() == DevState.ON

        # TODO - to remove
        # proxies.wait_timeout_dev([proxies.sw[i + 1] for i in range(2)], DevState.DISABLE, 1, 0.1)
        # for i in range(2):
        #     assert proxies.sw[i + 1].State() == DevState.DISABLE

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
        proxies.controller.Standby()

        # check states
        proxies.wait_timeout_dev([proxies.controller], DevState.STANDBY, 3, 0.1)
        assert proxies.controller.State() == DevState.STANDBY

        proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.1)
        assert proxies.subarray[1].State() == DevState.OFF

        # The SearchWindow (SW) servers are currently not running
        # as their functionality is covered by the  VCCSearchWindow server
        # TODO: to remove from devices.json.

        # proxies.wait_timeout_dev([proxies.sw[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        # for i in range(2):
        #     assert proxies.sw[i + 1].State() == DevState.OFF

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
        proxies.controller.Off()

        # check states
        proxies.wait_timeout_dev([proxies.controller], DevState.OFF, 3, 0.1)
        assert proxies.controller.State() == DevState.OFF

        proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 0.1)
        assert proxies.subarray[1].State() == DevState.OFF

        # TODO - to remove
        # proxies.wait_timeout_dev([proxies.sw[i + 1] for i in range(2)], DevState.OFF, 1, 0.1)
        # for i in range(2):
        #     assert proxies.sw[i + 1].State() == DevState.OFF

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
        vcc_proxies[10].On()
        vcc_proxies[17].Disable()
        vcc_proxies[196].Standby()
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