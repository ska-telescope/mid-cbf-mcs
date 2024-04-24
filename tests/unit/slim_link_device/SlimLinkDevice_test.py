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
from ska_control_model import HealthState, SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.slim.slim_link_component_manager import BER_PASS_THRESHOLD
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
        mock_slim_rx_unhealthy: unittest.mock.Mock,
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/fs_links/001",
            device_class=SlimLink,
        )
        harness.add_mock_device(
            "talon-x/slim-tx-rx/fs-tx0",
            mock_slim_tx,
        )
        harness.add_mock_device(
            "talon-x/slim-tx-rx/fs-tx1",
            mock_slim_tx_regenerate,
        )
        harness.add_mock_device(
            "talon-x/slim-tx-rx/fs-rx0",
            mock_slim_rx,
        )
        harness.add_mock_device(
            "talon-x/slim-tx-rx/fs-rx1",
            mock_slim_rx_unhealthy,
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
        assert device_under_test.State() == DevState.ON
        
    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_attrReadWrite(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        
        device_under_test.txDeviceName = tx_device_name
        assert device_under_test.txDeviceName == tx_device_name
        
        device_under_test.rxDeviceName = rx_device_name
        assert device_under_test.rxDeviceName == rx_device_name
        
        self.test_ConnectTxRx(
            device_under_test=device_under_test,
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            change_event_callbacks=change_event_callbacks,
        )
        assert device_under_test.linkName == f"{tx_device_name}->{rx_device_name}"
        assert device_under_test.txIdleCtrlWord == 123456
        assert device_under_test.rxIdleCtrlWord == 123456
        assert device_under_test.bitErrorRate == 8e-12
        counters = device_under_test.read_counters
        for ind, val in enumerate([0, 1, 2, 3, 0, 0, 6, 7, 8]):
            assert counters[ind] == val
        

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_ConnectTxRx(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
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
        device_under_test.txDeviceName = tx_device_name
        device_under_test.rxDeviceName = rx_device_name
        device_under_test.simulationMode = SimulationMode.FALSE

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

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx1",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_ConnectTxRxRegenerateICW(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
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
        device_under_test.txDeviceName = tx_device_name
        device_under_test.rxDeviceName = rx_device_name
        device_under_test.simulationMode = SimulationMode.FALSE

        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.txIdleCtrlWord == (
            hash(device_under_test.txDeviceName) & 0x00FFFFFFFFFFFFFF
        )
        assert (
            device_under_test.txIdleCtrlWord
            == device_under_test.rxIdleCtrlWord
        )

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

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_VerifyConnection(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the VerifyConnection() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_ConnectTxRx(
            device_under_test=device_under_test,
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            change_event_callbacks=change_event_callbacks,
        )
        result, msg = device_under_test.VerifyConnection()
        assert result == ResultCode.OK
        assert device_under_test.healthState == HealthState.OK
        assert msg[0] == f"Link health check OK: {device_under_test.linkName}"

    def test_VerifyConnectionEmptyDeviceNames(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the VerifyConnection() command without assigning Tx/Rx device names (proxies will be None).

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_ConnectTxRxEmptyDeviceNames(
            device_under_test, change_event_callbacks
        )
        result, msg = device_under_test.VerifyConnection()
        assert result == ResultCode.OK
        assert device_under_test.healthState == HealthState.UNKNOWN
        assert msg[0] == "Tx and Rx devices have not been connected."

    ## Test case: verify connection using rx1 mock. Will fail last 3 health checks
    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx1",
            ),
        ],
    )
    def test_VerifyConnectionUnhealthy(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the VerifyConnection() command with a mock set to fail health checks.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_ConnectTxRx(
            device_under_test=device_under_test,
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            change_event_callbacks=change_event_callbacks,
        )
        result, msg = device_under_test.VerifyConnection()
        assert result == ResultCode.OK
        assert device_under_test.healthState == HealthState.FAILED
        assert (
            msg[0]
            == f"block_lost_count not zero. cdr_lost_count not zero. bit-error-rate higher than {BER_PASS_THRESHOLD}. "
        )

    ## Test case: verify connection but unsync ICW before issuing command. will fail 1st health check
    ## I think this would have to be an integration test since it requires writing to a SlimTxRx attr.
    # @pytest.mark.parametrize(
    #     "tx_device_name, rx_device_name",
    #     [
    #         (
    #             "talon-x/slim-tx-rx/fs-tx0",
    #             "talon-x/slim-tx-rx/fs-rx0",
    #         ),
    #     ],
    # )
    # def test_VerifyConnectionUnhealthyICW(
    #     self: TestSlimLink,
    #     tx_device_name: str,
    #     rx_device_name: str,
    #     device_under_test: context.DeviceProxy,
    #     change_event_callbacks: MockTangoEventCallbackGroup,
    # ) -> None:
    #     """
    #     Test the VerifyConnection() command

    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     """
    #     self.test_ConnectTxRx(
    #         device_under_test=device_under_test,
    #         tx_device_name=tx_device_name,
    #         rx_device_name=rx_device_name,
    #         change_event_callbacks=change_event_callbacks,
    #     )
    #     device_under_test._rx_device_proxy.idle_ctrl_word = 987654
    #     result, msg = device_under_test.VerifyConnection()
    #     assert result == ResultCode.OK
    #     assert device_under_test.healthState == HealthState.FAILED
    #     assert msg[0] == "Expected and received idle control word do not match. "

    ## Integration test case: set TxRx proxy to None at some point in the try block to invoke a DevFailed exception.

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_DisconnectTxRx(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the DisconnectTxRx() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_ConnectTxRx(
            device_under_test=device_under_test,
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            change_event_callbacks=change_event_callbacks,
        )

        result_code, command_id = device_under_test.DisconnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        for progress_point in ("20", "40", "60", "80", "100"):
            change_event_callbacks[
                "longRunningCommandProgress"
            ].assert_change_event((f"{command_id[0]}", progress_point))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[0, "Disonnected Tx Rx. {device_under_test.rxDeviceName} now in serial loopback."]',
            )
        )
        assert device_under_test.linkName == ""

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_DisconnectTxRxEmptyDeviceNames(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the DisconnectTxRx() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_adminModeOnline(device_under_test)
        device_under_test.simulationMode = SimulationMode.FALSE

        result_code, command_id = device_under_test.DisconnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[3, "Rx proxy is not set. SlimLink must be connected before it can be disconnected."]',
            )
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_ClearCounters(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the ClearCounters() command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        self.test_ConnectTxRx(
            device_under_test=device_under_test,
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            change_event_callbacks=change_event_callbacks,
        )
        counters = device_under_test.read_counters
        for ind, val in enumerate([0, 1, 2, 3, 0, 0, 6, 7, 8]):
            assert counters[ind] == val
        result, msg = device_under_test.ClearCounters()
        assert result == ResultCode.OK
        assert msg[0] == f"Counters cleared: {device_under_test.linkName}"

    def test_ClearCountersEmptyDeviceNames(
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
        device_under_test.simulationMode = SimulationMode.FALSE
        result, msg = device_under_test.ClearCounters()
        assert result == ResultCode.OK
        assert msg[0] == "Tx and Rx devices have not been connected."
