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

# Standard imports
import sys
import os
import time
import json
import copy
import logging

# Path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Tango imports
import tango
from tango import DevState
import pytest

# SKA specific imports
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_tango_base.control_model import LoggingLevel, HealthState
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_base.commands import ResultCode


class TestVcc:
    """
    Test class for Vcc device class integration testing.
    """

    @pytest.mark.parametrize(
        "vcc_id", 
        [4]
    )
    def test_Vcc_ConfigureScan_Scan_EndScan(
        self,
        test_proxies: pytest.fixture,
        vcc_id: int
    ) -> None:
        """
        Test a minimal successful scan configuration.
        """
        # The VCC and bands should be in the ON state after being initialised

        test_proxies.vcc[vcc_id].loggingLevel = LoggingLevel.DEBUG
        test_proxies.vcc[vcc_id].adminMode = AdminMode.ONLINE

        test_proxies.wait_timeout_dev([test_proxies.vcc[vcc_id]], DevState.ON, 3, 1)
        assert test_proxies.vcc[vcc_id].State() == DevState.ON
        
        config_file_name = "Vcc_ConfigureScan_basic.json"
        f = open(data_file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = copy.deepcopy(json.loads(json_str))
        f.close()

        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        frequency_band = configuration["frequency_band"]
        freq_band_index = dict(zip(freq_band_dict().keys(), ['12', '12', '3', '4', '5', '5']))
        test_proxies.vcc[vcc_id].TurnOnBandDevice(frequency_band)
        time.sleep(2)
        assert test_proxies.vcc[vcc_id].frequencyBand == freq_band_dict()[frequency_band]

        for band, proxy in test_proxies.vccBand[vcc_id].items():
            if band == freq_band_index[frequency_band]:
                assert proxy.state() == DevState.ON
            else:
                assert proxy.state() == DevState.OFF

        test_proxies.vcc[vcc_id].ConfigureScan(json_str)
        test_proxies.wait_timeout_obs([test_proxies.vcc[vcc_id]], ObsState.READY, 3, 1)

        assert test_proxies.vcc[vcc_id].configID == configuration["config_id"]
        assert test_proxies.vcc[vcc_id].rfiFlaggingMask == str(configuration["rfi_flagging_mask"])
        if "band_5_tuning" in configuration:
                if test_proxies.vcc[vcc_id].frequencyBand in [4, 5]:
                    band5Tuning_config = configuration["band_5_tuning"]
                    for i in range(0, len(band5Tuning_config)):
                        assert test_proxies.vcc[vcc_id].band5Tuning[i] == band5Tuning_config[i]
        if "frequency_band_offset_stream_1" in configuration:
            assert  test_proxies.vcc[vcc_id].frequencyBandOffsetStream1 == configuration["frequency_band_offset_stream_1"]
        if "frequency_band_offset_stream_2" in configuration:
            assert  test_proxies.vcc[vcc_id].frequencyBandOffsetStream2 == configuration["frequency_band_offset_stream_2"] 
        assert test_proxies.vcc[vcc_id].scfoBand1 == configuration["scfo_band_1"]
        assert test_proxies.vcc[vcc_id].scfoBand2 == configuration["scfo_band_2"]
        assert test_proxies.vcc[vcc_id].scfoBand3 == configuration["scfo_band_3"]
        assert test_proxies.vcc[vcc_id].scfoBand4 == configuration["scfo_band_4"]
        assert test_proxies.vcc[vcc_id].scfoBand5a == configuration["scfo_band_5a"]
        assert test_proxies.vcc[vcc_id].scfoBand5b == configuration["scfo_band_5b"]

        test_proxies.vcc[vcc_id].Scan("1")
        test_proxies.wait_timeout_obs([test_proxies.vcc[vcc_id]], ObsState.SCANNING, 3, 1)
        assert test_proxies.vcc[vcc_id].obsState == ObsState.SCANNING
        test_proxies.vcc[vcc_id].EndScan()
        test_proxies.wait_timeout_obs([test_proxies.vcc[vcc_id]], ObsState.READY, 3, 1)
        assert test_proxies.vcc[vcc_id].obsState == ObsState.READY
        
        test_proxies.vcc[vcc_id].ConfigureScan(json_str)
        test_proxies.wait_timeout_obs([test_proxies.vcc[vcc_id]], ObsState.READY, 3, 1)

        test_proxies.vcc[vcc_id].Scan("1")
        test_proxies.wait_timeout_obs([test_proxies.vcc[vcc_id]], ObsState.SCANNING, 3, 1)
        assert test_proxies.vcc[vcc_id].obsState == ObsState.SCANNING
        test_proxies.vcc[vcc_id].EndScan()
        test_proxies.wait_timeout_obs([test_proxies.vcc[vcc_id]], ObsState.READY, 3, 1)
        assert test_proxies.vcc[vcc_id].obsState == ObsState.READY

        test_proxies.vcc[vcc_id].TurnOffBandDevice(frequency_band)
        time.sleep(2)

        for _, proxy in test_proxies.vccBand[vcc_id].items():
            assert proxy.state() == DevState.OFF

        (result_code, msg) = test_proxies.vcc[vcc_id].Off()
        test_proxies.wait_timeout_dev([test_proxies.vcc[vcc_id]], DevState.OFF, 3, 1)
        assert test_proxies.vcc[vcc_id].State() == DevState.OFF
        assert result_code[0] == ResultCode.OK