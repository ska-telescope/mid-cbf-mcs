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

import os

# Standard imports
import time

import pytest
from ska_tango_base.control_model import AdminMode
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import FspModes

file_path = os.path.dirname(os.path.abspath(__file__))


# Tango imports

# Local imports


class TestFsp:
    """
    Test class for Fsp device class integration testing.
    """

    @pytest.mark.parametrize("fsp_id", [1])
    def test_Connect(
        self: TestFsp, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # after init devices should be in DISABLE state
        assert test_proxies.fsp[fsp_id].State() == DevState.DISABLE

        # trigger start_communicating by setting the AdminMode to ONLINE
        test_proxies.fsp[fsp_id].adminMode = AdminMode.ONLINE

        # fsp device should be in OFF state after start_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.fsp[fsp_id]], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.fsp[fsp_id].State() == DevState.OFF

    @pytest.mark.parametrize("fsp_id", [1])
    def test_On(
        self: TestFsp, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        """
        Test the "On" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # send the On command
        test_proxies.fsp[fsp_id].On()

        test_proxies.wait_timeout_dev(
            [test_proxies.fsp[fsp_id]], DevState.ON, wait_time_s, sleep_time_s
        )
        assert test_proxies.fsp[fsp_id].State() == DevState.ON

    @pytest.mark.parametrize("fsp_id", [1])
    def test_Off(
        self: TestFsp, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        """
        Test the "Off" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # send the Off command
        test_proxies.fsp[fsp_id].Off()

        test_proxies.wait_timeout_dev(
            [test_proxies.fsp[fsp_id]], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.fsp[fsp_id].State() == DevState.OFF

    @pytest.mark.parametrize("fsp_id", [1])
    def test_Standby(
        self: TestFsp, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        """
        Test the "Standby" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # send the Standby command
        test_proxies.fsp[fsp_id].Standby()

        test_proxies.wait_timeout_dev(
            [test_proxies.fsp[fsp_id]],
            DevState.STANDBY,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.fsp[fsp_id].State() == DevState.STANDBY

    @pytest.mark.parametrize("fsp_id", [1])
    def test_SetFunctionMode(
        self, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        """
        Test SetFunctionMode command state changes.
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        test_proxies.fsp[fsp_id].On()

        test_proxies.wait_timeout_dev(
            [test_proxies.fsp[fsp_id]], DevState.ON, wait_time_s, sleep_time_s
        )
        assert test_proxies.fsp[fsp_id].State() == DevState.ON

        # set function mode to CORR
        test_proxies.fsp[fsp_id].SetFunctionMode("CORR")
        time.sleep(1)
        function_mode = FspModes.CORR.value
        assert test_proxies.fsp[fsp_id].functionMode == function_mode

        # set function mode to PSS
        test_proxies.fsp[fsp_id].SetFunctionMode("PSS-BF")
        time.sleep(1)
        function_mode = FspModes.PSS_BF.value
        assert test_proxies.fsp[fsp_id].functionMode == function_mode

        # set function mode to PST
        test_proxies.fsp[fsp_id].SetFunctionMode("PST-BF")
        time.sleep(1)
        function_mode = FspModes.PST_BF.value
        assert test_proxies.fsp[fsp_id].functionMode == function_mode

        # set function mode to VLBI
        test_proxies.fsp[fsp_id].SetFunctionMode("VLBI")
        time.sleep(1)
        function_mode = FspModes.VLBI.value
        assert test_proxies.fsp[fsp_id].functionMode == function_mode

        # set function mode to IDLE
        test_proxies.fsp[fsp_id].SetFunctionMode("IDLE")
        time.sleep(1)
        function_mode = FspModes.IDLE.value
        assert test_proxies.fsp[fsp_id].functionMode == function_mode

    @pytest.mark.parametrize("fsp_id", [1])
    def test_AddRemoveSubarrayMembership(
        self, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        # subarray membership should be empty
        assert len(test_proxies.fsp[fsp_id].subarrayMembership) == 0

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
        assert len(test_proxies.fsp[fsp_id].subarrayMembership) == 0

    @pytest.mark.parametrize("fsp_id", [1])
    def test_Disconnect(
        self, test_proxies: pytest.fixture, fsp_id: int
    ) -> None:
        """
        Verify the component manager can stop communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        test_proxies.fsp[fsp_id].adminMode = AdminMode.OFFLINE

        # fsp device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.fsp[fsp_id]],
            DevState.DISABLE,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.fsp[fsp_id].State() == DevState.DISABLE
