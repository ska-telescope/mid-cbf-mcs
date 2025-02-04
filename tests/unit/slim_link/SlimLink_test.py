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

import gc
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, HealthState, SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.slim.slim_link_device import SlimLink

from ... import test_utils

# Disable garbage collection to prevent tests hanging
gc.disable()

# Path
file_path = os.path.dirname(os.path.abspath(__file__))


class TestSlimLink:
    """
    Test class for SlimLink.
    """

    @pytest.fixture(name="test_context")
    def slim_link_test_context(
        self: TestSlimLink, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        A fixture that provides a test context for the SlimLink device.

        :param initial_mocks: A dictionary of initial mocks to be added to the test context.
        :return: A test context for the SlimLink device.
        """
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/fs_links/001",
            device_class=SlimLink,
            LRCTimeout="10",
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestSlimLink, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestSlimLink, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestSlimLink, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_Online(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test that the devState is appropriately set after device startup.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="adminMode",
            attribute_value=AdminMode.ONLINE,
        )
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.ON,
        )

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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the ConnectTxRx() command's happy path.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)
        device_under_test.txDeviceName = tx_device_name
        device_under_test.rxDeviceName = rx_device_name

        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "ConnectTxRx completed OK"]',
            ),
        )

        # Attr values are set in mocks in conftest.py
        assert device_under_test.txIdleCtrlWord == 123456
        assert (
            device_under_test.txIdleCtrlWord
            == device_under_test.rxIdleCtrlWord
        )

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_ConnectTxRx_not_allowed(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the ConnectTxRx() command before the device has been started up.

        :param tx_device_name: FQDN used to create a proxy to a (mocked) SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a (mocked) SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.txDeviceName = tx_device_name
        device_under_test.rxDeviceName = rx_device_name

        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    def test_ConnectTxRx_empty_device_names(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the ConnectTxRx() command when no Tx or Rx device names have been set.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[3, "DsSlimTxRx device names have not been set."]',
            ),
        )

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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the ConnectTxRx() command using a Tx mock that ommits the idle_ctrl_word
        attr to trigger ICW regeneration in the DUT.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)
        device_under_test.txDeviceName = tx_device_name
        device_under_test.rxDeviceName = rx_device_name

        result_code, command_id = device_under_test.ConnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "ConnectTxRx completed OK"]',
            ),
        )

        assert device_under_test.txIdleCtrlWord == (
            hash(device_under_test.txDeviceName) & 0x00FFFFFFFFFFFFFF
        )

        assert (
            device_under_test.txIdleCtrlWord
            == device_under_test.rxIdleCtrlWord
        )

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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test all attributes in the tango interface for readability/writability.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.txDeviceName = tx_device_name
        assert device_under_test.txDeviceName == tx_device_name

        device_under_test.rxDeviceName = rx_device_name
        assert device_under_test.rxDeviceName == rx_device_name

        self.test_ConnectTxRx(
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            device_under_test=device_under_test,
            event_tracer=event_tracer,
        )

        assert (
            device_under_test.linkName == f"{tx_device_name}->{rx_device_name}"
        )
        # Attr values are set in mocks in conftest.py
        assert device_under_test.txIdleCtrlWord == 123456
        assert device_under_test.rxIdleCtrlWord == 123456
        assert device_under_test.bitErrorRate == 8e-12
        counters = device_under_test.counters
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
    def test_VerifyConnection(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the VerifyConnection() command's happy path.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_ConnectTxRx(
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            device_under_test=device_under_test,
            event_tracer=event_tracer,
        )
        result, msg = device_under_test.VerifyConnection()
        assert [result, msg[0]] == [
            ResultCode.OK,
            "VerifyConnection completed OK",
        ]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="healthState",
            attribute_value=HealthState.OK,
        )

    def test_VerifyConnection_empty_device_names(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the VerifyConnection() command without assigning Tx/Rx device names (proxies will be None).

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_ConnectTxRx_empty_device_names(
            device_under_test, event_tracer
        )
        result, msg = device_under_test.VerifyConnection()
        assert [result, msg[0]] == [
            ResultCode.OK,
            "VerifyConnection completed OK",
        ]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="healthState",
            attribute_value=HealthState.UNKNOWN,
        )

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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the VerifyConnection() command with a mock that is set to fail health checks.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_ConnectTxRx(
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            device_under_test=device_under_test,
            event_tracer=event_tracer,
        )
        result, msg = device_under_test.VerifyConnection()
        assert [result, msg[0]] == [
            ResultCode.OK,
            "VerifyConnection completed OK",
        ]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="healthState",
            attribute_value=HealthState.FAILED,
        )

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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the DisconnectTxRx() command's happy path.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_ConnectTxRx(
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            device_under_test=device_under_test,
            event_tracer=event_tracer,
        )

        result_code, command_id = device_under_test.DisconnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "DisconnectTxRx completed OK"]',
            ),
        )
        assert device_under_test.linkName == ""

    @pytest.mark.parametrize(
        "tx_device_name, rx_device_name",
        [
            (
                "talon-x/slim-tx-rx/fs-tx0",
                "talon-x/slim-tx-rx/fs-rx0",
            ),
        ],
    )
    def test_DisconnectTxRx_not_allowed(
        self: TestSlimLink,
        tx_device_name: str,
        rx_device_name: str,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the DisconnectTxRx() command when the device was abruptly set offline after connecting.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_ConnectTxRx(
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            device_under_test=device_under_test,
            event_tracer=event_tracer,
        )

        device_under_test.adminMode = AdminMode.OFFLINE

        result_code, command_id = device_under_test.DisconnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    def test_DisconnectTxRx_empty_device_names(
        self: TestSlimLink,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the DisconnectTxRx() command without connecting first.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        result_code, command_id = device_under_test.DisconnectTxRx()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[3, "Rx proxy is not set. SlimLink must be connected before it can be disconnected."]',
            ),
        )

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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the ClearCounters() command's happy path.

        :param tx_device_name: FQDN used to create a proxy to a SlimTx device.
        :param rx_device_name: FQDN used to create a proxy to a SlimRx device.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_ConnectTxRx(
            tx_device_name=tx_device_name,
            rx_device_name=rx_device_name,
            device_under_test=device_under_test,
            event_tracer=event_tracer,
        )
        counters = device_under_test.counters
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
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the ClearCounters() command

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)
        result, msg = device_under_test.ClearCounters()
        assert [result, msg[0]] == [
            ResultCode.OK,
            "ClearCounters completed OK",
        ]
