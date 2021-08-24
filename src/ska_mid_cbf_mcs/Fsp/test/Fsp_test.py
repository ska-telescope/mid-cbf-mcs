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

from Fsp.Fsp import Fsp
from ska_tango_base.control_model import HealthState, AdminMode, ObsState

@pytest.mark.usefixtures(
    "create_fsp_proxy",
    "create_corr_proxy",
    "create_pss_proxy",
    "create_pst_proxy",
    "create_vlbi_proxy"
)

class TestFsp:
    """
    @classmethod
    def mocking(cls):
    """#Mock external libraries.
    """
        # Example : Mock numpy
        # cls.numpy = CspController.numpy = MagicMock()
    """

    def test_SetFunctionMode(
            self,
            create_fsp_proxy,
            create_corr_proxy,
            create_pss_proxy,
            create_pst_proxy,
            create_vlbi_proxy
    ):
        """
        Test SetFunctionMode command state changes.
        """
        create_corr_proxy.Init()
        create_pss_proxy.Init()
        create_pst_proxy.Init()
        create_vlbi_proxy.Init()
        create_fsp_proxy.Init()
        time.sleep(3)

        # all function modes should be disabled after initialization
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to CORR
        create_fsp_proxy.SetFunctionMode("CORR")
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.ON
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to PSS
        create_fsp_proxy.SetFunctionMode("PSS-BF")
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.ON
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to PST
        create_fsp_proxy.SetFunctionMode("PST-BF")
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.ON
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to VLBI
        create_fsp_proxy.SetFunctionMode("VLBI")
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.ON

        # set function mode to IDLE
        create_fsp_proxy.SetFunctionMode("IDLE")
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE

    def test_AddRemoveSubarrayMembership(self, create_fsp_proxy):
        create_fsp_proxy.Init()
        time.sleep(3)

        # subarray membership should be empty
        assert create_fsp_proxy.subarrayMembership == None

        # add FSP to some subarrays
        create_fsp_proxy.AddSubarrayMembership(3)
        create_fsp_proxy.AddSubarrayMembership(4)
        time.sleep(1)
        assert create_fsp_proxy.subarrayMembership == (3, 4)

        # remove from a subarray
        create_fsp_proxy.RemoveSubarrayMembership(3)
        time.sleep(1)
        assert create_fsp_proxy.subarrayMembership == (4,)

        # add again...
        create_fsp_proxy.AddSubarrayMembership(15)
        time.sleep(1)
        assert create_fsp_proxy.subarrayMembership == (4, 15)

        # remove from all subarrays
        create_fsp_proxy.RemoveSubarrayMembership(4)
        create_fsp_proxy.RemoveSubarrayMembership(15)
        time.sleep(1)
        assert create_fsp_proxy.subarrayMembership == None
