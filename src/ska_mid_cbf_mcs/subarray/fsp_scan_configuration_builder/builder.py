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
from typing import Callable

from ska_telmodel import channel_map

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.commons.vcc_gain_utils import get_vcc_ripple_correction


class FspScanConfigurationBuilder:
    _function_mode: FspModes
    _function_configuration: dict
    _dish_utils: DISHUtils
    _wideband_shift: int
    _subarray_dish_ids: set
    _frequency_band: str

    def __init__(
        self: FspScanConfigurationBuilder,
        function_configuration: dict,
        dish_utils: DISHUtils,
        subarray_dish_ids: set,
        wideband_shift: int,
        frequency_band: str,
    ):
        """Constructor for the FspScanConfigurationBuilder. Constructs FSP
        Configurations from a function modes (CORR, PST, etc.) configuration.

        :param self: FspScanConfigurationBuilder object
        :param function_configuration: dictionary of the Function mode configuration from the input ConfigureScan configuration
        :param dish_utils: DISHUtils that contains the dish_id, vcc_id, and k_value information
        :param subarray_dish_ids: List of dish_ids that are a member of the subarray
        :param wideband_shift: Wideband shift (Hz)
        :param frequency_band: The name of the frequency band ("1", "2", "5a", etc.)
        :raises ValueError: If the function_configuration does not contain a "processing_regions" key in
        """
        if "processing_regions" not in function_configuration:
            raise ValueError(
                "Function configuration is missing processing_regions parameter"
            )
        self._function_configuration = copy.deepcopy(function_configuration)
        self._dish_utils = dish_utils
        self._subarray_dish_ids = subarray_dish_ids
        self._wideband_shift = wideband_shift
        self._frequency_band = frequency_band

    def _fsp_config_from_processing_regions(
        self: FspScanConfigurationBuilder, processing_regions: list[dict]
    ) -> list[dict]:
        """Create a list of FSP configurations for a given list of processing regions

        :param processing_regions: a list of processing regions to generate configurations from
        :param function_mode: the function mode of the processing regions
        :raises ValueError: if the list of processing regions contains at least one invalid
        processing region or other configuration values are not valid
        :return: list of individual FSP configurations for the processing regions
        """

        fsp_configurations = []

        for index, processing_region in enumerate(processing_regions):
            # Calculate the fsp configs for the processing region
            try:
                fsp_configuration = self._fsp_config_from_processing_region(
                    processing_region
                )
            except ValueError as ve:
                msg = f"Failure processing processing region at index {index}: {ve}"
                raise ValueError(msg)

            fsp_configurations.extend(fsp_configuration)

        # the Host-LUT channel offset is based on the number of fine channels
        # in the FSP, as well as the number of FSP in the configuration
        host_lut_channel_offsets = [
            index * const.CENTRAL_FINE_CHANNELS
            for index in range(0, len(fsp_configurations))
        ]
        for host_lut_channel_offset, fsp_config in zip(
            host_lut_channel_offsets, fsp_configurations
        ):
            fsp_config["host_lut_channel_offset"] = host_lut_channel_offset

        return fsp_configurations

    ###############################################
    # Functions for inversing the vcc:fsp parings
    # from partition_spectrum_to_frequency_slices()
    ###############################################

    def _fs_to_vcc_infos_remap(
        self: FspScanConfigurationBuilder,
        calculated_fsp_ids: list,
        vcc_to_fs_infos: dict,
        function_ptr: Callable[[int, str, dict], any] | None = None,
    ) -> dict:
        """
        Returns remapped_vcc_to_fs_infos, a remapped dictionary of the given vcc_to_fs_infos
        that flips vcc_to_fs_infos[vcc_id][fsp_id] to remapped_vcc_to_fs_infos[fsp_id][vcc_id_str]

        This function does two mapping action on the given vcc_to_fs_infos dictionary:
           1.  With the given vcc_to_fs_infos, it remaps the VCC ID:FSP ID paring
               to FSP ID:VCC ID (see code comenet for more detail on this remapping)
           2a. If given a function pointer as an argument, it will perform the
               function on vcc_to_fs_infos[vcc_id][fsp_id] and store it at
               remapped_vcc_to_fs_infos[fsp_id][vcc_id_str]
           2b. If no function pointer is given, or None is given, it will store
               vcc_to_fs_infos[vcc_id][fsp_id] at remapped_vcc_to_fs_infos[fsp_id][vcc_id_str]

        If a function pointer is given, remapped_vcc_to_fs_infos[fsp_id][vcc_id_str]
        does not store the original values given at vcc_to_fs_infos[vcc_id][fsp_id],
        it will only store the value(s) returned by the function pointer.


        Essentially this as a mapping function on the vcc_to_fs_infos dictionary.
        Reference to mapping functions: https://docs.python.org/3/library/functions.html#map

        The argument `function_ptr` takes the following arguments:
            vcc_id: The ID value of a VCC
            fsp_id: The ID value of a FSP
            vcc_to_fs_infos: Given with _fs_to_vcc_infos_remap's arguments

        :param calculated_fsp_ids: list of required FSP IDs for the given Scan Configuration
        :param vcc_to_fs_infos: A dictionary that maps dish ids to a dictionary with information about fsp boundaries
                                More info regarding the fsp boundaries dictionary:
                                https://confluence.skatelescope.org/display/SE/Processing+Regions+for+CORR+-+Identify+and+Select+Fine+Channels#ProcessingRegionsforCORRIdentifyandSelectFineChannels-ExampleCalculatedFrequencySliceBoundaryInformation
        :param function_ptr: a function pointer that process the value(s) at vcc_to_fs_infos[vcc_id][fsp_id],
                             and then store the process info at inversed_vcc_to_fs_infos[fsp_id][vcc_id_str]
                             (Optional, defaults to None)

        :return: A remapped vcc_to_fs_infos dictionary
        :rtype: dict

        """
        # to explain the loops below, I'm moving from a per-vcc config in
        # vcc_to_fs_infos to a per-fsp config, as well as rename the fields to
        # match what HPS wants.

        # essentially I have in vcc_to_fs_infos:
        # vcc1:
        #     fsp_1:
        #           values A
        #     fsp_2:
        #           values B
        # vcc2:
        #     fsp_1:
        #           values C
        #     fsp_2:
        #           values D

        # But I need them sent down to HPS as:
        # fsp_1:
        #     vcc 1:
        #          values A
        #     vcc 2:
        #          values C
        # fsp_2:
        #     vcc 1:
        #          values B
        #     vcc 2:
        #          values D

        remapped_fs_to_vcc_infos = {}
        for fsp_id in calculated_fsp_ids:
            remapped_fs_to_vcc_infos[fsp_id] = {}
            for vcc_id in vcc_to_fs_infos.keys():
                # HPS wants vcc id to be a string value, not int
                vcc_id_str = str(vcc_id)
                remapped_fs_to_vcc_infos[fsp_id][vcc_id_str] = {}
                if function_ptr is None:
                    remapped_fs_to_vcc_infos[fsp_id][
                        vcc_id_str
                    ] = vcc_to_fs_infos[vcc_id][fsp_id]
                else:
                    remapped_fs_to_vcc_infos[fsp_id][
                        vcc_id_str
                    ] = function_ptr(fsp_id, vcc_id, vcc_to_fs_infos)

        return remapped_fs_to_vcc_infos

    def _calculate_vcc_id_to_fc_gain(
        self: FspScanConfigurationBuilder,
        fsp_id: int,
        vcc_id: int,
        vcc_to_fs_infos: dict,
    ) -> list:
        """
        An function point for _fs_to_vcc_infos_remap()
        Calculate vcc_id_to_fc_gain values for the given fsp_id and vcc_id

        vcc_id_to_fc_gain is the gain values needed by the 16k fine channelizer
        to correct for ripple in the signal created by VCC frequency response
        :param vcc_id: The ID value of a VCC
        :param fsp_id: The ID value of a FSP
        :param vcc_to_fs_infos: A dictionary that maps dish ids to a dictionary with information about fsp boundaries
                                More info regarding the fsp boundaries dictionary:
                                https://confluence.skatelescope.org/display/SE/Processing+Regions+for+CORR+-+Identify+and+Select+Fine+Channels#ProcessingRegionsforCORRIdentifyandSelectFineChannels-ExampleCalculatedFrequencySliceBoundaryInformation

        :return: a list that contains Fine Channelizer Gain corrections values for the given FSP ID and VCC ID
        :rtype: list

        """
        # SCFO shift is needed by both the RDT and FC
        scfo_fsft = vcc_to_fs_infos[vcc_id][fsp_id]["freq_scfo_shift"]

        # k value needed to calculate gain
        dish_id = self._dish_utils.vcc_id_to_dish_id[vcc_id]
        freq_offset_k = self._dish_utils.dish_id_to_k[dish_id]

        return get_vcc_ripple_correction(
            freq_band=self._frequency_band,
            scfo_fsft=scfo_fsft,
            freq_offset_k=freq_offset_k,
        )

    def _calculate_vcc_id_to_rdt_freq_shifts(
        self: FspScanConfigurationBuilder,
        fsp_id: int,
        vcc_id: int,
        vcc_to_fs_infos: dict,
    ) -> dict:
        """
        An function point for _fs_to_vcc_infos_remap()
        Calculates vcc_id_to_rdt_freq_shifts values

        vcc_id_to_rdt_freq_shifts are the shift values needed by the
        Resampler Delay Tracker (rdt) for each vcc of the FSP:
        freq_down_shift  - the the shift to move the FS into the center of the
                           digitized frequency (Hz)
        freq_align_shift - the shift to align channels between FSs (Hz)
        freq_wb_shift    - the wideband shift (Hz)
        freq_scfo_shift  - the frequency shift required due to Sample Clock
                           Frequency Offset (SCFO) sampling (Hz)

        See CIP-2622, or parent epic CIP-2145

        :param vcc_id: The ID value of a VCC
        :param fsp_id: The ID value of a FSP
        :param vcc_to_fs_infos: A dictionary that maps dish ids to a dictionary with information about fsp boundaries
                                More info regarding the fsp boundaries dictionary:
                                https://confluence.skatelescope.org/display/SE/Processing+Regions+for+CORR+-+Identify+and+Select+Fine+Channels#ProcessingRegionsforCORRIdentifyandSelectFineChannels-ExampleCalculatedFrequencySliceBoundaryInformation

        :return: dictionary that contains Resampler Delay Tracker correction values for the given FSP and VCC
        :rtype: dict

        """
        vcc_id_to_rdt_freq_shifts = {}
        vcc_id_to_rdt_freq_shifts[fsp_id] = {}

        down_shift = vcc_to_fs_infos[vcc_id][fsp_id]["alignment_shift_freq"]
        vcc_id_to_rdt_freq_shifts["freq_down_shift"] = down_shift

        align_shift = vcc_to_fs_infos[vcc_id][fsp_id]["alignment_shift_freq"]
        vcc_id_to_rdt_freq_shifts["freq_align_shift"] = align_shift
        vcc_id_to_rdt_freq_shifts["freq_wb_shift"] = self._wideband_shift

        # SCFO shift is needed by both the RDT and FC
        scfo_fsft = vcc_to_fs_infos[vcc_id][fsp_id]["freq_scfo_shift"]
        vcc_id_to_rdt_freq_shifts["freq_scfo_shift"] = scfo_fsft

        return vcc_id_to_rdt_freq_shifts

    ####################################################
    # End of functions for inversing the vcc:fsp parings
    # from partition_spectrum_to_frequency_slices()
    ####################################################

    def _process_start_channel_id(
        self: FspScanConfigurationBuilder,
        calculated_fsp_infos: dict,
        start_channel_id: int,
        channel_count: int,
    ) -> list:
        """
        Process the start channel ids based on the values calcualted in
        fine_channel_partitioner.partition_spectrum_to_frequency_slices()
        and the start channel id given.

        Note: The generic name start channel id is used here.
        For CORR processing region, it will be the sdp_start_channel_id value.
        For PST processing region, it will be the pst_start_channel_id value

        :param calculated_fsp_infos: The fsp infos calculated from
                                     fine_channel_partitioner.partition_spectrum_to_frequency_slices()
        :param start_channel_id: The start channel id given for a processing region
        :param channel_count: The channel count given for a processing region

        :return: A list of proceesed start channel ids based ont eh values
                 calculated in calculated_fsp_infos
        :rtype: list

        """
        # fsp_info["start_channel_id"] is the continuous start channel
        # id of the fsp's in a processing region
        #
        # Example: PR has sdp_start_channel_id = 100, and num_channels = 100,
        # we have have 3 FSPs (fsp_ids = [3, 4, 5]), the partition gives us:
        # FSP 3 - sdp_start_channel_id = 0
        # FSP 4 - sdp_start_channel_id = 40
        # FSP 5 - sdp_start_channel_id = 80
        #
        # The partitioner doesn't know about the processing regions
        # sdp_start_channel_id so it always starts at 0, add the PR
        # sdp_start_channel_id to the values.
        #
        # The lines of code below collects these into an array ([100, 140, 180])
        # as well as the last channel + 1 of the PR ([100, 140, 180, 200])
        #
        # We will be using these values to split up the output_host, output_port
        # and output_link map values for the fsps.
        start_channel_ids = [
            start_channel_id + fsp_info["start_channel_id"]
            for fsp_info in calculated_fsp_infos.values()
        ]
        start_channel_ids.append(start_channel_id + channel_count)

        return start_channel_ids

    def _process_output_mappings(
        self: FspScanConfigurationBuilder,
        calculated_fsp_infos: dict,
        output_mappings: dict,
        calculated_fsp_ids: list,
        start_channel_ids: list,
    ) -> dict:
        """
        Process the output port, output host, and output map by spliting the given values up,
        according to the start channel ids of the FSPs

        :param calculated_fsp_infos: The fsp infos calculated from
                                     fine_channel_partitioner.partition_spectrum_to_frequency_slices()
        :param output_mappings: A dictionary that contains output_port,
                                output_host, and output_link mappings to be processed.
                                This is pass to the function instead of the entire processing region as  CORR and PST
                                processing regions have the mappings in different locations inside the processing region configurations (as of Scan Configuration 5.0)
                                Note: Since these values are optional in a processing region, it is option that output_mapping contains those keys
        :param calculated_fsp_ids: The IDs of the FSP calcualted in calculated_fsp_infos
        :param start_channel_ids: The start channel ids of the processing region that the mappings originated from

        :return:    The processed output_port, output_host, output_link_map.
                    Each of the processed output mapping will be in a FSP ID (int) to Output_<> mapping (list)

        :rtype: dict


        """
        fsp_to_output_port_map = {}
        fsp_to_output_host_map = {}
        fsp_to_output_link_map = {}
        if "output_port" in output_mappings:
            # Split up the PR output ports according to the start channel ids of
            # the FSPs.
            #
            # See note in _process_start_channel_id() for explainations on
            # how the channels are split
            #
            # We use the array of start_channel_ids, and split up the
            # processing region output_port at the given start_channel_ids,
            #
            # Assuming the following start_channel_ids are given [100, 140, 180, 200]:
            #
            # if processing_region_config["output_port"] =
            # [
            #    [100, 14000],
            #    [120, 14001],
            #    [140, 14002],
            #    [160, 14003],
            #    [180, 14004],
            # ]
            #
            # running channel_map.split_channel_map_at() with
            # start_channel_ids = [100, 140, 180, 200] will result in
            # the array:
            #
            # [
            #     [ [100, 14000], [120, 14001] ],
            #     [ [140, 14002], [160, 14003] ],
            #     [ [180, 14004] ],
            # ]
            #
            # BUT we will also set rebase_groups to 0 to shift the channel_ids
            # such that the first channel_id is 0, so it becomes:
            # [
            #     [ [0, 14000], [20, 14001] ],
            #     [ [0, 14002], [20, 14003] ],
            #     [ [0, 14004] ],
            # ]

            split_output_ports = channel_map.split_channel_map_at(
                channel_map=output_mappings["output_port"],
                channel_groups=start_channel_ids,
                rebase_groups=0,
            )

            # Use zip to create a dictionary that maps the fsp to the output map
            # list above, so the result will be fsp_to_output_port_map =
            #
            # {
            #    3: [ [0, 14000], [20, 14001] ],
            #    4: [ [0, 14002], [20, 14003] ],
            #    5: [ [0, 14004] ],
            # }
            #
            # We also shift the maps by the fsp_start_ch of the fsp. we do this
            # because we'll be adding the channel_id with the channel_offset
            # when we send the channel_id to IP and port mapping to the SPEAD
            # Descriptor or Host-LUT.
            #
            # if the fsp_start_ch for the FSPs are [4400, 60, 80], then the
            # final mapping is:
            #
            # {
            #    3: [ [4400, 14000], [4420, 14001] ],
            #    4: [ [60, 14002], [80, 14003] ],
            #    5: [ [80, 14004] ],
            # }
            #
            # We can then use this dictionary later when building the fsp config

            for fsp_id, fsp_output_ports in zip(
                calculated_fsp_ids, split_output_ports
            ):
                fsp_to_output_port_map[fsp_id] = channel_map.shift_channel_map(
                    channel_map=fsp_output_ports,
                    channel_shift=calculated_fsp_infos[fsp_id]["fsp_start_ch"],
                )

        # do the same as output_port for output_hosts
        if "output_host" in output_mappings:
            split_output_hosts = channel_map.split_channel_map_at(
                channel_map=output_mappings["output_host"],
                channel_groups=start_channel_ids,
                rebase_groups=0,
            )

            for fsp_id, fsp_output_hosts in zip(
                calculated_fsp_ids, split_output_hosts
            ):
                fsp_to_output_host_map[fsp_id] = channel_map.shift_channel_map(
                    channel_map=fsp_output_hosts,
                    channel_shift=calculated_fsp_infos[fsp_id]["fsp_start_ch"],
                )

        # And again the same for output_link_map
        #
        # when we split the output_link map, which has a fewer mappings
        # than our start_channel_ids, like:
        # [[100, 1]]
        #
        # we will get:
        # [
        #   [[100,1]],
        #   [[100,1]],
        #   [[100,1]],
        # ]
        #
        # seems a bit extra, but this will support if/when output_link_map
        # contains more than one link.
        split_output_link_maps = channel_map.split_channel_map_at(
            channel_map=output_mappings["output_link_map"],
            channel_groups=start_channel_ids,
            rebase_groups=0,
        )

        for fsp_id, fsp_output_link_map in zip(
            calculated_fsp_ids, split_output_link_maps
        ):
            fsp_to_output_link_map[fsp_id] = channel_map.shift_channel_map(
                channel_map=fsp_output_link_map,
                channel_shift=calculated_fsp_infos[fsp_id]["fsp_start_ch"],
            )

        return {
            "output_port": fsp_to_output_port_map,
            "output_host": fsp_to_output_host_map,
            "output_link_map": fsp_to_output_link_map,
        }

    def _fsp_config_from_processing_region(
        self: FspScanConfigurationBuilder,
        processing_region_config: dict,
    ) -> list[dict]:
        """
        Abstraction Function, to be implemented in child FSP Mode specific class.
        Create a list of FSP configurations for a given processing region config

        :param processing_region_config: The processing region configuration, see telescope model for details
        :param wideband_shift: The wideband shift to apply to the region (Hz)
        :param function_mode: the function mode to configure the FSP's
        :raises ValueError: if the processing region or other configuration values are not valid
        :return: list of individual FSP configurations for a processing region
        """

        raise NotImplementedError(
            "_fsp_config_from_processing_region should be implemented in the child FSP Mode specific class."
        )

    def build(self: FspScanConfigurationBuilder) -> list[dict]:
        """Builds the individual FSP configurations based on the provided
        processing region configuration and other necessary config values
        provided in the initialization of this class.

        :raises ValueError: if values in the configuration are invalid
        :return: a list of FSP configurations
        """
        fsp_config = self._fsp_config_from_processing_regions(
            self._function_configuration["processing_regions"]
        )
        return fsp_config
