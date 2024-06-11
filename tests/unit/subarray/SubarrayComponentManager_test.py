# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# #
# # This file is part of the mid-cbf-mcs project
# #
# #
# #
# # Distributed under the terms of the BSD-3-Clause license.
# # See LICENSE.txt for more info.

# """Contain the tests for the CbfSubarray component manager."""

# from __future__ import annotations

# import json

# # Standard imports
# import math
# import os
# from typing import List

# import pytest
# from ska_tango_base.commands import ResultCode

# from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
# from ska_mid_cbf_mcs.subarray.subarray_component_manager import (
#     CbfSubarrayComponentManager,
# )
# from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# # Data file path
# data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# class TestCbfSubarrayComponentManager:
#     """
#     Test class for CbfSubarrayComponentManager tests.
#     """

#     @pytest.mark.parametrize(
#         "freq_band, \
#         receptor_id, \
#         sample_rate_const_for_band, \
#         base_dish_sample_rate_for_bandMHz",
#         [
#             (
#                 "1",
#                 "SKA100",
#                 1,
#                 3960,
#             ),
#             (
#                 "3",
#                 "SKA100",
#                 0.8,
#                 3168,
#             ),
#         ],
#     )
#     def test_calculate_fs_sample_rate(
#         self: TestCbfSubarrayComponentManager,
#         subarray_component_manager: CbfSubarrayComponentManager,
#         freq_band: str,
#         receptor_id: str,
#         sample_rate_const_for_band: float,
#         base_dish_sample_rate_for_bandMHz: int,
#     ) -> None:
#         """
#         Test calculate_fs_sample_rate.
#         """
#         with open(data_file_path + "sys_param_4_boards.json") as f:
#             sp = f.read()
#         subarray_component_manager.update_sys_param(sp)

#         sys_param = json.loads(sp)
#         freq_offset_k = sys_param["dish_parameters"][receptor_id]["k"]
#         mhz_to_hz = 1000000
#         total_num_freq_slice = 20
#         freq_offset_delta_f = 1800
#         oversampling_factor = 10 / 9
#         dish_sample_rate = (base_dish_sample_rate_for_bandMHz * mhz_to_hz) + (
#             sample_rate_const_for_band * freq_offset_k * freq_offset_delta_f
#         )
#         expected_fs_sample_rate = (
#             dish_sample_rate * oversampling_factor / total_num_freq_slice
#         )
#         output_fs_sample_rate = (
#             subarray_component_manager._calculate_fs_sample_rate(
#                 freq_band, receptor_id
#             )
#         )
#         assert math.isclose(
#             output_fs_sample_rate["fs_sample_rate"], expected_fs_sample_rate
#         )
