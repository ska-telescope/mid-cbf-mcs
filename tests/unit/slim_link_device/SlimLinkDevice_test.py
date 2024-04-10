#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the SlimLink."""

from __future__ import annotations

# Standard imports
import os
import time

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, SimulationMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

from ... import test_utils

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports

CONST_WAIT_TIME = 0.5


class TestSlimLink:
    """
    Test class for SlimLink tests.
    """

    def test_State(
        self: TestSlimLink, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestSlimLink, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestSlimLink, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_adminModeOnline(
        self: TestSlimLink,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.UNKNOWN

    def test_ConnectTxRx(
        self: TestSlimLink,
        device_under_test: tango.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the ConnectTxRx() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        # Put the device in simulation mode
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.adminMode = AdminMode.ONLINE

        change_event_attr_list = [
            "longRunningCommandResult",
            "longRunningCommandProgress",
        ]
        attr_event_ids = test_utils.change_event_subscriber(
            device_under_test, change_event_callbacks, change_event_attr_list
        )
        device_under_test.txDeviceName = "test_tx"
        device_under_test.rxDeviceName = "test_rx"
        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]
        for progress_point in (10, 20, 30, 60, 80, 100):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", f"{progress_point}"))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", f'[0, "Connection to {device_under_test.linkName} (simulator) successful"]')
        )

    def test_VerifyConnection(
        self: TestSlimLink,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test the VerifyConnection() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        result = device_under_test.VerifyConnection()
        assert result[0][0] == ResultCode.OK

    def test_DisconnectTxRx(
        self: TestSlimLink,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test the DisconnectTxRx() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        result = device_under_test.DisconnectTxRx()
        assert result[0][0] == ResultCode.OK

    def test_ClearCounters(
        self: TestSlimLink,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test the ClearCounters() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        result = device_under_test.ClearCounters()
        assert result[0][0] == ResultCode.OK
