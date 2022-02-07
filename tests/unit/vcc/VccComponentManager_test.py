#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the Vcc component manager."""

from __future__ import annotations

from typing import List

# Standard imports
import os
import time
import json
import pytest

import tango

from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# Data file path
file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

class TestVccComponentManager:
    """
    Test class for VccComponentManager tests.
    """

    def test_init_start_stop_communicating(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        tango_harness: TangoHarness
    ) -> None:
        """
        Test component manager initialization and communication establishment 
        with subordinate devices.

        :param vcc_component_manager: vcc component manager under test.
        """
        vcc_component_manager.start_communicating()
        assert vcc_component_manager.connected

        vcc_component_manager.stop_communicating()

        assert not vcc_component_manager.connected

    @pytest.mark.parametrize(
        "frequency_band", 
        ["5a"]
    )
    def test_turn_on_off_band_device(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        tango_harness: TangoHarness,
        frequency_band: str
    ) -> None:
        """
        Test turning on band device.

        :param vcc_component_manager: vcc component manager under test.
        :param frequency_band: frequency band ID
        """
        vcc_component_manager.start_communicating()
        (result_code, msg) = vcc_component_manager.turn_on_band_device(frequency_band)
        assert result_code == ResultCode.OK
        (result_code, msg) = vcc_component_manager.turn_off_band_device(frequency_band)
        assert result_code == ResultCode.OK


    @pytest.mark.parametrize(
        "config_file_name, \
        jones_matrix_file_name", 
        [
            (
                "Vcc_ConfigureScan_basic.json",
                "jonesmatrix_unit_test.json"
            )
        ]
    )
    def test_update_jones_matrix(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        config_file_name: str,
        jones_matrix_file_name: str,
    ) -> None:
        """
        Test Vcc's UpdateJonesMatrix command

        :param vcc_component_manager: vcc component manager under test.
        :param config_file_name: JSON file for the configuration
        :param jones_matrix_file_name: JSON file for the jones matrix
        """
        vcc_component_manager.start_communicating()

        # jones matrix values should be set to 0.0 after init
        num_cols = 16
        num_rows = 26
        assert vcc_component_manager.jones_matrix == [[0.0] * num_cols for _ in range(num_rows)]
        
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        vcc_component_manager.turn_on_band_device(configuration["frequency_band"])

        vcc_component_manager.configure_scan(json_str)

        # read the json file
        f = open(file_path + jones_matrix_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        jones_matrix = json.loads(json_str)

        # update the jones matrix
        for m in jones_matrix["jonesMatrix"]:
            vcc_component_manager.update_jones_matrix(json.dumps(m["matrixDetails"]))
        
        min_fs_id = 1
        max_fs_id = 26
        matrix_len = 16 
        for m in jones_matrix["jonesMatrix"]:
            for receptor in m["matrixDetails"]:
                rec_id = receptor["receptor"]
                if rec_id == vcc_component_manager.receptor_id:
                    for frequency_slice in receptor["receptorMatrix"]:
                        fs_id = frequency_slice["fsid"]
                        matrix = frequency_slice["matrix"]
                        if min_fs_id <= fs_id <= max_fs_id and len(matrix) == matrix_len:
                            assert list(vcc_component_manager.jones_matrix[fs_id - 1]) == list(matrix)


    @pytest.mark.parametrize(
        "config_file_name, \
        delay_model_file_name", 
        [
            (
                "Vcc_ConfigureScan_basic.json",
                "delaymodel_unit_test.json"
            )
        ]
    )
    def test_update_delay_model(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        config_file_name: str,
        delay_model_file_name: str
    ) -> None:
        """
        Test Vcc's UpdateDelayModel Command.

        :param vcc_component_manager: vcc component manager under test.
        :param config_file_name: JSON file for the configuration
        :param delay_model_file_name: JSON file for the delay model
        """

        # delay model values should be set to 0.0 after init
        num_cols = 6
        num_rows = 26
        assert vcc_component_manager.delay_model == [[0] * num_cols for i in range(num_rows)]
        
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        vcc_component_manager.turn_on_band_device(configuration["frequency_band"])

        vcc_component_manager.configure_scan(json_str)
        
        # read the json file
        f = open(file_path + delay_model_file_name)
        json_str_model = f.read().replace("\n", "")
        f.close()
        delay_model = json.loads(json_str_model)

        # update the delay model
        for m in delay_model["delayModel"]:
            vcc_component_manager.receptor_id = m["delayDetails"][0]["receptor"]
            assert vcc_component_manager.receptor_id == m["delayDetails"][0]["receptor"]
            vcc_component_manager.update_delay_model(json.dumps(m["delayDetails"]))
        
        min_fs_id = 1
        max_fs_id = 26
        model_len = 6
        for m in delay_model["delayModel"]:
            for delayDetails in m["delayDetails"]:
                for frequency_slice in delayDetails["receptorDelayDetails"]:
                    fs_id = frequency_slice["fsid"]
                    coeff = frequency_slice["delayCoeff"]
                    if min_fs_id <= fs_id <= max_fs_id and len(coeff) == model_len:
                        assert vcc_component_manager.delay_model[fs_id - 1] == frequency_slice["delayCoeff"] 

    @pytest.mark.parametrize(
        "config_file_name",
        [
            (
                "Vcc_ConfigureScan_basic.json"
            )
        ]
    )
    def test_configure_scan(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        config_file_name: str
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param vcc_component_manager: vcc component manager under test.
        :param config_file_name: JSON file for the configuration 
        """
        vcc_component_manager.start_communicating()
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        vcc_component_manager.turn_on_band_device(configuration["frequency_band"])
        assert vcc_component_manager.frequency_band == freq_band_dict()[configuration["frequency_band"]]

        (result_code, msg) = vcc_component_manager.configure_scan(json_str)
        assert result_code == ResultCode.OK
        assert vcc_component_manager.config_id == configuration["config_id"]
        assert vcc_component_manager.stream_tuning == configuration["band_5_tuning"]
        assert vcc_component_manager.frequency_band_offset_stream_1 == configuration["frequency_band_offset_stream_1"]
        assert vcc_component_manager.frequency_band_offset_stream_2 == configuration["frequency_band_offset_stream_2"]
        assert vcc_component_manager.rfi_flagging_mask == str(configuration["rfi_flagging_mask"])



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
            )
        ]
    )
    def test_scan_end_scan_go_to_idle(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        config_file_name: str,
        scan_id: int
    ) -> None:
        """
        Test Vcc's Scan command state changes.

        :param vcc_component_manager: vcc component manager under test.
        :param config_file_name: JSON file for the configuration
        :param scan_id: the scan id
        """
        vcc_component_manager.start_communicating()
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        vcc_component_manager.configure_scan(json_string)

        # Use callable 'Scan'  API
        (result_code, msg) = vcc_component_manager.scan(scan_id)
        assert result_code == ResultCode.STARTED
        assert vcc_component_manager.scan_id == scan_id

        (result_code, msg) = vcc_component_manager.end_scan()
        assert result_code == ResultCode.OK


    @pytest.mark.parametrize(
        "sw_config_file_name, \
        config_file_name",
        [
            (
                "Vcc_ConfigureSearchWindow_basic.json",
                "Vcc_ConfigureScan_basic.json"
            )
        ]
    )
    def test_configure_search_window(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        sw_config_file_name: str,
        config_file_name: str
    ):
        """
        Test a minimal successful search window configuration.

        :param vcc_component_manager: vcc component manager under test.
        :param sw_config_file_name: JSON file for the search window configuration
        :param config_file_name: JSON file for the scan configuration
        """
        vcc_component_manager.start_communicating()
        # set receptorID to 1 to correctly test tdcDestinationAddress
        vcc_component_manager.receptor_id = 1
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        vcc_component_manager.configure_scan(json_string)

        # configure search window
        f = open(file_path + sw_config_file_name)
        (result_code, msg) = vcc_component_manager.configure_search_window(f.read().replace("\n", ""))
        f.close()
        assert result_code == ResultCode.OK
