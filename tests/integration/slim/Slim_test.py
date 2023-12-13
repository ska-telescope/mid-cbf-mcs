#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Slim."""
from __future__ import annotations

import os

import pytest
from ska_tango_base.control_model import AdminMode, LoggingLevel
from tango import DevState

# Standard imports

# Path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# Tango imports

# SKA specific imports


class TestSlim:
    """
    Test class for Slim device class integration testing.
    """

    def test_Connect(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param test_proxies: the proxies test fixture
        """
        wait_time_s = 3
        sleep_time_s = 1

        # Start monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.ONLINE

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.ONLINE
            proxy.set_timeout_millis(10000)

        # The Slim should be in the OFF state after being initialised
        test_proxies.slim.loggingLevel = LoggingLevel.DEBUG
        test_proxies.slim.adminMode = AdminMode.ONLINE

        test_proxies.wait_timeout_dev(
            [test_proxies.slim], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.slim.State() == DevState.OFF

    def test_On(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        """
        wait_time_s = 3
        sleep_time_s = 1

        device_under_test = test_proxies.slim

        # Turn on the LRUs and then the Slim devices
        for proxy in test_proxies.talon_lru:
            proxy.On()
        device_under_test.On()
        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.ON, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.ON

    def test_Off(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the "Off" command

        :param test_proxies: the proxies test fixture
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.slim

        device_under_test.Off()

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.OFF

    def test_Disconnect(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = device_under_test = test_proxies.slim

        device_under_test.Off()

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.DISABLE, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.DISABLE

        # Stop monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.OFFLINE

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.OFFLINE
            proxy.set_timeout_millis(10000)
