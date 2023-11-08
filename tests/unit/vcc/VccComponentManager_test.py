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

import json

# Standard imports
import os
import unittest

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager

# Data file paths
file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
vcc_param_path = (
    os.path.dirname(os.path.abspath(__file__)) + "/../../../mnt/vcc_param/"
)


class TestVccComponentManager:
    """
    Test class for VccComponentManager tests.
    """

    def test_init_start_stop_communicating(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
    ) -> None:
        """
        Test component manager initialization and communication establishment.

        :param vcc_component_manager: vcc component manager under test.
        """
        vcc_component_manager.start_communicating()
        assert vcc_component_manager.connected

        vcc_component_manager.stop_communicating()
        assert not vcc_component_manager.connected

    @pytest.mark.parametrize(
        "argin",
        [
            {
                "frequency_band": "1",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "2",
                "dish_sample_rate": 999999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "3",
                "dish_sample_rate": 999999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "4",
                "dish_sample_rate": 999999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "5a",
                "dish_sample_rate": 999999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "5b",
                "dish_sample_rate": 999999,
                "samples_per_frame": 18,
            },
        ],
    )
    def test_configure_band(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        mock_vcc_controller: unittest.mock.Mock,
        mock_vcc_band: unittest.mock.Mock,
        argin: dict,
    ) -> None:
        """
        Test band configuration.

        :param vcc_component_manager: vcc component manager under test.
        :param mock_vcc_controller: VCC controller mock fixture
        :param mock_vcc_band: VCC band mock fixture
        :param argin: frequency band ID, sample rate, num samples per frame
        """
        vcc_component_manager.start_communicating()
        vcc_component_manager.on()

        (result_code, _) = vcc_component_manager.configure_band(
            json.dumps(argin)
        )
        assert result_code == ResultCode.OK

        # Check for band configuration
        mock_vcc_controller.ConfigureBand.assert_next_call(
            freq_band_dict()[argin["frequency_band"]]["band_index"]
        )

        # Check for internal parameter configuration
        internal_params_file_name = (
            vcc_param_path
            + "internal_params_receptor"
            + str(vcc_component_manager.receptor_id)
            + "_band"
            + argin["frequency_band"]
            + ".json"
        )
        with open(internal_params_file_name, "r") as f:
            json_string = f.read()
            args = json.loads(json_string)
            args.update({"dish_sample_rate": argin["dish_sample_rate"]})
            args.update({"samples_per_frame": argin["samples_per_frame"]})
            json_string = json.dumps(args)
        mock_vcc_band.SetInternalParameters.assert_next_call(json_string)

    @pytest.mark.parametrize(
        "config_file_name, \
        jones_matrix_file_name",
        [("Vcc_ConfigureScan_basic.json", "jonesmatrix_unit_test.json")],
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
        vcc_component_manager.on()

        # jones matrix values should be set to "" after init
        assert vcc_component_manager.jones_matrix == ""

        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        vcc_component_manager.configure_band(
            json.dumps(
                {
                    "frequency_band": configuration["frequency_band"],
                    "dish_sample_rate": 999999,
                    "samples_per_frame": 18,
                }
            )
        )

        vcc_component_manager.configure_scan(json_str)

        # read the json file
        f = open(file_path + jones_matrix_file_name)
        input_jones_matrix = f.read().replace("\n", "")
        f.close()
        input_jones_matrix_obj = json.loads(input_jones_matrix)

        # update the Jones matrix
        # Set the receptor id arbitrarily to the first receptor
        # in the Jones matrix
        input_jones_matrix_first_receptor = input_jones_matrix_obj[
            "jones_matrix"
        ][0]
        vcc_component_manager.receptor_id = input_jones_matrix_first_receptor[
            "receptor"
        ][1]
        assert (
            vcc_component_manager.receptor_id
            == input_jones_matrix_first_receptor["receptor"][1]
        )
        vcc_component_manager.update_jones_matrix(input_jones_matrix)

        # check that the Jones matrix is no longer an empty string
        updated_jones_matrix_obj = json.loads(
            vcc_component_manager.jones_matrix
        )
        assert len(updated_jones_matrix_obj) != 0

        # check that the matrix values were copied
        for entry in input_jones_matrix_obj["jones_matrix"]:
            if entry["receptor"][1] == vcc_component_manager.receptor_id:
                input_jones_matrix_for_receptor = json.dumps(entry)
                # the updated Jones matrix for vcc is a single entry
                # for the given receptor and should be the first (only)
                # item in the list of entries allowed by the schema
                updated_jones_matrix_for_vcc = json.dumps(
                    updated_jones_matrix_obj["jones_matrix"][0]
                )
                # compare the Jones matrices as strings
                assert (
                    input_jones_matrix_for_receptor
                    == updated_jones_matrix_for_vcc
                )

    @pytest.mark.parametrize(
        "config_file_name, \
        delay_model_file_name",
        [("Vcc_ConfigureScan_basic.json", "delaymodel_unit_test.json")],
    )
    def test_update_delay_model(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        config_file_name: str,
        delay_model_file_name: str,
    ) -> None:
        """
        Test Vcc's UpdateDelayModel Command.

        :param vcc_component_manager: vcc component manager under test.
        :param config_file_name: JSON file for the configuration
        :param delay_model_file_name: JSON file for the delay model
        """
        vcc_component_manager.start_communicating()
        vcc_component_manager.on()

        # delay model should be empty string after init
        assert vcc_component_manager.delay_model == ""

        f = open(file_path + config_file_name)
        config = f.read().replace("\n", "")
        configuration = json.loads(config)
        f.close()

        vcc_component_manager.configure_band(
            json.dumps(
                {
                    "frequency_band": configuration["frequency_band"],
                    "dish_sample_rate": 999999,
                    "samples_per_frame": 18,
                }
            )
        )

        vcc_component_manager.configure_scan(config)

        # read the json file
        f = open(file_path + delay_model_file_name)
        input_delay_model = f.read().replace("\n", "")
        f.close()
        input_delay_model_obj = json.loads(input_delay_model)

        # update the delay model
        # Set the receptor id arbitrarily to the first receptor
        # in the delay model
        input_delay_model_first_receptor = input_delay_model_obj[
            "delay_details"
        ][0]
        vcc_component_manager.receptor_id = input_delay_model_first_receptor[
            "receptor"
        ][1]
        assert (
            vcc_component_manager.receptor_id
            == input_delay_model_first_receptor["receptor"][1]
        )
        vcc_component_manager.update_delay_model(input_delay_model)

        # check that the delay model is no longer an empty string
        updated_delay_model_obj = json.loads(vcc_component_manager.delay_model)
        assert len(updated_delay_model_obj) != 0

        # check that the coeff values were copied
        for entry in input_delay_model_obj["delay_details"]:
            if entry["receptor"][1] == vcc_component_manager.receptor_id:
                input_delay_model_for_receptor = json.dumps(entry)
                # the updated delay model for vcc is a single entry
                # for the given receptor and should be the first (only)
                # item in the list of entries allowed by the schema
                updated_delay_model_for_vcc = json.dumps(
                    updated_delay_model_obj["delay_details"][0]
                )
                # compare the delay models as strings
                assert (
                    input_delay_model_for_receptor
                    == updated_delay_model_for_vcc
                )

    @pytest.mark.parametrize(
        "config_file_name", ["Vcc_ConfigureScan_basic.json"]
    )
    def test_configure_scan(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        mock_vcc_controller: unittest.mock.Mock,
        mock_vcc_band: unittest.mock.Mock,
        config_file_name: str,
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param vcc_component_manager: vcc component manager under test.
        :param mock_vcc_controller: VCC controller mock fixture
        :param mock_vcc_band: VCC band mock fixture
        :param config_file_name: JSON file for the configuration
        """
        vcc_component_manager.start_communicating()
        vcc_component_manager.on()

        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        vcc_component_manager.configure_band(
            json.dumps(
                {
                    "frequency_band": configuration["frequency_band"],
                    "dish_sample_rate": 999999,
                    "samples_per_frame": 18,
                }
            )
        )
        assert (
            vcc_component_manager.frequency_band
            == freq_band_dict()[configuration["frequency_band"]]["band_index"]
        )

        (result_code, _) = vcc_component_manager.configure_scan(json_str)
        assert result_code == ResultCode.OK
        assert vcc_component_manager.config_id == configuration["config_id"]
        assert (
            vcc_component_manager.stream_tuning
            == configuration["band_5_tuning"]
        )
        assert (
            vcc_component_manager.frequency_band_offset_stream1
            == configuration["frequency_band_offset_stream1"]
        )
        assert (
            vcc_component_manager.frequency_band_offset_stream2
            == configuration["frequency_band_offset_stream2"]
        )
        assert vcc_component_manager.rfi_flagging_mask == str(
            configuration["rfi_flagging_mask"]
        )
        mock_vcc_band.ConfigureScan.assert_next_call(json_str)

        vcc_component_manager.deconfigure()
        assert vcc_component_manager.frequency_band == 0
        assert vcc_component_manager.config_id == ""
        assert vcc_component_manager.stream_tuning == (0, 0)
        assert vcc_component_manager.frequency_band_offset_stream1 == 0
        assert vcc_component_manager.frequency_band_offset_stream2 == 0
        assert vcc_component_manager.rfi_flagging_mask == ""
        # mock_vcc_controller.Unconfigure.assert_next_call() # TODO CIP-1850

    @pytest.mark.parametrize(
        "config_file_name", ["Vcc_ConfigureScan_basic.json"]
    )
    @pytest.mark.skip(reason="Intermittent failure in the pipeline")
    def test_configure_scan_invalid_frequency_band(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        mock_vcc_band: unittest.mock.Mock,
        config_file_name: str,
    ) -> None:
        """
        Test a scan configuration when the frequency band in the argument
        does not match the last configured frequency band.

        :param vcc_component_manager: vcc component manager under test.
        :param mock_vcc_band: VCC band mock fixture
        :param config_file_name: JSON file for the configuration
        """
        vcc_component_manager.start_communicating()
        vcc_component_manager.on()

        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()

        configuration = json.loads(json_str)
        freq_band = freq_band_dict()[configuration["frequency_band"]]

        # Try without configuring the band first
        (result_code, msg) = vcc_component_manager.configure_scan(json_str)
        assert result_code == ResultCode.FAILED
        assert (
            msg == f"Error in Vcc.ConfigureScan; scan configuration "
            f"frequency band {freq_band} not the same as enabled band device 0"
        )
        mock_vcc_band.ConfigureScan.assert_not_called()

        # Configure the band to something different
        other_freq_bands = list(
            set(["1", "2", "3", "4", "5a", "5b"])
            - set(configuration["frequency_band"])
        )
        vcc_component_manager.configure_band(
            json.dumps(
                {
                    "frequency_band": other_freq_bands[0],
                    "dish_sample_rate": 999999,
                    "samples_per_frame": 18,
                }
            )
        )
        assert (
            vcc_component_manager.frequency_band
            == freq_band_dict()[other_freq_bands[0]]["band_index"]
        )

        (result_code, msg) = vcc_component_manager.configure_scan(json_str)
        assert result_code == ResultCode.FAILED
        assert (
            msg == f"Error in Vcc.ConfigureScan; scan configuration "
            f"frequency band {freq_band} not the same as enabled band device "
            f"{vcc_component_manager.frequency_band}"
        )
        mock_vcc_band.ConfigureScan.assert_not_called()

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id",
        [
            ("Vcc_ConfigureScan_basic.json", 1),
            ("Vcc_ConfigureScan_basic.json", 2),
        ],
    )
    def test_scan_end_scan_go_to_idle(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        mock_vcc_band: unittest.mock.Mock,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test Vcc's Scan command state changes.

        :param vcc_component_manager: vcc component manager under test.
        :param mock_vcc_band: VCC band mock fixture
        :param config_file_name: JSON file for the configuration
        :param scan_id: the scan id
        """
        vcc_component_manager.start_communicating()
        vcc_component_manager.on()

        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_string)
        vcc_component_manager.configure_band(
            json.dumps(
                {
                    "frequency_band": configuration["frequency_band"],
                    "dish_sample_rate": 999999,
                    "samples_per_frame": 18,
                }
            )
        )
        vcc_component_manager.configure_scan(json_string)

        # Use callable 'Scan'  API
        (result_code, _) = vcc_component_manager.scan(scan_id)
        assert result_code == ResultCode.STARTED
        assert vcc_component_manager.scan_id == scan_id
        mock_vcc_band.Scan.assert_next_call(scan_id)

        (result_code, _) = vcc_component_manager.end_scan()
        assert result_code == ResultCode.OK
        mock_vcc_band.EndScan.assert_next_call()

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
    def test_configure_search_window(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        sw_config_file_name: str,
        config_file_name: str,
    ):
        """
        Test a minimal successful search window configuration.

        :param vcc_component_manager: vcc component manager under test.
        :param sw_config_file_name: JSON file for the search window configuration
        :param config_file_name: JSON file for the scan configuration
        """
        vcc_component_manager.start_communicating()
        vcc_component_manager.on()

        # set receptorID to 1 to correctly test tdcDestinationAddress
        vcc_component_manager.receptor_id = 1
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        vcc_component_manager.configure_scan(json_string)

        # configure search window
        f = open(file_path + sw_config_file_name)
        (result_code, _) = vcc_component_manager.configure_search_window(
            f.read().replace("\n", "")
        )
        f.close()
        assert result_code == ResultCode.OK

    @pytest.mark.parametrize(
        "argin",
        [
            {
                "frequency_band": "1",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "2",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "3",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "4",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "5a",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
            {
                "frequency_band": "5b",
                "dish_sample_rate": 99999,
                "samples_per_frame": 18,
            },
        ],
    )
    def test_abort_obs_reset(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        mock_vcc_controller: unittest.mock.Mock,
        mock_vcc_band: unittest.mock.Mock,
        argin: dict,
    ) -> None:
        """
        Test Vcc's Abort and ObsReset commands.

        :param vcc_component_manager: vcc component manager under test.
        :param mock_vcc_controller: VCC controller mock fixture
        :param mock_vcc_band: VCC band mock fixture
        :param frequency_band: frequency band ID
        """
        self.test_configure_band(
            vcc_component_manager,
            mock_vcc_controller,
            mock_vcc_band,
            argin,
        )

        (result_code, _) = vcc_component_manager.abort()
        # mock_vcc_band.Abort.assert_next_call() # TODO CIP-1850
        assert result_code == ResultCode.OK

        (result_code, _) = vcc_component_manager.obsreset()
        assert result_code == ResultCode.OK
        # mock_vcc_band.ObsReset.assert_next_call() # TODO CIP-1850
