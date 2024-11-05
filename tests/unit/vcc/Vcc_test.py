#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Vcc."""

from __future__ import annotations

import gc
import json
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, ObsState, ResultCode, SimulationMode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.vcc.vcc_device import Vcc

from ... import test_utils

# Path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Disable garbage collection to prevent tests hanging
gc.disable()


class TestVcc:
    """
    Test class for VCC.
    """

    # TODO: Check configured parameters in READY and IDLE?
    # TODO: Test invalid frequency band
    # TODO: subarrayMembership?
    # TODO: Simulator vs mock HPS?
    # TODO: Validate ConfigureScan at VCC level?

    @pytest.fixture(name="test_context")
    def vcc_test_context(
        self: TestVcc, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that creates a test context for the Vcc device.

        :param initial_mocks: A dictionary of initial mocks to be used in the test context.
        :return: A test context for the Vcc device.
        """
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/vcc/001",
            device_class=Vcc,
            TalonLRUAddress="mid_csp_cbf/talon_lru/001",
            VccControllerAddress="talondx-001/vcc-app/vcc-controller",
            Band1And2Address="talondx-001/vcc-app/vcc-band-1-and-2",
            Band3Address="talondx-001/vcc-app/vcc-band-3",
            Band4Address="talondx-001/vcc-app/vcc-band-4",
            Band5Address="talondx-001/vcc-app/vcc-band-5",
            SW1Address="mid_csp_cbf/vcc_sw1/001",
            SW2Address="mid_csp_cbf/vcc_sw2/001",
            DeviceID="1",
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def device_online(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> bool:
        """
        Helper function to start up and turn on the DUT.

        :param device_under_test: DeviceProxy to the device under test.
        """
        # Set a given device to AdminMode.ONLINE and DevState.ON
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="adminMode",
            attribute_value=AdminMode.ONLINE,
        )
        return device_under_test.adminMode == AdminMode.ONLINE

    def test_State(
        self: TestVcc, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.state() == DevState.DISABLE

    def test_subarrayMembership(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test reading/writing subarrayMembership while catching the corresponding change events.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        assert device_under_test.subarrayMembership == 0
        device_under_test.subarrayMembership = 1
        assert device_under_test.subarrayMembership == 1

        # Assert subarrayMembership attribute event change
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="subarrayMembership",
            attribute_value=1,
        )

    def test_Status(
        self: TestVcc, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestVcc, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_Online(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test turning the device online.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        # Set a given device to AdminMode.ONLINE and DevState.ON
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
        "frequency_band, success",
        [
            (
                "fail",
                False,
            ),
            ("1", True),
            ("2", True),
            ("5a", True),
            ("5b", True),
        ],
    )
    def test_ConfigureBand(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        frequency_band: str,
        success: bool,
    ) -> None:
        """
        Test ConfigureBand with both failing and passing configurations.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param frequency_band: The frequency band to configure.
        :param success: A parameterized value used to test success and failure conditions.
        """
        # Prepare device for observation
        assert self.device_online(device_under_test, event_tracer)

        # Setting band configuration with invalid frequency band

        band_configuration = {
            "frequency_band": frequency_band,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # Test issuing invalid frequency band
        return_value = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        if success:
            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "ConfigureBand completed OK"]',
                ),
            )

            # Assert frequencyBand attribute was pushed
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="frequencyBand",
                attribute_value=freq_band_dict()[frequency_band]["band_index"],
            )

        else:
            # Check that the queued command failed
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.FAILED.value}, "frequency_band {frequency_band} is invalid."]',
                ),
            )

    @pytest.mark.parametrize(
        "config_file_name, scan_id", [("Vcc_ConfigureScan_basic.json", 1)]
    )
    def test_Scan(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration.
        :param scan_id: An identifier for the scan operation.
        """
        # Prepare device for observation
        assert self.device_online(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Test happy path observing command sequence
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # Assert frequencyBand attribute updated
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=freq_band_dict()[freq_band_name]["band_index"],
        )

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        previous_state = ObsState.IDLE
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
            ObsState.IDLE,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
            )
            previous_state = obs_state

        # Assert frequencyBand attribute reset during GoToIdle
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=0,
        )

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_Scan_reconfigure(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test Vcc's ability to reconfigure and run multiple scans.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration.
        :param scan_id: An identifier for the scan operation.
        """
        # Prepare device for observation
        assert self.device_online(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Test happy path observing command sequence
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # Assert frequencyBand attribute updated
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=freq_band_dict()[freq_band_name]["band_index"],
        )

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        previous_state = ObsState.IDLE
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
            )
            previous_state = obs_state

        # 2nd round of observation
        command_dict = {}
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).cbf_has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="obsState",
            attribute_value=ObsState.CONFIGURING,
            previous_value=previous_state,
        )

        previous_state = ObsState.CONFIGURING
        for obs_state in [
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
                target_n_events=2,
            )
            previous_state = obs_state

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).cbf_has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
            previous_value=previous_state,
        )

        # Assert frequencyBand attribute reset during GoToIdle
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=0,
        )

    @pytest.mark.parametrize(
        "config_file_name",
        ["Vcc_ConfigureScan_basic.json"],
    )
    def test_Abort_from_ready(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
    ) -> None:
        """
        Test Abort from ObsState.READY.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration.
        """
        # Prepare device for observation
        assert self.device_online(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Test issuing Abort and ObsReset from READY
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # Assert frequencyBand attribute updated
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=freq_band_dict()[freq_band_name]["band_index"],
        )

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Abort"] = device_under_test.Abort()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        previous_state = ObsState.IDLE
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.ABORTING,
            ObsState.ABORTED,
            ObsState.RESETTING,
            ObsState.IDLE,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
            )
            previous_state = obs_state

        # Assert frequencyBand attribute reset during ObsReset
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=0,
        )

        # Finally, ensure configuration works as expected after resetting
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # Assert frequencyBand attribute updated
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=freq_band_dict()[freq_band_name]["band_index"],
        )

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
                target_n_events=2,
            )
            previous_state = obs_state

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_Abort_from_scanning(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test Abort from ObsState.SCANNING.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration.
        :param scan_id: An identifier for the scan operation.
        """
        # Prepare device for observation
        assert self.device_online(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Test issuing Abort and ObsReset from SCANNING
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # Assert frequencyBand attribute updated
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=freq_band_dict()[freq_band_name]["band_index"],
        )

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["Abort"] = device_under_test.Abort()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        previous_state = ObsState.IDLE
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.ABORTING,
            ObsState.ABORTED,
            ObsState.RESETTING,
            ObsState.IDLE,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
            )
            previous_state = obs_state

        # Assert frequencyBand attribute reset during ObsReset
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=0,
        )

        # Finally, ensure configuration works as expected after resetting
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # Assert frequencyBand attribute updated
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="frequencyBand",
            attribute_value=freq_band_dict()[freq_band_name]["band_index"],
        )

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # Check all obsState transitions
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
        ]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="obsState",
                attribute_value=obs_state.value,
                previous_value=previous_state,
                target_n_events=2,
            )
            previous_state = obs_state
