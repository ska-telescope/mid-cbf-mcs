from __future__ import annotations

import copy
import ctypes

from ska_mid_cbf_tdc_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import FspModes
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.builder import (
    FspScanConfigurationBuilder,
)
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.fine_channel_partitioner import (
    partition_spectrum_to_frequency_slices,
)


class FspScanConfigurationBuilderCorr(FspScanConfigurationBuilder):

    """
    Correlation FSP Mode specific class for FspScanConfigurationBuilderCorr
    """

    def __init__(
        self: FspScanConfigurationBuilderCorr,
        function_configuration: dict,
        dish_utils: DISHUtils,
        subarray_dish_ids: set,
        wideband_shift: int,
        frequency_band: str,
    ):
        """Constructor for the FspScanConfigurationBuilderCorr. Constructs FSP
        Configurations from a Corr FSP Mode configuration.

        :param self: FspScanConfigurationBuilderCorr object
        :param function_configuration: dictionary of the Function mode configuration from the input ConfigureScan configuration
        :param dish_utils: DISHUtils that contains the dish_id, vcc_id, and k_value information
        :param subarray_dish_ids: List of dish_ids that are a member of the subarray
        :param wideband_shift: Wideband shift (Hz)
        :param frequency_band: The name of the frequency band ("1", "2", "5a", etc.)
        :raises ValueError: If the function_configuration does not contain a "processing_regions" key in
        """

        super().__init__(
            function_configuration,
            dish_utils,
            subarray_dish_ids,
            wideband_shift,
            frequency_band,
        )

        self._function_mode = FspModes.CORR

    def _fsp_config_from_processing_region(
        self: FspScanConfigurationBuilderCorr,
        processing_region_config: dict,
    ) -> list[dict]:
        """Create a list of FSP configurations for a given processing region config

        :param processing_region_config: The processing region configuration, see telescope model for details
        :param wideband_shift: The wideband shift to apply to the region (Hz)
        :param function_mode: the function mode to configure the FSP's
        :raises ValueError: if the processing region or other configuration values are not valid
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
            for dish_id in self._subarray_dish_ids:
                dish_ids.append(dish_id)
        else:
            for dish_id in processing_region_config["receptors"]:
                if dish_id in self._subarray_dish_ids:
                    dish_ids.append(dish_id)
                else:
                    raise ValueError(
                        f"receptor {dish_id} is not in the set "
                        + f"of subarray receptors {self._subarray_dish_ids}"
                    )

        vcc_to_fs_infos = {}
        # Need to send vcc shift values for all subarray vcc's not just those
        # specified in the `receptors` property
        for dish_id in self._subarray_dish_ids:
            calculated_fsp_infos = partition_spectrum_to_frequency_slices(
                fsp_ids=fsp_ids,
                start_freq=processing_region_config["start_freq"],
                channel_width=processing_region_config["channel_width"],
                channel_count=processing_region_config["channel_count"],
                k_value=self._dish_utils.dish_id_to_k[dish_id],
                wideband_shift=self._wideband_shift,
                band_name=self._frequency_band,
            )
            vcc_to_fs_infos[
                self._dish_utils.dish_id_to_vcc_id[dish_id]
            ] = calculated_fsp_infos

        calculated_fsp_ids = list(calculated_fsp_infos.keys())

        # Calculate vcc_id_to_fc_gain and vcc_id_to_rdt_freq_shifts values
        vcc_id_to_rdt_freq_shifts: dict = self._fs_to_vcc_infos_remap(
            calculated_fsp_ids,
            vcc_to_fs_infos,
            self._calculate_vcc_id_to_rdt_freq_shifts,
        )
        vcc_id_to_fc_gain: dict = self._fs_to_vcc_infos_remap(
            calculated_fsp_ids,
            vcc_to_fs_infos,
            self._calculate_vcc_id_to_fc_gain,
        )

        # Adjust the start_channel_ids based on
        start_channel_ids = self._process_start_channel_id(
            calculated_fsp_infos,
            processing_region_config["sdp_start_channel_id"],
            processing_region_config["channel_count"],
        )
        # Split up the PR output ports according to the start channel ids of the FSPs.
        # See the comments in _process_output_mappings() for more details
        output_mappings = {}

        # output_port and output_host are optional parameters
        if "output_port" in processing_region_config:
            output_mappings["output_port"] = processing_region_config[
                "output_port"
            ]

        if "output_host" in processing_region_config:
            output_mappings["output_host"] = processing_region_config[
                "output_host"
            ]

        # No need to check for output_link_map as at least one is required
        # (as of Scan Configuration 3.0)
        output_mappings["output_link_map"] = processing_region_config[
            "output_link_map"
        ]

        processed_output_mappings = self._process_output_mappings(
            calculated_fsp_infos,
            output_mappings,
            calculated_fsp_ids,
            start_channel_ids,
        )
        fsp_to_output_port_map = processed_output_mappings["output_port"]
        fsp_to_output_host_map = processed_output_mappings["output_host"]
        fsp_to_output_link_map = processed_output_mappings["output_link_map"]

        # Build individual fsp configs
        fsp_configs = []

        for fsp_id, calculated_fsp_info in calculated_fsp_infos.items():
            fsp_config = {}
            # Required values
            fsp_config["fsp_id"] = fsp_id
            fsp_config["function_mode"] = self._function_mode.name
            fsp_config["frequency_slice_id"] = calculated_fsp_info["fs_id"]
            fsp_config["integration_factor"] = processing_region_config[
                "integration_factor"
            ]
            fsp_config["receptors"] = copy.copy(dish_ids)

            # The 0-14880 channel number where we want to start processing in
            # the FS, which is the fsp_start_ch value
            fsp_config["fs_start_channel_offset"] = calculated_fsp_info[
                "fsp_start_ch"
            ]

            # spead / fsp channel_offset
            # this offset flows down to SPEAD into value channel_id.
            # channel_id needs to be set such that the 'start' is
            # sdp_start_channel_id of the fsp.
            #
            # spead_channel_offset = "absolute" sdp_start_channel_id - fsp_start_ch
            # WITH unsigned 32-bit integer underflow, because the FW will add the
            # channel number (0 to 744)*20  to this value WITH overflow and put it
            # in the SPEAD packets.
            #
            # The fsp.sdp_start_channel_id is only relative to the
            # assigned fsps, and not to the pr.sdp_start_channel_id, so the
            # "absolute" sdp_start_channel_id is to add the fsp and pr
            # start_channel_ids together.
            fsp_config["spead_channel_offset"] = ctypes.c_uint32(
                processing_region_config["sdp_start_channel_id"]
                + calculated_fsp_info["start_channel_id"]
                - calculated_fsp_info["fsp_start_ch"]
            ).value

            fsp_config[
                "vcc_id_to_rdt_freq_shifts"
            ] = vcc_id_to_rdt_freq_shifts[fsp_id]

            fsp_config["vcc_id_to_fc_gain"] = vcc_id_to_fc_gain[fsp_id]

            fsp_config["output_link_map"] = fsp_to_output_link_map[fsp_id]

            # Optional values:
            if "output_host" in processing_region_config:
                fsp_config["output_host"] = fsp_to_output_host_map[fsp_id]
            if "output_port" in processing_region_config:
                fsp_config["output_port"] = fsp_to_output_port_map[fsp_id]

            fsp_configs.append(fsp_config)

        return fsp_configs
