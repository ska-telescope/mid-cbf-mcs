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

# Standard imports
import sys
import os
import time
import json

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports
from ska_tango_base.control_model import HealthState, AdminMode, ObsState


@pytest.mark.skip(reason="this class is currently untested")
class TestFsp:
    """
    Test class for Fsp device class integration testing.
    """

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
        time.sleep(1)
        assert test_proxies.fsp[fsp_id].subarrayMembership == (3, 4)

        # remove from a subarray
        test_proxies.fsp[fsp_id].RemoveSubarrayMembership(3)
        time.sleep(1)
        assert test_proxies.fsp[fsp_id].subarrayMembership == (4,)

        # add again...
        test_proxies.fsp[fsp_id].AddSubarrayMembership(15)
        time.sleep(1)
        assert test_proxies.fsp[fsp_id].subarrayMembership == (4, 15)

        # remove from all subarrays
        test_proxies.fsp[fsp_id].RemoveSubarrayMembership(4)
        test_proxies.fsp[fsp_id].RemoveSubarrayMembership(15)
        time.sleep(1)
        assert test_proxies.fsp[fsp_id].subarrayMembership == None
