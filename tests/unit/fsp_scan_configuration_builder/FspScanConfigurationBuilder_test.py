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

    def test_set_fsp_mode(self: TestFspScanConfigurationBuilder):
        pass

    def test_set_config(self: TestFspScanConfigurationBuilder):
        pass

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

        if config_name is not None:
            with open(json_file_path + params["configure_scan_file"]) as file:
                json_str = file.read().replace("\n", "")

            full_configuration = json.loads(json_str)
        else:
            full_configuration = None

        builder = fsp_builder()

        with pytest.raises(AssertionError):
            builder.set_fsp_mode(fsp_mode).set_config(
                full_configuration
            ).build()

    @pytest.mark.parametrize(
        "config_name",
        ["ConfigureScan_4_1_CORR.json", "ConfigureScan_1_0_CORR.json"],
    )
    def test_invalid_config(
        self: TestFspScanConfigurationBuilder, config_name: str
    ):
        pass

    @pytest.mark.parametrize(
        "config_name",
        ["ConfigureScan_4_1_CORR.json", "ConfigureScan_1_0_CORR.json"],
    )
    def test_build_valid_corr(
        self: TestFspScanConfigurationBuilder, config_name: str
    ):
        pass
