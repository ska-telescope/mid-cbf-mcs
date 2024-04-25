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
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_control_model import HealthState, SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.slim.slim_link_device import SlimLink
from ska_mid_cbf_mcs.testing import context

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
        self: TestSlimLink, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        harness.add_device(
            device_name="mid_csp_cbf/fs_links/001",
            device_class=SlimLink,
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

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

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_AttrReadWrite(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test all attributes in the tango interface for readability/writability.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
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
        assert (
            device_under_test.linkName == f"{tx_device_name}->{rx_device_name}"
        )
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

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
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

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "ConnectTxRx completed OK"]',
            )
        )

        assert device_under_test.txIdleCtrlWord == 123456
        assert (
            device_under_test.txIdleCtrlWord
            == device_under_test.rxIdleCtrlWord
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_ConnectTxRx_empty_device_names(
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
                '[3, "DsSlimTxRx device names have not been set."]',
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
    def test_ConnectTxRx_regenerate_idle_ctrl_word(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the ConnectTxRx() command using a Tx mock that has no idle_ctrl_word
        attr set in order to trigger ICW regeneration in the DUT

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
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

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "ConnectTxRx completed OK"]',
            )
        )

        assert device_under_test.txIdleCtrlWord == (
            hash(device_under_test.txDeviceName) & 0x00FFFFFFFFFFFFFF
        )
        assert (
            device_under_test.txIdleCtrlWord
            == device_under_test.rxIdleCtrlWord
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
        assert [result, msg[0]] == [
            ResultCode.OK,
            "VerifyConnection completed OK",
        ]
        assert device_under_test.healthState == HealthState.OK

    def test_VerifyConnection_empty_device_names(
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
        self.test_ConnectTxRx_empty_device_names(
            device_under_test, change_event_callbacks
        )
        result, msg = device_under_test.VerifyConnection()
        assert [result, msg[0]] == [
            ResultCode.OK,
            "VerifyConnection completed OK",
        ]
        assert device_under_test.healthState == HealthState.UNKNOWN

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx1",
            ),
        ],
    )
    def test_VerifyConnection_unhealthy_link(
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
        assert [result, msg[0]] == [
            ResultCode.OK,
            "VerifyConnection completed OK",
        ]
        assert device_under_test.healthState == HealthState.FAILED

    # Test case: verify connection but unsync ICW before issuing command. will fail 1st health check
    # I think this would have to be an integration test since it requires writing to a SlimTxRx attr.
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

    # Integration test case: set TxRx proxy to None at some point in the try block to invoke a DevFailed exception.

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

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "DisconnectTxRx completed OK"]',
            )
        )
        assert device_under_test.linkName == ""

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_DisconnectTxRx_empty_device_names(
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
                '[3, "Rx proxy is not set. SlimLink must be connected before it can be disconnected."]',
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
        assert [result, msg[0]] == [
            ResultCode.OK,
            "ClearCounters completed OK",
        ]

    def test_ClearCounters_empty_device_names(
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
        assert [result, msg[0]] == [
            ResultCode.OK,
            "ClearCounters completed OK",
        ]
