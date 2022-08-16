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

import socket

import pytest

# Tango imports
from ska_tango_base.base.base_device import (
    _DEBUGGER_PORT,  # DeviceStateModel, removed in v0.11.3
)
from ska_tango_base.control_model import AdminMode
from tango import DevState

# Standard imports


# Local imports


@pytest.mark.usefixtures("test_proxies")
class TestCbfController:
    """
    Test class for CbfController device class integration testing.
    """

    @pytest.mark.skip(reason="enable to test DebugDevice")
    def test_DebugDevice(self, test_proxies):
        port = test_proxies.controller.DebugDevice()
        assert port == _DEBUGGER_PORT
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", _DEBUGGER_PORT))
        test_proxies.controller.On()

    def test_Connect(self, test_proxies):
        """
        Test the initial states and verify the component manager
        can start communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # after init devices should be in DISABLE state
        assert test_proxies.controller.State() == DevState.DISABLE
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.DISABLE
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert (
                        test_proxies.fspSubarray[i][j][k].State()
                        == DevState.DISABLE
                    )

        # trigger start_communicating by setting the AdminMode to ONLINE
        test_proxies.controller.adminMode = AdminMode.ONLINE

        # controller device should be in OFF state after start_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.controller.State() == DevState.OFF

    def test_On(self, test_proxies):
        """
        Test the "On" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # send the On command
        test_proxies.controller.On()

        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.ON, wait_time_s, sleep_time_s
        )
        assert test_proxies.controller.State() == DevState.ON

        # after init devices should be in DISABLE state
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].adminMode == AdminMode.ONLINE
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].adminMode == AdminMode.ONLINE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].adminMode == AdminMode.ONLINE
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert (
                        test_proxies.fspSubarray[i][j][k].adminMode
                        == AdminMode.ONLINE
                    )

        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.subarray[i]],
                DevState.ON,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[i].State() == DevState.ON

        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]], DevState.ON, wait_time_s, sleep_time_s
            )
            assert test_proxies.fsp[i].State() == DevState.ON

        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    test_proxies.wait_timeout_dev(
                        [test_proxies.fspSubarray[i][j][k]],
                        DevState.ON,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.fspSubarray[i][j][k].State()
                        == DevState.ON
                    )

        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]], DevState.ON, wait_time_s, sleep_time_s
            )
            assert test_proxies.vcc[i].State() == DevState.ON

    def test_Off(self, test_proxies):
        """
        Test the "Off" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # send the Off command
        test_proxies.controller.Off()

        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.controller.State() == DevState.OFF

        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.subarray[i]],
                DevState.OFF,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert test_proxies.vcc[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert test_proxies.fsp[i].State() == DevState.OFF

        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    test_proxies.wait_timeout_dev(
                        [test_proxies.fspSubarray[i][j][k]],
                        DevState.OFF,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.fspSubarray[i][j][k].State()
                        == DevState.OFF
                    )

    def test_Standby(self, test_proxies):
        """
        Test the "Standby" command
        """
        wait_time_s = 3
        sleep_time_s = 0.1

        # send the Standby command
        test_proxies.controller.Standby()

        test_proxies.wait_timeout_dev(
            [test_proxies.controller],
            DevState.STANDBY,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.controller.State() == DevState.STANDBY

        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]],
                DevState.STANDBY,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.vcc[i].State() == DevState.STANDBY

        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]],
                DevState.STANDBY,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.fsp[i].State() == DevState.STANDBY

    def test_Disconnect(self, test_proxies):
        """
        Verify the component manager can stop communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        test_proxies.controller.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.controller],
            DevState.DISABLE,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.controller.State() == DevState.DISABLE
        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.subarray[i]],
                DevState.DISABLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]],
                DevState.DISABLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.vcc[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]],
                DevState.DISABLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.fsp[i].State() == DevState.DISABLE
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    test_proxies.wait_timeout_dev(
                        [test_proxies.fspSubarray[i][j][k]],
                        DevState.DISABLE,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.fspSubarray[i][j][k].State()
                        == DevState.DISABLE
                    )
