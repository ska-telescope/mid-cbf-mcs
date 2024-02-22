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
import time

import pytest
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from tango import DeviceData, DevShort, DevState

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

# Standard imports

# Path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# Tango imports

# SKA specific imports


class TestVcc:
    """
    Test class for Vcc device class integration testing.
    """

    @pytest.mark.parametrize("vcc_id", [1])
    def test_Connect(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id
        """
        wait_time_s = 3
        sleep_time_s = 1

        # Start monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.ONLINE

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.ONLINE
            proxy.set_timeout_millis(10000)

        # The VCC and bands should be in the OFF state after being initialised
        test_proxies.vcc[vcc_id].loggingLevel = LoggingLevel.DEBUG
        test_proxies.vcc[vcc_id].adminMode = AdminMode.ONLINE

        test_proxies.wait_timeout_dev(
            [test_proxies.vcc[vcc_id]], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.vcc[vcc_id].State() == DevState.OFF

    @pytest.mark.parametrize("vcc_id", [1])
    def test_On(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id
        """
        wait_time_s = 3
        sleep_time_s = 1

        device_under_test = test_proxies.vcc[vcc_id]

        # Turn on the LRUs and then the VCC devices
        for proxy in test_proxies.talon_lru:
            proxy.On()
        device_under_test.On()
        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.ON, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.ON

    @pytest.mark.parametrize("vcc_id", [1])
    def test_Off(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test the "Off" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.vcc[vcc_id]

        device_under_test.Off()

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize("vcc_id", [1])
    def test_Standby(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test the "Standby" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.vcc[vcc_id]

        device_under_test.Standby()

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.STANDBY, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.STANDBY

    @pytest.mark.parametrize(
        "config_file_name, \
        vcc_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_ConfigureScan(
        self: TestVcc,
        test_proxies: pytest.fixture,
        config_file_name: str,
        vcc_id: int,
    ) -> None:
        """
        Test the "ConfigureScan" command

        :param test_proxies: the proxies test fixture
        :param config_file_name: the name of the JSON file
            containing the configuration
        :param vcc_id: the fsp id

        """

        device_under_test = test_proxies.vcc[vcc_id]
        wait_time_s = 1
        sleep_time_s = 1

        assert device_under_test.adminMode == AdminMode.ONLINE

        device_under_test.On()

        f = open(data_file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = copy.deepcopy(json.loads(json_str))
        f.close()

        band_configuration = {
            "frequency_band": configuration["frequency_band"],
            "dish_sample_rate": 999999,
            "samples_per_frame": 18,
        }
        test_proxies.vcc[vcc_id].ConfigureBand(json.dumps(band_configuration))
        time.sleep(2)
        assert (
            test_proxies.vcc[vcc_id].frequencyBand
            == freq_band_dict()[configuration["frequency_band"]]["band_index"]
        )

        test_proxies.vcc[vcc_id].ConfigureScan(json_str)
        test_proxies.wait_timeout_obs(
            [test_proxies.vcc[vcc_id]],
            ObsState.READY,
            wait_time_s,
            sleep_time_s,
        )

        assert test_proxies.vcc[vcc_id].configID == configuration["config_id"]
        assert test_proxies.vcc[vcc_id].rfiFlaggingMask == str(
            configuration["rfi_flagging_mask"]
        )
        if "band_5_tuning" in configuration:
            if test_proxies.vcc[vcc_id].frequencyBand in [4, 5]:
                band5Tuning_config = configuration["band_5_tuning"]
                for i in range(0, len(band5Tuning_config)):
                    assert (
                        test_proxies.vcc[vcc_id].band5Tuning[i]
                        == band5Tuning_config[i]
                    )
        if "frequency_band_offset_stream1" in configuration:
            assert (
                test_proxies.vcc[vcc_id].frequencyBandOffsetStream1
                == configuration["frequency_band_offset_stream1"]
            )
        if "frequency_band_offset_stream2" in configuration:
            assert (
                test_proxies.vcc[vcc_id].frequencyBandOffsetStream2
                == configuration["frequency_band_offset_stream2"]
            )

        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize(
        "vcc_id, \
        scan_id",
        [(1, 1)],
    )
    def test_Scan(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int, scan_id: int
    ) -> None:
        """
        Test the "Scan" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        wait_time_s = 1
        sleep_time_s = 1

        device_under_test = test_proxies.vcc[vcc_id]

        assert device_under_test.adminMode == AdminMode.ONLINE

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.ON, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.ON

        scan_id_device_data = DeviceData()
        scan_id_device_data.insert(DevShort, scan_id)

        device_under_test.Scan(scan_id_device_data)

        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.SCANNING, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.SCANNING

        assert device_under_test.scanID == scan_id

    @pytest.mark.parametrize("vcc_id", [1])
    def test_EndScan(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test the "EndScan" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        wait_time_s = 1
        sleep_time_s = 1

        device_under_test = test_proxies.vcc[vcc_id]

        assert device_under_test.adminMode == AdminMode.ONLINE

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.ON, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.ON

        device_under_test.EndScan()
        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.READY, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize("vcc_id", [1])
    def test_GoToIdle(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test the "GoToIdle" command

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """
        wait_time_s = 1
        sleep_time_s = 1

        device_under_test = test_proxies.vcc[vcc_id]

        assert device_under_test.adminMode == AdminMode.ONLINE

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.ON, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.ON

        device_under_test.GoToIdle()

        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.IDLE, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.IDLE
    
    @pytest.mark.parametrize(
        "config_file_name, \
        vcc_id",
        [("Vcc_ConfigureScan_basic.json", 1)],
    )
    def test_OffFromFault(
        self: TestVcc,
        test_proxies: pytest.fixture,
        config_file_name: str,
        vcc_id: int,
    ) -> None:
        """
        Verify the component manager can execute Off after the device has been put into fault state.

        :param vcc_id: the fsp id

        """

        device_under_test = test_proxies.vcc[vcc_id]
        wait_time_s = 1
        sleep_time_s = 1

        assert device_under_test.adminMode == AdminMode.ONLINE

        # abort from READY
        self.test_ConfigureScan(test_proxies, config_file_name, vcc_id)
        
        device_under_test.Off()

        # controller device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.OFF

        # Stop monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.OFFLINE

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.OFFLINE
            proxy.set_timeout_millis(10000)

    @pytest.mark.parametrize(
        "config_file_name, \
        vcc_id, \
        scan_id",
        [("Vcc_ConfigureScan_basic.json", 1, 1)],
    )
    def test_Abort_ObsReset(
        self: TestVcc,
        test_proxies: pytest.fixture,
        config_file_name: str,
        vcc_id: int,
        scan_id: int,
    ) -> None:
        """
        Test the "ConfigureScan" command

        :param test_proxies: the proxies test fixture
        :param config_file_name: the name of the JSON file
            containing the configuration
        :param vcc_id: the fsp id

        """

        device_under_test = test_proxies.vcc[vcc_id]
        wait_time_s = 1
        sleep_time_s = 1

        assert device_under_test.adminMode == AdminMode.ONLINE

        # abort from READY
        self.test_ConfigureScan(test_proxies, config_file_name, vcc_id)

        device_under_test.Abort()
        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.ABORTED, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.ABORTED

        device_under_test.ObsReset()
        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.IDLE, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.IDLE

        # abort from SCANNING
        self.test_ConfigureScan(test_proxies, config_file_name, vcc_id)
        self.test_Scan(test_proxies, vcc_id, scan_id)

        device_under_test.Abort()
        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.ABORTED, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.ABORTED

        device_under_test.ObsReset()
        test_proxies.wait_timeout_obs(
            [device_under_test], ObsState.IDLE, wait_time_s, sleep_time_s
        )
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize("vcc_id", [1])
    def test_Disconnect(
        self: TestVcc, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Verify the component manager can stop communicating

        :param test_proxies: the proxies test fixture
        :param vcc_id: the fsp id

        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.vcc[vcc_id]

        device_under_test.Off()

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.DISABLE, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.DISABLE

        # Stop monitoring the TalonLRUs and power switch devices
        for proxy in test_proxies.power_switch:
            proxy.adminMode = AdminMode.OFFLINE

        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.OFFLINE
            proxy.set_timeout_millis(10000)
