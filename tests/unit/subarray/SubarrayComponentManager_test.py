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
        "receptor_ids",
        [
            (["SKA001", "SKA036", "SKA063", "SKA100"]),
            (["SKA063", "SKA001", "SKA100"]),
        ],
    )
    def test_add_remove_receptors_valid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[str],
    ) -> None:
        """
        Test adding and removing valid receptors.

        :param subarray_component_manager: subarray component manager under test.
        :param receptor_ids: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        subarray_component_manager.add_receptors(receptor_ids)

        assert [
            subarray_component_manager.receptors[i]
            for i in range(len(receptor_ids))
        ] == receptor_ids

        subarray_component_manager.remove_receptors(receptor_ids)

        assert subarray_component_manager.receptors == []

    @pytest.mark.parametrize(
        "receptor_ids",
        [(["SKA001", "SKA036", "SKA063"]), (["SKA063", "SKA100"])],
    )
    def test_add_receptor_invalid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[str],
    ) -> None:
        """
        Test adding invalid receptor cases.

        :param subarray_component_manager: subarray component manager under test.
        :param receptor_ids: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        # assign VCCs to a different subarray, then attempt assignment
        for receptor in receptor_ids[:-1]:
            vcc_id = subarray_component_manager._receptor_to_vcc[receptor]
            vcc_proxy = subarray_component_manager._proxies_vcc[vcc_id - 1]
            vcc_proxy.subarrayMembership = (
                subarray_component_manager.subarray_id + 1
            )

        subarray_component_manager.add_receptors(receptor_ids[:-1])

        assert subarray_component_manager.receptors == []

        vcc_id = subarray_component_manager._receptor_to_vcc[receptor_ids[-1]]
        vcc_proxy = subarray_component_manager._proxies_vcc[vcc_id - 1]
        vcc_proxy.subarrayMembership = subarray_component_manager.subarray_id

        # try adding same receptor twice
        subarray_component_manager.add_receptors([receptor_ids[-1]])
        subarray_component_manager.add_receptors([receptor_ids[-1]])
        assert subarray_component_manager.receptors == [receptor_ids[-1]]

    @pytest.mark.parametrize(
        "receptor_ids",
        [(["SKA001", "SKA036", "SKA063"]), (["SKA063", "SKA100"])],
    )
    def test_remove_receptor_invalid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[str],
    ) -> None:
        """
        Test removing invalid receptor cases.

        :param subarray_component_manager: subarray component manager under test.
        :param receptor_ids: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        # try removing receptors before assignment
        assert subarray_component_manager.receptors == []
        subarray_component_manager.remove_receptors(receptor_ids)
        assert subarray_component_manager.receptors == []

        # try removing unassigned receptor
        subarray_component_manager.add_receptors(receptor_ids[:-1])
        subarray_component_manager.remove_receptors([receptor_ids[-1]])
        assert subarray_component_manager.receptors == receptor_ids[:-1]

    @pytest.mark.parametrize(
        "receptor_ids",
        [
            (["SKA001", "SKA036", "SKA063", "SKA100"]),
            (["SKA063", "SKA001", "SKA100"]),
        ],
    )
    def test_remove_all_receptors_invalid_valid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[str],
    ) -> None:
        """
        Test valid use of remove_all_receptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        subarray_component_manager.start_communicating()

        # try removing receptors before assignment
        result = subarray_component_manager.remove_all_receptors()
        assert result[0] == ResultCode.FAILED

        # remove all receptors
        subarray_component_manager.add_receptors(receptor_ids)
        result = subarray_component_manager.remove_all_receptors()
        assert result[0] == ResultCode.OK
        assert subarray_component_manager.receptors == []

    @pytest.mark.parametrize(
        "config_file_name, \
        receptor_ids",
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
        receptor_ids: List[str],
    ) -> None:
        """
        Test scan parameter validation and configuration.

        :param subarray_component_manager: subarray component manager under test.
        :param config_file_name: scan configuration file name.
        :param receptor_ids: receptor IDs to use in test.
        """
        subarray_component_manager.start_communicating()

        f = open(data_file_path + config_file_name)
        config_string = f.read().replace("\n", "")
        f.close()
        config_json = json.loads(config_string)

        subarray_component_manager.add_receptors(receptor_ids)
        subarray_component_manager.frequency_offset_k = [11] * 197

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
        receptor_ids",
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
        receptor_ids: List[str],
    ) -> None:
        """
        Test scan operation.

        :param subarray_component_manager: subarray component manager under test.
        :param config_file_name: scan configuration file name.
        :param scan_file_name: scan file name.
        :param receptor_ids: receptor IDs to use in test.
        """
        self.test_validate_and_configure_scan(
            subarray_component_manager,
            tango_harness,
            config_file_name,
            receptor_ids,
        )

        # start scan
        f = open(data_file_path + scan_file_name)
        scan_json = json.loads(f.read().replace("\n", ""))
        f.close()

        (result_code, msg) = subarray_component_manager.scan(scan_json)

        assert subarray_component_manager.scan_id == int(scan_json["scan_id"])
        assert result_code == ResultCode.STARTED

    @pytest.mark.parametrize(
        "freq_band, \
        receptor_id, \
        freq_offset_k, \
        sample_rate_const_for_band, \
        base_dish_sample_rate_for_bandMHz",
        [
            (
                "1",
                "SKA100",
                [0] * 197,
                1,
                3960,
            ),
            (
                "3",
                "SKA100",
                [11] * 197,
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
        freq_offset_k: List[int],
    ) -> None:
        """
        Test calculate_fs_sample_rate.
        """

        mhz_to_hz = 1000000
        total_num_freq_slice = 20
        freq_offset_delta_f = 1800
        oversampling_factor = 10 / 9
        dish_sample_rate = (base_dish_sample_rate_for_bandMHz * mhz_to_hz) + (
            sample_rate_const_for_band * freq_offset_k[0] * freq_offset_delta_f
        )
        expected_fs_sample_rate = (
            dish_sample_rate * oversampling_factor / total_num_freq_slice
        )
        expected_fs_sample_rate = expected_fs_sample_rate / mhz_to_hz
        subarray_component_manager.frequency_offset_k = freq_offset_k
        subarray_component_manager.frequency_offset_delta_f = (
            freq_offset_delta_f
        )
        output_fs_sample_rate = (
            subarray_component_manager._calculate_fs_sample_rate(
                freq_band, receptor_id
            )
        )
        assert math.isclose(
            output_fs_sample_rate["fs_sample_rate"], expected_fs_sample_rate
        )
