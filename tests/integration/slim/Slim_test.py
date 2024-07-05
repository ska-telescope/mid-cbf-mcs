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

    def test_Connect(self: TestSlim, test_proxies: pytest.fixture) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param test_proxies: the proxies test fixture
        """
        # Start monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.simulationMode = SimulationMode.TRUE
            proxy.adminMode = AdminMode.ONLINE
            assert proxy.State() == DevState.ON

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.ONLINE
            time.sleep(0.1)
            assert proxy.State() == DevState.OFF

        for mesh in test_proxies.slim:
            mesh.simulationMode = SimulationMode.TRUE
            mesh.loggingLevel = LoggingLevel.DEBUG
            mesh.adminMode = AdminMode.ONLINE
            assert mesh.State() == DevState.OFF

    def test_On(
        self: TestSlim,
        device_under_test: list[pytest.fixture],
        lru_proxies: list[pytest.fixture],
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        """
        # Turn on the LRUs and then the Slim devices
        for proxy in lru_proxies:
            result_code, command_id = proxy.On()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "On completed OK"]')
            )

        for mesh in device_under_test:
            mesh.On()
            assert mesh.State() == DevState.ON

    def test_SlimTest_Before_Configure(
        self: TestSlim,
        device_under_test: list[pytest.fixture],
    ) -> None:
        """
        Test the "SlimTest" command before the Mesh has been configured.
        Expects that a IndexError be caught when trying to read counters.

        :param test_proxies: the proxies test fixture
        """
        for mesh in device_under_test:
            rc, message = mesh.SlimTest()

            # SlimTest's is_allowed should reject the command
            # since it was issued before configuration
            assert rc == ResultCode.REJECTED

    def test_Configure(
        self: TestSlim,
        device_under_test: list[pytest.fixture],
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "Configure" command

        :param test_proxies: the proxies test fixture
        """

        for mesh in device_under_test:
            with open(data_file_path + "slim_test_config.yaml", "r") as f:
                result_code, command_id = mesh.Configure(f.read())

            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
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
        self: TestSlim, device_under_test: list[pytest.fixture]
    ) -> None:
        """
        Test the "SlimTest" command after the Mesh has been configured.
        This should return a ResultCode.OK

        :param test_proxies: the proxies test fixture
        """
        for mesh in device_under_test:
            return_code, message = mesh.SlimTest()
            assert return_code == ResultCode.OK

    def test_Off(
        self: TestSlim,
        device_under_test: list[pytest.fixture],
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "Off" command

        :param test_proxies: the proxies test fixture
        """
        for mesh in device_under_test:
            result_code, command_id = mesh.Off()
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "Off completed OK"]')
            )

    def test_Disconnect(
        self: TestSlim,
        device_under_test: list[pytest.fixture],
        lru_proxies: list[pytest.fixture],
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
        test_proxies: pytest.fixture,
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        """
        for mesh in device_under_test:
            assert mesh.State() == DevState.OFF

            # trigger stop_communicating by setting the AdminMode to OFFLINE
            mesh.adminMode = AdminMode.OFFLINE
            assert mesh.State() == DevState.DISABLE

        # Stop monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.OFFLINE
            assert proxy.State() == DevState.DISABLE

        for proxy in lru_proxies:
            result_code, command_id = proxy.Off()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "Off completed OK"]')
            )
            proxy.adminMode = AdminMode.OFFLINE
            assert proxy.State() == DevState.DISABLE
