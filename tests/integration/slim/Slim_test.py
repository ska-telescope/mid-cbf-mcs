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
import time

import pytest
from ska_control_model import SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, HealthState, LoggingLevel
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
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

    def test_Connect(
        self: TestSlim,
        device_under_test: pytest.fixture,
        test_proxies: pytest.fixture,
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param test_proxies: the proxies test fixture
        """
        # Start monitoring the TalonLRUs and power switch devices
        for ps in test_proxies.power_switch:
            ps.simulationMode = SimulationMode.TRUE
            ps.adminMode = AdminMode.ONLINE
            assert ps.State() == DevState.ON

        for lru in test_proxies.talon_lru:
            lru.adminMode = AdminMode.ONLINE
            time.sleep(0.2)
            assert lru.State() == DevState.OFF

        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.loggingLevel = LoggingLevel.DEBUG
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

    def test_On(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        test_proxies: pytest.fixture,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        """
        # Turn on the LRUs and then the Slim devices
        for lru in test_proxies.talon_lru:
            result_code, command_id = lru.On()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "On completed OK"]')
            )

        device_under_test.On()
        assert device_under_test.State() == DevState.ON

    def test_SlimTest_Before_Configure(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test the "SlimTest" command before the Mesh has been configured.
        Expects that a IndexError be caught when trying to read counters.

        :param test_proxies: the proxies test fixture
        """
        rc, message = device_under_test.SlimTest()

        # SlimTest's is_allowed should reject the command
        # since it was issued before configuration
        assert rc == ResultCode.REJECTED

    def test_Configure(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "Configure" command

        :param test_proxies: the proxies test fixture
        """
        with open(data_file_path + "slim_test_config.yaml", "r") as f:
            result_code, command_id = device_under_test.Configure(f.read())

        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "Configure completed OK"]')
        )

        # TBD what change event calls should happen, would need the SlimLink simulator
        # to push events if we want it to properly model the real world system.
        change_event_callbacks["healthState"].assert_change_event(
            HealthState.UNKNOWN
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_SlimTest_After_Configure(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the "SlimTest" command after the Mesh has been configured.
        This should return a ResultCode.OK

        :param test_proxies: the proxies test fixture
        """
        return_code, message = device_under_test.SlimTest()
        assert return_code == ResultCode.OK

    def test_Off(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "Off" command

        :param test_proxies: the proxies test fixture
        """
        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "Off completed OK"]')
        )

    def test_Disconnect(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        test_proxies: pytest.fixture,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        """
        assert device_under_test.State() == DevState.OFF

        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE

        # Stop monitoring the TalonLRUs and power switch devices
        for ps in test_proxies.power_switch:
            ps.adminMode = AdminMode.OFFLINE
            assert ps.State() == DevState.DISABLE

        for lru in test_proxies.talon_lru:
            result_code, command_id = lru.Off()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "Off completed OK"]')
            )
            lru.adminMode = AdminMode.OFFLINE
            assert lru.State() == DevState.DISABLE
