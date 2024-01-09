#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the SlimLink."""
from __future__ import annotations

import os
from time import sleep

import pytest
from ska_tango_base.control_model import AdminMode, HealthState, LoggingLevel
from tango import DevState

# Standard imports

# Path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# Tango imports

# SKA specific imports


class TestSlimLink:
    """
    Test class for Slim device class integration testing.
    """

    def test_Connect(self: TestSlimLink, test_proxies: pytest.fixture) -> None:
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

        device_under_test = test_proxies.slim_link

        # The Slim should be in the UNKNOWN state after being initialised
        for link in device_under_test:
            link.loggingLevel = LoggingLevel.DEBUG
            link.adminMode = AdminMode.ONLINE

            test_proxies.wait_timeout_dev(
                [link], DevState.UNKNOWN, wait_time_s, sleep_time_s
            )
            assert link.State() == DevState.UNKNOWN

    def test_Disconnect(
        self: TestSlimLink, test_proxies: pytest.fixture
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.slim_link

        for link in device_under_test:
            # trigger stop_communicating by setting the AdminMode to OFFLINE
            link.adminMode = AdminMode.OFFLINE

            # controller device should be in DISABLE state after stop_communicating
            test_proxies.wait_timeout_dev(
                [link], DevState.DISABLE, wait_time_s, sleep_time_s
            )
            assert link.State() == DevState.DISABLE

        # Stop monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.OFFLINE

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.OFFLINE
            proxy.set_timeout_millis(10000)

    def test_VerifyConnection(
        self: TestSlimLink, test_proxies: pytest.fixture
    ) -> None:
        """
        Verify the component manager can verify a link's health

        :param test_proxies: the proxies test fixture
        """

        sleep_time_s = 0.1

        device_under_test = test_proxies.slim_link

        for idx, link in enumerate(device_under_test):
            link.txDeviceName = "talondx/slim-tx-rx/tx-sim" + str(idx)
            link.rxDeviceName = "talondx/slim-tx-rx/rx-sim" + str(idx)
            link.ConnectTxRx()
            sleep(sleep_time_s)
            link.VerifyConnection()
            assert link.healthState == HealthState.OK
