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
import unittest
import unittest.mock
from typing import Iterator

import pytest
from ska_control_model import SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode

from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.slim.slim_link_device import SlimLink
from ska_mid_cbf_mcs.testing import context

from ... import test_utils

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports

CONST_WAIT_TIME = 1


class TestSlimLink:
    """
    Test class for SlimLink tests.
    """
    
    @pytest.fixture(name="test_context")
    def slim_link_test_context(
        self: TestSlimLink,
        mock_slim_tx: unittest.mock.Mock,
        mock_slim_tx_regenerate: unittest.mock.Mock,
        mock_slim_rx: unittest.mock.Mock,
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/fs_links/001",
            device_class=SlimLink,
        )
        harness.add_mock_device(
            "talon_x/slim_tx_rx/tx0",
            mock_slim_tx,
        )
        harness.add_mock_device(
            "talon_x/slim_tx_rx/tx1",
            mock_slim_tx_regenerate,
        )
        harness.add_mock_device(
            "talon_x/slim_tx_rx/rx0",
            mock_slim_rx,
        )

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestSlimLink, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestSlimLink, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestSlimLink, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_adminModeOnline(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

    def test_ConnectTxRx(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the ConnectTxRx() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        device_under_test.txDeviceName = "talon_x/slim_tx_rx/tx0"
        device_under_test.rxDeviceName = "talon_x/slim_tx_rx/rx0"
        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE
        
        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]
        
        for progress_point in ("10", "20", "30", "60", "80", "100"):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", progress_point))
            
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[0, "Connected Tx Rx successfully: {device_under_test.linkName}"]',
            )
        )
        
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        
    def test_ConnectTxRxEmptyDeviceNames(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the ConnectTxRx() command when no Tx or Rx device names have been set.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE
        
        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]
            
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[3, "Tx or Rx device FQDN have not been set."]',
            )
        )
        
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        
    def test_ConnectTxRxRegenerateICW(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the ConnectTxRx() command using a Tx mock that has no idle_ctrl_word 
        attr set in order to trigger ICW regeneration in the DUT

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        device_under_test.txDeviceName = "talon_x/slim_tx_rx/tx1"
        device_under_test.rxDeviceName = "talon_x/slim_tx_rx/rx0"
        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE
        
        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.txIdleCtrlWord == (hash(device_under_test.txDeviceName) & 0x00FFFFFFFFFFFFFF)
        assert device_under_test.txIdleCtrlWord == device_under_test.rxIdleCtrlWord
        
        for progress_point in ("10", "20", "30", "60", "80", "100"):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", progress_point))
            
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[0, "Connected Tx Rx successfully: {device_under_test.linkName}"]',
            )
        )
        
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_VerifyConnection(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
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
        device_under_test: context.DeviceProxy,
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
        device_under_test: context.DeviceProxy,
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
