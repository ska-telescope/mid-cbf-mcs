#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the FspScanConfigurationBuilder"""
from __future__ import annotations

import copy
import json
import os

import pytest

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import FspModes
from ska_mid_cbf_mcs.subarray.fsp_scan_configuration_builder.builder import (
    FspScanConfigurationBuilder as fsp_builder,
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
        corr_config = {}

        # Setup subarray & dish_utils
        with open(json_file_path + "sys_param_4_boards.json") as file:
            json_str = file.read().replace("\n", "")
            sys_param_configuration = json.loads(json_str)
        subarray_dish_ids = list(
            sys_param_configuration["dish_parameters"].keys()
        )
        dish_util = DISHUtils(sys_param_configuration)

        with pytest.raises(ValueError):
            fsp_builder(
                function_mode=FspModes.CORR,
                function_configuration=corr_config,
                dish_utils=dish_util,
                subarray_dish_ids=subarray_dish_ids,
                wideband_shift=0,
                frequency_band="1",
            )

    @pytest.mark.parametrize(
        "config_name",
        [
            "ConfigureScan_basic_CORR.json",
            "ConfigureScan_4_1_CORR.json",
            "ConfigureScan_AA4_values.json",
            "ConfigureScan_CORR_2_non_overlapping_band_2_PRs.json",
            "ConfigureScan_CORR_2_overlapping_band_2_PRs.json",
        ],
    )
    def test_build_corr(self: TestFspScanConfigurationBuilder, config_name):
        # Assumption: Enough fsp_ids in the processing region to config the PR
        # Assumption: No extra fsp ids (that would end up being un-unconfigured)
        # Assumption: No duplicate fsp_ids between processing regions

        # Setup configuration
        with open(json_file_path + config_name) as file:
            json_str = file.read().replace("\n", "")
            full_configuration = json.loads(json_str)

        corr_config = full_configuration["midcbf"]["correlation"]
        common_config = full_configuration["common"]

        # Setup subarray & dish_utils
        with open(json_file_path + "sys_param_4_boards.json") as file:
            json_str = file.read().replace("\n", "")
            sys_param_configuration = json.loads(json_str)
        subarray_dish_ids = list(
            sys_param_configuration["dish_parameters"].keys()
        )
        dish_util = DISHUtils(sys_param_configuration)

        builder = fsp_builder(
            function_mode=FspModes.CORR,
            function_configuration=corr_config,
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
        for index, pr_config in enumerate(corr_config["processing_regions"]):
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

            assert fsp["function_mode"] == FspModes.CORR.name
            assert (
                fsp["integration_factor"]
                == corr_config["processing_regions"][pr_index][
                    "integration_factor"
                ]
            )
            assert (
                fsp["output_link_map"]
                == corr_config["processing_regions"][pr_index][
                    "output_link_map"
                ]
            )

            if "output_host" in corr_config["processing_regions"][pr_index]:
                assert (
                    fsp["output_host"]
                    == corr_config["processing_regions"][pr_index][
                        "output_host"
                    ]
                )

            assert fsp["fsp_id"] in all_fsp_ids
            all_fsp_ids.remove(fsp["fsp_id"])

            assert "channel_offset" in fsp

        # Assert that all PR-fsps_ids got configured
        assert len(fsp_to_pr) == len(
            corr_config["processing_regions"]
        ), "There are PRs that didn't get any configured FSP"

        for pr_index, pr_config in enumerate(
            corr_config["processing_regions"]
        ):
            # Assert all ports accounted for in configured FSP's
            if "output_port" in pr_config:
                expected_output_port = copy.deepcopy(pr_config["output_port"])
                for fsp_config in fsp_to_pr[pr_index]:
                    actual_output_ports = fsp_config["output_port"]
                    for port in actual_output_ports:
                        fsp_id = fsp_config["fsp_id"]
                        assert (
                            port in expected_output_port
                        ), f"Assigned output_port in FSP: {fsp_id}, was not expected for PR index {index}, or was duplicated from another FSP"
                        expected_output_port.remove(port)
                assert (
                    len(expected_output_port) == 0
                ), f"There are unassigned output_ports for PR index {index}"

            # Assert vcc to rdt shift values set for all receptors
            if "receptors" in pr_config:
                receptor_list = pr_config["receptors"]
            else:
                receptor_list = subarray_dish_ids

            for fsp_config in fsp_to_pr[pr_index]:
                for receptor in receptor_list:
                    vcc_id = dish_util.dish_id_to_vcc_id[receptor]

                    # Note, hps wants vcc in the vcc_id_to_rdt_freq_shifts dict
                    # to be a string
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
