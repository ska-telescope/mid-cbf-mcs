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

import json
import os

import pytest

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import FspModes
from ska_mid_cbf_mcs.fsp_scan_configuration_builder.builder import (
    FspScanConfigurationBuilder as fsp_builder,
)

# from ska_mid_cbf_mcs.commons.fine_channel_partitioner import (
#     calculate_fs_info,
#     get_coarse_channels,
#     get_end_freqeuency,
# )

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
            )

    @pytest.mark.parametrize(
        "config_name",
        [
            "ConfigureScan_basic_CORR.json",
            "ConfigureScan_4_1_CORR.json",
            "ConfigureScan_AA4_values.json",
        ],
    )
    def test_build_corr(self: TestFspScanConfigurationBuilder, config_name):
        # Setup configuration
        with open(json_file_path + config_name) as file:
            json_str = file.read().replace("\n", "")
            full_configuration = json.loads(json_str)

        corr_config = full_configuration["midcbf"]["correlation"]

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
        )

        actual_output = builder.build()

        total_fsps = 0
        total_expected_output_ports = 0
        for pr_config in corr_config["processing_regions"]:
            total_fsps += len(pr_config["fsp_ids"])
            if "output_port" in pr_config:
                total_expected_output_ports += len(pr_config["output_port"])

        assert len(actual_output) == total_fsps

        # assert values set
        total_actual_output_ports = 0
        for fsp in actual_output:
            assert fsp["function_mode"] == FspModes.CORR.name

            if "output_port" in pr_config:
                total_actual_output_ports += len(fsp["output_port"])

        if "output_port" in pr_config:
            assert total_expected_output_ports == total_actual_output_ports
