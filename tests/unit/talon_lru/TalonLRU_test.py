#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the TalonLRU."""

from __future__ import annotations

import time
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.talon_lru.talon_lru_device import TalonLRU
from ska_mid_cbf_mcs.testing import context

CONST_WAIT_TIME = 2


class TestTalonLRU:
    """
    Test class for the TalonLRU
    """

    @pytest.fixture(name="test_context")
    def talon_lru_test_context(
        self: TestTalonLRU, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        harness.add_device(
            device_class=TalonLRU,
            device_name="mid_csp_cbf/talon_lru/001",
            TalonDxBoard1="001",
            TalonDxBoard2="002",
            PDU1="002",
            PDU1PowerOutlet="AA41",
            PDU2="002",
            PDU2PowerOutlet="AA41",
            PDUCommandTimeout="20",
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestTalonLRU, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestTalonLRU, device_under_test: context.DeviceProxy
    ) -> None:
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestTalonLRU, device_under_test: context.DeviceProxy
    ) -> None:
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_startup_state(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        power_switch_1: context.DeviceProxy,
        power_switch_2: context.DeviceProxy,
    ) -> None:
        """
        Tests that the state of the TalonLRU device when it starts up is correct.
        """
        assert device_under_test.State() == DevState.DISABLE

        # Trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        # Check the device state based on the mock power switch behaviour
        if (
            power_switch_1.stimulusMode == "conn_fail"
            or power_switch_2.stimulusMode == "conn_fail"
        ):
            assert device_under_test.State() == DevState.UNKNOWN
        else:
            assert device_under_test.State() == DevState.OFF

    def test_On(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        power_switch_1: context.DeviceProxy,
        power_switch_2: context.DeviceProxy,
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """
        # Skip this test for stimulus modes that are not valid
        if (
            power_switch_1.stimulusMode == "conn_fail"
            or power_switch_2.stimulusMode == "conn_fail"
        ):
            pytest.skip(
                "TalonLRU device is not in a valid startup state for this test"
            )

        # Trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        # Send the long running command 'On'
        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        # Assert the expected result, given the stimulus mode of the power switches.
        if (
            power_switch_1.stimulusMode == "conn_success"
            and power_switch_2.stimulusMode == "conn_success"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK}, "LRU successfully turn on: both outlets successfully turned on"]',
                )
            )
            assert device_under_test.State() == DevState.ON
        elif (
            power_switch_1.stimulusMode == "command_fail"
            and power_switch_2.stimulusMode == "command_fail"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.FAILED}, "LRU failed to turned on: both oulets failed to turn on]',
                )
            )
            assert device_under_test.State() == DevState.FAULT
        else:
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK}, "LRU successfully turn on: one outlet successfully turned on"]',
                )
            )
            assert device_under_test.State() == DevState.ON

        # Assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_Off(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        power_switch_1: context.DeviceProxy,
        power_switch_2: context.DeviceProxy,
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """

        # Skip this test for stimulus modes that are not valid
        if (
            power_switch_1.stimulusMode == "conn_fail"
            or power_switch_2.stimulusMode == "conn_fail"
        ):
            pytest.skip(
                "TalonLRU device is not in a valid startup state for this test"
            )

        # Trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        # Send the Off command
        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        # Check that the state updates correctly when the device callbacks are called
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f'[{ResultCode.OK}, "Configure completed OK"]',
            )
        )

        # Assert the expected result, given the stimulus mode of the power switches.
        if (
            power_switch_1.stimulusMode == "conn_success"
            and power_switch_2.stimulusMode == "conn_success"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK}, "LRU successfully turned off: both outlets turned off"]',
                )
            )
            assert device_under_test.State() == DevState.ON
        elif (
            power_switch_1.stimulusMode == "command_fail"
            and power_switch_2.stimulusMode == "command_fail"
        ):
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.FAILED}, "LRU failed to turned off: failed to turn off both outlets"]',
                )
            )
            assert device_under_test.State() == DevState.FAULT
        else:
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.FAILED}, "LRU failed to turned off: only one outlet turned off"]',
                )
            )
            assert device_under_test.State() == DevState.FAULT

        # Assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_OnOff(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        mock_power_switch1: context.DeviceProxy,
        mock_power_switch2: context.DeviceProxy,
    ) -> None:
        """
        Tests that the On command followed by the Off command works appropriately.
        """

        # Skip this test for certain configurations
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            pytest.skip(
                "Test sequence is not valid for this configuration of stimulus"
            )

        self.test_On(
            device_under_test,
            change_event_callbacks,
            mock_power_switch1,
            mock_power_switch2,
        )
        self.test_Off(
            device_under_test,
            change_event_callbacks,
            mock_power_switch1,
            mock_power_switch2,
        )
