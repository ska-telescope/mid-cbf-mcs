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

    @pytest.mark.parametrize(
        "params",
        [
            {
                "param_description": "no fsp_mode",
                "fsp_mode": None,
                "config_name": "ConfigureScan_4_1_CORR.json",
            },
            {
                "param_description": "no config",
                "fsp_mode": FspModes.CORR,
                "config_name": None,
            },
            {
                "param_description": "bad config",
                "fsp_mode": FspModes.CORR,
                "config_name": {},
            },
        ],
    )
    def test_build_invalid(
        self: TestFspScanConfigurationBuilder, params: dict
    ):
        fsp_mode = params["fsp_mode"]
        config_name = params["config_name"]

        if type(config_name) is str:
            with open(json_file_path + params["config_name"]) as file:
                json_str = file.read().replace("\n", "")

            full_configuration = json.loads(json_str)
        else:
            full_configuration = params["config_name"]

        builder = fsp_builder()

        with pytest.raises(AssertionError):
            builder.set_fsp_mode(fsp_mode).set_config(
                full_configuration
            ).build()

    def test_invalid_set_fsp_mode(self: TestFspScanConfigurationBuilder):
        builder = fsp_builder()
        with pytest.raises(AssertionError):
            builder.set_fsp_mode(None)

    def test_invalid_set_wideband_shift(self: TestFspScanConfigurationBuilder):
        builder = fsp_builder()
        with pytest.raises(AssertionError):
            builder.set_wideband_shift(None)

    @pytest.mark.parametrize("dish_ids", [None, set()])
    def test_invalid_set_subarray_dish_ids(
        self: TestFspScanConfigurationBuilder, dish_ids
    ):
        builder = fsp_builder()
        with pytest.raises(AssertionError):
            builder.set_subarray_dish_ids(dish_ids)

    def test_invalid_set_config(self: TestFspScanConfigurationBuilder):
        builder = fsp_builder()

        with pytest.raises(AssertionError):
            builder.set_config(None)

    def test_invalid_set_dish_utils(self: TestFspScanConfigurationBuilder):
        builder = fsp_builder()

        with pytest.raises(AssertionError):
            builder.set_dish_utils(None)

    @pytest.mark.parametrize(
        "config_name",
        ["ConfigureScan_4_1_CORR.json", "ConfigureScan_1_0_CORR.json"],
    )
    def test_invalid_config(
        self: TestFspScanConfigurationBuilder, config_name: str
    ):
        pass

    def test_build_corr(self: TestFspScanConfigurationBuilder):
        with open(json_file_path + "ConfigureScan_basic_CORR.json") as file:
            json_str = file.read().replace("\n", "")
            full_configuration = json.loads(json_str)

        print(full_configuration)

        with open(json_file_path + "sys_param_4_boards.json") as file:
            json_str = file.read().replace("\n", "")
            sys_param_configuration = json.loads(json_str)

        builder = fsp_builder()

        # Setup DishUtils
        dish_util = DISHUtils(sys_param_configuration)

        # setup dish_ids
        subarray_dish_ids = list(
            sys_param_configuration["dish_parameters"].keys()
        ).pop()

        builder.set_fsp_mode(FspModes.CORR)
        builder.set_config(full_configuration)
        builder.set_dish_utils(dish_util)
        builder.set_subarray_dish_ids(subarray_dish_ids)
        builder.set_wideband_shift(0)

        # actual_output = builder.build()

        # check outputs
