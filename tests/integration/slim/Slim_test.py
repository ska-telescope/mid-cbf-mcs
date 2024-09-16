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
from ska_control_model import SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, LoggingLevel
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

    def test_Online(
        self: TestSlim,
        device_under_test: pytest.fixture,
        test_proxies: pytest.fixture,
        change_event_callbacks: MockTangoEventCallbackGroup,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
        ps_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param device_under_test: the device under test
        :param test_proxies: a test fixture containing all subdevice proxies needed by the device under test.
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        :param lru_change_event_callbacks: a mock object that receives TalonLru's subscribed change events.
        :param ps_change_event_callbacks: a mock object that receives PowerSwitch's subscribed change events.
        """
        # after init devices should be in DISABLE state, but just in case...
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.loggingLevel = LoggingLevel.DEBUG

        # Start monitoring the TalonLRUs and power switch devices
        for ps in test_proxies.power_switch:
            ps.adminMode = AdminMode.ONLINE
            ps_change_event_callbacks["State"].assert_change_event(DevState.ON)

        for lru in test_proxies.talon_lru:
            lru.adminMode = AdminMode.ONLINE
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.OFF
            )

        device_under_test.adminMode = AdminMode.ONLINE
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        lru_change_event_callbacks.assert_not_called()
        ps_change_event_callbacks.assert_not_called()

    def test_On(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        test_proxies: pytest.fixture,
        change_event_callbacks: MockTangoEventCallbackGroup,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "On" command

        :param device_under_test: the device under test
        :param test_proxies: the proxies test fixture
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        :param lru_change_event_callbacks: a mock object that receives TalonLru's subscribed change events.
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
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.ON
            )

        device_under_test.On()
        change_event_callbacks["State"].assert_change_event(DevState.ON)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        lru_change_event_callbacks.assert_not_called()

    def test_SlimTest_Before_Configure(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test the "SlimTest" command before the Mesh has been configured.
        Expects IndexError to be caught when trying to read counters and rejects the command.

        :param device_under_test: the device under test
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

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        with open(data_file_path + "slim_test_config.yaml", "r") as f:
            result_code, command_id = device_under_test.Configure(f.read())

        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "Configure completed OK"]')
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_SlimTest_After_Configure(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the "SlimTest" command after the Mesh has been properly configured.
        This should return a ResultCode.OK

        :param device_under_test: the device under test
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

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "Off completed OK"]')
        )
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_Offline(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        test_proxies: pytest.fixture,
        change_event_callbacks: MockTangoEventCallbackGroup,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
        ps_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param device_under_test: the device under test
        :param test_proxies: a test fixture containing all subdevice proxies needed by the device under test.
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        :param lru_change_event_callbacks: a mock object that receives TalonLru's subscribed change events.
        :param ps_change_event_callbacks: a mock object that receives PowerSwitch's subscribed change events.
        """
        assert device_under_test.State() == DevState.OFF

        device_under_test.adminMode = AdminMode.OFFLINE
        change_event_callbacks["State"].assert_change_event(DevState.DISABLE)

        # Stop monitoring the TalonLRUs and power switch devices
        for lru in test_proxies.talon_lru:
            result_code, command_id = lru.Off()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "Off completed OK"]')
            )
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.OFF
            )

            lru.adminMode = AdminMode.OFFLINE
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.DISABLE
            )

        for ps in test_proxies.power_switch:
            ps.adminMode = AdminMode.OFFLINE
            ps_change_event_callbacks["State"].assert_change_event(
                DevState.DISABLE
            )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        lru_change_event_callbacks.assert_not_called()
        ps_change_event_callbacks.assert_not_called()
