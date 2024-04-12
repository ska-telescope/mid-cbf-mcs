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

# Standard imports
import os
import time
from typing import Iterator

import pytest
import ska_tango_testing.context
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from ska_tango_testing.harness import TangoTestHarness, TangoTestHarnessContext
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.vcc.vcc_device import Vcc

from ... import test_utils

# import gc
# gc.disable()

# Path
file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Tango imports

# SKA imports

CONST_WAIT_TIME = 1


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> ska_tango_testing.context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run

    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/vcc/001")


@pytest.fixture(name="change_event_callbacks")
def vcc_change_event_callbacks(
    device_under_test: ska_tango_testing.context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "longRunningCommandProgress",
        "frequencyBand",
        "obsState",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


class TestVcc:
    """
    Test class for Vcc tests.
    """

    @pytest.fixture(name="test_context")
    def vcc_test_context(self: TestVcc) -> Iterator[TangoTestHarnessContext]:
        harness = ska_tango_testing.context.ThreadedTestTangoContextManager()
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

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestVcc, device_under_test: ska_tango_testing.context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`ska_tango_testing.context.DeviceProxy`.
        """
        assert device_under_test.state() == DevState.DISABLE

    def test_Status(
        self: TestVcc, device_under_test: ska_tango_testing.context.DeviceProxy
    ) -> None:
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestVcc, device_under_test: ska_tango_testing.context.DeviceProxy
    ) -> None:
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_adminMode(
        self: TestVcc, device_under_test: ska_tango_testing.context.DeviceProxy
    ) -> None:
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestVcc,
        device_under_test: ska_tango_testing.context.DeviceProxy,
        command: str,
    ) -> None:
        """
        Test the On command

        :param device_under_test: fixture that provides a
            :py:class: proxy to the device under test, in a
            :py:class:`ska_tango_testing.context.DeviceProxy`.
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
        device_under_test: ska_tango_testing.context.DeviceProxy,
        config_file_name: str,
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: JSON file for the configuration
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.state() == DevState.OFF
        device_under_test.On()
        assert device_under_test.state() == DevState.ON

        with open(file_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")
            configuration = json.loads(json_str)

        freq_band_name = configuration["frequency_band"]

        # test ConfigureBand
        band_configuration = {
            "frequency_band": freq_band_name,
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }
        result_code, command_id = device_under_test.ConfigureBand(
            json.dumps(band_configuration)
        )
        assert result_code == [ResultCode.QUEUED]

        # assert command progress and result OK
        change_event_callbacks[
            "longRunningCommandProgress"
        ].assert_change_event((f"{command_id[0]}", f"{100}"))
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "ConfigureBand completed OK."]')
        )
        # assert frequencyBand attribute updated
        change_event_callbacks["frequencyBand"].assert_change_event(
            freq_band_dict()[freq_band_name]["band_index"]
        )

        # test ConfigureScan
        result_code, command_id = device_under_test.ConfigureScan(json_str)
        assert result_code == [ResultCode.QUEUED]

        # assert command progress and result OK
        change_event_callbacks[
            "longRunningCommandProgress"
        ].assert_change_event((f"{command_id[0]}", f"{100}"))
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "ConfigureScan completed OK."]')
        )
        # assert obsState updated
        change_event_callbacks["obsState"].assert_change_event(
            ObsState.CONFIGURING.value
        )
        change_event_callbacks["obsState"].assert_change_event(
            ObsState.READY.value
        )

        # test GoToIdle
        (
            result_code,
            command_id,
        ) = (
            device_under_test.GoToIdle()
        )  # assert command progress and result OK
        change_event_callbacks[
            "longRunningCommandProgress"
        ].assert_change_event((f"{command_id[0]}", f"{100}"))
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[0, "GoToIdle completed OK."]')
        )
        # assert obsState updated
        change_event_callbacks["obsState"].assert_change_event(
            ObsState.IDLE.value
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_id",
    #     [
    #         ("Vcc_ConfigureScan_basic.json", 1),
    #         ("Vcc_ConfigureScan_basic.json", 2),
    #     ],
    # )
    # def test_Scan(
    #     self: TestVcc,
    #     device_under_test: CbfDeviceProxy,
    #     config_file_name: str,
    #     scan_id: int,
    # ) -> None:
    #     """
    #     Test Vcc's Scan command state changes.

    #     First calls test_Vcc_ConfigureScan to get it in the ready state
    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     :param config_file_name: JSON file for the configuration
    #     :param scan_id: the scan id
    #     """
    #     # turn on device and configure scan
    #     self.test_Vcc_ConfigureScan(device_under_test, config_file_name)

    #     scan_id_device_data = tango.DeviceData()
    #     scan_id_device_data.insert(tango.DevShort, scan_id)

    #     # Use callable 'Scan'  API
    #     (result_code, _) = device_under_test.Scan(scan_id_device_data)
    #     assert result_code == ResultCode.STARTED
    #     assert device_under_test.obsState == ObsState.SCANNING

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_id",
    #     [
    #         ("Vcc_ConfigureScan_basic.json", 1),
    #         ("Vcc_ConfigureScan_basic.json", 2),
    #     ],
    # )
    # def test_EndScan(
    #     self: TestVcc,
    #     device_under_test: CbfDeviceProxy,
    #     config_file_name: str,
    #     scan_id: int,
    # ) -> None:
    #     """
    #     Test Vcc's EndScan command state changes.

    #     First calls test_Scan to get it in the Scanning state
    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     :param config_file_name: JSON file for the configuration
    #     :param scan_id: the scan id
    #     """
    #     self.test_Scan(device_under_test, config_file_name, scan_id)

    #     (result_code, _) = device_under_test.EndScan()
    #     assert device_under_test.obsState == ObsState.READY

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_id",
    #     [
    #         ("Vcc_ConfigureScan_basic.json", 1),
    #         ("Vcc_ConfigureScan_basic.json", 2),
    #     ],
    # )
    # def test_Reconfigure_Scan_EndScan_GoToIdle(
    #     self: TestVcc,
    #     device_under_test: CbfDeviceProxy,
    #     config_file_name: str,
    #     scan_id: int,
    # ) -> None:
    #     """
    #     Test Vcc's ability to reconfigure and run multiple scans.

    #     Calls test_EndScan to get it in the ready state after a first test run.
    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     :param config_file_name: JSON file for the configuration
    #     :param scan_id: the scan id
    #     """
    #     self.test_EndScan(device_under_test, config_file_name, scan_id)

    #     # try reconfiguring and scanning again (w/o power cycling)
    #     f = open(file_path + config_file_name)
    #     json_str = f.read().replace("\n", "")
    #     configuration = json.loads(json_str)
    #     f.close()

    #     band_configuration = {
    #         "frequency_band": configuration["frequency_band"],
    #         "dish_sample_rate": 999999,
    #         "samples_per_frame": 18,
    #     }
    #     device_under_test.ConfigureBand(json.dumps(band_configuration))

    #     (result_code, _) = device_under_test.ConfigureScan(json_str)
    #     time.sleep(CONST_WAIT_TIME)
    #     assert result_code == ResultCode.OK
    #     assert device_under_test.obsState == ObsState.READY

    #     # rescanning
    #     scan_id_device_data = tango.DeviceData()
    #     scan_id_device_data.insert(tango.DevShort, scan_id)

    #     (result_code, _) = device_under_test.Scan(scan_id_device_data)
    #     assert result_code == ResultCode.STARTED
    #     assert device_under_test.obsState == ObsState.SCANNING
    #     (result_code, _) = device_under_test.EndScan()
    #     assert result_code == ResultCode.OK
    #     assert device_under_test.obsState == ObsState.READY

    #     (result_code, _) = device_under_test.GoToIdle()
    #     assert device_under_test.obsState == ObsState.IDLE
    #     assert result_code == ResultCode.OK

    # @pytest.mark.parametrize(
    #     "config_file_name", [("Vcc_ConfigureScan_basic.json")]
    # )
    # def test_Abort_FromReady(
    #     self, device_under_test: CbfDeviceProxy, config_file_name: str
    # ) -> None:
    #     """
    #     Test a Abort() from ready state.

    #     First calls test_Vcc_ConfigureScan to get it in ready state.
    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     :param config_file_name: JSON file for the configuration
    #     """
    #     self.test_Vcc_ConfigureScan(device_under_test, config_file_name)

    #     device_under_test.Abort()
    #     time.sleep(CONST_WAIT_TIME)
    #     assert device_under_test.obsState == ObsState.ABORTED

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_id",
    #     [
    #         ("Vcc_ConfigureScan_basic.json", 1),
    #         ("Vcc_ConfigureScan_basic.json", 2),
    #     ],
    # )
    # def test_Abort_FromScanning(
    #     self: TestVcc,
    #     device_under_test: CbfDeviceProxy,
    #     config_file_name: str,
    #     scan_id: int,
    # ) -> None:
    #     """
    #     Test a Abort() from scanning state.

    #     First calls test_Scan to get it in the scanning state
    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     :param config_file_name: JSON file for the configuration
    #     :param scan_id: the scan id
    #     """
    #     self.test_Scan(device_under_test, config_file_name, scan_id)

    #     device_under_test.Abort()
    #     time.sleep(CONST_WAIT_TIME)
    #     assert device_under_test.obsState == ObsState.ABORTED

    # @pytest.mark.parametrize(
    #     "config_file_name", [("Vcc_ConfigureScan_basic.json")]
    # )
    # def test_ObsReset(
    #     self, device_under_test: CbfDeviceProxy, config_file_name: str
    # ) -> None:
    #     """
    #     Test ObsReset() command from aborted state.

    #     First calls test_Abort_FromReady to get it in aborted state.
    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     :param config_file_name: JSON file for the configuration
    #     """

    #     self.test_Abort_FromReady(device_under_test, config_file_name)

    #     device_under_test.ObsReset()
    #     time.sleep(CONST_WAIT_TIME)
    #     assert device_under_test.obsState == ObsState.IDLE

    # @pytest.mark.parametrize(
    #     "sw_config_file_name, \
    #     config_file_name",
    #     [
    #         (
    #             "Vcc_ConfigureSearchWindow_basic.json",
    #             "Vcc_ConfigureScan_basic.json",
    #         )
    #     ],
    # )
    # def test_ConfigureSearchWindow_basic(
    #     self: TestVcc,
    #     device_under_test: CbfDeviceProxy,
    #     sw_config_file_name: str,
    #     config_file_name: str,
    # ):
    #     """
    #     Test a minimal successful search window configuration.
    #     """
    #     device_under_test.adminMode = AdminMode.ONLINE
    #     device_under_test.loggingLevel = LoggingLevel.DEBUG
    #     device_under_test.On()
    #     device_under_test.loggingLevel = LoggingLevel.DEBUG
    #     # set dishID to SKA001 to correctly test tdcDestinationAddress
    #     device_under_test.dishID = "SKA001"
    #     f = open(file_path + config_file_name)
    #     json_string = f.read().replace("\n", "")
    #     f.close()
    #     device_under_test.ConfigureScan(json_string)
    #     time.sleep(3)

    #     # configure search window
    #     f = open(file_path + sw_config_file_name)
    #     device_under_test.ConfigureSearchWindow(f.read().replace("\n", ""))
    #     f.close()
