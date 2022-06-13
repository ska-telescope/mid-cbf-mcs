#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the TalonLRU device."""

from __future__ import annotations

import time

# Standard imports
import pytest

# Local imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, PowerMode

# Tango imports
from tango import DevState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness


class TestTalonLRU:
    """Test class for the TalonLRU device"""

    def test_State(
        self: TestTalonLRU,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestTalonLRU,
        device_under_test: CbfDeviceProxy,
    ) -> None:

        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestTalonLRU,
        device_under_test: CbfDeviceProxy,
    ) -> None:

        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_startup_state(
        self, tango_harness: TangoHarness, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Tests that the state of the TalonLRU device when it starts up is correct.
        """
        assert device_under_test.State() == DevState.DISABLE

        # trigger the mock start_communicating
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(2)
        assert device_under_test.adminMode == AdminMode.ONLINE

        mock_power_switch1 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/001"
        )
        mock_power_switch2 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/002"
        )

        # Check the device state based on the mock power switch behaviour
        if (
            mock_power_switch1.stimulusMode == "conn_success"
            or mock_power_switch2.stimulusMode == "conn_success"
            or mock_power_switch1.stimulusMode == "command_fail"
            or mock_power_switch2.stimulusMode == "command_fail"
        ):
            assert device_under_test.State() == DevState.OFF
        else:
            assert device_under_test.State() == DevState.FAULT

    def test_On(
        self, tango_harness: TangoHarness, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """

        mock_power_switch1 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/001"
        )
        mock_power_switch2 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/002"
        )

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
        self, tango_harness: TangoHarness, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Tests that the On command behaves appropriately.
        """

        mock_power_switch1 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/001"
        )
        mock_power_switch2 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/002"
        )

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
        self, tango_harness: TangoHarness, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Tests that the On command followed by the Off command works appropriately.
        """
        mock_power_switch1 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/001"
        )
        mock_power_switch2 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/002"
        )

        # Skip this test for certain configurations
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            pytest.skip(
                "Test sequence is not valid for this configuration of stimulus"
            )

        self.test_On(tango_harness, device_under_test)
        self.test_Off(tango_harness, device_under_test)
