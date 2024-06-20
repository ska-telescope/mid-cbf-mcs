#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for TalonBoard."""

from __future__ import annotations

# Standard imports
import gc
import os
from typing import Any, Iterator
from unittest.mock import Mock

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevFailed, DevState

from ska_mid_cbf_mcs.talon_board.talon_board_device import TalonBoard
from ska_mid_cbf_mcs.testing.mock.mock_dependency import MockDependency

# To prevent tests hanging during gc.
gc.disable()

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports


class TestTalonBoard:
    """
    Test class for TalonBoard tests.
    """

    @pytest.fixture(name="test_context")
    def talon_board_test_context(
        self: TestTalonBoard,
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
        initial_mocks: dict[str, Mock],
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        harness = context.ThreadedTestTangoContextManager()

        def mock_ping(self, **kwargs: Any) -> bool:
            """
            Replace requests.request method with a mock method.

            :param url: the URL
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.InfluxdbQueryClient(
                request.param["sim_ping_fault"],
            ).ping()

        def mock_do_queries(self) -> list[list]:
            """
            Replace requests.request method with a mock method.

            :param url: the URL
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.InfluxdbQueryClient().do_queries()

        monkeypatch.setattr(
            "ska_mid_cbf_mcs.talon_board.influxdb_query_client.InfluxdbQueryClient.ping",
            mock_ping,
        )
        monkeypatch.setattr(
            "ska_mid_cbf_mcs.talon_board.influxdb_query_client.InfluxdbQueryClient.do_queries",
            mock_do_queries,
        )

        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/talon_board/001",
            device_class=TalonBoard,
            TalonDxBoardAddress="192.168.8.1",
            InfluxDbPort="8086",
            InfluxDbOrg="ska",
            InfluxDbBucket="talon",
            InfluxDbAuthToken="test",
            Instance="talon1_test",
            TalonDxSysIdAddress=request.param["sim_sysid_property"],
            TalonDx100GEthernetAddress="talondx-001/ska-talondx-100-gigabit-ethernet/100g_eth",
            TalonStatusAddress="talondx-001/ska-talondx-status/status",
            HpsMasterAddress="talondx-001/hpsmaster/hps-1",
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_State(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_Status(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_adminMode(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_StartupState(
        self: TestTalonBoard,
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
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": None,
            },
        ],
        indirect=True,
    )
    def test_StartupState_missing_property(
        self: TestTalonBoard,
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
        assert device_under_test.State() == DevState.UNKNOWN

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_ping_fault": False,
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_On(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the On() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """

        self.test_StartupState(device_under_test)

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "On completed OK"]',
            )
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_ping_fault": False,
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_On_not_allowed(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the On() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """
        with pytest.raises(
            DevFailed, match="Communication with component is not established"
        ):
            device_under_test.On()

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_ping_fault": False,
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_On_already_on(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the On() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """

        self.test_StartupState(device_under_test)

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "On completed OK"]',
            )
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '"Command not allowed"',
            )
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_ping_fault": True,
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_On_ping_fail(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the On() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """

        self.test_StartupState(device_under_test)

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[3, "Failed to connect to InfluxDB"]',
            )
        )

        assert device_under_test.State() == DevState.FAULT

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_ping_fault": False,
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            }
        ],
        indirect=True,
    )
    def test_readWriteAttr(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the that all attr can be read/written correctly.
        """
        self.test_StartupState(device_under_test)
        # Device must be on in order to query InfluxDB
        self.test_On(device_under_test, change_event_callbacks)

        # Private Attr
        assert device_under_test.subarrayID == ""
        assert device_under_test.dishID == ""
        assert device_under_test.vccID == ""
        device_under_test.subarrayID = "1"
        device_under_test.dishID = "2"
        device_under_test.vccID = "3"
        assert device_under_test.subarrayID == "1"
        assert device_under_test.dishID == "2"
        assert device_under_test.vccID == "3"

        # All these values are read from mocked device attr
        # TalonStatus Attr
        assert device_under_test.ipAddr == "192.168.8.1"
        assert device_under_test.bitstreamVersion == "0.2.6"
        assert device_under_test.bitstreamChecksum == 0xBEEFBABE

        # TalonStatus Attr
        assert device_under_test.iopllLockedFault is False
        assert device_under_test.fsIopllLockedFault is False
        assert device_under_test.commsIopllLockedFault is False
        assert device_under_test.systemClkFault is False
        assert device_under_test.emifBlFault is False
        assert device_under_test.emifBrFault is False
        assert device_under_test.emifTrFault is False
        assert device_under_test.ethernet0PllFault is False
        assert device_under_test.ethernet1PllFault is False
        assert device_under_test.slimPllFault is False

        # All these values are read from InfluxDB
        assert device_under_test.fpgaDieTemperature == 32.0
        assert device_under_test.humiditySensorTemperature == 32.0
        assert all(temp == 32.0 for temp in device_under_test.dimmTemperatures)

        assert all(
            temp == 32.0 for temp in device_under_test.mboTxTemperatures
        )
        assert all(v == 3.3 for v in device_under_test.mboTxVccVoltages)
        # Not currently queried.
        # assert all(not fault for fault in device_under_test.mboTxFaultStatus)
        # assert all(not status for status in device_under_test.mboTxLolStatus)
        # assert all(not status for status in device_under_test.mboTxLosStatus)

        assert all(v == 3.3 for v in device_under_test.mboRxVccVoltages)
        # Not currently queried.
        # assert all(not status for status in device_under_test.mboRxLolStatus)
        # assert all(not status for status in device_under_test.mboRxLosStatus)

        assert all(pwm == 255 for pwm in device_under_test.fansPwm)
        # Not currently queried.
        # assert all(not enabled for enabled in device_under_test.fansPwmEnable)
        assert all(not fault for fault in device_under_test.fansFault)

        assert all(v == 10.0 for v in device_under_test.ltmInputVoltage)
        assert all(v == 10.0 for v in device_under_test.ltmOutputVoltage1)
        assert all(v == 10.0 for v in device_under_test.ltmOutputVoltage2)

        assert all(i == 1.0 for i in device_under_test.ltmInputCurrent)
        assert all(i == 1.0 for i in device_under_test.ltmOutputCurrent1)
        assert all(i == 1.0 for i in device_under_test.ltmOutputCurrent2)

        assert all(temp == 32.0 for temp in device_under_test.ltmTemperature1)
        assert all(temp == 32.0 for temp in device_under_test.ltmTemperature2)

        assert all(not warn for warn in device_under_test.ltmVoltageWarning)

        assert all(not warn for warn in device_under_test.ltmCurrentWarning)

        assert all(
            not warn for warn in device_under_test.ltmTemperatureWarning
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
