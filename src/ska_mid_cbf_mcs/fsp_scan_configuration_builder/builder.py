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
    function_mode: FspModes
    function_configuration: dict
    dish_utils: DISHUtils
    wideband_shift: int
    subarray_dish_ids: set

    def __init__(
        self: FspScanConfigurationBuilder,
        function_mode: FspModes,
        function_configuration: dict,
        dish_utils: DISHUtils,
        subarray_dish_ids: set,
        wideband_shift: int,
    ):
        self.function_mode = function_mode
        if "processing_regions" not in function_configuration:
            raise ValueError(
                "Function configuration is missing processing_regions parameter"
            )
        self.function_configuration = copy.deepcopy(function_configuration)
        self.dish_utils = dish_utils
        self.subarray_dish_ids = subarray_dish_ids
        self.wideband_shift = wideband_shift

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
                dish_ids.append(dish_id)
        else:
            for dish_id in processing_region_config["receptors"]:
                dish_ids.append(dish_id)

        vcc_to_fs_infos = {}
        for dish_id in dish_ids:
            calculated_fsp_infos = partition_spectrum_to_frequency_slices(
                fsp_ids=fsp_ids,
                start_freq=processing_region_config["start_freq"],
                channel_width=processing_region_config["channel_width"],
                channel_count=processing_region_config["channel_count"],
                k_value=self.dish_utils.dish_id_to_k[dish_id],
                wideband_shift=self.wideband_shift,
            )
            vcc_to_fs_infos[
                self.dish_utils.dish_id_to_vcc_id[dish_id]
            ] = calculated_fsp_infos

        calculated_fsp_ids = list(calculated_fsp_infos.keys())

        # vcc_id_to_rdt_freq_shifts are the shift values needed by the
        # Resampler Delay Tracker (rdt) for each vcc of the FSP:
        # freq_down_shift  - the the shift to move the FS into the center of the
        #                    digitized requency (k dependent)
        # freq_align_shift - the shift to align channels between FSs
        # freq_wb_shift    - the wideband shift
        # freq_scfo_shift  - the frequency shift required due to SCFO sampling
        #
        # See CIP-2622, or parent epic CIP-2145
        #
        # to explain the loops below, I'm moving from a per-vcc config in
        # vcc_to_fs_infos to a per-fsp config, as well as rename the fields to
        # match what HPS wants.
        #
        # essentially I have in vcc_to_fs_infos:
        # vcc1:
        #     fsp_1:
        #           shift values A
        #     fsp_2:
        #           shift values B
        # vcc2:
        #     fsp_1:
        #           shift values C
        #     fsp_2:
        #           shift values D
        #
        # But I need them sent down to HPS as:
        # fsp_1:
        #     vcc 1:
        #          shift values A
        #     vcc 2:
        #          shift values C
        # fsp_2:
        #     vcc 1:
        #          shift values B
        #     vcc 2:
        #          shift values D

        vcc_id_to_rdt_freq_shifts = {}
        for fsp_id in calculated_fsp_ids:
            vcc_id_to_rdt_freq_shifts[fsp_id] = {}
            for vcc_id in vcc_to_fs_infos.keys():
                # HPS wants vcc id to be a string value, not int
                vcc_id_str = str(vcc_id)
                vcc_id_to_rdt_freq_shifts[fsp_id][vcc_id_str] = {}
                vcc_id_to_rdt_freq_shifts[fsp_id][vcc_id_str][
                    "freq_down_shift"
                ] = vcc_to_fs_infos[vcc_id][fsp_id]["vcc_downshift_freq"]
                vcc_id_to_rdt_freq_shifts[fsp_id][vcc_id_str][
                    "freq_align_shift"
                ] = vcc_to_fs_infos[vcc_id][fsp_id]["alignment_shift_freq"]
                vcc_id_to_rdt_freq_shifts[fsp_id][vcc_id_str][
                    "freq_wb_shift"
                ] = self.wideband_shift
                # Note: don't have the info to calculate freq_scfo_shift here,
                # will be added further in processing at
                # fsp_corr_subarry_component_manager._build_hps_fsp_config
                # because fsp_corr has
                # resampler_delay_tracker.output_sample_rate value

        output_port = (
            processing_region_config["output_port"]
            if "output_port" in processing_region_config
            else []
        )

        if len(output_port) > 0:
            # Split up the PR output ports according to the start channel ids of
            # the FSPs
            sdp_start_channel_ids = [
                fsp_info["sdp_start_channel_id"]
                for fsp_info in calculated_fsp_infos.values()
            ]
            sdp_start_channel_ids.append(
                processing_region_config["sdp_start_channel_id"]
                + processing_region_config["channel_count"]
            )

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

        for fsp_id in calculated_fsp_infos.keys():
            fsp_config = {}
            # Required values
            fsp_config["fsp_id"] = fsp_id
            fsp_config["function_mode"] = self.function_mode.name
            fsp_config["frequency_slice_id"] = calculated_fsp_infos[fsp_id][
                "fs_id"
            ]
            fsp_config["integration_factor"] = processing_region_config[
                "integration_factor"
            ]
            fsp_config["channel_offset"] = (
                calculated_fsp_infos[fsp_id]["sdp_start_channel_id"]
                - calculated_fsp_infos[fsp_id]["fsp_start_ch"]
            )
            fsp_config["output_link_map"] = processing_region_config[
                "output_link_map"
            ]

            fsp_config[
                "vcc_id_to_rdt_freq_shifts"
            ] = vcc_id_to_rdt_freq_shifts[fsp_id]

            # Optional values
            if "output_host" in processing_region_config:
                fsp_config["output_host"] = processing_region_config[
                    "output_host"
                ]
            if "output_port" in processing_region_config:
                fsp_config["output_port"] = fsp_to_output_port_map[fsp_id]

            fsp_configs.append(fsp_config)

        return fsp_configs

    def build(self: FspScanConfigurationBuilder) -> list[dict]:
        """_summary_

        :return: _description_
        """
        fsp_config = self._fsp_config_from_processing_regions(
            self.function_configuration["processing_regions"]
        )
        return fsp_config
