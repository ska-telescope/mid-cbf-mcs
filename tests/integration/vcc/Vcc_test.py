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
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
import pytest

# SKA specific imports
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

@pytest.mark.usefixtures(
    "create_vcc_proxy",
    "create_band_12_proxy",
    "create_band_3_proxy",
    "create_band_4_proxy",
    "create_band_5_proxy",
    "create_sw_1_proxy"
)

class TestVcc:
    """
    @classmethod
    def mocking(cls):
    """#Mock external libraries.
    """
        # Example : Mock numpy
        # cls.numpy = CspMaster.numpy = MagicMock()
    """

    def test_Vcc_ConfigureScan_basic(
        self,
        create_vcc_proxy,
        create_band_12_proxy,
        create_band_3_proxy,
        create_band_4_proxy,
        create_band_5_proxy
    ):
        """
        Test a minimal successful scan configuration.
        """

        #TODO: The VCC and bands should be in the OFF state 
        # after being initialised, should not have to manually
        # turn off

        create_vcc_proxy.Off()
        time.sleep(2)
        assert create_vcc_proxy.State() == DevState.OFF
        
        time.sleep(2)
        create_band_12_proxy.Off()
        time.sleep(2)
        create_band_3_proxy.Off()
        time.sleep(2)
        create_band_4_proxy.Off()
        time.sleep(2)
        create_band_5_proxy.Off()
        time.sleep(2)

        assert create_band_12_proxy.State() == DevState.OFF
        assert create_band_3_proxy.State() == DevState.OFF
        assert create_band_4_proxy.State() == DevState.OFF
        assert create_band_5_proxy.State() == DevState.OFF

        create_vcc_proxy.On()

        time.sleep(2)

        assert create_vcc_proxy.State() == DevState.ON
        

        config_file_name = "/../../data/Vcc_ConfigureScan_basic.json"
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = copy.deepcopy(json.loads(json_str))
        f.close()

        frequency_band = configuration["frequency_band"]
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        freq_band_name =  frequency_bands[frequency_band]
        create_vcc_proxy.TurnOnBandDevice(freq_band_name)

        time.sleep(2)

        if freq_band_name in ["1", "2"]:
            assert create_band_12_proxy.State() == DevState.ON
            assert create_band_3_proxy.State() == DevState.DISABLE
            assert create_band_4_proxy.State() == DevState.DISABLE
            assert create_band_5_proxy.State() == DevState.DISABLE
        elif freq_band_name == "3":
            assert create_band_12_proxy.State() == DevState.DISABLE
            assert create_band_3_proxy.State() == DevState.ON
            assert create_band_4_proxy.State() == DevState.DISABLE
            assert create_band_5_proxy.State() == DevState.DISABLE
        elif freq_band_name == "4":
            assert create_band_12_proxy.State() == DevState.DISABLE
            assert create_band_3_proxy.State() == DevState.DISABLE
            assert create_band_4_proxy.State() == DevState.ON
            assert create_band_5_proxy.State() == DevState.DISABLE
        elif freq_band_name in ["5a", "5b"]:
            assert create_band_12_proxy.State() == DevState.DISABLE
            assert create_band_3_proxy.State() == DevState.DISABLE
            assert create_band_4_proxy.State() == DevState.DISABLE
            assert create_band_5_proxy.State() == DevState.ON
        else:
            # The frequency band name has been validated at this point
            # so this shouldn't happen
            logging.error("Incorrect frequency band: " + freq_band_name)


        create_vcc_proxy.ConfigureScan(json_str)

        assert create_vcc_proxy.configID == configuration["config_id"]
        assert create_vcc_proxy.frequencyBand == configuration["frequency_band"]
        assert create_vcc_proxy.rfiFlaggingMask == str(configuration["rfi_flagging_mask"])
        if "band_5_tuning" in configuration:
                if create_vcc_proxy.frequencyBand in [4, 5]:
                    band5Tuning_config = configuration["band_5_tuning"]
                    for i in range(0, len(band5Tuning_config)):
                        assert create_vcc_proxy.band5Tuning[i] == band5Tuning_config[i]
        if "frequency_band_offset_stream_1" in configuration:
            assert  create_vcc_proxy.frequencyBandOffsetStream1 == configuration["frequency_band_offset_stream_1"]
        if "frequency_band_offset_stream_2" in configuration:
            assert  create_vcc_proxy.frequencyBandOffsetStream2 == configuration["frequency_band_offset_stream_2"] 
        assert create_vcc_proxy.scfoBand1 == configuration["scfo_band_1"]
        assert create_vcc_proxy.scfoBand2 == configuration["scfo_band_2"]
        assert create_vcc_proxy.scfoBand3 == configuration["scfo_band_3"]
        assert create_vcc_proxy.scfoBand4 == configuration["scfo_band_4"]
        assert create_vcc_proxy.scfoBand5a == configuration["scfo_band_5a"]
        assert create_vcc_proxy.scfoBand5b == configuration["scfo_band_5b"]

        time.sleep(2)

        create_vcc_proxy.TurnOffBandDevice(freq_band_name)

        time.sleep(2)

        if freq_band_name in ["1", "2"]:
            assert create_band_12_proxy.State() == DevState.OFF
        elif freq_band_name == "3":
            assert create_band_3_proxy.State() == DevState.OFF
        elif freq_band_name == "4":
            assert create_band_4_proxy.State() == DevState.OFF
        elif freq_band_name in ["5a", "5b"]:
            assert create_band_5_proxy.State() == DevState.OFF
        else:
            # The frequency band name has been validated at this point
            # so this shouldn't happen
            logging.error("Incorrect frequency band: " + freq_band_name)
        
        time.sleep(2)

        create_vcc_proxy.Off()

        time.sleep(2)

        assert create_vcc_proxy.State() == DevState.OFF