from ska_mid_cbf_tdc_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import FspModes
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.builder import (
    FspScanConfigurationBuilder,
)
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.fine_channel_partitioner import (
    partition_spectrum_to_frequency_slices,
)

# As of AA1.0 and Scan Configuration 5.0, PST Channel Width is predetermined
PST_CHANNEL_WIDTH = 53760


class FspScanConfigurationBuilderPst(FspScanConfigurationBuilder):

    """
    Correlation FSP Mode specific class for FspScanConfigurationBuilder
    """

    def __init__(
        self: FspScanConfigurationBuilder,
        function_configuration: dict,
        dish_utils: DISHUtils,
        subarray_dish_ids: set,
        wideband_shift: int,
        frequency_band: str,
    ):
        """Constructor for the FspScanConfigurationBuilder. Constructs FSP
        Configurations from a PST FSP Mode configuration.

        :param self: FspScanConfigurationBuilder object
        :param function_configuration: dictionary of the Function mode configuration from the input ConfigureScan configuration
        :param dish_utils: DISHUtils that contains the dish_id, vcc_id, and k_value information
        :param subarray_dish_ids: List of dish_ids that are a member of the subarray
        :param wideband_shift: Wideband shift (Hz)
        :param frequency_band: The name of the frequency band ("1", "2", "5a", etc.)
        :raises ValueError: If the function_configuration does not contain a "processing_regions" key in
        """

        self._function_mode = FspModes.PST
        super().__init__(
            function_configuration,
            dish_utils,
            subarray_dish_ids,
            wideband_shift,
            frequency_band,
        )

    def _fsp_config_from_processing_region(
        self: FspScanConfigurationBuilder,
        processing_region_config: dict,
    ) -> list[dict]:
        """
        Create a list of FSP configurations for a given processing region config

        :param processing_region_config: The processing region configuration, see telescope model for details
        :param wideband_shift: The wideband shift to apply to the region (Hz)
        :param function_mode: the function mode to configure the FSP's
        :raises ValueError: if the processing region or other configuration values are not valid
        :return: list of individual FSP configurations for a processing region
        """

        # sort the ids, just in case they are given in non-ascending order
        fsp_ids: list[int] = processing_region_config["fsp_ids"]
        fsp_ids.sort()
        timing_beams = processing_region_config["timing_beams"]
        dish_ids = []
        for timing_beam in timing_beams:
            if (
                "receptors" not in timing_beam
                or len(timing_beam["receptors"]) == 0
            ):
                for dish_id in self._subarray_dish_ids:
                    dish_ids.append(dish_id)
            else:
                for dish_id in timing_beam["receptors"]:
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
                channel_width=PST_CHANNEL_WIDTH,
                channel_count=processing_region_config["channel_count"],
                k_value=self._dish_utils.dish_id_to_k[dish_id],
                wideband_shift=self._wideband_shift,
                band_name=self._frequency_band,
                fsp_mode=self._function_mode,
            )
            vcc_to_fs_infos[
                self._dish_utils.dish_id_to_vcc_id[dish_id]
            ] = calculated_fsp_infos

        calculated_fsp_ids = list(calculated_fsp_infos.keys())

        # Calculate vcc_id_to_fc_gain and vcc_id_to_rdt_freq_shifts values
        vcc_id_to_rdt_freq_shifts: dict = (
            self._calculate_vcc_id_to_rdt_freq_shifts(
                calculated_fsp_ids, vcc_to_fs_infos
            )
        )

        # TODO:
        # CIP-2813: Currently FSP does not do anything with the output mappings
        # Will revisit in CIP-3202 or when we update "Visibiltiy Transport" for PST

        # Adjust the start_channel_ids based on
        # start_channel_ids = self._process_start_channel_id(
        #     calculated_fsp_infos,
        #     processing_region_config["pst_start_channel_id"],
        #     processing_region_config["channel_count"],
        # )

        # Split up the PR output ports according to the start channel ids of the FSPs.
        # See the comments in _process_output_mappings() for more details
        # Unlike Corr PR, all three fields are requried for PST PR
        # output_mappings = {
        #     "output_port": [],
        #     "output_host": [],
        #     "output_link_map": [],
        # }

        # for timing_beam in timing_beams:
        #     output_mappings["output_port"].extend(timing_beam["output_port"])
        #     output_mappings["output_host"].extend(timing_beam["output_host"])
        #     output_mappings["output_link_map"].extend(
        #         timing_beam["output_link_map"]
        #     )

        # processed_output_mappings = self._process_output_mappings(
        #     calculated_fsp_infos,
        #     output_mappings,
        #     calculated_fsp_ids,
        #     start_channel_ids,
        # )
        # fsp_to_output_port_map = processed_output_mappings["output_port"]
        # fsp_to_output_host_map = processed_output_mappings["output_host"]
        # fsp_to_output_link_map = processed_output_mappings["output_link_map"]

        # Build individual fsp configs
        fsp_configs = []

        for fsp_id, calculated_fsp_info in calculated_fsp_infos.items():
            fsp_config = {}
            # Required values
            fsp_config["fsp_id"] = fsp_id
            fsp_config["function_mode"] = self._function_mode.name
            fsp_config["frequency_slice_id"] = calculated_fsp_info["fs_id"]

            # TODO: Need to reconciled why there is a difference in field name between Scan Config and what
            # the FSP HPS App is expecting
            fsp_config["fsp_start_channel_id"] = processing_region_config[
                "pst_start_channel_id"
            ]

            # For now, copy all the timing beams for a PR to all FSP Config
            fsp_config["timing_beams"] = timing_beams

            fsp_config[
                "vcc_id_to_rdt_freq_shifts"
            ] = vcc_id_to_rdt_freq_shifts[fsp_id]

            # TODO:
            # CIP-2813: Currently FSP does not do anything with the output mappings
            # Will revisit in CIP-3202 or when we update "Visibiltiy Transport" for PST

            # fsp_config["output_link_map"] = fsp_to_output_link_map[fsp_id]
            # fsp_config["output_host"] = fsp_to_output_host_map[fsp_id]
            # fsp_config["output_port"] = fsp_to_output_port_map[fsp_id]

            fsp_configs.append(fsp_config)

        return fsp_configs
