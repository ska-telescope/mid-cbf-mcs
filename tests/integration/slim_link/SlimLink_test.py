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


class TestSlimLink:
    """
    Test class for Slim device class integration testing.
    """

    def test_Online(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        # after init devices should be in DISABLE state, but just in case...
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.loggingLevel = LoggingLevel.DEBUG

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE
        change_event_callbacks["State"].assert_change_event(DevState.ON)
        change_event_callbacks["healthState"].assert_change_event(
            HealthState.UNKNOWN
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_ConnectTxRx(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "ConnectTxRx" command

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        device_under_test.txDeviceName = "talondx/slim-tx-rx/tx-sim0"
        device_under_test.rxDeviceName = "talondx/slim-tx-rx/rx-sim0"
        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "ConnectTxRx completed OK"]')
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_VerifyConnection(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "VerifyConnection" method amd verify that the component manager can verify a link's health

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        assert (
            device_under_test.linkName
            == "talondx/slim-tx-rx/tx-sim0->talondx/slim-tx-rx/rx-sim0"
        )

        result_code, message = device_under_test.VerifyConnection()
        assert result_code == ResultCode.OK
        change_event_callbacks["healthState"].assert_change_event(
            HealthState.OK
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_DisconnectTxRx(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "DisconnectTxRx" command

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        result_code, command_id = device_under_test.DisconnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "DisconnectTxRx completed OK"]')
        )

        assert device_under_test.linkName == ""

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_Offline(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param device_under_test: the device under test
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        """
        device_under_test.adminMode = AdminMode.OFFLINE
        change_event_callbacks["State"].assert_change_event(DevState.DISABLE)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
