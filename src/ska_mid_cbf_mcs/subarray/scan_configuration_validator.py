from __future__ import annotations  # allow forward references in type hints

import copy
import json
import logging
import math
import sys
from collections import defaultdict

# Tango imports
import tango
from ska_tango_base.control_model import ObsState

import ska_mid_cbf_mcs.subarray.subarray_component_manager as scm
from ska_mid_cbf_mcs.attribute_proxy import CbfAttributeProxy
from ska_mid_cbf_mcs.commons.global_enum import (
    FspModes,
    ScanConfiguration,
    const,
    freq_band_dict,
)

# SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

"""
ScanConfigurationValidator: Contains functions that validates a given Scan Configuration
"""


class ScanConfigurationValidator:
    # To get a list of Fuction Mode names from the FspModes Enum in gloval_enum.py
    valid_function_modes = [function_modes.name for function_modes in FspModes]

    # Valid FSP IDs for specific FSP Modes
    supported_fsp_ids = {
        FspModes.CORR: {1, 2, 3, 4},
        FspModes.PST_BF: {5, 6, 7, 8},
    }

    adr_99_function_mode_match = {
        "idle": "IDLE",
        "correlation": "CORR",
        "pss": "PSS-BF",
        "pst": "PST-BF",
        "vlbi": "VLBI",
    }

    def __init__(
        self: ScanConfigurationValidator,
        scan_configuration: str,
        subarray_component_manager: scm.CbfSubarrayComponentManager,
        logger: logging.Logger,
    ) -> None:
        """
        Constructor for ScanConfigurationValidator

        :param scan_configuration: A Scan Configuration json string
        :param subarray_component_manager: a CbfSubarrayComponentManager object that is requesting the validation
        :param logger: A Logger object to handle logging message for the class
        """

        self._scan_configuration = scan_configuration
        self._count_fsp = subarray_component_manager._count_fsp
        self._proxies_fsp = subarray_component_manager._proxies_fsp
        self._proxies_assigned_vcc = (
            subarray_component_manager._proxies_assigned_vcc
        )
        self._proxies_fsp_pss_subarray_device = (
            subarray_component_manager._proxies_fsp_pss_subarray_device
        )
        self._dish_ids = subarray_component_manager._dish_ids
        self._subarray_id = subarray_component_manager._subarray_id
        self.logger = logger

    def validate_input(self: ScanConfigurationValidator) -> tuple[bool, str]:
        """
        Validates if the Scan Configuration in self.scan_configuration is valid

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        self.seen_fsp_id = set()
        try:
            full_configuration = json.loads(self._scan_configuration)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self.logger.info(msg)
            return (False, msg)

        scan_configuration_version = (
            (full_configuration["interface"]).split("/")
        )[-1]

        # Post ADR99 Scan Configuration Changes
        if scan_configuration_version in ScanConfiguration.ADR99_VERSIONS:
            result_code, msg = self._validate_input_adr_99(full_configuration)

        # Pre ADR99 Scan Configuration Changes
        elif (
            scan_configuration_version in ScanConfiguration.PRE_ADR99_VERSIONS
        ):
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
            result_code, msg = self._validate_input_pre_adr_99(
                configuration, common_configuration
            )

        # Invalid Version Case
        else:
            msg = f"Error: The version defined in the Scan Configuration is not supported by MCS: version {scan_configuration_version}"
            result_code = False

        return (result_code, msg)

    def _validate_input_pre_adr_99(
        self: ScanConfigurationValidator,
        configuration: dict,
        common_configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates a pre ADR 99/pre v4.0 Scan Configuration

        :param configuration: The ["cbf"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """

        result_code, msg = self._validate_subscription_point(configuration)
        if result_code is False:
            return (False, msg)

        result_code, msg = self._validate_vcc()
        if result_code is False:
            return (False, msg)

        result_code, msg = self._validate_search_window(configuration)
        if result_code is False:
            return (False, msg)

        result_code, msg = self._validate_fsp_pre_adr_99(
            configuration, common_configuration
        )
        if result_code is False:
            return (False, msg)

        return (True, "Scan configuration is valid.")

    def _validate_fsp_pre_adr_99(
        self: ScanConfigurationValidator,
        configuration: dict,
        common_configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates the FSP Configuration for a pre ADR 99/pre v4.0 Scan Configuration

        :param configuration: The ["cbf"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Validate FSP
        count = 1
        for fsp in configuration["fsp"]:
            fsp = copy.deepcopy(fsp)
            try:
                fsp_id = int(fsp["fsp_id"])
                result_code, msg = self._validate_fsp_id(fsp_id)
                self.seen_fsp_id.add(fsp_id)
                if result_code is False:
                    return (False, msg)
                count += 1
            except KeyError:
                msg = f"Invalid Scan Configuration; FSP ID not found for the #{count} FSP"
                return (False, msg)
            fsp_proxy = self._proxies_fsp[fsp_id - 1]

            # Validate functionMode.
            try:
                function_mode_value = self.valid_function_modes.index(
                    fsp["function_mode"]
                )
            except ValueError:
                return (
                    False,
                    f"{fsp['function_mode']} is not a valid FSP function mode.",
                )

            self._validate_cbf_configuration(
                fsp, configuration, common_configuration
            )
            # Configure FSP
            try:
                # FYI, Will also modify the fsp dict
                result_code, msg = self._validate_fsp_in_correct_mode(
                    fsp, fsp_id, function_mode_value, fsp_proxy
                )
                if result_code is False:
                    return (False, msg)

                match function_mode_value:
                    case 1:
                        result_code, msg = self._validate_corr_function_mode(
                            fsp, common_configuration
                        )

                    case 2:
                        result_code, msg = self._validate_pss_function_mode(
                            fsp
                        )

                    case 3:
                        result_code, msg = self._validate_pst_function_mode(
                            fsp
                        )

                    case _:
                        return (
                            False,
                            f"{self.valid_function_modes[function_mode_value]} is not a valid function mode for MCS",
                        )

                if result_code is False:
                    return (False, msg)

            except tango.DevFailed:  # exception in ConfigureScan
                msg = (
                    "An exception occurred while configuring FSPs:"
                    f"\n{sys.exc_info()[1].args[0].desc}\n"
                    "Aborting configuration"
                )
                self.logger.error(msg)
                return (False, msg)

            msg = "Validate FSP: Validation Complete"
            self.logger.info(msg)
            return (True, msg)

    def _validate_fsp_id(
        self: ScanConfigurationValidator, fsp_id: int
    ) -> tuple[bool, str]:
        """
        Validates the FSP ID given matches the criteria setup for the Scan Configuration

        :param fsp_id: A int value representing the FSP that we want to validate from the ["cbf"]/["midcbf"] section of the Scan Configuration

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # TODO for AA 1.0: Add check so that CORR is on 1-4
        # TODO for AA 1.0: Add check so that PST is on 5-8
        # AA 0.5 Requirment: Supports only FSP 1-8
        if fsp_id > 4:
            msg = (
                "AA 0.5 Requirment: Supports only FSP 1-4."
                f" FSP ID given: {fsp_id}"
            )
            self.logger.error(msg)
            return (False, msg)

        if fsp_id in self.seen_fsp_id:
            msg = f"FSP ID {fsp_id} already assigned to another Processing Region"
            self.logger.error(msg)
            return (False, msg)

        if fsp_id in list(range(1, self._count_fsp + 1)):
            msg = f"fsp_id {fsp_id} is valid"
            self.logger.info(msg)
            return (True, msg)
        else:
            msg = (
                f"'fsp_id' must be an integer in the range [1, {self._count_fsp}]."
                " Aborting configuration."
            )
            self.logger.error(msg)
            return (False, msg)

    def _validate_fsp_in_correct_mode(
        self: ScanConfigurationValidator,
        fsp: dict,
        fsp_id: int,
        function_mode_value: int,
        fsp_proxy: CbfDeviceProxy,
    ):
        """
        Validates that the given FSP Proxy is in the correct mode

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary
        :param fsp_id:  The ID value assigned to the FSP we are validating
        :param function_mode_value: the int value of the FspMode enum that represent the function mode of the FSP
        :param fsp_proxy: Device Proxy of the FSP that is being validated

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """

        fsp_function_mode = fsp_proxy.functionMode
        if fsp_function_mode not in [
            FspModes.IDLE.value,
            function_mode_value,
        ]:
            msg = f"FSP {fsp_id} currently set to function mode {self.valid_function_modes.index(fsp_function_mode)}, \
                    cannot be used for {fsp['function_mode']} \
                    until it is returned to IDLE."
            return (False, msg)

        msg = "Validate FSP in Correct Mode: Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_cbf_configuration(
        self: ScanConfigurationValidator,
        fsp: dict,
        configuration: dict,
        common_configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates the ["cbf"] portion of the Scan Configuration (Pre-ADR 99/Pre-v4.0)

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary
        :param configuration: The ["midcbf"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
            bool to indicate if the scan configuration is valid or not
            str message about the configuration
        :rtype: tuple[bool, str]
        """

        # TODO - why add these keys to the fsp dict - not good practice!
        # TODO - create a new dict from a deep copy of the fsp dict.
        # TODO - Updated so that is assumes fsp has been deep copied higher in the stack
        fsp["frequency_band"] = common_configuration["frequency_band"]
        if "frequency_band_offset_stream1" in configuration:
            fsp["frequency_band_offset_stream1"] = configuration[
                "frequency_band_offset_stream1"
            ]
        if "frequency_band_offset_stream2" in configuration:
            fsp["frequency_band_offset_stream2"] = configuration[
                "frequency_band_offset_stream2"
            ]
        if fsp["frequency_band"] in ["5a", "5b"]:
            fsp["band_5_tuning"] = common_configuration["band_5_tuning"]
        if fsp["frequency_band"] in ["3", "4"]:
            msg = f"invalid frequency_band value of {fsp['frequency_band']}"
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate CBF Configuration: Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_corr_function_mode(
        self: ScanConfigurationValidator, fsp: dict, common_configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the configuration parameters given for CORR Function Mode.  This function is for backwards compatibility with Scan Configuration Pre-ADR 99/pre v4.0

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """

        result_code, msg = self._validate_receptors(fsp)
        if result_code is False:
            return (False, msg)

        frequencyBand = freq_band_dict()[fsp["frequency_band"]]["band_index"]
        # Validate frequencySliceID.
        # See for ex. Fig 8-2 in the Mid.CBF DDD
        if int(fsp["frequency_slice_id"]) in list(
            range(1, const.NUM_FREQUENCY_SLICES_BY_BAND[frequencyBand] + 1)
        ):
            pass
        else:
            msg = (
                "'frequencySliceID' must be an integer in the range "
                f"[1, {const.NUM_FREQUENCY_SLICES_BY_BAND[frequencyBand]}] "
                f"for a 'frequencyBand' of {fsp['frequency_band']}."
            )
            self.logger.error(msg)
            return (False, msg)

        # Validate zoom_factor.
        if int(fsp["zoom_factor"]) in list(range(7)):
            pass
        else:
            msg = "'zoom_factor' must be an integer in the range [0, 6]."
            # this is a fatal error
            self.logger.error(msg)
            return (False, msg)

        # Validate zoomWindowTuning.
        if int(fsp["zoom_factor"]) > 0:  # zoomWindowTuning is required
            if "zoom_window_tuning" in fsp:
                if fsp["frequency_band"] not in [
                    "5a",
                    "5b",
                ]:  # frequency band is not band 5
                    frequencyBand = [
                        "1",
                        "2",
                        "3",
                        "4",
                        "5a",
                        "5b",
                    ].index(fsp["frequency_band"])
                    frequency_band_start = [
                        *map(
                            lambda j: j[0] * 10**9,
                            [
                                const.FREQUENCY_BAND_1_RANGE,
                                const.FREQUENCY_BAND_2_RANGE,
                                const.FREQUENCY_BAND_3_RANGE,
                                const.FREQUENCY_BAND_4_RANGE,
                            ],
                        )
                    ][frequencyBand] + fsp["frequency_band_offset_stream1"]

                    frequency_slice_range = (
                        frequency_band_start
                        + (fsp["frequency_slice_id"] - 1)
                        * const.FREQUENCY_SLICE_BW
                        * 10**6,
                        frequency_band_start
                        + fsp["frequency_slice_id"]
                        * const.FREQUENCY_SLICE_BW
                        * 10**6,
                    )

                    if (
                        frequency_slice_range[0]
                        <= int(fsp["zoom_window_tuning"]) * 10**3
                        <= frequency_slice_range[1]
                    ):
                        pass
                    else:
                        msg = "'zoomWindowTuning' must be within observed frequency slice."
                        self.logger.error(msg)
                        return (False, msg)
                # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                else:
                    if common_configuration["band_5_tuning"] == [
                        0,
                        0,
                    ]:  # band5Tuning not specified
                        pass
                    else:
                        # TODO: these validations of BW range are done many times
                        # in many places - use a common function; also may be possible
                        # to do them only once (ex. for band5Tuning)

                        frequency_slice_range_1 = (
                            fsp["band_5_tuning"][0] * 10**9
                            + fsp["frequency_band_offset_stream1"]
                            - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                            + (fsp["frequency_slice_id"] - 1)
                            * const.FREQUENCY_SLICE_BW
                            * 10**6,
                            fsp["band_5_tuning"][0] * 10**9
                            + fsp["frequency_band_offset_stream1"]
                            - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                            + fsp["frequency_slice_id"]
                            * const.FREQUENCY_SLICE_BW
                            * 10**6,
                        )

                        frequency_slice_range_2 = (
                            fsp["band_5_tuning"][1] * 10**9
                            + fsp["frequency_band_offset_stream2"]
                            - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                            + (fsp["frequency_slice_id"] - 1)
                            * const.FREQUENCY_SLICE_BW
                            * 10**6,
                            fsp["band_5_tuning"][1] * 10**9
                            + fsp["frequency_band_offset_stream2"]
                            - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                            + fsp["frequency_slice_id"]
                            * const.FREQUENCY_SLICE_BW
                            * 10**6,
                        )

                        if (
                            frequency_slice_range_1[0]
                            <= int(fsp["zoom_window_tuning"]) * 10**3
                            <= frequency_slice_range_1[1]
                        ) or (
                            frequency_slice_range_2[0]
                            <= int(fsp["zoom_window_tuning"]) * 10**3
                            <= frequency_slice_range_2[1]
                        ):
                            pass
                        else:
                            msg = "'zoomWindowTuning' must be within observed frequency slice."
                            self.logger.error(msg)
                            return (False, msg)
            else:
                msg = "FSP specified, but 'zoomWindowTuning' not given."
                self.logger.error(msg)
                return (False, msg)

        result_code, msg = self._valdiate_integration_time(fsp)
        if result_code is False:
            return (False, msg)

        # Validate fspChannelOffset
        try:
            if "channel_offset" in fsp:
                if int(fsp["channel_offset"]) >= 0:
                    pass
                # TODO has to be a multiple of 14880
                else:
                    msg = "fspChannelOffset must be greater than or equal to zero"
                    self.logger.error(msg)
                    return (False, msg)
        except (TypeError, ValueError):
            msg = "fspChannelOffset must be an integer"
            self.logger.error(msg)
            return (False, msg)

        # validate outputlink
        # check the format
        result_code, msg = self._validate_output_link_map(
            fsp["output_link_map"]
        )
        if result_code is False:
            return (False, msg)

        # Validate channelAveragingMap.
        if "channel_averaging_map" in fsp:
            try:
                # validate dimensions
                for i in range(0, len(fsp["channel_averaging_map"])):
                    assert len(fsp["channel_averaging_map"][i]) == 2

                # validate averaging factor
                for i in range(0, len(fsp["channel_averaging_map"])):
                    # validate channel ID of first channel in group
                    if (
                        int(fsp["channel_averaging_map"][i][0])
                        == i
                        * const.NUM_FINE_CHANNELS
                        / const.NUM_CHANNEL_GROUPS
                    ):
                        pass  # the default value is already correct
                    else:
                        msg = (
                            f"'channelAveragingMap'[{i}][0] is not the channel ID of the "
                            f"first channel in a group (received {fsp['channel_averaging_map'][i][0]})."
                        )
                        self.logger.error(msg)
                        return (False, msg)

                    # validate averaging factor
                    if int(fsp["channel_averaging_map"][i][1]) in [
                        0,
                        1,
                        2,
                        3,
                        4,
                        6,
                        8,
                    ]:
                        pass
                    else:
                        msg = (
                            f"'channelAveragingMap'[{i}][1] must be one of "
                            f"[0, 1, 2, 3, 4, 6, 8] (received {fsp['channel_averaging_map'][i][1]})."
                        )
                        self.logger.error(msg)
                        return (False, msg)
            except (
                TypeError,
                AssertionError,
            ):  # dimensions not correct
                msg = "channel Averaging Map dimensions not correct"
                self.logger.error(msg)
                return (False, msg)

        msg = "FSP CORR Validation Complete"
        self.logger.info(msg)
        return (True, msg)

        # TODO: validate destination addresses: outputHost, outputPort

    def _validate_pss_function_mode(
        self: ScanConfigurationValidator, fsp: dict
    ) -> tuple[bool, str]:
        """
        Validates the configuration parameters given for PST Function Mode.  To be used (at this time) to validate Scan Configuration Pre-ADR 99/pre v4.0
        Note common_configuration is not used, but requried in function definition to be consistent with the other function when passed as a function pointer


        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        if int(fsp["search_window_id"]) in [1, 2]:
            pass
        else:  # searchWindowID not in valid range
            msg = (
                "'searchWindowID' must be one of [1, 2] "
                f"(received {fsp['search_window_id']})."
            )
            self.logger.info(msg)
            return (False, msg)
        if len(fsp["search_beam"]) <= 192:
            for searchBeam in fsp["search_beam"]:
                if 1 > int(searchBeam["search_beam_id"]) > 1500:
                    # searchbeamID not in valid range
                    msg = (
                        "'searchBeamID' must be within range 1-1500 "
                        f"(received {searchBeam['search_beam_id']})."
                    )
                    self.logger.info(msg)
                    return (False, msg)

                for (
                    fsp_pss_subarray_proxy
                ) in self._proxies_fsp_pss_subarray_device:
                    searchBeamID = fsp_pss_subarray_proxy.searchBeamID
                    fsp_id = fsp_pss_subarray_proxy.get_property("FspID")[
                        "FspID"
                    ][0]
                    if searchBeamID is None:
                        pass
                    else:
                        for search_beam_ID in searchBeamID:
                            if (
                                int(searchBeam["search_beam_id"])
                                != search_beam_ID
                            ):
                                pass
                            elif (
                                fsp_pss_subarray_proxy.obsState
                                == ObsState.IDLE
                            ):
                                pass
                            else:
                                msg = (
                                    f"'searchBeamID' {search_beam_ID} is already "
                                    f"being used in another subarray by FSP {fsp_id}"
                                )
                                self.logger.info(msg)
                                return (False, msg)

                # Validate dishes
                # if not given, assign first DISH ID in subarray, as
                # there is currently only support for 1 DISH per beam
                if "receptor_ids" not in searchBeam:
                    searchBeam["receptor_ids"] = [self._dish_ids.copy()[0]]

                # Sanity check:
                for dish in searchBeam["receptor_ids"]:
                    if dish not in self._dish_ids:
                        msg = (
                            f"Receptor {dish} does not belong to "
                            f"subarray {self._subarray_id}."
                        )
                        self.logger.error(msg)
                        return (False, msg)

                if (
                    searchBeam["enable_output"] is False
                    or searchBeam["enable_output"] is True
                ):
                    pass
                else:
                    msg = "'outputEnabled' is not a valid boolean"
                    self.logger.info(msg)
                    return (False, msg)

                if isinstance(searchBeam["averaging_interval"], int):
                    pass
                else:
                    msg = "'averagingInterval' is not a valid integer"
                    self.logger.info(msg)
                    return (False, msg)

                if self._validate_ip(
                    searchBeam["search_beam_destination_address"]
                ):
                    pass
                else:
                    msg = "'searchBeamDestinationAddress' is not a valid IP address"
                    self.logger.info(msg)
                    return (False, msg)

        else:
            msg = "More than 192 SearchBeams defined in PSS-BF config"
            self.logger.info(msg)
            return (False, msg)

        msg = "FSP PSS Validation Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_pst_function_mode(
        self: ScanConfigurationValidator, fsp: dict
    ) -> tuple[bool, str]:
        """
        Validates the configuration parameters given for PST Function Mode.  To be used (at this time) to validate Scan Configuration Pre-ADR 99/pre v4.0
        Note common_configuration is not used, but requried in function definition to be consistent with the other function when passed as a function pointer

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        if len(fsp["timing_beam"]) <= 16:
            for timingBeam in fsp["timing_beam"]:
                if 1 > int(timingBeam["timing_beam_id"]) > 16:
                    # timingBeamID not in valid range
                    msg = (
                        "'timingBeamID' must be within range 1-16 "
                        f"(received {timingBeam['timing_beam_id']})."
                    )
                    return (False, msg)
                for (
                    fsp_pst_subarray_proxy
                ) in self._proxies_fsp_pst_subarray_device:
                    timingBeamID = fsp_pst_subarray_proxy.timingBeamID
                    fsp_id = fsp_pst_subarray_proxy.get_property("FspID")[
                        "FspID"
                    ][0]
                    if timingBeamID is None:
                        pass
                    else:
                        for timing_beam_ID in timingBeamID:
                            if (
                                int(timingBeam["timing_beam_id"])
                                != timing_beam_ID
                            ):
                                pass
                            elif (
                                fsp_pst_subarray_proxy.obsState
                                == ObsState.IDLE
                            ):
                                pass
                            else:
                                msg = (
                                    f"'timingBeamID' {timing_beam_ID} is already "
                                    f"being used in another subarray by FSP {fsp_id}"
                                )
                                return (False, msg)

                # Validate dishes
                # if not given, assign all DISH IDs belonging to subarray
                if "receptor_ids" not in timingBeam:
                    timingBeam["receptor_ids"] = self._dish_ids.copy()

                for dish in timingBeam["receptor_ids"]:
                    if dish not in self._dish_ids:
                        msg = (
                            f"Receptor {dish} does not belong to "
                            f"subarray {self._subarray_id}."
                        )
                        self.logger.error(msg)
                        return (False, msg)
                if (
                    timingBeam["enable_output"] is False
                    or timingBeam["enable_output"] is True
                ):
                    pass
                else:
                    msg = "'outputEnabled' is not a valid boolean"
                    return (False, msg)

                if self._validate_ip(
                    timingBeam["timing_beam_destination_address"]
                ):
                    pass
                else:
                    msg = "'timingBeamDestinationAddress' is not a valid IP address"
                    return (False, msg)

        msg = "FSP PST Validation Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_subscription_point(
        self: ScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Checks if subscription points are requested in the Scan Configuration and validates that the requested subscription points's device server are reachable

        :param configuration: The ["cbf"]/["midcbf"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        subscription_points = [
            "doppler_phase_corr_subscription_point",
            "delay_model_subscription_point",
            "jones_matrix_subscription_point",
            "timing_beam_weights_subscription_point",
        ]

        subscribed = []
        for subscription_point in subscription_points:
            if subscription_point in configuration:
                try:
                    attribute_proxy = CbfAttributeProxy(
                        fqdn=configuration[subscription_point],
                        logger=self.logger,
                    )
                    attribute_proxy.ping()
                except (
                    tango.DevFailed
                ):  # attribute doesn't exist or is not set up correctly
                    msg = (
                        f"Attribute {configuration[subscription_point]}"
                        " not found or not set up correctly for "
                        "'{subscription_point}'. Aborting configuration."
                    )
                    self.logger.error(msg)
                    return (False, msg)
                subscribed.append((subscription_point))

        msg = f"Finish Validating Subscription Points for: {subscribed}"
        self.logger.info(msg)
        return (True, msg)

    def _validate_vcc(self: ScanConfigurationValidator) -> tuple[bool, str]:
        """
        Validats that the assigned VCC proxies found in the Subarray Devices are on

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        for dish_id, proxy in self._proxies_assigned_vcc.items():
            if proxy.State() != tango.DevState.ON:
                msg = f"VCC {self._proxies_vcc.index(proxy) + 1} is not ON. Aborting configuration."
                return (False, msg)
        msg = "Validate VCC: Compelte"
        self.logger.info(msg)
        return (True, msg)

    def _validate_search_window(
        self: ScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the Search Window specified in the The ["cbf"]/["midcbf"] portion of the full Scan Configuration

        :param configuration: The ["cbf"]/["midcbf"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Validate searchWindow.
        if "search_window" in configuration:
            # check if searchWindow is an array of maximum length 2
            if len(configuration["search_window"]) > 2:
                msg = (
                    "'searchWindow' must be an array of maximum length 2. "
                    "Aborting configuration."
                )
                self.logger.error(msg)
                return (False, msg)
            for sw in configuration["search_window"]:
                if sw["tdc_enable"]:
                    for receptor in sw["tdc_destination_address"]:
                        dish = receptor["receptor_id"]
                        if dish not in self._dish_ids:
                            msg = (
                                f"'searchWindow' DISH ID {dish} "
                                + "not assigned to subarray. Aborting configuration."
                            )
                            self.logger.error(msg)
                            return (False, msg)
            msg = "Validate Search Window: Complete"
            self.logger.info(msg)
            return (True, msg)
        else:
            msg = "Validate Search Window: Search Window not in Configuration: Complete"
            self.logger.info(msg)
            return (True, msg)

    def _validate_receptors(
        self: ScanConfigurationValidator, fsp: dict
    ) -> tuple[bool, str]:
        """
        Validates that the "receptors" value found in fsp/processing_region is within specification

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # dishes may not be specified in the
        # configuration at all, or the list may be empty
        if "receptors" in fsp and len(fsp["receptors"]) > 0:
            self.logger.debug(f"List of receptors: {self._dish_ids}")
            for dish in fsp["receptors"]:
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
            self.logger.info(msg)

        msg = "Validate Receptor: Complete"
        self.logger.info(msg)
        return (True, msg)

    def _valdiate_integration_time(
        self: ScanConfigurationValidator, fsp: dict
    ) -> tuple[bool, str]:
        """
        Validates that the integration_factor value found in fsp/processing_region is within specification

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Validate integrationTime.
        if int(fsp["integration_factor"]) in list(
            range(
                const.MIN_INT_TIME,
                10 * const.MIN_INT_TIME + 1,
                const.MIN_INT_TIME,
            )
        ):
            msg = "Balidate Integration Time: Complete"
            self.logger.info(msg)
            return (True, msg)
        else:
            msg = (
                "'integrationTime' must be an integer in the range"
                f" [1, 10] multiplied by {const.MIN_INT_TIME}."
            )
            self.logger.error(msg)
            return (False, msg)

    def _validate_output_link_map(
        self: ScanConfigurationValidator, output_link_map: dict
    ) -> tuple[bool, str]:
        """
        Validates that the channel/values Output Link Map pair contains int, int

        :param output_link_map: A Channel/Value pair of ints

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
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
        self.logger.info(msg)
        return (True, msg)

    def _validate_ip(self: scm.CbfSubarrayComponentManager, ip: str) -> bool:
        """
        Validate IP address format.

        :param ip: IP address to be evaluated

        :return: whether or not the IP address format is valid
        :rtype: bool
        """
        splitip = ip.split(".")
        if len(splitip) != 4:
            return False
        for ipparts in splitip:
            if not ipparts.isdigit():
                return False
            ipval = int(ipparts)
            if ipval < 0 or ipval > 255:
                return False
        return True

    # Below: new validation required by / specific to Post ADR 99

    def _validate_input_adr_99(
        self: ScanConfigurationValidator,
        full_configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates a post ADR 99/v4.0 or greater Scan Configuration

        :param full_configuration: The Scan Configuration as a JSOn Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["midcbf"])

        result_code, msg = self._validate_vcc()
        if result_code is False:
            return (False, msg)

        if "pss" in full_configuration:
            result_code, msg = self._validate_pss_function_mode_adr_99(
                full_configuration["pss"]
            )
            if result_code is False:
                return (False, msg)

        if "pst" in full_configuration:
            result_code, msg = self._validate_pst_function_mode_adr_99(
                full_configuration["pst"]
            )
            if result_code is False:
                return (False, msg)

        result_code, msg = self._validate_common(common_configuration)
        if result_code is False:
            return (False, msg)

        result_code, msg = self._validate_midcbf(configuration)
        if result_code is False:
            return (False, msg)

        return (True, "Scan configuration is valid.")

    def _validate_midcbf(
        self: ScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the ["midcbf"] portion of the Scan Configuration (Post-ADR 99/Post-v4.0)

        :param configuration: The ["midcbf"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """

        result_code, msg = self._validate_midcbf_keys(configuration)
        if result_code is False:
            return (False, msg)

        at_least_one_mode_flag = False
        if "correlation" in configuration:
            # fsp = group of processing regions.  Variable was named fsp for compatibility with abstracted functions for 2.4 validations
            function_mode_value = FspModes[
                self.adr_99_function_mode_match["correlation"]
            ]
            result_code, msg = self._validate_processing_regions(
                "correlation", function_mode_value, configuration
            )
            if result_code is False:
                return (False, msg)
            at_least_one_mode_flag = True

        if at_least_one_mode_flag is False:
            msg = "No Function Mode Specified in the MidCBF portion of the Scan Configuration"
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate MidCBF: Validation Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_processing_regions(
        self: ScanConfigurationValidator,
        function_mode: str,
        function_mode_value: int,
        configuration: dict,
    ) -> tuple[bool, str]:
        """
        Validates the Processing Regions of a Scan Configuration of a single FSP Modde

        :param function_mode: A string that indicates which function mode is being validated
        :param fucntion_mode_value: a int value of the FspModes Enumeration options
        :param configuration: The ["midcbf"] portion of the full Scan Configuration as a Dictionary

        :return: A tuple of True/False to indicate that the configuration is valid, and a message
        :rtype: tuple[bool, str]

        """
        # To ensure we are not using duplicated FSP between Processing Regions Within a Single Subarray
        seen_fsp_id = set()
        for processing_region in configuration[function_mode][
            "processing_regions"
        ]:
            processing_region = copy.deepcopy(processing_region)

            if (
                len(processing_region["fsp_ids"]) > 4
                or len(processing_region["fsp_ids"]) < 1
            ):
                msg = f"AA 0.5 only support 1-4 fsp_id with a single fsp_ids in a processing region, fsp_id given: {len(processing_region['fsp_ids'])}"
                self.logger.error(msg)
                return (False, msg)

            result_code, msg = self._validate_processing_region_frequency(
                processing_region
            )
            if result_code is False:
                return (False, msg)

            sdp_start_channel_id = int(
                processing_region["sdp_start_channel_id"]
            )
            channel_count = int(processing_region["channel_count"])

            output_host = processing_region["output_host"]
            result_code, msg = self._validate_channels_maps(
                output_host, "output_host", sdp_start_channel_id, channel_count
            )
            if result_code is False:
                return (False, msg)

            output_port = processing_region["output_port"]
            result_code, msg = self._validate_channels_maps(
                output_port, "output_port", sdp_start_channel_id, channel_count
            )
            if result_code is False:
                return (False, msg)

            output_link_map = processing_region["output_link_map"]
            result_code, msg = self._validate_channels_maps(
                output_link_map,
                "output_link_map",
                sdp_start_channel_id,
                channel_count,
            )
            if result_code is False:
                return (False, msg)

            (
                result_code,
                msg,
            ) = self._validate_max_20_channel_to_same_port_per_host(
                output_host, output_port, sdp_start_channel_id, channel_count
            )
            if result_code is False:
                return (False, msg)

            count = 0
            for fsp_id_str in processing_region["fsp_ids"]:
                try:
                    fsp_id = int(fsp_id_str)
                    result_code, msg = self._validate_fsp_id_adr_99(
                        fsp_id, FspModes(function_mode_value), seen_fsp_id
                    )
                    if result_code is False:
                        return (False, msg)
                    count += 1
                except KeyError:
                    msg = f"Invalid Scan Configuration; FSP ID not found for the #{count} FSP"
                    return (False, msg)

                fsp_proxy = self._proxies_fsp[fsp_id - 1]

                # Configure processing_regions
                try:
                    # FYI, Will also modify the fsp dict
                    # TODO: Run Full Test to see if removing below will affect System Tests
                    # processing_regions["frequency_band"] = common_configuration["frequency_band"]
                    result_code, msg = self._validate_fsp_in_correct_mode(
                        processing_region,
                        fsp_id,
                        function_mode_value,
                        fsp_proxy,
                    )
                    if result_code is False:
                        return (False, msg)

                except tango.DevFailed:  # exception in ConfigureScan
                    msg = (
                        "An exception occurred while configuring FSPs:"
                        f"\n{sys.exc_info()[1].args[0].desc}\n"
                        "Aborting configuration"
                    )
                    self.logger.error(msg)
                    return (False, msg)

            # validate The Function Mode for each processing regions
            result_code, msg = self._validate_corr_function_mode_adr_99(
                processing_region
            )
            if result_code is False:
                return (False, msg)

        msg = f"FSP Validation: Complete for {function_mode} function mode"
        self.logger.info(msg)
        return (True, msg)

    def _validate_corr_function_mode_adr_99(
        self: ScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the Correlation Processing Region is within ADR 99's Scan Configuration specification
        Note common_configuration is not used, but requried in function definition to be consistent with the other function when passed as a function pointer

        :param processing_region: A section of the Scan Configuration (Dictionary) that contains a group of FSP and their configurations
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        result_code, msg = self._validate_receptors(processing_region)
        if result_code is False:
            return (False, msg)

        result_code, msg = self._valdiate_integration_time(processing_region)
        if result_code is False:
            return (False, msg)

        result_code, msg = self._validate_output_link_map(
            processing_region["output_link_map"]
        )
        if result_code is False:
            return (False, msg)

        msg = "FSP CORR Validation Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_pst_function_mode_adr_99(
        self: ScanConfigurationValidator, pst_configuration: dict
    ) -> tuple[bool, str]:
        msg = "MCS Current Does not Support PST Configurations, Skipping"
        self.logger.warning(msg)
        return (True, msg)

    def _validate_pss_function_mode_adr_99(
        self: ScanConfigurationValidator, pss_configuration: dict
    ) -> tuple[bool, str]:
        msg = "MCS Current Does not Support PSS Configurations, Skipping"
        self.logger.warning(msg)
        return (True, msg)

    def _validate_processing_region_frequency(
        self: ScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the values found in a Processing Region is within the range specified in ADR 99 and that there are enough FSP to cover the range

        :param processing_region: A processing region in ["processing_region"] portion of the full Scan Configuration as a Dictionary


        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        channel_width = int(processing_region["channel_width"])
        channel_count = int(processing_region["channel_count"])
        sdp_start_channel_id = int(processing_region["sdp_start_channel_id"])

        # valid_channel_width = {
        #     210,420,840,1680,3360,6720,13440,26880,40320,53760,80640,
        #     107520,161280,215040,322560,416640,430080,645120,}

        # For AA 0.5, only width of 13440 is acepted
        valid_channel_width = {13440}

        # Edit the Error message once more valid channel width are added
        if channel_width not in valid_channel_width:
            msg = f"Invalid value for channel_width:{channel_width}.  AA 0.5 supports only 13440Hz"
            self.logger.error(msg)
            return (False, msg)

        if channel_count % 20 != 0:
            msg = f"Invalid value for channel_count, not a multiple of 20: {channel_count}"
            self.logger.error(msg)
            return (False, msg)

        if channel_count < 1 or channel_count > 58982:
            msg = f"Invalid value for channel_count, outside of range [1,58982]:{channel_count}"
            self.logger.error(msg)
            return (False, msg)

        if sdp_start_channel_id < 0:
            msg = f"Invalid value for sdp_start_channel_id, must be a positive integer: {sdp_start_channel_id}"
            self.logger.error(msg)
            return (False, msg)

        # Check that the Bandwidth specified is within the alloweable range
        result_code, msg = self._validate_processing_region_within_bandwidth(
            processing_region
        )
        if result_code is False:
            return (False, msg)

        # Check that we have enough FSP to cover the required Bandwidth requested
        result_code, msg = self._validate_fsp_requirement_by_given_bandwidth(
            processing_region
        )
        if result_code is False:
            return (False, msg)

        msg = "Validate Processing Region Frequency Options Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_fsp_requirement_by_given_bandwidth(
        self: ScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the Processing Region contains enough FSP to process the Bandwidth that was specified from start_freq, channel_width, and channel_count

        :param processing_region: A section of the Scan Configuration (Dictionary) that contains a group of FSP and their configurations

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # check if we have enough FSP for the given Frequency Band
        fsp_given = processing_region["fsp_ids"]
        start_freq = processing_region["start_freq"]
        channel_width = processing_region["channel_width"]
        channel_count = processing_region["channel_count"]

        end_freq = start_freq + ((channel_count - 1) * channel_width)
        coarse_channel_low = math.floor(
            (start_freq + const.FS_BW // 2) / const.FS_BW
        )
        coarse_channel_high = math.floor(
            (end_freq + const.FS_BW // 2) / const.FS_BW
        )
        coarse_channels = list(
            range(coarse_channel_low, coarse_channel_high + 1)
        )

        if len(fsp_given) < len(coarse_channels):
            msg = (
                "Not enought FSP Given in the Processing Region for the Frequency Band Specified in the Common"
                f"\nFSP Required: {len(coarse_channels)} FSP Given: {len(fsp_given)}"
            )
            self.logger.error(msg)
            return (False, msg)

        msg = (
            "Validate FSP requirement by Freqency Band: Complete:"
            f"FSP Required: {coarse_channels} FSP Given: {fsp_given}"
        )
        self.logger.info(msg)
        return (True, msg)

    def _validate_processing_region_within_bandwidth(
        self: ScanConfigurationValidator, processing_region: dict
    ) -> tuple[bool, str]:
        """
        Validates that the Processing Region's frequency range falls within 0 Hz to 1,981,808,640 Hz
        Gives a warning if the range given as calucalted from the start_freq, channel_width and channel_count is outside the range for Bands 1 & 2 (350MHz to 1760MHz)

        :param processing_region: A section of the Scan Configuration (Dictionary) that contains a group of FSP and their configurations
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Entire processing region must fit within the specified band - reject if not completely within band

        start_freq = processing_region["start_freq"]
        channel_width = processing_region["channel_width"]
        channel_count = processing_region["channel_count"]

        # TODO double check that correct math is done here
        # The actual start of the band is at start_freq - (channel_width/2) because start_freq the the center of the first fine channel
        lower_freq = start_freq - (channel_width / 2)
        # the upper freq is at lower_freq + (channel_width * channel_count)
        upper_freq = lower_freq + (channel_width * channel_count)

        # First Check: check that it is within the acceptable range that MCS will take in [0-1981808640]
        lower, upper = 0, 1981808640
        if (lower_freq < lower) or (upper_freq > upper):
            msg = (
                "The Processing Region is not within the range for the [0-1981808640] that is acepted by MCS",
                f"\nProcessing Region range: {lower_freq} - {upper_freq} with starting center at {start_freq}",
            )
            self.logger.error(msg)
            return (False, msg)

        # Second Check: Gives a warning if the given range is outside of [Band1.lower-Band2.upper]'s range
        lower, upper = (
            const.FREQUENCY_BAND_1_RANGE_HZ[0],
            const.FREQUENCY_BAND_2_RANGE_HZ[1],
        )
        if (lower_freq < lower) or (upper_freq > upper):
            msg = (
                f"The Processing Region is not within the range for [Band1.lower-Band2.upper]: [{lower}-{upper}]",
                f"\nProcessing Region range: {lower_freq} - {upper_freq} with starting center at {start_freq}",
            )
            self.logger.warning(msg)

        msg = "Validate Processing Region Within Band: Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_channels_maps(
        self: ScanConfigurationValidator,
        map_pairs: list[list[int, int]],
        map_type: str,
        sdp_start_channel_id: int,
        channel_count: int,
    ):
        """
        Validates that the Channel Map pairs for Output Host, Output Port or Output Link Map
        Depends on which Channel Map Pairs is passed with map_pairs

        :param map_pairs:  A list of list of int, int tuple that contains the channel and a value (port, host, etc.)
        :param map_type: The name of the type of map  that was passed in wiht map_pairs

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # for output_host, output_port, output_link_map
        # make sure only 20 channels are sent to a specific port
        # AA 0.5 + AA 1.0: channel idea must be in increments of 20

        # channel_count = len(map_pairs*20) for ADR
        map_channel_count = len(map_pairs * 20)
        if map_channel_count > channel_count:
            msg = (
                f"{map_type} exceeds the max allowable channel "
                f"as there are more channels specified in {map_type}({map_channel_count}) then given in channel_count({channel_count})."
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

        prev = map_pairs[0][0] - 20

        # check that channels are in increment of 20
        for channel, value in map_pairs:
            if channel - prev != 20:
                msg = (
                    f"{map_type} channel map pair [{channel},{value}]:",
                    f"channel must be in increments of 20 (Previous Channel: {prev})",
                    "For AA 0.5 and AA 1.0",
                )
                self.logger.error(msg)
                return (False, msg)
            prev = channel

        msg = f"Validate Channel Maps for {map_type} : Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_max_20_channel_to_same_port_per_host(
        self: ScanConfigurationValidator,
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
                    bool to indicate if the scan configuration is valid or not
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
        self.logger.info(msg)
        return (True, msg)

    def _validate_fsp_id_adr_99(
        self: ScanConfigurationValidator,
        fsp_id: int,
        fsp_mode: FspModes,
        seen_fsp_id: set[int],
    ) -> tuple[bool, str]:
        """
        Validates the FSP ID given matches the criteria setup for the Scan Configuration.  Used for Post ADR 99/ AA 1.0 to restrict which FSP for CORR and PST

        :param fsp_id: A int value representing the FSP that we want to validate from the ["midcbf"] section of the Scan Configuration
        :param fsp_mode: A FspModes Enum that indicates thee FSP Mode for the given fsp_id
        :param seen_fsp_id: a Hashset of intergers that keeps track of FSP IDs already seen in the subarray

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # TODO for AA 1.0: Add check so that CORR is on 1-4
        # TODO for AA 1.0: Add check so that PST is on 5-8
        # AA 0.5 Requirment: Supports only FSP 1-8

        if fsp_id not in self.supported_fsp_ids[fsp_mode]:
            msg = f"AA 0.5 Requirment: {fsp_mode.name} Supports only FSP {self.supported_fsp_ids[fsp_mode]}."
            self.logger.error(msg)
            return (False, msg)

        if fsp_id in seen_fsp_id:
            msg = f"FSP ID {fsp_id} already assigned to another Processing Region"
            self.logger.error(msg)
            return (False, msg)

        if fsp_id in list(range(1, self._count_fsp + 1)):
            seen_fsp_id.add(fsp_id)
            msg = f"fsp_id {fsp_id} is valid"
            self.logger.info(msg)
            return (True, msg)
        else:
            msg = (
                f"'fsp_id' must be an integer in the range [1, {self._count_fsp}]."
                " Aborting configuration."
            )
            self.logger.error(msg)
            return (False, msg)

    def _validate_common(
        self: ScanConfigurationValidator, common_configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the value in the ["common"] portion of the full Scan Configuration of a Post ADR 99 Scan Configuration

        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        frequency_band = common_configuration["frequency_band"]
        subarray_id = common_configuration["subarray_id"]

        supported_frequency_band = {"1", "2"}
        # Currently MCS Supported Value for frequency_band: [1,2]
        if frequency_band not in supported_frequency_band:
            msg = f"frequency_band {frequency_band} not supported. MCS currently only supports {supported_frequency_band}, Rejecting Scan Coniguration"
            self.logger.error(msg)
            return (False, msg)

        # Current MCS Supported Values for subarray_id : [1]
        if int(subarray_id) != 1:
            msg = f"subarray_id {subarray_id} not supported. MCS currently only supports [{1}]"
            self.logger.error(msg)
            return (False, msg)

        if "band_5_tunning" in common_configuration:
            msg = "band_5_tunning is currently not supportd in MCS, Rejecting Scan Coniguration"
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate Common: Completed"
        self.logger.info(msg)
        return (True, msg)

    def _validate_midcbf_keys(
        self: ScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the keys for the ["midcbf"] portion of the Scan Configuration (Post-ADR 99/Post-v4.0)

        :param fsp: The ["fsp"] or a processing_region in the ["processing_regions"] portion of the full Scan Configuration as a Dictionary
        :param configuration: The ["midcbf"] portion of the full Scan Configuration as a Dictionary
        :param common_configuration: The ["common"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
            bool to indicate if the scan configuration is valid or not
            str message about the configuration
        :rtype: tuple[bool, str]
        """

        # Create helper functions for below when MCS being support it

        result_code, msg = self._validate_subscription_point(configuration)
        if result_code is False:
            return (False, msg)

        result_code, msg = self._validate_search_window_adr99(configuration)
        if result_code is False:
            return (False, msg)

        # Not Supported Currently in AA 0.5/AA 1.0
        if "frequency_band_offset_stream1" in configuration:
            msg = "frequency_band_offset_stream1 Currently Not Supported In AA 0.5/AA 1.0"
            self.logger.error(msg)
            return (False, msg)
            # Not Supported Currently in AA 0.5/AA 1.0
            # fsp["frequency_band_offset_stream1"] = configuration[
            #     "frequency_band_offset_stream1"
            # ]

        # Not Supported Currently in AA 0.5/AA 1.0
        if "frequency_band_offset_stream2" in configuration:
            msg = "frequency_band_offset_stream2 Currently Not Supported In AA 0.5/AA 1.0"
            self.logger.error(msg)
            return (False, msg)
            # Not Supported Currently in AA 0.5/AA 1.0
            # fsp["frequency_band_offset_stream2"] = configuration[
            #     "frequency_band_offset_stream2"
            # ]

        # Not Supported Currently in AA 0.5/AA 1.0
        if "rfi_flagging_mask" in configuration:
            msg = "rfi_flagging_mask Currently Not Supported In AA 0.5/AA 1.0"
            self.logger.error(msg)
            return (False, msg)

        # Not Supported Currently in AA 0.5/AA 1.0
        if "vlbi" in configuration:
            msg = "vlbi Currently Not Supported In AA 0.5/AA 1.0"
            self.logger.error(msg)
            return (False, msg)

        msg = "Validate CBF Configuration: Complete"
        self.logger.info(msg)
        return (True, msg)

    def _validate_search_window_adr99(
        self: ScanConfigurationValidator, configuration: dict
    ) -> tuple[bool, str]:
        """
        Validates the Search Window specified in the The ["cbf"]/["midcbf"] portion of the full Scan Configuration

        :param configuration: The ["cbf"]/["midcbf"] portion of the full Scan Configuration as a Dictionary

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]
        """
        # Validate searchWindow.
        if "search_window" in configuration:
            msg = "search_window Not Supported in AA 0.5 and AA 1.0"
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
            # for sw in configuration["search_window"]:
            #     if sw["tdc_enable"]:
            #         for receptor in sw["tdc_destination_address"]:
            #             dish = receptor["receptor_id"]
            #             if dish not in self._dish_ids:
            #                 msg = (
            #                     f"'searchWindow' DISH ID {dish} "
            #                     + "not assigned to subarray. Aborting configuration."
            #                 )
            #                 self.logger.error(msg)
            #                 return (False, msg)
        else:
            msg = "Validate Search Window: Search Window not in Configuration: Complete"
            self.logger.info(msg)
            return (True, msg)
