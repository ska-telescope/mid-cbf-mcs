#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the fine_channel_partitioner"""

import os

import pytest

from ska_mid_cbf_tdc_mcs.commons.global_enum import const
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.fine_channel_partitioner import (
    partition_spectrum_to_frequency_slices,
)

# Paths
file_path = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

valid_fsp_ids = [1, 2, 3, 4, 5, 6]
valid_channel_width = const.FINE_CHANNEL_WIDTH
valid_start_freq = int(350e6)
valid_wb_shift = int(52.7e6)
valid_channel_count = 58980
valid_k_value = 1000
valid_frequency_band_name = "1"


@pytest.mark.parametrize(
    "parameters",
    [
        {
            "description": "within single FS",
            "start_freq": 350000000,
            "channel_count": 600,
            "fsp_ids": [1],
            "wideband_shift": 0,
            "band_name": "1",
        },
        {
            "description": "within single FS with wideband shift",
            "start_freq": 350000000,
            "channel_count": 600,
            "fsp_ids": [1],
            "wideband_shift": int(52.7e6),
            "band_name": "1",
        },
        {
            "description": "full single FS with wideband shift",
            "start_freq": 297271296,
            "channel_count": 14740,
            "fsp_ids": [2],
            "wideband_shift": 0,
            "band_name": "1",
        },
        {
            "description": "two FSP worth",
            "start_freq": 1089994752,
            "channel_count": 29480,
            "fsp_ids": [3, 4],
            "wideband_shift": 0,
            "band_name": "1",
        },
        {
            "description": "multiple fsp with wideband",
            "start_freq": 693633024,
            "channel_count": 44220,
            "fsp_ids": [5, 6, 7, 8],
            "wideband_shift": int(52.7e6),
            "band_name": "1",
        },
        {
            "description": "working spectrum (FS 0 - 9)",
            "start_freq": 0,
            "channel_count": 140080,
            "fsp_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "wideband_shift": 0,
            "band_name": "1",
        },
        {
            "description": "multiple fsp, non-sequential ids",
            "start_freq": 693633024,
            "channel_count": 44220,
            "fsp_ids": [1, 3, 6, 8],
            "wideband_shift": int(52.7e6),
            "band_name": "1",
        },
    ],
)
def test_partition_spectrum_to_frequency_slices_valid(parameters: dict):
    results = partition_spectrum_to_frequency_slices(
        fsp_ids=parameters["fsp_ids"],
        start_freq=parameters["start_freq"],
        channel_width=const.FINE_CHANNEL_WIDTH,
        channel_count=parameters["channel_count"],
        k_value=1000,
        wideband_shift=parameters["wideband_shift"],
        band_name=parameters["band_name"],
    )
    # assert we get the same number of fsp configs for the given fsp ids
    assert len(parameters["fsp_ids"]) == len(results)
    assert parameters["fsp_ids"] == list(results.keys())

    total_channels = 0
    expected_start_frequency = parameters["start_freq"]
    for _, fsp_config in results.items():
        coarse_ch = fsp_config["fs_id"]

        start_frequency = (
            parameters["wideband_shift"]
            + coarse_ch * const.FS_BW
            + fsp_config["alignment_shift_freq"]
            + fsp_config["start_ch"] * const.FINE_CHANNEL_WIDTH
        )
        expected_end_frequency = start_frequency + (
            const.FINE_CHANNEL_WIDTH * (fsp_config["num_channels"] - 1)
        )
        end_frequency = (
            parameters["wideband_shift"]
            + coarse_ch * const.FS_BW
            + fsp_config["alignment_shift_freq"]
            + fsp_config["end_ch"] * const.FINE_CHANNEL_WIDTH
        )

        # Currently require multiples of 20 for SPEAD packets, but this will
        # eventually change, so this assertion may eventually change later (AA*)
        assert (
            fsp_config["num_channels"]
        ) % const.NUM_CHANNELS_PER_SPEAD_STREAM == 0
        assert (
            fsp_config["start_ch"]
        ) % const.NUM_CHANNELS_PER_SPEAD_STREAM == 0
        assert (
            fsp_config["end_ch"] + 1
        ) % const.NUM_CHANNELS_PER_SPEAD_STREAM == 0

        # Assert that start/end channel frequencies are correct
        assert start_frequency == expected_start_frequency
        assert end_frequency == expected_end_frequency
        assert fsp_config["start_channel_id"] == total_channels

        total_channels += fsp_config["num_channels"]
        expected_start_frequency = end_frequency + const.FINE_CHANNEL_WIDTH

    assert parameters["channel_count"] == total_channels


@pytest.mark.parametrize(
    "fsp_ids, start_freq, channel_width, channel_count, k_value, wideband_shift, band_name",
    [
        (
            None,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            [],
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            None,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            -1,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            None,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            0,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            None,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            0,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            2223,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            [1],
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            valid_frequency_band_name,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            None,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
            "invalid_freq_band",
        ),
    ],
)
def test_partition_spectrum_to_frequency_slices_invalid_args(
    fsp_ids,
    start_freq,
    channel_width,
    channel_count,
    k_value,
    wideband_shift,
    band_name,
):
    with pytest.raises(ValueError):
        partition_spectrum_to_frequency_slices(
            fsp_ids=fsp_ids,
            start_freq=start_freq,
            channel_width=channel_width,
            channel_count=channel_count,
            k_value=k_value,
            wideband_shift=wideband_shift,
            band_name=band_name,
        )
