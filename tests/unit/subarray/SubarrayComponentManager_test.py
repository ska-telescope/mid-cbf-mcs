#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the CbfSubarray component manager."""

from __future__ import annotations

import json

# Standard imports
import math
import os
from typing import List

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.subarray.subarray_component_manager import (
    CbfSubarrayComponentManager,
)
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestCbfSubarrayComponentManager:
    """
    Test class for CbfSubarrayComponentManager tests.
    """

    def test_init_start_communicating(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
    ) -> None:
        """
        Test component manager initialization and communication establishment
        with subordinate devices.

        :param subarray_component_manager: subarray component manager under test.
        """
        subarray_component_manager.start_communicating()
        assert subarray_component_manager.connected

    @pytest.mark.parametrize(
        "receptors",
        [
            (["SKA001", "SKA036", "SKA063", "SKA100"]),
            (["SKA063", "SKA001", "SKA100"]),
        ],
    )
    def test_add_release_vcc_valid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptors: List[str],
    ) -> None:
        """
        Test adding and removing valid receptors.

        :param subarray_component_manager: subarray component manager under test.
        :param receptors: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        subarray_component_manager.assign_vcc(receptors)

        assert [
            subarray_component_manager.dish_ids[i]
            for i in range(len(receptors))
        ] == receptors

        subarray_component_manager.release_vcc(receptors)

        assert subarray_component_manager.dish_ids == []

    @pytest.mark.parametrize(
        "receptors", [(["SKA001", "SKA036", "SKA063"]), (["SKA063", "SKA100"])]
    )
    def test_add_receptor_invalid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptors: List[str],
    ) -> None:
        """
        Test adding invalid receptor cases.

        :param subarray_component_manager: subarray component manager under test.
        :param receptors: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        # assign VCCs to a different subarray, then attempt assignment
        for receptor in receptors[:-1]:
            vcc_id = subarray_component_manager._dish_utils.dish_id_to_vcc_id[
                receptor
            ]
            vcc_proxy = subarray_component_manager._proxies_vcc[vcc_id - 1]
            vcc_proxy.subarrayMembership = (
                subarray_component_manager.subarray_id + 1
            )

        subarray_component_manager.assign_vcc(receptors[:-1])

        assert subarray_component_manager.dish_ids == []

        vcc_id = subarray_component_manager._dish_utils.dish_id_to_vcc_id[
            receptors[-1]
        ]
        vcc_proxy = subarray_component_manager._proxies_vcc[vcc_id - 1]
        vcc_proxy.subarrayMembership = subarray_component_manager.subarray_id

        # try adding same receptor twice
        subarray_component_manager.assign_vcc([receptors[-1]])
        subarray_component_manager.assign_vcc([receptors[-1]])
        assert subarray_component_manager.dish_ids == [receptors[-1]]

    @pytest.mark.parametrize(
        "receptors", [(["SKA001", "SKA036", "SKA063"]), (["SKA063", "SKA100"])]
    )
    def test_remove_receptor_invalid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptors: List[str],
    ) -> None:
        """
        Test removing invalid receptor cases.

        :param subarray_component_manager: subarray component manager under test.
        :param receptors: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        # try removing receptors before assignment
        assert subarray_component_manager.dish_ids == []
        subarray_component_manager.release_vcc(receptors)
        assert subarray_component_manager.dish_ids == []

        # try removing unassigned receptor
        subarray_component_manager.assign_vcc(receptors[:-1])
        subarray_component_manager.release_vcc([receptors[-1]])
        assert subarray_component_manager.dish_ids == receptors[:-1]

    @pytest.mark.parametrize(
        "receptors",
        [
            (["SKA001", "SKA036", "SKA063", "SKA100"]),
            (["SKA063", "SKA001", "SKA100"]),
        ],
    )
    def test_release_all_vcc_invalid_valid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptors: List[str],
    ) -> None:
        """
        Test valid use of release_all_vcc command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        subarray_component_manager.start_communicating()

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        # try removing receptors before assignment
        result = subarray_component_manager.release_all_vcc()
        assert result[0] == ResultCode.FAILED

        # remove all receptors
        subarray_component_manager.assign_vcc(receptors)
        result = subarray_component_manager.release_all_vcc()
        assert result[0] == ResultCode.OK
        assert subarray_component_manager.dish_ids == []

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            )
        ],
    )
    def test_validate_and_configure_scan(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        config_file_name: str,
        receptors: List[str],
    ) -> None:
        """
        Test scan parameter validation and configuration.

        :param subarray_component_manager: subarray component manager under test.
        :param config_file_name: scan configuration file name.
        :param receptors: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        f = open(data_file_path + config_file_name)
        config_string = f.read().replace("\n", "")
        f.close()
        config_json = json.loads(config_string)

        subarray_component_manager.assign_vcc(receptors)

        result = subarray_component_manager.validate_input(config_string)
        assert result[0]

        # configure scan
        subarray_component_manager.configure_scan(config_string)
        assert (
            subarray_component_manager.config_id
            == config_json["common"]["config_id"]
        )
        band_index = freq_band_dict()[config_json["common"]["frequency_band"]][
            "band_index"
        ]
        assert subarray_component_manager.frequency_band == band_index

        assert subarray_component_manager._ready

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            )
        ],
    )
    def test_scan_end_scan(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[str],
    ) -> None:
        """
        Test scan operation.

        :param subarray_component_manager: subarray component manager under test.
        :param config_file_name: scan configuration file name.
        :param scan_file_name: scan file name.
        :param receptors: receptor IDs to use in test.
        """
        self.test_validate_and_configure_scan(
            subarray_component_manager,
            tango_harness,
            config_file_name,
            receptors,
        )

        # start scan
        f = open(data_file_path + scan_file_name)
        scan_json = json.loads(f.read().replace("\n", ""))
        f.close()

        (result_code, msg) = subarray_component_manager.scan(scan_json)

        assert subarray_component_manager.scan_id == scan_json["scan_id"]
        assert result_code == ResultCode.STARTED

    @pytest.mark.parametrize(
        "freq_band, \
        receptor_id, \
        sample_rate_const_for_band, \
        base_dish_sample_rate_for_bandMHz",
        [
            (
                "1",
                "SKA100",
                1,
                3960,
            ),
            (
                "3",
                "SKA100",
                0.8,
                3168,
            ),
        ],
    )
    def test_calculate_fs_sample_rate(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        freq_band: str,
        receptor_id: str,
        sample_rate_const_for_band: float,
        base_dish_sample_rate_for_bandMHz: int,
    ) -> None:
        """
        Test calculate_fs_sample_rate.
        """
        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        sys_param = json.loads(sp)
        freq_offset_k = sys_param["dish_parameters"][receptor_id]["k"]
        mhz_to_hz = 1000000
        total_num_freq_slice = 20
        freq_offset_delta_f = 1800
        oversampling_factor = 10 / 9
        dish_sample_rate = (base_dish_sample_rate_for_bandMHz * mhz_to_hz) + (
            sample_rate_const_for_band * freq_offset_k * freq_offset_delta_f
        )
        expected_fs_sample_rate = (
            dish_sample_rate * oversampling_factor / total_num_freq_slice
        )
        output_fs_sample_rate = (
            subarray_component_manager._calculate_fs_sample_rate(
                freq_band, receptor_id
            )
        )
        assert math.isclose(
            output_fs_sample_rate["fs_sample_rate"], expected_fs_sample_rate
        )
