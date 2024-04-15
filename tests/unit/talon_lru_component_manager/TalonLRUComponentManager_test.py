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

# Standard imports
import pytest

# Local imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.talon_lru.talon_lru_component_manager import (
    TalonLRUComponentManager,
)
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# Tango imports


class TestTalonLRUComponentManager:
    """Test class for the TalonLRU device"""

    def test_startup_state(
        self,
        tango_harness: TangoHarness,
        talon_lru_component_manager: TalonLRUComponentManager,
    ) -> None:
        """
        Tests that the state of the TalonLRU device when it starts up is correct.
        """
        mock_power_switch1 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/001"
        )
        mock_power_switch2 = tango_harness.get_device(
            "mid_csp_cbf/power_switch/002"
        )

        talon_lru_component_manager.start_communicating()
        # Check the device state and pdu1_power_mode based on mock_power_switch1 behaviour
        if mock_power_switch1.stimulusMode == "conn_fail":
            assert (
                talon_lru_component_manager.pdu1_power_mode
                == PowerState.UNKNOWN
            )
        elif mock_power_switch1.stimulusMode == "invalid_start_state":
            assert (
                talon_lru_component_manager.pdu1_power_mode
                == mock_power_switch1.GetOutletPowerState()
            )
        else:
            assert talon_lru_component_manager.pdu1_power_mode == PowerState.OFF

        # Check the device state and pdu2_power_mode based on mock_power_switch2 behaviour
        if mock_power_switch2.stimulusMode == "conn_fail":
            assert (
                talon_lru_component_manager.pdu2_power_mode
                == PowerState.UNKNOWN
            )
        elif mock_power_switch2.stimulusMode == "invalid_start_state":
            assert (
                talon_lru_component_manager.pdu2_power_mode
                == mock_power_switch2.GetOutletPowerState()
            )
        else:
            assert talon_lru_component_manager.pdu2_power_mode == PowerState.OFF

    def test_On(
        self,
        tango_harness: TangoHarness,
        talon_lru_component_manager: TalonLRUComponentManager,
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

        talon_lru_component_manager.start_communicating()
        # Send the On command
        (result_code, _) = talon_lru_component_manager.on()

        # Check the command result, device state and PDU power modes
        if (
            mock_power_switch1.stimulusMode == "command_fail"
            and mock_power_switch2.stimulusMode == "command_fail"
        ):
            assert result_code == ResultCode.FAILED
            assert talon_lru_component_manager.pdu1_power_mode == PowerState.OFF
            assert talon_lru_component_manager.pdu2_power_mode == PowerState.OFF
        else:
            assert result_code == ResultCode.OK

            if mock_power_switch1.stimulusMode == "command_fail":
                assert (
                    talon_lru_component_manager.pdu1_power_mode
                    == PowerState.OFF
                )
            else:
                assert (
                    talon_lru_component_manager.pdu1_power_mode == PowerState.ON
                )

            if mock_power_switch2.stimulusMode == "command_fail":
                assert (
                    talon_lru_component_manager.pdu2_power_mode
                    == PowerState.OFF
                )
            else:
                assert (
                    talon_lru_component_manager.pdu2_power_mode == PowerState.ON
                )

    def test_Off(
        self,
        tango_harness: TangoHarness,
        talon_lru_component_manager: TalonLRUComponentManager,
    ) -> None:
        """
        Tests that the Off command behaves appropriately.
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

        talon_lru_component_manager.start_communicating()
        # Get the initial device state and power modes
        initial_pdu1_power_mode = talon_lru_component_manager.pdu1_power_mode
        initial_pdu2_power_mode = talon_lru_component_manager.pdu2_power_mode

        # Send the Off command
        (result_code, _) = talon_lru_component_manager.off()

        # Check the command result, device state and PDU power modes
        if mock_power_switch1.stimulusMode == "command_fail":
            assert result_code == ResultCode.FAILED
            assert (
                talon_lru_component_manager.pdu1_power_mode
                == initial_pdu1_power_mode
            )
        else:
            assert talon_lru_component_manager.pdu1_power_mode == PowerState.OFF

        if mock_power_switch2.stimulusMode == "command_fail":
            assert result_code == ResultCode.FAILED
            assert (
                talon_lru_component_manager.pdu2_power_mode
                == initial_pdu2_power_mode
            )
        else:
            assert talon_lru_component_manager.pdu2_power_mode == PowerState.OFF

        if (
            mock_power_switch1.stimulusMode != "command_fail"
            and mock_power_switch2.stimulusMode != "command_fail"
        ):
            assert result_code == ResultCode.OK

    def test_OnOff(
        self,
        tango_harness: TangoHarness,
        talon_lru_component_manager: CbfDeviceProxy,
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

        self.test_On(tango_harness, talon_lru_component_manager)
        self.test_Off(tango_harness, talon_lru_component_manager)
