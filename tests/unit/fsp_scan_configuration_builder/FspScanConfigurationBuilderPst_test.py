#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the FspScanConfigurationBuilderCorr"""
from __future__ import annotations

import copy
import json
import os

import pytest
from ska_telmodel import channel_map

from ska_mid_cbf_tdc_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.builder_pst import (
    FspScanConfigurationBuilderPst as fsp_builder,
)

# Paths
file_path = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestFspScanConfigurationBuilder:
    """
    Test class for FspScanConfigurationBuilder.
    """

    def test_invalid_config(self: TestFspScanConfigurationBuilder):
        # missing processing_regions
        pst_config = {}

        # Setup subarray & dish_utils
        with open(json_file_path + "sys_param_8_boards.json") as file:
            json_str = file.read().replace("\n", "")
            sys_param_configuration = json.loads(json_str)
        subarray_dish_ids = list(
            sys_param_configuration["dish_parameters"].keys()
        )
        dish_util = DISHUtils(sys_param_configuration)

        with pytest.raises(ValueError):
            fsp_builder(
                function_configuration= pst_config,
                dish_utils=dish_util,
                subarray_dish_ids=subarray_dish_ids,
                wideband_shift=0,
                frequency_band="1",
            )

    def test_build_invalid_receptor_not_in_subarray_receptors(
        self: TestFspScanConfigurationBuilder,
    ):
        # Setup configuration
        with open(json_file_path + "ConfigureScan_basic_PST.json") as file:
            json_str = file.read().replace("\n", "")
            full_configuration = json.loads(json_str)

        pst_config = full_configuration["midcbf"]["pst_bf"]

        # add bad receptor
        pst_config["processing_regions"][0]["timing_beams"][0]["receptors"] = ["SKA999"]

        # Setup subarray & dish_utils
        with open(json_file_path + "sys_param_8_boards.json") as file:
            json_str = file.read().replace("\n", "")
            sys_param_configuration = json.loads(json_str)
        subarray_dish_ids = list(
            sys_param_configuration["dish_parameters"].keys()
        )
        dish_util = DISHUtils(sys_param_configuration)

        with pytest.raises(ValueError):
            fsp_builder(
                function_configuration=pst_config,
                dish_utils=dish_util,
                subarray_dish_ids=subarray_dish_ids,
                wideband_shift=0,
                frequency_band="1",
            ).build()

    @pytest.mark.parametrize(
        "config_name",
        [
            "ConfigureScan_basic_PST.json",
            # "ConfigureScan_4_1_CORR.json",
            # "ConfigureScan_AA4_values.json",
            # "ConfigureScan_CORR_2_non_overlapping_band_2_PRs.json",
            # "ConfigureScan_CORR_2_overlapping_band_2_PRs.json",
        ],
    )
    def test_build_pst(self: TestFspScanConfigurationBuilder, config_name):
        # Assumption: Enough fsp_ids in the processing region to config the PR
        # Assumption: No extra fsp ids (that would end up being un-unconfigured)
        # Assumption: No duplicate fsp_ids between processing regions

        # Setup configuration
        with open(json_file_path + config_name) as file:
            json_str = file.read().replace("\n", "")
            full_configuration = json.loads(json_str)

        pst_config = full_configuration["midcbf"]["pst_bf"]
        common_config = full_configuration["common"]

        # Setup subarray & dish_utils
        with open(json_file_path + "sys_param_8_boards.json") as file:
            json_str = file.read().replace("\n", "")
            sys_param_configuration = json.loads(json_str)
        subarray_dish_ids = list(
            sys_param_configuration["dish_parameters"].keys()
        )
        dish_util = DISHUtils(sys_param_configuration)

        builder = fsp_builder(
            function_configuration=pst_config,
            dish_utils=dish_util,
            subarray_dish_ids=subarray_dish_ids,
            wideband_shift=0,
            frequency_band=common_config["frequency_band"],
        )

        # Run function
        actual_output = builder.build()

        # Setup expectations
        total_fsps = 0
        fsp_id_to_pr_map = {}
        all_fsp_ids = set()
        for index, pr_config in enumerate(pst_config["processing_regions"]):
            total_fsps += len(pr_config["fsp_ids"])
            # Just so we can refer back to the PR when comparing output
            for fsp_id in pr_config["fsp_ids"]:
                fsp_id_to_pr_map[fsp_id] = index
                all_fsp_ids.add(fsp_id)

        # assert actual values set
        assert len(actual_output) == total_fsps
        fsp_to_pr = {}
        for fsp in actual_output:
            pr_index = fsp_id_to_pr_map[fsp["fsp_id"]]

            # group fsp configs to the pr
            if pr_index not in fsp_to_pr:
                fsp_to_pr[pr_index] = []
            fsp_to_pr[pr_index].append(fsp)

            assert fsp["function_mode"] == FspModes.PST.name
            assert (
                # Given MCS only supports 1 link mapping of link = 1, we should
                # always get [[0,1]] for all fsp output_link_maps
                fsp["output_link_map"]
                == [[fsp["fs_start_channel_offset"], 1]]
            )

            assert fsp["fsp_id"] in all_fsp_ids
            all_fsp_ids.remove(fsp["fsp_id"])
            
        # Assert that all PR-fsps_ids got configured
        assert len(fsp_to_pr) == len(
            pst_config["processing_regions"]
        ), "There are PRs that didn't get any configured FSP"

        for pr_index, pr_config in enumerate(
            pst_config["processing_regions"]
        ):
            # Assert all ports accounted for in configured FSP's
            if "output_port" in pr_config:
                expected_output_ports = copy.deepcopy(pr_config["output_port"])
                expected_ports = [
                    output_port[1] for output_port in expected_output_ports
                ]
                for fsp_config in fsp_to_pr[pr_index]:
                    actual_output_ports = fsp_config["output_port"]

                    for port in actual_output_ports:
                        # we expect the port in the PR config ports
                        fsp_id = fsp_config["fsp_id"]
                        assert (
                            port[1] in expected_ports
                        ), f"Assigned output_port in FSP: {fsp_id}, was not expected for PR index {index}, or was duplicated from another FSP"
                        index_of_port = expected_ports.index(port[1])
                        expected_ports.pop(index_of_port)

                        # the port is assigned to an output host
                        # and matches the pr output_host config
                        if "output_host" in fsp_config:
                            fsp_ip = channel_map.channel_map_at(
                                fsp_config["output_host"], port[0]
                            )

                            # trick, we want the absolute sdp_start_channel_id,
                            # but we can get it from the channel_offset
                            # and the fs_start_channel_offset
                            fsp_sdp_start_channel_id = (
                                fsp_config["spead_channel_offset"]
                                + fsp_config["fs_start_channel_offset"]
                            )

                            # shift the channel by the absolute sdp_start_channel_id
                            # and look up the channel_id in the pr.output_host map
                            pr_ip = channel_map.channel_map_at(
                                pr_config["output_host"],
                                port[0] + fsp_sdp_start_channel_id,
                            )

                            # They should result in the same mapped ip value
                            assert (
                                fsp_ip == pr_ip
                            ), f"output_port {port} of fsp_id: {fsp_id} does not map to the same fsp ip {fsp_ip} as the processing region ip {fsp_ip}"
                assert (
                    len(expected_ports) == 0
                ), f"There are unassigned output_ports for PR index {index}"

            for fsp_config in fsp_to_pr[pr_index]:
                # Assert VCC to RDT shift and 16k FC gain values set for all
                # subarray receptors
                for receptor in subarray_dish_ids:
                    vcc_id = dish_util.dish_id_to_vcc_id[receptor]

                    # NOTE: HPS wants the VCC ID key in the dict to be a string
                    vcc_id_str = str(vcc_id)
                    assert (
                        vcc_id_str in fsp_config["vcc_id_to_rdt_freq_shifts"]
                    )
                    vcc_id_shift_config = fsp_config[
                        "vcc_id_to_rdt_freq_shifts"
                    ][vcc_id_str]
                    assert "freq_down_shift" in vcc_id_shift_config
                    assert "freq_align_shift" in vcc_id_shift_config
                    assert "freq_wb_shift" in vcc_id_shift_config
                    assert "freq_scfo_shift" in vcc_id_shift_config

                # assert the receptors are set if they are set in the PR, else
                # they are the subarray receptors
                for timing_beam_index, timing_beam in enumerate(fsp_config["timing_beams"]):
                    assert "receptors" in timing_beam
                    if "receptors" in pr_config["timing_beams"][timing_beam_index]:
                        assert timing_beam["receptors"] == pr_config["timing_beams"][timing_beam_index]["receptors"]
                    else:
                        assert timing_beam["receptors"] == subarray_dish_ids
