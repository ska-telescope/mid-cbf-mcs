#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CspMaster."""

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
from CspMaster.CspMaster import CspMaster
from global_enum import HealthState, AdminMode

# Device test case
@pytest.mark.usefixtures("tango_context", "initialize_device", "create_cbfmaster_proxy")

class TestCspMaster(object):
    device = CspMaster
    properties = {'SkaLevel': '1', 'GroupDefinitions': '',
                  'CentralLoggingTarget': '', 'ElementLoggingTarget': '',
                  'StorageLoggingTarget': 'localhost', 'CentralAlarmHandler': '', 
                  'CspMidCbf': 'mid_csp_cbf/sub_elt/master',
                  'CspMidPss': 'mid_csp_pss/sub_elt/master',
                  'CspMidPst': 'mid_csp_pst/sub_elt/master',
                  }
    empty = None  # Should be []

    @classmethod
    def mocking(cls):
        """Mock external libraries."""
        # Example : Mock numpy
        # cls.numpy = CspMaster.numpy = MagicMock()

    def test_properties(self, tango_context):
        # test the properties
        pass

    def test_State(self, tango_context, create_cbfmaster_proxy):
        """Test for State after initialization """
        # reinitalize Csp Master and CbfMaster devices
        tango_context.device.Init()
        create_cbfmaster_proxy.Init()
        # seleep for a while to wait for state transition
        time.sleep(2)
        csp_state = tango_context.device.State()
        assert csp_state in [DevState.STANDBY, DevState.INIT]

    def test_adminMode(self, tango_context):
        """ Test the adminMode attribute w/r"""
        tango_context.device.adminMode = AdminMode.OFFLINE.value
        assert tango_context.device.adminMode.value == AdminMode.OFFLINE.value

    def test_On_invalid_argument(self, tango_context):
        """Test for the excution of the On command with a wrong input argument"""
        with pytest.raises(tango.DevFailed) as df:
            argin = ["cbf", ]
            tango_context.device.On(argin)
        assert "No proxy for device" in str(df.value)

    def test_On_valid_state(self, tango_context, create_cbfmaster_proxy):
        """
        Test for execution of On command when the CbfTestMaster is in the right state
        """
        #reinit CSP and CBFTest master devices
        tango_context.device.Init()
        create_cbfmaster_proxy.Init()
        # sleep for a while to wait state transition
        time.sleep(2)
        # check CspMstar state
        assert tango_context.device.State() == DevState.STANDBY
        # issue the "On" command on CbfTestMaster device
        argin = ["mid_csp_cbf/sub_elt/master",]
        tango_context.device.On(argin)
        time.sleep(3)
        assert tango_context.device.State() == DevState.ON

    def test_On_invalid_state(self, tango_context, create_cbfmaster_proxy):
        """
        Test for the execution of the On command when the CbfTestMaster 
        is in an invalid state
        """
        #reinit CSP and CBFTest master devices
        tango_context.device.Init()
        create_cbfmaster_proxy.Init()
        # sleep for a while to wait for state transitions
        time.sleep(2)
        assert create_cbfmaster_proxy.State() == DevState.STANDBY
        # issue the command to switch off the CbfMaster
        argin=["",]
        create_cbfmaster_proxy.Off(argin)
        # wait for the state transition from STANDBY to OFF
        time.sleep(3)
        assert create_cbfmaster_proxy.State() == DevState.OFF
        # issue the command to switch on the CbfMaster device
        with pytest.raises(tango.DevFailed) as df:
            argin = ["mid_csp_cbf/sub_elt/master", ]
            tango_context.device.On(argin)
        assert "Command failure" in str(df.value.args[0].desc)
        assert 0
