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

import json
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

# from ska_tango_testing import context
from ska_mid_cbf_mcs.testing import context
from ska_mid_cbf_mcs.vcc.vcc_device import Vcc

from ...test_utils import device_online_and_on

# Path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestVcc:
    """
    Test class for Vcc tests.
    """

    # TODO: check configured parameters in READY and IDLE?
    # TODO: test invalid frequency band
    # TODO: subarrayMembership?
    # TODO: simulator vs mock HPS?
    # TODO: validate ConfigureScan at VCC level?

    @pytest.fixture(name="test_context")
    def vcc_test_context(
        self: TestVcc, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
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

    def test_State(
        self: TestVcc, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`context.DeviceProxy`.
        """
        assert device_under_test.state() == DevState.DISABLE

    def test_Status(
        self: TestVcc, device_under_test: context.DeviceProxy
    ) -> None:
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestVcc, device_under_test: context.DeviceProxy
    ) -> None:
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        command: str,
    ) -> None:
        """
        Test the On/Off/Standby commands

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`context.DeviceProxy`.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF

        if command == "On":
            expected_result = ResultCode.OK
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            expected_result = ResultCode.REJECTED
            expected_state = DevState.OFF
            result = device_under_test.Off()
        elif command == "Standby":
            expected_result = ResultCode.REJECTED
            expected_state = DevState.OFF
            result = device_under_test.Standby()

        assert result[0][0] == expected_result
        assert device_under_test.State() == expected_state

    @pytest.mark.parametrize(
        "config_file_name, scan_id", [("Vcc_ConfigureScan_basic.json", 1)]
    )
    def test_Scan(
        self: TestVcc,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param config_file_name: JSON file for the configuration
        """
        # prepare device for observation
        assert device_online_and_on(device_under_test)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test issuing AbortScan and ObsReset from SCANNING
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # assert frequencyBand attribute updated
        change_event_callbacks["frequencyBand"].assert_change_event(
            freq_band_dict()[freq_band_name]["band_index"]
        )
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert frequencyBand attribute reset during GoToIdle
        change_event_callbacks["frequencyBand"].assert_change_event(0)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_Scan_reconfigure(
        self: TestVcc,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test Vcc's ability to reconfigure and run multiple scans.

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param config_file_name: JSON file for the configuration
        :param scan_id: the scan id
        """
        # prepare device for observation
        assert device_online_and_on(device_under_test)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test issuing AbortScan and ObsReset from SCANNING
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # assert frequencyBand attribute updated
        change_event_callbacks["frequencyBand"].assert_change_event(
            freq_band_dict()[freq_band_name]["band_index"]
        )
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # second round of observation
        command_dict = {}
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.READY,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert frequencyBand attribute reset during GoToIdle
        change_event_callbacks["frequencyBand"].assert_change_event(0)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "config_file_name",
        [("Vcc_ConfigureScan_basic.json")],
    )
    def test_AbortScan_from_ready(
        self: TestVcc,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        config_file_name: str,
    ) -> None:
        """
        Test a AbortScan from ObsState.READY.

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param config_file_name: JSON file for the configuration
        """
        # prepare device for observation
        assert device_online_and_on(device_under_test)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test issuing AbortScan and ObsReset from READY
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # assert frequencyBand attribute updated
        change_event_callbacks["frequencyBand"].assert_change_event(
            freq_band_dict()[freq_band_name]["band_index"]
        )
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["AbortScan"] = device_under_test.AbortScan()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.ABORTING,
            ObsState.ABORTED,
            ObsState.RESETTING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert frequencyBand attribute reset during ObsReset
        change_event_callbacks["frequencyBand"].assert_change_event(0)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_AbortScan_from_scanning(
        self: TestVcc,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test a AbortScan from ObsState.SCANNING.

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param config_file_name: JSON file for the configuration
        """
        # prepare device for observation
        assert device_online_and_on(device_under_test)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)
        freq_band_name = configuration["frequency_band"]
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test issuing AbortScan and ObsReset from SCANNING
        command_dict["ConfigureBand"] = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        # assert frequencyBand attribute updated
        change_event_callbacks["frequencyBand"].assert_change_event(
            freq_band_dict()[freq_band_name]["band_index"]
        )
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["AbortScan"] = device_under_test.AbortScan()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.ABORTING,
            ObsState.ABORTED,
            ObsState.RESETTING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert frequencyBand attribute reset during ObsReset
        change_event_callbacks["frequencyBand"].assert_change_event(0)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
