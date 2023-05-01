#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Vcc."""

import copy
import json
import os
import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, LoggingLevel, ObsState
from tango import DevState

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

    @pytest.mark.parametrize("vcc_id", [4])
    def test_Vcc_ConfigureScan_Scan_EndScan(
        self, test_proxies: pytest.fixture, vcc_id: int
    ) -> None:
        """
        Test a minimal successful scan configuration.
        """
        wait_time_s = 3
        sleep_time_s = 1

        # Start monitoring the TalonLRUs and power switch devices
        test_proxies.power_switch.adminMode = AdminMode.ONLINE
        for proxy in test_proxies.talon_lru:
            proxy.adminMode = AdminMode.ONLINE

        # The VCC and bands should be in the OFF state after being initialised
        test_proxies.vcc[vcc_id].loggingLevel = LoggingLevel.DEBUG
        test_proxies.vcc[vcc_id].adminMode = AdminMode.ONLINE

        test_proxies.wait_timeout_dev(
            [test_proxies.vcc[vcc_id]], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.vcc[vcc_id].State() == DevState.OFF

        # Turn on the LRUs and then the VCC devices
        for proxy in test_proxies.talon_lru:
            proxy.On()
        test_proxies.vcc[vcc_id].On()
        test_proxies.wait_timeout_dev(
            [test_proxies.vcc[vcc_id]], DevState.ON, wait_time_s, 1
        )
        assert test_proxies.vcc[vcc_id].State() == DevState.ON

        config_file_name = "Vcc_ConfigureScan_basic.json"
        f = open(data_file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = copy.deepcopy(json.loads(json_str))
        f.close()

        frequency_band = configuration["frequency_band"]
        test_proxies.vcc[vcc_id].ConfigureBand(frequency_band)
        time.sleep(2)
        assert (
            test_proxies.vcc[vcc_id].frequencyBand
            == freq_band_dict()[frequency_band]["band_index"]
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
        if "frequency_band_offset_stream_1" in configuration:
            assert (
                test_proxies.vcc[vcc_id].frequencyBandOffsetStream1
                == configuration["frequency_band_offset_stream_1"]
            )
        if "frequency_band_offset_stream_2" in configuration:
            assert (
                test_proxies.vcc[vcc_id].frequencyBandOffsetStream2
                == configuration["frequency_band_offset_stream_2"]
            )

        test_proxies.vcc[vcc_id].Scan("1")
        test_proxies.wait_timeout_obs(
            [test_proxies.vcc[vcc_id]],
            ObsState.SCANNING,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.vcc[vcc_id].obsState == ObsState.SCANNING
        test_proxies.vcc[vcc_id].EndScan()
        test_proxies.wait_timeout_obs(
            [test_proxies.vcc[vcc_id]],
            ObsState.READY,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.vcc[vcc_id].obsState == ObsState.READY

        test_proxies.vcc[vcc_id].ConfigureScan(json_str)
        test_proxies.wait_timeout_obs(
            [test_proxies.vcc[vcc_id]],
            ObsState.READY,
            wait_time_s,
            sleep_time_s,
        )

        test_proxies.vcc[vcc_id].Scan("1")
        test_proxies.wait_timeout_obs(
            [test_proxies.vcc[vcc_id]],
            ObsState.SCANNING,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.vcc[vcc_id].obsState == ObsState.SCANNING
        test_proxies.vcc[vcc_id].EndScan()
        test_proxies.wait_timeout_obs(
            [test_proxies.vcc[vcc_id]],
            ObsState.READY,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.vcc[vcc_id].obsState == ObsState.READY

        test_proxies.vcc[vcc_id].GoToIdle()
        time.sleep(2)

        for proxy in test_proxies.talon_lru:
            proxy.Off()
        (result_code, msg) = test_proxies.vcc[vcc_id].Off()
        test_proxies.wait_timeout_dev(
            [test_proxies.vcc[vcc_id]], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.vcc[vcc_id].State() == DevState.OFF
        assert result_code[0] == ResultCode.OK
