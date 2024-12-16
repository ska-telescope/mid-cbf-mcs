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

import gc
import unittest
from typing import Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_tdc_mcs.talon_lru.talon_lru_device import TalonLRU

from ... import test_utils

# To prevent tests hanging during gc.
gc.disable()


class TestTalonLRU:
    """
    Test class for the TalonLRU.
    """

    @pytest.fixture(name="test_context")
    def talon_lru_test_context(
        self: TestTalonLRU,
        initial_mocks: dict[str, Mock],
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that creates a test context for the TalonLRU device.

        :param initial_mocks: A dictionary of initial mocks to be added to the test context.
        :return: A test context for the TalonLRU device.
        """
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_class=TalonLRU,
            device_name="mid_csp_cbf/talon_lru/001",
            TalonDxBoard1="001",
            TalonDxBoard2="002",
            PDU1="001",
            PDU1PowerOutlet="AA41",
            PDU2="002",
            PDU2PowerOutlet="AA41",
            LRCTimeout="20",
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        :param power_switch_1: A mock power switch device.
        :param power_switch_2: A mock power switch device.
        """
        if (
            power_switch_1.stimulusMode == "command_success"
            and power_switch_2.stimulusMode == "command_success"
        ):
            pass
        else:
            pytest.skip(
                "Redundant test case: Parameters do not affect this test"
            )

        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        :param power_switch_1: A mock power switch device.
        :param power_switch_2: A mock power switch device.
        """
        if (
            power_switch_1.stimulusMode == "command_success"
            and power_switch_2.stimulusMode == "command_success"
        ):
            pass
        else:
            pytest.skip(
                "Redundant test case: Parameters do not affect this test"
            )

        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        :param power_switch_1: A mock power switch device.
        :param power_switch_2: A mock power switch device.
        """
        if (
            power_switch_1.stimulusMode == "command_success"
            and power_switch_2.stimulusMode == "command_success"
        ):
            pass
        else:
            pytest.skip(
                "Redundant test case: Parameters do not affect this test"
            )

        assert device_under_test.adminMode == AdminMode.OFFLINE

    def device_online_and_off(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Helper function to start up the DUT.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
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
            attribute_value=DevState.OFF,
        )

    def test_startup_state(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Tests the TalonLRU device's startup state.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param power_switch_1: A mock power switch device.
        :param power_switch_2: A mock power switch device.
        """
        if (
            power_switch_1.stimulusMode == "command_success"
            and power_switch_2.stimulusMode == "command_success"
        ):
            pass
        else:
            pytest.skip(
                "Redundant test case: Parameters do not affect this test"
            )

        self.device_online_and_off(device_under_test, event_tracer)

    @pytest.mark.skip(reason="Skipping test involving nested LRC")
    def test_On(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Tests the On() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param power_switch_1: a mock power switch device.
        :param power_switch_2: a mock power switch device.
        """
        self.device_online_and_off(device_under_test, event_tracer)

        # Send the long running command 'On'
        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        # Assert the expected result, given the stimulus mode of the power switches.
        # Currently only set to work for mismatched PDUs to reduce test time and complexity
        expected_result_map = {
            ("command_success", "command_success"): (
                ResultCode.OK,
                "On completed OK",
                DevState.ON,
            ),
            ("command_success", "command_fail"): (
                ResultCode.OK,
                "On completed OK",
                DevState.ON,
            ),
            ("command_fail", "command_success"): (
                ResultCode.OK,
                "On completed OK",
                DevState.ON,
            ),
            ("command_fail", "command_fail"): (
                ResultCode.FAILED,
                "LRU failed to turn on: both outlets failed to turn on",
                None,
            ),
        }

        result_code, message, state = expected_result_map.get(
            (power_switch_1.stimulusMode, power_switch_2.stimulusMode)
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{result_code.value}, "{message}"]',
            ),
        )

        if state is not None:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="state",
                attribute_value=state,
            )

    @pytest.mark.skip(reason="Skipping test involving nested LRC")
    def test_Off_from_off(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests that the Off command from an off state behaves appropriately.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        # Trigger the mock start_communicating
        self.device_online_and_off(device_under_test, event_tracer)

        # Send the Off command
        result_code, command_id = device_under_test.Off()
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

    @pytest.mark.skip(reason="Skipping test involving nested LRC")
    def test_On_Off(
        self: TestTalonLRU,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        power_switch_1: unittest.mock.Mock,
        power_switch_2: unittest.mock.Mock,
    ) -> None:
        """
        Tests that the On command followed by the Off command works appropriately.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param power_switch_1: a mock power switch device.
        :param power_switch_2: a mock power switch device.
        """
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
        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        # Assert the expected result, given the stimulus mode of the power switches.
        # Currently only set to work for mismatched PDUs to reduce test time and complexity
        result_map = {
            ("command_success", "command_success"): (
                ResultCode.OK,
                "Off completed OK: both outlets turned off",
                DevState.OFF,
            ),
            ("command_success", "command_fail"): (
                ResultCode.FAILED,
                "LRU failed to turn off: one outlet failed to turn off",
                None,
            ),
            ("command_fail", "command_success"): (
                ResultCode.FAILED,
                "LRU failed to turn off: one outlet failed to turn off",
                None,
            ),
            ("command_fail", "command_fail"): (
                ResultCode.FAILED,
                "LRU failed to turn off: failed to turn off both outlets",
                None,
            ),
        }

        result_code, message, state = result_map.get(
            (power_switch_1.stimulusMode, power_switch_2.stimulusMode)
        )

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", f'[{result_code.value}, "{message}"]')
        )

        if state is not None:
            change_event_callbacks["state"].assert_change_event(state)

        # Assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
