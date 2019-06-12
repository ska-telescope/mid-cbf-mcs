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

from Fsp.Fsp import Fsp
from global_enum import HealthState, AdminMode, ObsState

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
        # cls.numpy = CspMaster.numpy = MagicMock()
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

        # set function mode to 1 (CORR)
        create_fsp_proxy.SetFunctionMode(1)
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.ON
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to 2 (PSS)
        create_fsp_proxy.SetFunctionMode(2)
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.ON
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to 3 (PST)
        create_fsp_proxy.SetFunctionMode(3)
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.ON
        assert create_vlbi_proxy.State() == DevState.DISABLE

        # set function mode to 4 (VLBI)
        create_fsp_proxy.SetFunctionMode(4)
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.ON

        # set function mode to 0 (IDLE)
        create_fsp_proxy.SetFunctionMode(0)
        time.sleep(1)
        assert create_corr_proxy.State() == DevState.DISABLE
        assert create_pss_proxy.State() == DevState.DISABLE
        assert create_pst_proxy.State() == DevState.DISABLE
        assert create_vlbi_proxy.State() == DevState.DISABLE
