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

from ska_mid_cbf_mcs.testing import context
from ska_mid_cbf_mcs.talon_lru.talon_lru_device import TalonLRU


class TestTalonLRU:
    """
    Test class for the TalonLRU
    """

    @pytest.fixture(name="test_context")
    def talon_lru_test_context(self: TestTalonLRU, initial_mocks: dict[str, Mock]) -> Iterator[context.TTCMExt.TCExt]:
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
            harness.add_mock_device(device_name=name, device=mock)

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
        assert device_under_test.state() == DevState.DISABLE

    def test_Status(
        self: TestTalonLRU, device_under_test: context.DeviceProxy
    ) -> None:
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestTalonLRU, device_under_test: context.DeviceProxy
    ) -> None:
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_startup_state(
        self, device_under_test: context.DeviceProxy, mock_power_switch1: context.DeviceProxy, mock_power_switch2: context.DeviceProxy
    ) -> None:
        """
        Tests that the state of the TalonLRU device when it starts up is correct.
        """
        assert device_under_test.State() == DevState.DISABLE

        # Trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(2)
        assert device_under_test.adminMode == AdminMode.ONLINE


        # Check the device state based on the mock power switch behaviour
        # TODO: Break out as parameterized test
        if (
            mock_power_switch1.stimulusMode == "conn_success"
            or mock_power_switch2.stimulusMode == "conn_success"
            or mock_power_switch1.stimulusMode == "command_fail"
            or mock_power_switch2.stimulusMode == "command_fail"
        ):
            assert device_under_test.State() == DevState.OFF
        else:
            assert device_under_test.State() == DevState.UNKNOWN






    def test_On(
        self: TestTalonLRU, device_under_test: context.DeviceProxy, mock_power_switch1: context.DeviceProxy, mock_power_switch2: context.DeviceProxy
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """
        # Skip this test for certain configurations
        if (
            mock_power_switch1.stimulusMode == "conn_fail"
            or mock_power_switch1.stimulusMode == "invalid_start_state"
            or mock_power_switch2.stimulusMode == "conn_fail"
            or mock_power_switch2.stimulusMode == "invalid_start_state"
        ):
            pytest.skip(
                "TalonLRU device is not in a valid startup state for this test"
            )

        # trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(2)
        assert device_under_test.adminMode == AdminMode.ONLINE

        # Send the On command
        result = device_under_test.On()

        # Check that the state updates correctly when the device callbacks are called
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            assert result[0][0] == ResultCode.FAILED
            assert device_under_test.State() == DevState.FAULT
        else:
            assert result[0][0] == ResultCode.OK
            assert device_under_test.State() == DevState.ON

    def test_Off(
        self: TestTalonLRU, device_under_test: context.DeviceProxy, mock_power_switch1: context.DeviceProxy, mock_power_switch2: context.DeviceProxy
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """

        # Skip this test for certain configurations
        if (
            mock_power_switch1.stimulusMode == "conn_fail"
            or mock_power_switch1.stimulusMode == "invalid_start_state"
            or mock_power_switch2.stimulusMode == "conn_fail"
            or mock_power_switch2.stimulusMode == "invalid_start_state"
        ):
            pytest.skip(
                "TalonLRU device is not in a valid startup state for this test"
            )

        # trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(2)
        assert device_under_test.adminMode == AdminMode.ONLINE

        # Send the On command
        result = device_under_test.Off()

        # Check that the state updates correctly when the device callbacks are called
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            assert result[0][0] == ResultCode.FAILED
            assert device_under_test.State() == DevState.FAULT
        else:
            assert result[0][0] == ResultCode.OK
            assert device_under_test.State() == DevState.OFF

    def test_OnOff(
          self: TestTalonLRU, device_under_test: context.DeviceProxy, mock_power_switch1: context.DeviceProxy, mock_power_switch2: context.DeviceProxy
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

        self.test_On(device_under_test, mock_power_switch1, mock_power_switch2)
        self.test_Off(device_under_test, mock_power_switch1, mock_power_switch2)
