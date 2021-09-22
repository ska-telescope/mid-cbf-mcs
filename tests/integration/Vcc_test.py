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

    def test_ConfigureScan(
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

        assert create_vcc_proxy.State() == DevState.OFF

        create_vcc_proxy.On()

        time.sleep(2)

        assert create_vcc_proxy.State() == DevState.ON
        

        config_file_name = "/../data/ConfigureScan_basic.json"
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        full_configuration = json.loads(json_str)
        common_configuration = copy.deepcopy(full_configuration["common"])
        cbf_configuration = copy.deepcopy(full_configuration["cbf"])
        f.close()

        freq_band_name = common_configuration["frequency_band"]
        create_vcc_proxy.TurnOnBandDevice(freq_band_name)

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

        if "config_id" in common_configuration:
            assert create_vcc_proxy.configID == common_configuration["config_id"]
        if "frequency_band" in common_configuration:
            assert create_vcc_proxy.frequencyBand == freq_band_dict()[common_configuration["frequency_band"]]
        
        if "rfi_flagging_mask" in cbf_configuration:
            assert create_vcc_proxy.rfiFlaggingMask == str(cbf_configuration["rfi_flagging_mask"])
        if "frequency_band_offset_stream_1" in cbf_configuration:
            assert  create_vcc_proxy.frequencyBandOffsetStream1 == cbf_configuration["frequency_band_offset_stream_1"]
        if "frequency_band_offset_stream_2" in cbf_configuration:
            assert  create_vcc_proxy.frequencyBandOffsetStream2 == cbf_configuration["frequency_band_offset_stream_2"] 
        if "scfo_band_1" in cbf_configuration:
            assert create_vcc_proxy.scfoBand1 == cbf_configuration["scfo_band_1"]

        time.sleep(2)

        create_vcc_proxy.Off()

        time.sleep(2)

        assert create_vcc_proxy.State() == DevState.OFF
