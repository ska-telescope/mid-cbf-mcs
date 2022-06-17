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

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from tango import DevState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# Path
file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Tango imports

# SKA imports

CONST_WAIT_TIME = 2


class TestVcc:
    """
    Test class for Vcc tests.
    """

    def test_State(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.state() == DevState.DISABLE

    def test_Status(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
    ) -> None:

        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
    ) -> None:

        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestVcc, device_under_test: CbfDeviceProxy, command: str
    ) -> None:
        """
        Test the On/Off/Standby Commands

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param command: the command to test (one of On/Off/Standby)
        """

        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.ON

        if command == "On":
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            expected_state = DevState.OFF
            result = device_under_test.Off()
        elif command == "Standby":
            expected_state = DevState.STANDBY
            result = device_under_test.Standby()

        time.sleep(CONST_WAIT_TIME)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state

    @pytest.mark.parametrize(
        "config_file_name", [("Vcc_ConfigureScan_basic.json")]
    )
    def test_Vcc_ConfigureScan_basic(
        self, device_under_test: CbfDeviceProxy, config_file_name: str
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
        assert device_under_test.state() == DevState.ON

        device_under_test.On()

        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        device_under_test.ConfigureBand(configuration["frequency_band"])

        device_under_test.ConfigureScan(json_str)
        assert device_under_test.obsState == ObsState.READY

        device_under_test.GoToIdle()

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id",
        [
            (
                "Vcc_ConfigureScan_basic.json",
                1,
            ),
            (
                "Vcc_ConfigureScan_basic.json",
                2,
            ),
        ],
    )
    def test_Scan_EndScan_GoToIdle(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test Vcc's Scan command state changes.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: JSON file for the configuration
        :param scan_id: the scan id
        """
        device_under_test.adminMode = AdminMode.ONLINE

        # turn on device and configure scan
        device_under_test.On()
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        (result_code, _) = device_under_test.ConfigureScan(json_string)
        time.sleep(CONST_WAIT_TIME)
        assert result_code == ResultCode.OK

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, str(scan_id))

        # Use callable 'Scan'  API
        (result_code, _) = device_under_test.Scan(scan_id_device_data)
        assert result_code == ResultCode.STARTED
        assert device_under_test.obsState == ObsState.SCANNING

        (result_code, _) = device_under_test.EndScan()
        assert device_under_test.obsState == ObsState.READY

        # try reconfiguring and scanning again
        (result_code, _) = device_under_test.ConfigureScan(json_string)
        time.sleep(CONST_WAIT_TIME)
        assert result_code == ResultCode.OK

        (result_code, _) = device_under_test.Scan(scan_id_device_data)
        assert result_code == ResultCode.STARTED
        assert device_under_test.obsState == ObsState.SCANNING
        (result_code, _) = device_under_test.EndScan()
        assert result_code == ResultCode.OK
        assert device_under_test.obsState == ObsState.READY

        (result_code, _) = device_under_test.GoToIdle()
        assert device_under_test.obsState == ObsState.IDLE
        assert result_code == ResultCode.OK

    @pytest.mark.parametrize(
        "sw_config_file_name, \
        config_file_name",
        [
            (
                "Vcc_ConfigureSearchWindow_basic.json",
                "Vcc_ConfigureScan_basic.json",
            )
        ],
    )
    def test_ConfigureSearchWindow_basic(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
        sw_config_file_name: str,
        config_file_name: str,
    ):
        """
        Test a minimal successful search window configuration.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        device_under_test.loggingLevel = LoggingLevel.DEBUG
        device_under_test.On()
        device_under_test.loggingLevel = LoggingLevel.DEBUG
        # set receptorID to 1 to correctly test tdcDestinationAddress
        device_under_test.receptorID = 1
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        device_under_test.ConfigureScan(json_string)
        time.sleep(3)

        # configure search window
        f = open(file_path + sw_config_file_name)
        device_under_test.ConfigureSearchWindow(f.read().replace("\n", ""))
        f.close()
