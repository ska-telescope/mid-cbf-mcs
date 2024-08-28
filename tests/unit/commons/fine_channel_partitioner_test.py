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

# from ska_mid_cbf_mcs.commons.fine_channel_partitioner import (
#     calculate_fs_info,
#     get_coarse_channels,
#     get_end_freqeuency,
# )

# Paths
file_path = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


def test_get_coarse_channels_valid():
    pass


def test_get_coarse_channels_invalid_channel_count():
    pass


def test_get_coarse_channels_invalid_channel_width():
    pass


def test_get_coarse_channels_invalid_start_freq():
    pass


def test_calculate_fs_info_valid():
    pass


def test_calculate_fs_info_invalid_fsp_ids():
    pass


def test_calculate_fs_info_too_many_fsp_ids():
    pass


def test_calculate_fs_info_dish_id_has_invalid_k():
    pass


def test_calculate_fs_info_empty_dish_id():
    pass


def test_get_end_frequency_valid():
    pass


def test_get_end_frequency_invalid_channel_count():
    pass


def test_get_end_frequency_invalid_channel_width():
    pass
