# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada
from __future__ import annotations  # allow forward references in type hints

import copy

from ska_telmodel import channel_map

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.fine_channel_partitioner import (
    partition_spectrum_to_frequency_slices,
)
from ska_mid_cbf_mcs.commons.global_enum import FspModes


class FspScanConfigurationBuilder:
    function_mode: FspModes = None
    function_configuration: dict = None
    dish_utils: DISHUtils = None
    wideband_shift: int = 0
    subarray_dish_ids: set = None

    def _fsp_config_from_processing_regions(
        self: FspScanConfigurationBuilder, processing_regions: list[dict]
    ) -> list[dict]:
        """Create a list of FSP configurations for a given list of processing regions

        :param processing_regions: a list of processing regions to generate configurations from
        :param function_mode: the function mode of the processing regions
        :return: list of individual FSP configurations for the processing regions
        """

        fsp_configurations = []

        for processing_region in processing_regions:
            # Calculate the fsp configs for the processing region
            fsp_configuration = self._fsp_config_from_processing_region(
                processing_region
            )

            fsp_configurations.extend(fsp_configuration)

        return fsp_configurations

    def _fsp_config_from_processing_region(
        self: FspScanConfigurationBuilder,
        processing_region_config: dict,
    ) -> list[dict]:
        """Create a list of FSP configurations for a given processing region config

        :param processing_region_config: The processing region configuration, see telescope model for details
        :param wideband_shift: The wideband shift to apply to the region
        :param function_mode: the function mode to configure the FSP's
        :return: list of individual FSP configurations for a processing region
        """

        # sort the ids, just in case they are given in non-ascending order
        fsp_ids: list[int] = processing_region_config["fsp_ids"]
        fsp_ids.sort()

        dish_ids = []
        if (
            "receptors" not in processing_region_config
            or len(processing_region_config["receptors"]) == 0
        ):
            for dish_id in self.subarray_dish_ids:
                dish_ids.append(self.dish_utils.dish_id_to_vcc_id[dish_id])
        else:
            for dish_id in processing_region_config["receptors"]:
                dish_ids.append(self.dish_utils.dish_id_to_vcc_id[dish_id])

        vcc_to_fs_infos = {}
        for dish_id in dish_ids:
            calculated_fs_infos = partition_spectrum_to_frequency_slices(
                fsp_ids=fsp_ids,
                start_freq=processing_region_config["start_freq"],
                channel_width=processing_region_config["channel_width"],
                channel_count=processing_region_config["channel_count"],
                k_value=self.dish_utils.dish_id_to_k(dish_ids),
                wideband_shift=self.wideband_shift,
            )
            vcc_to_fs_infos[
                self.dish_utils.dish_id_to_vcc_id[dish_ids]
            ] = calculated_fs_infos

        output_port = (
            processing_region_config["output_port"]
            if "output_port" in processing_region_config
            else []
        )

        if len(output_port) > 0:
            # Split up the PR output ports according to the start channel ids of the
            # FSPs
            sdp_start_channel_ids = [
                fs_info["stp_start_channel_id"]
                for fs_info in calculated_fs_infos.values()
            ]
            calculated_fsp_ids = list(calculated_fs_infos.keys())

            split_output_ports = channel_map.split_channel_map_at(
                channel_map=processing_region_config["output_port"],
                channel_groups=sdp_start_channel_ids,
                rebase_groups=None,
            )

            fsp_to_output_port_map = {}
            for fsp_id, fsp_output_ports in zip(
                calculated_fsp_ids, split_output_ports
            ):
                fsp_to_output_port_map[fsp_id] = fsp_output_ports

        # Build individual fsp configs
        fsp_configs = []

        for fsp_id in calculated_fs_infos.keys():
            fsp_config = {}
            # Required values
            fsp_config["fsp_id"] = fsp_id
            fsp_config["function_mode"] = self.function_mode
            fsp_config["frequency_slice_id"] = calculated_fs_infos[fsp_id][
                "fs_id"
            ]
            fsp_config["integration_factor"] = processing_region_config[
                "integration_factor"
            ]
            fsp_config["channel_offset"] = (
                calculated_fs_infos[fsp_id]["sdp_start_channel_id"]
                - calculated_fs_infos[fsp_id]["fsp_start_ch"]
            )
            fsp_config["output_link_map"] = processing_region_config[
                "output_link_map"
            ]
            vcc_id_to_rdt_freq_shifts = {}
            for vcc_id in vcc_to_fs_infos.keys():
                vcc_id_to_rdt_freq_shifts[vcc_id] = {}
                vcc_id_to_rdt_freq_shifts[vcc_id][
                    "freq_down_shift"
                ] = vcc_to_fs_infos[vcc_id]["vcc_downshift_freq"]
                vcc_id_to_rdt_freq_shifts[vcc_id][
                    "freq_align_shift"
                ] = vcc_to_fs_infos[vcc_id]["alignment_shift_freq"]
                vcc_id_to_rdt_freq_shifts[vcc_id][
                    "freq_wb_shift"
                ] = self.wideband_shift
                # Note: don't have the info to calculate freq_scfo_shift here,
                # will be added further in processing at
                # fsp_corr_subarry_component_manager._build_hps_fsp_config
                # because fsp_corr has
                # resampler_delay_tracker.output_sample_rate value
            fsp_config["vcc_id_to_rdt_freq_shifts"] = vcc_id_to_rdt_freq_shifts

            # Optional values
            if "output_host" in processing_region_config:
                fsp_config["output_host"] = processing_region_config[
                    "output_host"
                ]
            if len(fsp_to_output_port_map[fsp_id]) > 0:
                fsp_config["output_port"] = fsp_to_output_port_map[fsp_id]

            fsp_configs.append(fsp_config)

        return fsp_configs

    def set_fsp_mode(
        self: FspScanConfigurationBuilder, function_mode: FspModes
    ) -> FspScanConfigurationBuilder:
        assert function_mode is not None
        self.function_mode = function_mode
        return self

    def set_config(
        self: FspScanConfigurationBuilder, function_configuration: dict
    ) -> FspScanConfigurationBuilder:
        assert function_configuration is not None
        self.function_configuration = copy.deepcopy(function_configuration)
        return self

    def set_dish_utils(
        self: FspScanConfigurationBuilder, dish_utils: DISHUtils
    ) -> FspScanConfigurationBuilder:
        assert dish_utils is not None
        self.dish_utils = dish_utils
        return self

    def set_subarray_dish_ids(
        self: FspScanConfigurationBuilder, subarray_dish_ids: set
    ) -> FspScanConfigurationBuilder:
        assert subarray_dish_ids is not None
        assert len(subarray_dish_ids) > 0
        self.subarray_dish_ids = subarray_dish_ids
        return self

    def set_wideband_shift(
        self: FspScanConfigurationBuilder, wideband_shift: int
    ) -> FspScanConfigurationBuilder:
        assert wideband_shift is not None
        self.wideband_shift = wideband_shift
        return self

    def build(self: FspScanConfigurationBuilder) -> list[dict]:
        """_summary_

        :return: _description_
        """
        assert self.function_mode is not None
        assert self.dish_utils is not None
        assert self.wideband_shift is not None
        assert self.function_configuration is not None
        assert self.subarray_dish_ids is not None
        assert (
            "processing_regions" in self.function_configuration
        ), "function configuration requires a processing region to process"

        fsp_config = self._fsp_config_from_processing_regions(
            self.function_configuration["processing_regions"]
        )

        # TODO: Any other Function specific configuration outside of the FSP config

        return fsp_config
