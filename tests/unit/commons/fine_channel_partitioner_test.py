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

from ska_mid_cbf_mcs.commons.fine_channel_partitioner import (
    get_coarse_frequency_slice_channels,
    partition_spectrum_to_frequency_slices,
)
from ska_mid_cbf_mcs.commons.global_enum import const

# Paths
file_path = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# Start and end Frequency of coarse channels in Hz
coarse_channel_boundaries = [
    (-99090432, 99090431),
    (99090432, 297271295),
    (297271296, 495452159),
    (495452160, 693633023),
    (693633024, 891813887),
    (891813888, 1089994751),
    (1089994752, 1288175615),
    (1288175616, 1486356479),
    (1486356480, 1684537343),
    (1684537344, 1882718207),
]

valid_fsp_ids = [1, 2, 3, 4, 5, 6]
valid_channel_width = const.FINE_CHANNEL_WIDTH
valid_start_freq = int(350e6)
valid_wb_shift = int(52.7e6)
valid_channel_count = 58980
valid_k_value = 1000


def test_get_coarse_channels_invalid_args():
    with pytest.raises(Exception):
        get_coarse_frequency_slice_channels(
            start_freq=1, end_freq=0, wb_shift=0
        )


def test_get_coarse_channels_valid():
    total_coarse_channels = len(coarse_channel_boundaries)
    for start_channel_index in range(0, total_coarse_channels):
        start_channel = coarse_channel_boundaries[start_channel_index]
        for end_channel_index in range(0, total_coarse_channels):
            if end_channel_index < start_channel_index:
                continue
            end_channel = coarse_channel_boundaries[end_channel_index]
            expected_number_of_channels = (
                end_channel_index - start_channel_index + 1
            )
            actual_coarse_channels = get_coarse_frequency_slice_channels(
                start_channel[0], end_channel[1], 0
            )
            print(
                f"start index: {start_channel_index}, end index: {end_channel_index}"
            )
            print(actual_coarse_channels)
            assert expected_number_of_channels == len(actual_coarse_channels)
            assert actual_coarse_channels == list(
                range(start_channel_index, end_channel_index + 1)
            )


def test_partition_spectrum_to_frequency_slices_valid():
    pass


@pytest.mark.parametrize(
    "fsp_ids, start_freq, channel_width, channel_count, k_value, wideband_shift",
    [
        (
            None,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            [],
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            [-1],
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            None,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            -1,
            valid_channel_count,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            None,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            0,
            valid_k_value,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            None,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            0,
            valid_wb_shift,
        ),
        (
            valid_fsp_ids,
            valid_start_freq,
            valid_channel_width,
            valid_channel_count,
            2223,
            valid_wb_shift,
        ),
    ],
)
def test_partition_spectrum_to_frequency_slices_invalid_args(
    fsp_ids, start_freq, channel_width, channel_count, k_value, wideband_shift
):
    with pytest.raises(AssertionError):
        partition_spectrum_to_frequency_slices(
            fsp_ids=fsp_ids,
            start_freq=start_freq,
            channel_width=channel_width,
            channel_count=channel_count,
            k_value=k_value,
            wideband_shift=wideband_shift,
        )
