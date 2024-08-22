# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

from ska_telmodel import channel_map

from ska_mid_cbf_mcs.commons.fine_channel_partitioner import (
    calculate_fs_info,
    get_coarse_channels,
    get_end_freqeuency,
)


def create_vcc_configuration(common_config: dict, configuration: dict) -> dict:
    """_summary_

    :param common_config: _description_
    :param configuration: _description_
    :return: _description_
    """
    pass


def create_fsp_configuration(common_config: dict, configuration: dict) -> dict:
    """_summary_

    :param common_config: _description_
    :param configuration: _description_
    :return: _description_
    """
    pass


def create_fsp_corr_configuration(
    common_config: dict, configuration: dict
) -> dict:
    """_summary_

    :param common_config: _description_
    :param configuration: _description_
    :return: _description_
    """
    pass


def _create_fsp_configuration(
    processing_regions: list[dict], dish_to_k: dict, function_mode: str
) -> list[dict]:
    """Create a list of FSP configurations for a given list of processing regions

    :param processing_regions: a list of processing regions to generate configurations from
    :param dictionary: dictionary of all dish ids to their respective k value
    :param function_mode: the function mode of the processing regions
    :return: list of individual FSP configurations
    """

    fsp_configurations = []
    for processing_region_config in processing_regions:
        # TODO: When we support wideband shift, insert it here:
        wideband_shift = 0

        processing_region_dish_id_to_k = {}
        if (
            "receptors" not in processing_region_config
            or len(processing_regions["receptors"]) == 0
        ):
            processing_region_dish_id_to_k = dish_to_k.copy()
        else:
            for dish_id in processing_regions["receptors"]:
                processing_region_dish_id_to_k[dish_id] = dish_to_k[dish_id]

        # Calculate the fsp configs for the processing region
        fsp_configurations = {}
        fsp_configuration = _fsp_config_from_processing_region(
            processing_region_config,
            wideband_shift,
            processing_region_dish_id_to_k,
            function_mode,
        )

        fsp_configurations.extend(fsp_configuration)

    return fsp_configurations


def _fsp_config_from_processing_region(
    processing_region_config: dict,
    wideband_shift: int,
    dish_id_to_k: dict,
    function_mode: str,
) -> list[dict]:
    """Create a list of FSP configurations for a given processing region config

    :param processing_region_config: The processing region configuration, see telescope model for details
    :param wideband_shift: The wideband shift to apply to the region
    :param dish_id_to_k: the k_value of the region
    :param function_mode: the function mode to configure the FSP's
    :return: list of individual FSP configurations
    """

    # Calculate inferred value
    end_freq = get_end_freqeuency(
        start_freq=processing_region_config["start_freq"],
        channel_width=processing_region_config["channel_width"],
        channel_count=processing_region_config["channel_count"],
    )

    # get the coarse channeles this processing region will cover
    coarse_channels = get_coarse_channels(
        processing_region_config["start_freq"], end_freq, wideband_shift
    )

    # sort the ids, just in case they are given in non-ascending order
    fsp_ids: list[int] = processing_region_config["fsp_ids"]
    fsp_ids.sort()

    # validation ensures we have enough fsp_ids for coarse channels
    # but edge case where config supplies too many fsp_ids.
    # calculate_fs_info only returns fsp info for enough to cover the coarse
    # channels.
    fsp_to_dish_id_shift = {}
    for fsp_id in fsp_ids[: len(coarse_channels)]:
        fsp_to_dish_id_shift[fsp_id] = {}

    # need to run the calculation for each k_value, and collect the shift info
    # for the dish_id for each FSP.
    # only the vcc_downshift_freq and shift will differ between k, so it's
    # ok to use the last run for the rest of the values for the FSP config
    calculated_fs_infos = {}
    for dish_id, k_value in dish_id_to_k:
        calculated_fs_infos = calculate_fs_info(
            fsp_ids=fsp_ids,
            start_freq=processing_region_config["start_freq"],
            channel_width=processing_region_config["channel_width"],
            channel_count=processing_region_config["channel_count"],
            k_value=k_value,
            wideband_shift=wideband_shift,
        )

        # Collect the shift for the dish_id
        for fs_info in calculated_fs_infos.values():
            shift = {}
            shift["vcc_downshift_freq"] = fs_info["vcc_downshift_freq"]
            shift["alignment_shift_freq"] = fs_info["alignment_shift_freq"]
            shift["total_shift_freq"] = fs_info["total_shift_freq"]
            fsp_to_dish_id_shift[fs_info["fsp_id"]][dish_id] = shift

    output_port = (
        processing_region_config["output_port"]
        if "output_port" in processing_region_config
        else []
    )

    if len(output_port) > 0:
        # Split up the PR output ports according to the start channel ids of the FSPs
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
        fsp_config["frequency_slice_id"] = calculated_fs_infos[fsp]["fs_id"]
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
        fsp_config["dish_id_to_shift"] = fsp_to_dish_id_shift[
            fsp_config["fsp_id"]
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
