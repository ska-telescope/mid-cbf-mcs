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

from ska_mid_cbf_mcs.commons.fine_channel_partitioner import (
    partition_spectrum_to_frequency_slices,
)
from ska_mid_cbf_mcs.commons.global_enum import FspModes


class FspScanConfigurationBuilder:
    function_mode: FspModes = None
    function_configuration: dict = None

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
            # TODO: When we support wideband shift, insert it here:
            wideband_shift = 0

            # Algorithm needs a K-value, however this is only to calculate the major
            # shift, which the VCC's already calculate. So using k = 1000.
            # Note: alignment (minor) shift needs to be sent to each Resampler &
            # Delay tracker, but that value is not K-value dependent, and will be
            # the same regardless of k-value.
            k_value = 1000

            # Calculate the fsp configs for the processing region
            fsp_configuration = self._fsp_config_from_processing_region(
                processing_region,
                wideband_shift,
                k_value,
                self.function_mode.name,
            )

            fsp_configurations.extend(fsp_configuration)

        return fsp_configurations

    def _fsp_config_from_processing_region(
        self: FspScanConfigurationBuilder,
        processing_region_config: dict,
        wideband_shift: int,
        k_value: int,
        function_mode: str,
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

        calculated_fs_infos = partition_spectrum_to_frequency_slices(
            fsp_ids=fsp_ids,
            start_freq=processing_region_config["start_freq"],
            channel_width=processing_region_config["channel_width"],
            channel_count=processing_region_config["channel_count"],
            k_value=k_value,
            wideband_shift=wideband_shift,
        )

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
            calculated_fsp_ids.sort()

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

        for fsp in calculated_fs_infos.keys():
            fsp_config = {}
            fsp_config["fsp_id"] = calculated_fs_infos[fsp]["fsp_id"]
            fsp_config["function_mode"] = function_mode
            fsp_config["frequency_slice_id"] = calculated_fs_infos[fsp][
                "fs_id"
            ]
            fsp_config["integration_factor"] = processing_region_config[
                "integration_factor"
            ]
            fsp_config["output_link_map"] = processing_region_config[
                "output_link_map"
            ]
            fsp_config["channel_offset"] = (
                calculated_fs_infos[fsp]["sdp_start_channel_id"]
                - calculated_fs_infos[fsp]["fsp_start_ch"]
            )
            fsp_config["alignment_shift_freq"] = calculated_fs_infos[fsp][
                "alignment_shift_freq"
            ]

            # Optional values
            receptors = (
                processing_region_config["receptors"]
                if "receptors" in processing_region_config
                else []
            )
            output_hosts = (
                processing_region_config
                if "output_host" in processing_region_config
                else []
            )

            if len(receptors) > 0:
                fsp_config["receptors"] = receptors
            if len(output_hosts) > 0:
                fsp_config["output_host"] = output_hosts
            if len(fsp_to_output_port_map[fsp]) > 0:
                fsp_config["output_port"] = fsp_to_output_port_map[fsp]

            fsp_configs.append(fsp_config)

        return fsp_configs

    def set_fsp_mode(
        self: FspScanConfigurationBuilder, function_mode: FspModes
    ) -> FspScanConfigurationBuilder:
        self.function_mode = function_mode
        return self

    def set_config(
        self: FspScanConfigurationBuilder, function_configuration: dict
    ) -> FspScanConfigurationBuilder:
        self.function_configuration = copy.deepcopy(function_configuration)
        return self

    def build(self: FspScanConfigurationBuilder) -> dict:
        """_summary_

        :return: _description_
        """
        assert self.function_mode is not None
        assert self.function_configuration is not None

        assert (
            "processing_regions" in self.function_configuration
        ), "function configuration requires a processing region to process"

        fsp_config = self._fsp_config_from_processing_regions(
            self.function_configuration["processing_regions"]
        )

        # TODO: Any other Function specific configuration outside of the FSP config

        return fsp_config
