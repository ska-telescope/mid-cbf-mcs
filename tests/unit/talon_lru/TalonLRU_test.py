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
import unittest
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
    ) -> None:
        """
        Tests that the state of the TalonLRU device when it starts up is correct.
        """
        # Trigger the mock start_communicating
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

    def test_On(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """
        # Trigger the mock start_communicating
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        # Send the long running command 'On'
        result_code, command_id  = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        # Assert the expected result, given the stimulus mode of the power switches.
        expected_result_map = {
            ("command_success", "command_success"): (ResultCode.OK, "LRU successfully turn on: both outlets successfully turned on", DevState.ON),
            ("command_fail", "command_fail"): (ResultCode.FAILED, "LRU failed to turned on: both outlets failed to turn on", None),
            ("command_success", "command_fail"): (ResultCode.OK, "LRU successfully turn on: one outlet successfully turned on", DevState.ON),
            ("command_fail", "command_success"): (ResultCode.OK, "LRU successfully turn on: one outlet successfully turned on", DevState.ON)
        }

        result_code, message, state = expected_result_map.get((power_switch_1.stimulusMode, power_switch_2.stimulusMode))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", f'[{result_code.value}, "{message}"]')
        )
        if state is not None:
            assert device_under_test.State() == state

        # Assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_Off(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """
        # Trigger the mock start_communicating
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

        # Send the Off command
        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        # Assert the expected result, given the stimulus mode of the power switches.
        result_map = {
            ("command_success", "command_success"): (ResultCode.OK, "LRU successfully turned off: both outlets turned off", DevState.OFF),
            ("command_fail", "command_fail"): (ResultCode.FAILED, "LRU failed to turned off: failed to turn off both outlets", None),
            ("command_success", "command_fail"): (ResultCode.FAILED, "LRU failed to turned off: only one outlet turned off", None),
            ("command_fail", "command_success"): (ResultCode.FAILED, "LRU failed to turned off: only one outlet turned off", None)
        }

        result_code, message, state = result_map.get((power_switch_1.stimulusMode, power_switch_2.stimulusMode))

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", f'[{result_code.value}, "{message}"]')
        )

        if state is not None:
            assert device_under_test.State() == state

        # Assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_OnOff(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Tests that the On command followed by the Off command works appropriately.
        """

        # Skip this test for certain configurations
        if (
            power_switch_1.stimulusMode == "command_fail"
            and power_switch_2.stimulusMode == "command_fail"
        ):
            pytest.skip(
                "Test sequence is not valid for this configuration of stimulus"
            )

        self.test_On(
            device_under_test,
            change_event_callbacks,
            power_switch_1,
            power_switch_2,
        )
        self.test_Off(
            device_under_test,
            change_event_callbacks,
            power_switch_1,
            power_switch_2,
        )
