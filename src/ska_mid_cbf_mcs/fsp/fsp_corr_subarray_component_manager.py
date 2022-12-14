# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada
from __future__ import annotations

import json
import logging
from typing import Callable, List, Optional, Tuple

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


class FspCorrSubarrayComponentManager(
    CbfComponentManager, CspObsComponentManager
):
    """A component manager for the FspCorrSubarray device."""

    def __init__(
        self: FspCorrSubarrayComponentManager,
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param push_change_event: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        self._logger = logger

        self._connected = False

        self._receptors = []
        self._freq_band_name = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._frequency_slice_id = 0
        self._bandwidth = 0
        self._bandwidth_actual = const.FREQUENCY_SLICE_BW
        self._zoom_window_tuning = 0
        self._integration_time = 0
        self._scan_id = 0
        self._config_id = ""
        self._channel_averaging_map = [
            [
                int(i * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS)
                + 1,
                0,
            ]
            for i in range(const.NUM_CHANNEL_GROUPS)
        ]
        self._vis_destination_address = {
            "outputHost": [],
            "outputMac": [],
            "outputPort": [],
        }
        self._fsp_channel_offset = 0

        self._output_link_map = [[0, 0] for i in range(40)]

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )

    @property
    def frequency_band(self: FspCorrSubarrayComponentManager) -> tango.DevEnum:
        """
        Frequency Band

        :return: the frequency band
        :rtype: tango.DevEnum
        """
        return self._frequency_band

    @property
    def stream_tuning(self: FspCorrSubarrayComponentManager) -> List[float]:
        """
        Band 5 Tuning

        :return: an array of float,
                (first element corresponds to the first stream,
                second to the second stream).
        :rtype: List[float]
        """
        return self._stream_tuning

    @property
    def frequency_band_offset_stream_1(
        self: FspCorrSubarrayComponentManager,
    ) -> int:
        """
        Frequency Band Offset Stream 1

        :return: the frequency band offset for stream 1
        :rtype: int
        """
        return self._frequency_band_offset_stream_1

    @property
    def frequency_band_offset_stream_2(
        self: FspCorrSubarrayComponentManager,
    ) -> int:
        """
        Frequency Band Offset Stream 2

        :return: the frequency band offset for stream 2
        :rtype: int
        """
        return self._frequency_band_offset_stream_2

    @property
    def frequency_slice_id(self: FspCorrSubarrayComponentManager) -> int:
        """
        Frequency Slice ID

        :return: the frequency slice id
        :rtype: int
        """
        return self._frequency_slice_id

    @property
    def bandwidth(self: FspCorrSubarrayComponentManager) -> int:
        """
        Bandwidth

        :return: the corr bandwidth (bandwidth to be correlated
                 is <Full Bandwidth>/2^bandwidth).
        :rtype: int
        """
        return self._bandwidth

    @property
    def integration_time(self: FspCorrSubarrayComponentManager) -> int:
        """
        Integration Time

        :return: the integration time (millisecond).
        :rtype: int
        """
        return self._integration_time

    @property
    def fsp_channel_offset(self: FspCorrSubarrayComponentManager) -> int:
        """
        FSP Channel Offset

        :return: the FSP channel offset
        :rtype: int
        """
        return self._fsp_channel_offset

    @property
    def vis_destination_address(self: FspCorrSubarrayComponentManager) -> str:
        """
        VIS Destination Address

        :return: JSON string containing info about current SDP destination addresses being used
        :rtype: str
        """
        return self._vis_destination_address

    @property
    def output_link_map(
        self: FspCorrSubarrayComponentManager,
    ) -> List[List[int]]:
        """
        Output Link Map

        :return: the output link map
        :rtype: List[List[int]]
        """
        return self._output_link_map

    @property
    def channel_averaging_map(
        self: FspCorrSubarrayComponentManager,
    ) -> List[List[int]]:
        """
        Channel Averaging Map

        :return: the channel averaging map. Consists of 2*20 array of
                integers(20 tupples representing 20* 744 channels).
                The first element is the ID of the first channel in a channel group.
                The second element is the averaging factor
        :rtype: List[List[int]]
        """
        return self._channel_averaging_map

    @property
    def zoom_window_tuning(self: FspCorrSubarrayComponentManager) -> int:
        """
        Zoom Window Tuning

        :return: the zoom window tuning
        :rtype: int
        """
        return self._zoom_window_tuning

    @property
    def config_id(self: FspCorrSubarrayComponentManager) -> str:
        """
        Config ID

        :return: the config id
        :rtype: str
        """
        return self._config_id

    @property
    def scan_id(self: FspCorrSubarrayComponentManager) -> int:
        """
        Scan ID

        :return: the scan id
        :rtype: int
        """
        return self._scan_id

    @property
    def receptors(self: FspCorrSubarrayComponentManager) -> List[int]:
        """
        Receptors

        :return: list of receptor ids
        :rtype: List[int]
        """
        return self._receptors

    def start_communicating(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: FspCorrSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        self._logger.info(
            "Entering FspCorrSubarrayComponentManager.stop_communicating"
        )
        super().stop_communicating()

        self._connected = False

    def _add_receptors(
        self: FspCorrSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Add specified receptors to the subarray.

        :param argin: ids of receptors to add.
        """
        errs = []  # list of error messages

        for receptorID in argin:
            try:
                if receptorID not in self._receptors:
                    self._logger.info(f"Receptor {receptorID} added.")
                    self._receptors.append(receptorID)
                else:
                    log_msg = f"Receptor {receptorID} already assigned to current FSP subarray."
                    self._logger.warning(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append(f"Invalid receptor ID: {receptorID}")

        if errs:
            msg = "\n".join(errs)
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "_add_receptors execution",
                tango.ErrSeverity.ERR,
            )

    def _remove_receptors(
        self: FspCorrSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Remove specified receptors from the subarray.

        :param argin: ids of receptors to remove.
        """
        for receptorID in argin:
            if receptorID in self._receptors:
                self._logger.info(f"Receptor {receptorID} removed.")
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {receptorID} not assigned to FSP subarray. Skipping."
                self._logger.warning(log_msg)

    def _remove_all_receptors(self: FspCorrSubarrayComponentManager) -> None:
        """Remove all Receptors of this subarray"""
        self._remove_receptors(self._receptors[:])

    def configure_scan(
        self: FspCorrSubarrayComponentManager, configuration: str
    ) -> Tuple[ResultCode, str]:
        """
        Performs the ConfigureScan() command functionality

        :param configuration: The configuration as JSON formatted string
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self._deconfigure()

        configuration = json.loads(configuration)

        self._freq_band_name = configuration["frequency_band"]
        self._frequency_band = freq_band_dict()[self._freq_band_name]

        self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset_stream_1 = int(
            configuration["frequency_band_offset_stream_1"]
        )
        self._frequency_band_offset_stream_2 = int(
            configuration["frequency_band_offset_stream_2"]
        )

        self._remove_all_receptors()
        # "receptor_ids" values are pairs of str and int
        receptors_to_add = [receptor[1] for receptor in configuration["receptor_ids"]]
        self._add_receptors(receptors_to_add)

        self._frequency_slice_id = int(configuration["frequency_slice_id"])

        self._bandwidth = int(configuration["zoom_factor"])
        self._bandwidth_actual = int(
            const.FREQUENCY_SLICE_BW / 2 ** int(configuration["zoom_factor"])
        )

        if self._bandwidth != 0:  # zoomWindowTuning is required
            if self._frequency_band in list(
                range(4)
            ):  # frequency band is not band 5
                self._zoom_window_tuning = int(
                    configuration["zoom_window_tuning"]
                )

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
                ][self._frequency_band] + self._frequency_band_offset_stream_1
                frequency_slice_range = (
                    frequency_band_start
                    + (self._frequency_slice_id - 1)
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                    frequency_band_start
                    + self._frequency_slice_id
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                )

                if (
                    frequency_slice_range[0]
                    + self._bandwidth_actual * 10**6 / 2
                    <= int(configuration["zoom_window_tuning"]) * 10**3
                    <= frequency_slice_range[1]
                    - self._bandwidth_actual * 10**6 / 2
                ):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = (
                        "'zoomWindowTuning' partially out of observed frequency slice. "
                        "Proceeding."
                    )
                    self._logger.warning(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                self._zoom_window_tuning = configuration["zoom_window_tuning"]

                frequency_slice_range_1 = (
                    self._stream_tuning[0] * 10**9
                    + self._frequency_band_offset_stream_1
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + (self._frequency_slice_id - 1)
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                    self._stream_tuning[0] * 10**9
                    + self._frequency_band_offset_stream_1
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + self._frequency_slice_id
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                )

                frequency_slice_range_2 = (
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream_2
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + (self._frequency_slice_id - 1)
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream_2
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + self._frequency_slice_id
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                )

                if (
                    frequency_slice_range_1[0]
                    + self._bandwidth_actual * 10**6 / 2
                    <= int(configuration["zoom_window_tuning"]) * 10**3
                    <= frequency_slice_range_1[1]
                    - self._bandwidth_actual * 10**6 / 2
                ) or (
                    frequency_slice_range_2[0]
                    + self._bandwidth_actual * 10**6 / 2
                    <= int(configuration["zoom_window_tuning"]) * 10**3
                    <= frequency_slice_range_2[1]
                    - self._bandwidth_actual * 10**6 / 2
                ):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = (
                        "'zoomWindowTuning' partially out of observed frequency slice. "
                        "Proceeding."
                    )
                    self._logger.warning(log_msg)

        self._integration_time = int(configuration["integration_factor"])

        self._fsp_channel_offset = int(configuration["channel_offset"])

        if "output_host" in configuration:
            self._vis_destination_address["outputHost"] = configuration[
                "output_host"
            ]
        elif self._vis_destination_address["outputHost"] == []:
            self._vis_destination_address[
                "outputHost"
            ] = const.DEFAULT_OUTPUT_HOST

        if "output_mac" in configuration:
            self._vis_destination_address["outputMac"] = configuration[
                "output_mac"
            ]
        elif self._vis_destination_address["outputMac"] == []:
            self._vis_destination_address[
                "outputMac"
            ] = const.DEFAULT_OUTPUT_MAC

        if "output_port" in configuration:
            self._vis_destination_address["outputPort"] = configuration[
                "output_port"
            ]
        elif self._vis_destination_address["outputPort"] == []:
            self._vis_destination_address[
                "outputPort"
            ] = const.DEFAULT_OUTPUT_PORT

        self._output_link_map = configuration["output_link_map"]

        if "channel_averaging_map" in configuration:
            self._channel_averaging_map = configuration[
                "channel_averaging_map"
            ]
        else:
            self._channel_averaging_map = [
                [
                    int(i * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS)
                    + 1,
                    0,
                ]
                for i in range(const.NUM_CHANNEL_GROUPS)
            ]
            log_msg = (
                "FSP specified, but 'channelAveragingMap not given. Default to averaging "
                "factor = 0 for all channel groups."
            )
            self._logger.warning(log_msg)

        self._config_id = configuration["config_id"]

        return (
            ResultCode.OK,
            "FspCorrSubarray ConfigureScan command completed OK",
        )

    def scan(
        self: FspCorrSubarrayComponentManager,
        scan_id: int,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the Scan() command functionality

        :param scan_id: The scan id
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self._scan_id = scan_id

        return (ResultCode.OK, "FspCorrSubarray Scan command completed OK")

    def end_scan(
        self: FspCorrSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the EndScan() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        return (ResultCode.OK, "FspCorrSubarray EndScan command completed OK")

    def _deconfigure(
        self: FspCorrSubarrayComponentManager,
    ) -> None:

        self._freq_band_name = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._frequency_slice_id = 0
        self._bandwidth = 0
        self._bandwidth_actual = const.FREQUENCY_SLICE_BW
        self._zoom_window_tuning = 0
        self._integration_time = 0
        self._scan_id = 0
        self._config_id = ""

        self._channel_averaging_map = [
            [
                int(i * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS)
                + 1,
                0,
            ]
            for i in range(const.NUM_CHANNEL_GROUPS)
        ]
        self._vis_destination_address = {
            "outputHost": [],
            "outputMac": [],
            "outputPort": [],
        }
        self._fsp_channel_offset = 0
        self._output_link_map = [[0, 0] for i in range(40)]

        self._channel_info = []
        # self._channel_info.clear() #TODO:  not yet populated

    def go_to_idle(
        self: FspCorrSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the GoToIdle() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self._deconfigure()

        self._remove_all_receptors()

        return (ResultCode.OK, "FspCorrSubarray GoToIdle command completed OK")
