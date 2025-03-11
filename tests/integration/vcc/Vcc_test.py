#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Vcc."""
from __future__ import annotations

import copy
import json
import os

import pytest
from ska_control_model import ResultCode, SimulationMode
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestVcc:
    """
    Test class for Vcc device class integration testing.
    """

    def test_Online(
        self: TestVcc,
        device_under_test: pytest.fixture,
        test_proxies: pytest.fixture,
        change_event_callbacks: MockTangoEventCallbackGroup,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
        ps_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param device_under_test: the device under test
        :param test_proxies: a test fixture containing all subdevice proxies needed by the device under test.
        :param change_event_callbacks: a mock object that receives the DUT's subscribed change events.
        :param lru_change_event_callbacks: a mock object that receives TalonLru's subscribed change events.
        :param ps_change_event_callbacks: a mock object that receives PowerSwitch's subscribed change events.
        """

        # after init devices should be in DISABLE state, but just in case...
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.loggingLevel = LoggingLevel.DEBUG

        # Start monitoring the TalonLRUs and power switch devices
        for ps in test_proxies.power_switch:
            ps.adminMode = AdminMode.ONLINE
            ps_change_event_callbacks["State"].assert_change_event(DevState.ON)

        for lru in test_proxies.talon_lru:
            lru.adminMode = AdminMode.ONLINE
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.OFF
            )

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        lru_change_event_callbacks.assert_not_called()
        ps_change_event_callbacks.assert_not_called()

    def test_On(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        test_proxies: pytest.fixture,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "On" command

        :param device_under_test: the device under test
        :param test_proxies: a test fixture containing all subdevice proxies needed by the device under test.
        :param lru_change_event_callbacks: a mock object that receives TalonLru's subscribed change events.
        """

        # Turn on the LRUs and then the VCC devices
        for lru in test_proxies.talon_lru:
            result_code, command_id = lru.On()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks["lrcFinished"].assert_change_event(
                (f"{command_id[0]}", '[0, "On completed OK"]')
            )
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.ON
            )

        result_code, message = device_under_test.On()  # Slow command
        assert result_code == ResultCode.OK
        assert device_under_test.State() == DevState.ON

        # assert if any captured events have gone unaddressed
        lru_change_event_callbacks.assert_not_called()

    def test_Off(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "Off" command

        :param device_under_test: the device under test
        :param test_proxies: a test fixture containing all subdevice proxies needed by the device under test.
        :param lru_change_event_callbacks: a mock object that receives TalonLru's subscribed change events.
        """

        result_code, message = device_under_test.Off()  # Slow command
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

        # Turn DUT back on for next test.
        assert device_under_test.adminMode == AdminMode.ONLINE
        device_under_test.On()
        change_event_callbacks["State"].assert_change_event(DevState.ON)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    # TODO: Confirm this test is not needed since we are not implementing STANDBY
    # @pytest.mark.parametrize("vcc_id", [1])
    # def test_Standby(
    #     self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    # ) -> None:
    #     """
    #     Test the "Standby" command

    #     :param test_proxies: the proxies test fixture
    #     :param vcc_id: the fsp id

    #     """

    #     wait_time_s = 3
    #     sleep_time_s = 0.1

    #     device_under_test = test_proxies.vcc[vcc_id]

    #     device_under_test.Standby()

    #     test_proxies.wait_timeout_dev(
    #         [device_under_test], DevState.STANDBY, wait_time_s, sleep_time_s
    #     )
    #     assert device_under_test.State() == DevState.STANDBY

    @pytest.mark.parametrize(
        "config_file_name",
        ["Vcc_ConfigureScan_basic.json"],
    )
    def test_ConfigureScan(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        config_file_name: str,
    ) -> None:
        """
        Test the "ConfigureScan" command

        :param test_proxies: the proxies test fixture
        :param config_file_name: the name of the JSON file
            containing the configuration
        :param vcc_id: the fsp id

        """
        assert device_under_test.State() == DevState.ON

        with open(data_file_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = copy.deepcopy(json.loads(json_str))

        band_configuration = {
            "frequency_band": configuration["frequency_band"],
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }

        result_code, command_id = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "ConfigureBand completed OK"]')
        )

        assert (
            device_under_test.frequencyBand
            == freq_band_dict()[configuration["frequency_band"]]["band_index"]
        )

        result_code, command_id = device_under_test.ConfigureScan(json_str)
        assert result_code == [ResultCode.QUEUED]

        # TODO: Taylor, where does this state get set? configured=True calls the component_configured trigger..
        # I also don't understand how it ends up as READY since component_configured destination is CONFIGURING_READY
        change_event_callbacks["obsState"].assert_change_event(
            ObsState.CONFIGURING
        )

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "ConfigureScan completed OK"]')
        )

        change_event_callbacks["obsState"].assert_change_event(ObsState.READY)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "scan_id",
        [1],
    )
    def test_Scan(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        scan_id: int,
    ) -> None:
        """
        Test the "Scan" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        assert device_under_test.State() == DevState.ON

        result_code, command_id = device_under_test.Scan(scan_id)
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "Scan completed OK"]')
        )

        change_event_callbacks["obsState"].assert_change_event(
            ObsState.SCANNING
        )
        assert device_under_test.scanID == scan_id

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_EndScan(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "EndScan" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        assert device_under_test.State() == DevState.ON

        result_code, command_id = device_under_test.EndScan()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "EndScan completed OK"]')
        )
        change_event_callbacks["obsState"].assert_change_event(ObsState.READY)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_GoToIdle(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the "GoToIdle" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        assert device_under_test.State() == DevState.ON

        result_code, command_id = device_under_test.GoToIdle()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["lrcFinished"].assert_change_event(
            (f"{command_id[0]}", '[0, "GoToIdle completed OK"]')
        )

        change_event_callbacks["obsState"].assert_change_event(ObsState.IDLE)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_Abort_ObsReset(
        self: TestVcc,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test the "ConfigureScan" command

        :param test_proxies: the proxies test fixture
        :param config_file_name: the name of the JSON file
            containing the configuration
        :param vcc_id: the fsp id

        """
        assert device_under_test.obsState == ObsState.IDLE
        assert device_under_test.State() == DevState.ON

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Abort from READY
        self.test_ConfigureScan(
            device_under_test, change_event_callbacks, config_file_name
        )
        assert device_under_test.obsState == ObsState.READY

        command_dict["Abort"] = device_under_test.Abort()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks["lrcFinished"].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.ABORTING,
            ObsState.ABORTED,
            ObsState.RESETTING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert frequencyBand attribute reset during ObsReset
        # change_event_callbacks["frequencyBand"].assert_change_event(0)

        assert device_under_test.State() == DevState.ON
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

        # abort from SCANNING
        self.test_ConfigureScan(
            device_under_test, change_event_callbacks, config_file_name
        )
        self.test_Scan(device_under_test, change_event_callbacks, scan_id)
        assert device_under_test.obsState == ObsState.SCANNING

        command_dict["Abort"] = device_under_test.Abort()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            change_event_callbacks["lrcFinished"].assert_change_event(
                (
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                )
            )

        # check all obsState transitions
        for obs_state in [
            ObsState.ABORTING,
            ObsState.ABORTED,
            ObsState.RESETTING,
            ObsState.IDLE,
        ]:
            change_event_callbacks["obsState"].assert_change_event(
                obs_state.value
            )

        # assert frequencyBand attribute reset during ObsReset
        # change_event_callbacks["frequencyBand"].assert_change_event(0)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    def test_Disconnect(
        self: TestVcc,
        device_under_test: pytest.fixture,
        test_proxies: pytest.fixture,
        change_event_callbacks: MockTangoEventCallbackGroup,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
        ps_change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()  # Slow command
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE
        change_event_callbacks["State"].assert_change_event(DevState.DISABLE)

        # Stop monitoring the TalonLRUs and power switch devices
        for lru in test_proxies.talon_lru:
            result_code, command_id = lru.Off()
            assert result_code == [ResultCode.QUEUED]

            lru_change_event_callbacks["lrcFinished"].assert_change_event(
                (f"{command_id[0]}", '[0, "Off completed OK"]')
            )
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.OFF
            )

            lru.adminMode = AdminMode.OFFLINE
            lru_change_event_callbacks["State"].assert_change_event(
                DevState.DISABLE
            )

        for ps in test_proxies.power_switch:
            ps.adminMode = AdminMode.OFFLINE
            ps_change_event_callbacks["State"].assert_change_event(
                DevState.DISABLE
            )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
        lru_change_event_callbacks.assert_not_called()
        ps_change_event_callbacks.assert_not_called()
