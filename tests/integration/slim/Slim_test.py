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
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, HealthState, LoggingLevel
from tango import DevFailed, DevState

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

        for mesh in test_proxies.slim:
            # The Slim should be in the OFF state after being initialised
            mesh.loggingLevel = LoggingLevel.DEBUG
            mesh.adminMode = AdminMode.ONLINE

            test_proxies.wait_timeout_dev(
                [mesh], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert mesh.State() == DevState.OFF

    def test_On(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        """
        wait_time_s = 3
        sleep_time_s = 1

        # Turn on the LRUs and then the Slim devices
        for proxy in test_proxies.talon_lru:
            proxy.On()

        device_under_test = test_proxies.slim
        for mesh in device_under_test:
            mesh.On()
            test_proxies.wait_timeout_dev(
                [mesh], DevState.ON, wait_time_s, sleep_time_s
            )
            assert mesh.State() == DevState.ON

    def test_SlimTest_Before_Configure(
        self: TestSlim, test_proxies: pytest.fixture
    ) -> None:
        """
        Test the "SlimTest" command before the Mesh has been configured.
        Expects that a tango.DevFailed be caught

        :param test_proxies: the proxies test fixture
        """
        device_under_test = test_proxies.slim
        for mesh in device_under_test:
            with pytest.raises(
                DevFailed,
                match="The SLIM must be configured before SlimTest can be called",
            ):
                mesh.SlimTest()

    def test_Configure(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the "Configure" command

        :param test_proxies: the proxies test fixture
        """

        device_under_test = test_proxies.slim
        for mesh in device_under_test:
            with open(data_file_path + "slim_test_config.yaml", "r") as f:
                rc, msg = mesh.Configure(f.read())

            assert rc == ResultCode.OK
            for link in mesh.healthSummary:
                assert link == HealthState.OK

    def test_SlimTest_After_Configure(
        self: TestSlim, test_proxies: pytest.fixture
    ) -> None:
        """
        Test the "SlimTest" command after the Mesh has been configured.
        This should return a ResultCode.OK

        :param test_proxies: the proxies test fixture
        """
        device_under_test = test_proxies.slim
        for mesh in device_under_test:
            return_code, message = mesh.SlimTest()
            assert return_code == ResultCode.OK

    def test_Off(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the "Off" command

        :param test_proxies: the proxies test fixture
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.slim
        for mesh in device_under_test:
            mesh.Off()
            test_proxies.wait_timeout_dev(
                [mesh], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert mesh.State() == DevState.OFF

    def test_Disconnect(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.slim
        for mesh in device_under_test:
            assert mesh.State() == DevState.OFF

            # trigger stop_communicating by setting the AdminMode to OFFLINE
            mesh.adminMode = AdminMode.OFFLINE

            # controller device should be in disable state after stop_communicating
            test_proxies.wait_timeout_dev(
                [mesh], DevState.DISABLE, wait_time_s, sleep_time_s
            )
            assert mesh.State() == DevState.DISABLE

        # Stop monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.OFFLINE

        for proxy in test_proxies.talon_lru:
            proxy.Off()
            proxy.adminMode = AdminMode.OFFLINE
            proxy.set_timeout_millis(10000)
