from __future__ import annotations  # allow forward references in type hints

import copy
import json
import logging
from collections import defaultdict

from ska_mid_cbf_tdc_mcs.commons.global_enum import (
    FspModes,
    const,
    get_coarse_channels,
    get_end_frequency,
    scan_configuration_supported_value,
)

"""
SubarrayScanConfigurationValidator: Contains functions that validates a given
                                    Subarray Scan Configuration
"""


class SubarrayScanConfigurationValidator:
    # Valid FSP IDs
    (
        supported_fsp_id_lower,
        supported_fsp_id_upper,
    ) = scan_configuration_supported_value("fsp_ids")

    # Matches the value given by Scan Configuration for function mode (post v4.0)
    # to the enum value of the FspMode in global_enum.py
    function_mode_value_enum_match = {
        "idle": "IDLE",
        "correlation": "CORR",
        "pss": "PSS-BF",
        "pst": "PST-BF",
        "vlbi": "VLBI",
    }

    def __init__(
        self: SubarrayScanConfigurationValidator,
        scan_configuration: str,
        dish_ids: list[str],
        subarray_id: int,
        logger: logging.Logger,
        count_fsp: int,
    ) -> None:
        """
        Constructor for SubarrayScanConfigurationValidator

        :param scan_configuration: A Scan Configuration json string
        :param dish_ids: list of Dish IDs
        :param subarray_id: The ID of the Subarray's Scan Configuration being validated
        :param logger: A Logger object to handle logging message for the class
        :param count_fsp: Count of FSPs in a Subarray Component Manager to be validated
        """

        self._scan_configuration = scan_configuration
        self._count_fsp = count_fsp

        # TODO: PSS, PST, VLBI support
        # self._proxies_fsp_pss_subarray_device = None
        # self._proxies_fsp_pst_subarray_device = None

        self._dish_ids = dish_ids
        self._subarray_id = subarray_id
        self.logger = logger

    # --- Mid.CBF --- #

    def _validate_receptors(
        self: SubarrayScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the "receptors" value found in Processing Region is
        within the given specification

        :param processing_region: Processing Region configuration as a
                    Dictionary

        :return: tuple with:
                    bool to indicate if the receptors is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # dishes may not be specified in the
        # configuration at all, or the list may be empty
        if (
            "receptors" in processing_region
            and len(processing_region["receptors"]) > 0
        ):
            self.logger.debug(f"List of receptors: {self._dish_ids}")
            for dish in processing_region["receptors"]:
                if dish not in self._dish_ids:
                    msg = (
                        f"Receptor {dish} does not belong to "
                        f"subarray {self._subarray_id}."
                    )
                    self.logger.error(msg)
                    return (False, msg)
        else:
            msg = (
                "'receptors' not specified for Fsp CORR config."
                "Per ICD all receptors allocated to subarray are used"
            )
            self.logger.debug(msg)

        msg = "Validate Receptor: Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_integration_time(
        self: SubarrayScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the integration_factor value found in
        the Processing Region is within the given specification

        :param processing_region: Processing Region configuration as a
                    Dictionary

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Validate integrationTime.
        if int(processing_region["integration_factor"]) in list(
            range(
                const.MIN_INT_TIME,
                10 * const.MIN_INT_TIME + 1,
                const.MIN_INT_TIME,
            )
        ):
            msg = "Validate Integration Time: Complete"
            self.logger.debug(msg)
            return (True, msg)
        else:
            msg = (
                "'integrationTime' must be an integer in the range"
                f" [1, 10] multiplied by {const.MIN_INT_TIME}."
            )
            self.logger.error(msg)
            return (False, msg)

    def _validate_output_link_map(
        self: SubarrayScanConfigurationValidator, output_link_map: dict
    ) -> tuple[bool, str]:
        """
        Validates that the channel/values Output Link Map pair
        is of the type (int, int)

        :param output_link_map: A Channel/Value pair of ints

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        try:
            for element in output_link_map:
                (int(element[0]), int(element[1]))
        except (TypeError, ValueError, IndexError):
            msg = "'outputLinkMap' format not correct."
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate Output Link Map: Complete"
        self.logger.debug(msg)
        return (True, msg)

    # --- TODO: PSS --- #

    # TODO: Eventually Scan Configuration will change PSS to be used as Processing Regions

    def _validate_search_window(
        self: SubarrayScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the Search Window specified in MidCBF Configuration

        :param configuration: A MidCBF Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the search window is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Validate searchWindow.
        if "search_window" in configuration:
            if scan_configuration_supported_value("search_window") is False:
                msg = "search_window Not Supported in AA 0.5 and AA 1.0"
                self.logger.error(msg)
                return (False, msg)
            else:
                msg = "search_window is indicated as supported \
                but validation has not been implemented for it"
                self.logger.error(msg)
                return (False, msg)
                # not supported in AA 0.5 and AA 1.0
                # check if searchWindow is an array of maximum length 2
                # if len(configuration["search_window"]) > 2:
                #     msg = (
                #         "'searchWindow' must be an array of maximum length 2. "
                #         "Aborting configuration."
                #     )
                #     self.logger.error(msg)
                #     return (False, msg)
                # msg = "Validate Search Window: Complete"
                # self.logger.info(msg)
                # return (True, msg)
        else:
            msg = "Validate Search Window: Search Window not in Configuration: Complete"
            self.logger.debug(msg)
            return (True, msg)

    def _validate_pss_function_mode(
        self: SubarrayScanConfigurationValidator, pss: dict
    ) -> tuple[bool, str]:
        """
        Validates that the Configuration for PSS Function Mode is within
        Scan Configuration specification (post 4.0)

        :param pss: A PSS Configuration defined by Scan Configurations

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        msg = "MCS Current Does not Support PSS Configurations, Skipping"
        self.logger.warning(msg)
        return (True, msg)

    # --- TODO: PST --- #

    # TODO: 5.0 Scan Configuration will change PST to be used as Processing Regions

    def _validate_pst_function_mode(
        self: SubarrayScanConfigurationValidator, pst: dict
    ) -> tuple[bool, str]:
        """
        Validates that the Configuration for PST Function Mode is within
        Scan Configuration specification (post 4.0)

        :param pst: A PST Configuration defined by Scan Configurations

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        msg = "MCS Current Does not Support PST Configurations, Skipping"
        self.logger.warning(msg)
        return (True, msg)

    # --- Common --- #

    def _validate_common(
        self: SubarrayScanConfigurationValidator, common_configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the values in the Common Configuration

        :param common_configuration: A Common Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        frequency_band = common_configuration["frequency_band"]
        subarray_id = common_configuration["subarray_id"]

        supported_frequency_band = scan_configuration_supported_value(
            "frequency_band"
        )

        if frequency_band not in supported_frequency_band:
            msg = f"frequency_band {frequency_band} not supported. \
                    MCS currently only supports {supported_frequency_band}, \
                    Rejecting Scan Configuration"
            self.logger.error(msg)
            return (False, msg)

        # Checks Subarray ID Against Current MCS Supported Values
        supported_subarray_ids = scan_configuration_supported_value(
            "subarray_id"
        )
        if int(subarray_id) not in supported_subarray_ids:
            msg = (
                f"subarray_id {subarray_id} not supported. "
                f"MCS currently only supports {supported_subarray_ids}"
            )
            self.logger.error(msg)
            return (False, msg)

        if "band_5_tuning" in common_configuration:
            if scan_configuration_supported_value("band_5_tuning") is False:
                msg = "band_5_tuning is currently not supported in MCS, \
                      Rejecting Scan Configuration"
                self.logger.error(msg)
                return (False, msg)
            else:
                msg = "band_5_tuning is indicated as supported, but validation \
                        has not been implemented"
                self.logger.error(msg)
                return (False, msg)

        msg = "Validate Common: Completed"
        self.logger.debug(msg)
        return (True, msg)

    # --- Mid.CBF --- #

    def _validate_midcbf_keys(
        self: SubarrayScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the keys for the MidCBF Configurations of a Scan Configuration

        :param configuration: A MidCBF Configuration of the a Scan Configuration

        :return: tuple with:
            bool to indicate if the MidCBF keys are valid or not
            str message about the configuration
        :rtype: tuple[bool, str]
        """

        success, msg = self._validate_search_window(configuration)
        if success is False:
            return (False, msg)

        # Not Supported in AA 0.5/AA 1.0
        if "frequency_band_offset_stream1" in configuration:
            if (
                scan_configuration_supported_value(
                    "frequency_band_offset_stream1"
                )
                is False
            ):
                msg = "frequency_band_offset_stream1 Currently Not Supported In AA 0.5/AA 1.0"
                self.logger.error(msg)
                return (False, msg)
            else:
                msg = "frequency_band_offset_stream1 is indicated as supported but validation has not been implemented for it"
                self.logger.error(msg)
                return (False, msg)
                # Not Supported Currently in AA 0.5/AA 1.0
                # fsp["frequency_band_offset_stream1"] = configuration[
                #     "frequency_band_offset_stream1"
                # ]
                # if "frequency_band_offset_stream1" not in configuration:
                #     configuration["frequency_band_offset_stream1"] = 0
                # if (
                #     abs(int(configuration["frequency_band_offset_stream1"]))
                #     <= const.FREQUENCY_SLICE_BW * 10**6 / 2
                # ):
                #     pass
                # else:
                #     msg = (
                #         "Absolute value of 'frequencyBandOffsetStream1' must be at most half "
                #         "of the frequency slice bandwidth. Aborting configuration."
                #     )
                #     return (False, msg)

        # Not Supported in AA 0.5/AA 1.0
        if "frequency_band_offset_stream2" in configuration:
            if (
                scan_configuration_supported_value(
                    "frequency_band_offset_stream2"
                )
                is False
            ):
                msg = "frequency_band_offset_stream2 Currently Not Supported In AA 0.5/AA 1.0"
                self.logger.error(msg)
                return (False, msg)
            else:
                msg = "frequency_band_offset_stream2 is indicated as supported but validation has not been implemented for it"
                self.logger.error(msg)
                return (False, msg)
                # Not Supported Currently in AA 0.5/AA 1.0
                # fsp["frequency_band_offset_stream2"] = configuration[
                #     "frequency_band_offset_stream2"
                # ]
                # if "frequency_band_offset_stream2" not in configuration:
                # configuration["frequency_band_offset_stream2"] = 0
                # if (
                #     abs(int(configuration["frequency_band_offset_stream2"]))
                #     <= const.FREQUENCY_SLICE_BW * 10**6 / 2
                # ):
                #     pass
                # else:
                #     msg = (
                #         "Absolute value of 'frequencyBandOffsetStream2' must be at most "
                #         "half of the frequency slice bandwidth. Aborting configuration."
                #     )
                #     return (False, msg)

        # Not Supported in AA 0.5/AA 1.0
        if "rfi_flagging_mask" in configuration:
            if (
                scan_configuration_supported_value("rfi_flagging_mask")
                is False
            ):
                msg = "rfi_flagging_mask Currently Not Supported In AA 0.5/AA 1.0"
                self.logger.error(msg)
                return (False, msg)
            else:
                msg = "rfi_flagging_mask is indicated as supported but validation has not been implemented for it"
                self.logger.error(msg)
                return (False, msg)

        # Not Supported in AA 0.5/AA 1.0
        if "vlbi" in configuration:
            if scan_configuration_supported_value("vlbi") is False:
                msg = "vlbi Currently Not Supported In AA 0.5/AA 1.0"
                self.logger.error(msg)
                return (False, msg)
            else:
                msg = "vlbi is indicated as supported but validation has not been implemented for it"
                self.logger.error(msg)
                return (False, msg)

        msg = "Validate CBF Configuration: Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_processing_region_channel_values(
        self: SubarrayScanConfigurationValidator,
        processing_region: dict,
        fsp_mode: FspModes,
    ) -> tuple[bool, str]:
        """
        Validates that the channels values requested in a single processing region
        are valid

        :param processing_region: A Single Processing Region within
                                a Processing Regions Configuration

        :return: tuple with:
                    bool to indicate if the channel values are valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """

        channel_width = int(processing_region["channel_width"])
        channel_count = int(processing_region["channel_count"])
        sdp_start_channel_id = int(processing_region["sdp_start_channel_id"])

        valid_channel_width = scan_configuration_supported_value(
            "processing_region"
        )[fsp_mode]["channel_width"]

        # Edit the Error message once more valid channel width are added
        if channel_width not in valid_channel_width:
            msg = f"Invalid value for channel_width:{channel_width}. \
                    MCS supports only {valid_channel_width} (Values in hertz)"
            self.logger.error(msg)
            return (False, msg)

        valid_channel_count_values = scan_configuration_supported_value(
            "processing_region"
        )[fsp_mode]["channel_count"]

        channel_count_multiple = valid_channel_count_values["multiple"]
        if channel_count % channel_count_multiple != 0:
            msg = f"Invalid value for channel_count, not a multiple of {channel_count_multiple}: {channel_count}"
            self.logger.error(msg)
            return (False, msg)
        channel_count_range = valid_channel_count_values["range"]
        if (
            channel_count < channel_count_range[0]
            or channel_count > channel_count_range[1]
        ):
            msg = f"Invalid value for channel_count, outside of range {channel_count_range}:{channel_count}"
            self.logger.error(msg)
            return (False, msg)

        if sdp_start_channel_id < 0:
            msg = f"Invalid value for sdp_start_channel_id, must be a positive integer: {sdp_start_channel_id}"
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate Processing Region Channel Option Values: Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_fsp_id(
        self: SubarrayScanConfigurationValidator,
        fsp_id: int,
        fsp_mode: FspModes,
        supported_function_mode_fsp_ids: list[int],
        fsp_id_in_processing_region: set[int],
    ) -> tuple[bool, str]:
        """
        Validates the FSP ID given matches the criteria setup for the Scan Configuration.

        :param fsp_id: A int value representing the FSP that we want to validate
                        from the MidCBF Configuration
        :param fsp_mode: A FspModes Enum that indicates thee FSP Mode for the
                        given fsp_id
        :param supported_function_mode_fsp_ids: A list of supported FSP ID
                        for the given Function Mode
        :param fsp_id_in_processing_region: a Hashset of integers that
                        keeps track of FSP IDs already seen in the subarray

        :return: tuple with:
                    bool to indicate if the FSP ID is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """

        # first check that the fsp_id is a valid value
        if fsp_id not in range(
            self.supported_fsp_id_lower, self.supported_fsp_id_upper + 1
        ):
            msg = (
                "Current MCS only support FSP ID in range "
                f"[{self.supported_fsp_id_lower}-{self.supported_fsp_id_upper}] "
                f"FSP ID Given: {fsp_id}"
            )

        # next check that the fsp_id is valid for the FSP Mode
        # NOTE: When we remove the restrictions of FSP to specific mode, we can remove
        # the validation below
        # check in global_enum.py for the supported fsp id per fsp mode dictionary
        if fsp_id not in supported_function_mode_fsp_ids:
            msg = f"AA 0.5 Requirement: {fsp_mode.name} Supports only FSP {supported_function_mode_fsp_ids}."
            self.logger.error(msg)
            return (False, msg)

        if fsp_id in fsp_id_in_processing_region:
            msg = f"FSP ID {fsp_id} already assigned to another Processing Region"
            self.logger.error(msg)
            return (False, msg)

        # Check if the fsp_id is a valid FSP in the Subarray
        if fsp_id in list(range(1, self._count_fsp + 1)):
            fsp_id_in_processing_region.add(fsp_id)
            msg = f"fsp_id {fsp_id} is valid"
            self.logger.debug(msg)
            return (True, msg)
        else:
            msg = (
                f"'fsp_id' must be an integer in the range [1, {self._count_fsp}]."
                f" {fsp_id} is not a valid FSP in the Subarray Device. Aborting configuration."
            )
            self.logger.error(msg)
            return (False, msg)

    def _validate_corr_function_mode(
        self: SubarrayScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the Processing Region for CORR FSP Function Mode is within
        Scan Configuration specification

        :param processing_region: A Single Processing Region within
                                    a Processing Regions Configuration

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        success, msg = self._validate_receptors(processing_region)
        if success is False:
            return (False, msg)

        success, msg = self._validate_integration_time(processing_region)
        if success is False:
            return (False, msg)

        success, msg = self._validate_output_link_map(
            processing_region["output_link_map"]
        )
        if success is False:
            return (False, msg)

        msg = "FSP CORR Validation Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_max_20_channel_to_same_port_per_host(
        self: SubarrayScanConfigurationValidator,
        output_host_map: dict,
        output_port_map: dict,
        sdp_start_channel_id: int,
        channel_count: int,
    ) -> tuple[bool, str]:
        """
        Validates that we are sending only at most 20 channels to a single port per host
        This assumes that both output_host and output_port are valid

        :param output_host_map: A valid output_host channel map from a processing region
        :param output_port_map: A valid output_port channel map from a processing region
        :param sdp_start_channel_id: The first channel in the processing region
        :param channel_count: Count of channels specified in the processing region

        :return: tuple with:
                    bool to indicate if the channels sent is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        host_port_channel_count = defaultdict(lambda: defaultdict(int))
        output_host_dict = {key: value for key, value in output_host_map}
        output_port_dict = {key: value for key, value in output_port_map}
        current_host = output_host_dict[sdp_start_channel_id]
        current_port = output_port_dict[sdp_start_channel_id]

        for channel in range(
            sdp_start_channel_id, sdp_start_channel_id + channel_count
        ):
            if channel in output_host_dict:
                current_host = output_host_dict[channel]
            if channel in output_port_dict:
                current_port = output_port_dict[channel]

            host_port_channel_count[current_host][current_port] += 1

            if host_port_channel_count[current_host][current_port] > 20:
                msg = (
                    "There are over 20 channels assigned to a specific port within a single host "
                    f"Host:{current_host} Port:{current_port} Channel:{channel}"
                )
                self.logger.error(msg)
                return (False, msg)

        msg = "20 Max Channel To Same Port Within a Host: Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_processing_region_within_bandwidth(
        self: SubarrayScanConfigurationValidator,
        start_freq: int,
        channel_width: int,
        channel_count: int,
    ) -> tuple[bool, str]:
        """
        Validates that the Processing Region's frequency range falls
        within 0 Hz to 1,981,808,640 Hz

        Gives a warning if the range given as calculated from the start_freq,
        channel_width and channel_count is outside the range for
        Bands 1 & 2 (350MHz to 1760MHz)

        :param start_freq: The center start frequency given for Processing Region
        :param channel_width: The channel width given for the Processing Region
        :param channel_count: The channel count request for the Process Region

        :return: tuple with:
                    bool to indicate if the frequency range is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # The actual start of the band is at start_freq - (channel_width/2)
        # because start_freq the the center of the first fine channel
        processing_region_lower_freq = start_freq - (channel_width / 2)
        processing_region_upper_freq = processing_region_lower_freq + (
            channel_width * channel_count
        )

        # First Check: check that it is within the acceptable
        # range that MCS will take in [0-1981808640]
        (
            lower_freq_bound,
            upper_freq_bound,
        ) = scan_configuration_supported_value("frequency")
        if (processing_region_lower_freq < lower_freq_bound) or (
            processing_region_upper_freq > upper_freq_bound
        ):
            msg = (
                "The Processing Region is not within the range for the "
                f"[{lower_freq_bound}-{upper_freq_bound}] that is accepted by MCS"
                f"\nProcessing Region range: {processing_region_lower_freq} - {processing_region_upper_freq} with starting center at {start_freq}"
            )
            self.logger.error(msg)
            return (False, msg)

        # Second Check: Gives a warning if the given range
        # is outside of [Band1.lower-Band2.upper]'s range
        band1_lower_freq_bound, band2_upper_freq_bound = (
            const.FREQUENCY_BAND_1_RANGE_HZ[0],
            const.FREQUENCY_BAND_2_RANGE_HZ[1],
        )
        if (processing_region_lower_freq < band1_lower_freq_bound) or (
            processing_region_upper_freq > band2_upper_freq_bound
        ):
            msg = (
                f"The Processing Region is not within the range for \
                     [Band1.lower-Band2.upper]: [{band1_lower_freq_bound}-{band2_upper_freq_bound}]",
                f"\nProcessing Region range: {processing_region_lower_freq} - {processing_region_upper_freq}\
                      with starting center at {start_freq}",
            )
            self.logger.warning(msg)

        msg = "Validate Processing Region Within Band: Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_fsp_requirement_by_given_bandwidth(
        self: SubarrayScanConfigurationValidator,
        fsp_given: list[str],
        start_freq: int,
        channel_width: int,
        channel_count: int,
    ) -> tuple[bool, str]:
        """
        Validates that the Processing Region contains enough FSP to process the
        Bandwidth that was specified from start_freq, channel_width, and channel_count

        :param fsp_given: A list of FSP ID given for a Processing Region
        :param start_freq: The center start frequency given for Processing Region
        :param channel_width: The channel width given for the Processing Region
        :param channel_count: The channel count request for the Process Region

        :return: tuple with:
                    bool to indicate if the there is enough fsp or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # check if we have enough FSP for the given Frequency Band
        end_freq = get_end_frequency(start_freq, channel_width, channel_count)
        coarse_channels = get_coarse_channels(start_freq, end_freq, wb_shift=0)

        if len(fsp_given) < len(coarse_channels):
            msg = (
                "Not enough FSP assigned in the processing region to process the range of the requested spectrum"
                f"\nNumber of FSPs Required: {len(coarse_channels)}, Number of FSPs Given: {len(fsp_given)}"
            )
            self.logger.error(msg)
            return (False, msg)

        if len(fsp_given) > len(coarse_channels):
            msg = (
                "Too many FSP assigned in the processing region to process the range of the requested spectrum"
                f"\nNumber of FSPs Required: {len(coarse_channels)}, Number of FSPs Given: {len(fsp_given)}"
            )
            self.logger.error(msg)
            return (False, msg)

        msg = (
            "Validate FSP requirement by frequency Band: Complete:"
            f"FSP Required: {coarse_channels} FSP Given: {fsp_given}"
        )
        self.logger.debug(msg)
        return (True, msg)

    def _validate_processing_region_frequency(
        self: SubarrayScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the values found in a Processing Region is within the
        range specified and that there are enough FSP to cover the range

        :param processing_region: A Single Processing Region within
                                    a Processing Regions Configuration

        :return: tuple with:
                    bool to indicate if the frequency requested is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        channel_width = int(processing_region["channel_width"])
        channel_count = int(processing_region["channel_count"])
        fsp_given = processing_region["fsp_ids"]
        start_freq = int(processing_region["start_freq"])

        # Check that the Bandwidth specified is within the allowable range
        success, msg = self._validate_processing_region_within_bandwidth(
            start_freq, channel_width, channel_count
        )
        if success is False:
            return (False, msg)

        # Check that we have enough FSP to cover the required Bandwidth requested
        success, msg = self._validate_fsp_requirement_by_given_bandwidth(
            fsp_given, start_freq, channel_width, channel_count
        )
        if success is False:
            return (False, msg)

        msg = "Validate Processing Region Frequency Options Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_channels_maps(
        self: SubarrayScanConfigurationValidator,
        map_pairs: list[list[int, int]],
        map_type: str,
        sdp_start_channel_id: int,
        channel_count: int,
        fsp_mode: FspModes,
    ):
        """
        Validates the list of (channel id, value) pairs for Output Host,
        Output Port or Output Link Maps

        First check if the first Start Channel ID in the list matches the
        requested SDP Start Channel ID

        Then it branches off to specific validations for each map types, mainly
        to check that it has been incremented correctly

        :param map_pairs:  A list of list of int, int tuple that contains the
                            channel and a value (port, host, etc.)
        :param map_type: The name of the type of map  that was passed in with map_pairs
        :param sdp_start_channel_id: The given sdp start channel id for given
                            processing region
        :param channel_count: The channel count given for the processing region
        :param fsp_mode: The FSP Function Mode requested for the processing region

        :return: tuple with:
                    bool to indicate if the list of is (channel id, value) pairs valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # for output_host, output_port, output_link_map
        # make sure only 20 channels are sent to a specific port

        valid_values_for_processing_region = (
            scan_configuration_supported_value("processing_region")
        )

        # channel_count = len(map_pairs*20) for ADR
        channel_count_valid_values = valid_values_for_processing_region[
            fsp_mode
        ]["channel_count"]
        channel_count_multiple = channel_count_valid_values["multiple"]
        map_channel_count = len(map_pairs * channel_count_multiple)
        if map_channel_count > channel_count:
            msg = (
                f"{map_type} exceeds the max allowable channel "
                f"as there are more channels specified in\
                {map_type}({map_channel_count}) then given in\
                 channel_count({channel_count})."
            )
            self.logger.error(msg)
            return (False, msg)

        # check that the spd_start_channel_id matches the first channel in the map
        if sdp_start_channel_id != map_pairs[0][0]:
            msg = (
                f"Start Channel ID ({sdp_start_channel_id}) must be the same must match the"
                f" first channel entry of {map_type} ({map_pairs[0][0]})"
            )
            self.logger.error(msg)
            return (False, msg)

        valid_map_type_value = valid_values_for_processing_region[fsp_mode][
            map_type
        ]

        # specific check for output_link_map. Remove if the restriction is changed
        if map_type == "output_link_map":
            valid_output_link_map_value = valid_map_type_value["values"]
            if map_pairs[0][1] not in valid_output_link_map_value:
                msg = f"{map_pairs[0]} is not a supported pair for MCS \
                        valid output link(s): {valid_output_link_map_value}"
                self.logger.error(msg)
                return (False, msg)

        # check that channels are in increment for output_port
        if map_type == "output_port":
            output_port_increment = valid_map_type_value["increment"]
            prev = map_pairs[0][0] - output_port_increment
            for channel, value in map_pairs:
                if channel - prev != output_port_increment:
                    msg = (
                        f"{map_type} channel map pair [{channel},{value}]: "
                        f"channel must be in increments of 20 (Previous Channel: {prev}) "
                        "For AA 0.5 and AA 1.0"
                    )
                    self.logger.error(msg)
                    return (False, msg)
                prev = channel

        # check that channels are multiple of map_type_increment for output_host
        # and in ascending order
        if map_type == "output_host":
            output_host_difference_multiple = valid_map_type_value[
                "difference_multiple"
            ]
            prev = -1
            for channel, value in map_pairs:
                if (
                    channel - map_pairs[0][0]
                ) % output_host_difference_multiple != 0:
                    msg = (
                        f"{map_type} channel map pair [{channel},{value}]:",
                        f"difference between {map_type} values must be a multiple of 20",
                        "For AA 0.5 and AA 1.0",
                    )
                    self.logger.error(msg)
                    return (False, msg)
                if channel <= prev:
                    msg = (
                        "Output Host Values must be in ascending order and cannot be duplicate"
                        f"Current Value: {value} Previous Value: {prev}"
                    )
                    self.logger.error(msg)
                    return (False, msg)

                prev = channel

        msg = f"Validate Channel Maps for {map_type} : Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_processing_regions(
        self: SubarrayScanConfigurationValidator,
        function_mode: str,
        function_mode_value: int,
        configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates the Processing Regions of a Scan Configuration of a single FSP Mode

        :param function_mode: A string that indicates which function mode is being validated
        :param function_mode_value: a int value of the FspModes Enumeration options
        :param configuration: A MidCBF Configuration as a Dictionary

        :return: A tuple of True/False to indicate that the configuration is valid, and a message
        :rtype: tuple[bool, str]

        """
        # To ensure we are not using duplicated FSP between Processing Regions
        # within a single subarray
        fsp_id_in_processing_region = set()
        for processing_region in configuration[function_mode][
            "processing_regions"
        ]:
            processing_region = copy.deepcopy(processing_region)

            # Validations that the fps_id inside the the fsp_ids are valid values
            # is done in _validate_fsp_id below
            fsp_ids_range = scan_configuration_supported_value("fsp_ids")
            if (
                len(processing_region["fsp_ids"]) > fsp_ids_range[1]
                or len(processing_region["fsp_ids"]) < fsp_ids_range[0]
            ):
                msg = (
                    f"AA 0.5 only support fsp_ids with array length of 1-4,"
                    f"size of the fsp_ids given: {len(processing_region['fsp_ids'])}"
                )
                self.logger.error(msg)
                return (False, msg)

            success, msg = self._validate_processing_region_channel_values(
                processing_region, FspModes(function_mode_value)
            )
            if success is False:
                return (False, msg)

            success, msg = self._validate_processing_region_frequency(
                processing_region
            )
            if success is False:
                return (False, msg)

            sdp_start_channel_id = int(
                processing_region["sdp_start_channel_id"]
            )
            channel_count = int(processing_region["channel_count"])

            output_host = processing_region["output_host"]
            success, msg = self._validate_channels_maps(
                output_host,
                "output_host",
                sdp_start_channel_id,
                channel_count,
                FspModes(function_mode_value),
            )
            if success is False:
                return (False, msg)

            output_port = processing_region["output_port"]
            success, msg = self._validate_channels_maps(
                output_port,
                "output_port",
                sdp_start_channel_id,
                channel_count,
                FspModes(function_mode_value),
            )
            if success is False:
                return (False, msg)

            output_link_map = processing_region["output_link_map"]
            success, msg = self._validate_channels_maps(
                output_link_map,
                "output_link_map",
                sdp_start_channel_id,
                channel_count,
                FspModes(function_mode_value),
            )
            if success is False:
                return (False, msg)

            (
                success,
                msg,
            ) = self._validate_max_20_channel_to_same_port_per_host(
                output_host, output_port, sdp_start_channel_id, channel_count
            )
            if success is False:
                return (False, msg)

            supported_function_mode_fsp_ids = (
                scan_configuration_supported_value("processing_region")
            )[FspModes(function_mode_value)]["fsp_id"]

            for fsp_id_str in processing_region["fsp_ids"]:
                fsp_id = int(fsp_id_str)
                success, msg = self._validate_fsp_id(
                    fsp_id,
                    FspModes(function_mode_value),
                    supported_function_mode_fsp_ids,
                    fsp_id_in_processing_region,
                )
                if success is False:
                    return (False, msg)

            # validate The Function Mode for each processing regions
            success, msg = self._validate_corr_function_mode(processing_region)
            if success is False:
                return (False, msg)

            # TODO Add PST (and eventually PSS) post 5.0 Scan Configuration here
            # Consider adding a function table that gives a different
            # _validate_<mode>_function_mode function depending on the
            # function_mode_value given

        msg = f"FSP Validation: Complete for {function_mode} function mode"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_midcbf(
        self: SubarrayScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates a MidCBF Configuration

        :param configuration: A MidCBF Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """

        success, msg = self._validate_midcbf_keys(configuration)
        if success is False:
            return (False, msg)

        at_least_one_mode_flag = False
        if "correlation" in configuration:
            # fsp = group of processing regions.  Variable was named fsp for compatibility with abstracted functions for 2.4 validations
            function_mode_value = FspModes[
                self.function_mode_value_enum_match["correlation"]
            ]
            success, msg = self._validate_processing_regions(
                "correlation", function_mode_value, configuration
            )
            if success is False:
                return (False, msg)
            at_least_one_mode_flag = True

        if at_least_one_mode_flag is False:
            msg = "No Function Mode Specified in the MidCBF portion of the Scan Configuration"
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate MidCBF: Validation Complete"
        self.logger.debug(msg)
        return (True, msg)

    def _validate_scan_configuration(
        self: SubarrayScanConfigurationValidator,
        full_configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates a Scan Configuration

        :param full_configuration: The Full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["midcbf"])

        # TODO: As of 4.0 Scan Configuration, PSS and PST is at the top level
        # TODO: PST will be moved to a Processing Region in 5.0
        if "pss" in full_configuration:
            success, msg = self._validate_pss_function_mode(
                full_configuration["pss"]
            )
            if success is False:
                return (False, msg)

        if "pst" in full_configuration:
            success, msg = self._validate_pst_function_mode(
                full_configuration["pst"]
            )
            if success is False:
                return (False, msg)

        success, msg = self._validate_common(common_configuration)
        if success is False:
            return (False, msg)

        success, msg = self._validate_midcbf(configuration)
        if success is False:
            return (False, msg)

        return (True, "Scan configuration is valid.")

    def validate_input(
        self: SubarrayScanConfigurationValidator,
    ) -> bool:
        """
        Validates if the Scan Configuration in self.scan_configuration is valid

        :return: bool to indicate if the configuration is valid or not
        :rtype: bool

        """
        try:
            full_configuration = json.loads(self._scan_configuration)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan Configuration object is not a valid JSON object. Aborting configuration."
            self.logger.error(msg)
            return (False, msg)

        success, msg = self._validate_scan_configuration(full_configuration)

        return success, msg
