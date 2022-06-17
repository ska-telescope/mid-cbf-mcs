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

    @pytest.mark.parametrize("receptor_ids", [([1, 3, 4, 2]), ([4, 1, 2])])
    def test_add_remove_receptors_valid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[int],
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

    @pytest.mark.parametrize("receptor_ids", [([1, 3, 4]), ([4, 2])])
    def test_add_receptor_invalid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[int],
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

    @pytest.mark.parametrize("receptor_ids", [([1, 3, 4]), ([4, 2])])
    def test_remove_receptor_invalid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[int],
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

    @pytest.mark.parametrize("receptor_ids", [([1, 3, 4, 2]), ([4, 1, 2])])
    def test_remove_all_receptors_invalid_valid(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        receptor_ids: List[int],
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
        [("ConfigureScan_basic.json", [1, 3, 4, 2])],
    )
    def test_validate_and_configure_scan(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        config_file_name: str,
        receptor_ids: List[int],
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

        result = subarray_component_manager.validate_input(config_string)
        assert result[0]

        # configure scan
        subarray_component_manager.configure_scan(config_string)
        assert (
            subarray_component_manager.config_id
            == config_json["common"]["config_id"]
        )
        band_index = freq_band_dict()[config_json["common"]["frequency_band"]]
        assert subarray_component_manager.frequency_band == band_index

        assert subarray_component_manager._ready

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids",
        [("ConfigureScan_basic.json", "Scan1_basic.json", [1, 3, 4, 2])],
    )
    def test_scan_end_scan(
        self: TestCbfSubarrayComponentManager,
        subarray_component_manager: CbfSubarrayComponentManager,
        tango_harness: TangoHarness,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        """
        Test scan operation.

        :param subarray_component_manager: subarray component manager under test.
        :param config_file_name: scan configuration file name.
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
