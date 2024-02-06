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
from ska_tango_base.control_model import PowerMode, SimulationMode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.fsp.hps_fsp_corr_controller_simulator import (
    HpsFspCorrControllerSimulator,
)

# Data file path
FSP_CORR_PARAM_PATH = "mnt/fsp_param/"


class FspCorrSubarrayComponentManager(
    CbfComponentManager, CspObsComponentManager
):
    """A component manager for the FspCorrSubarray device."""

    def __init__(
        self: FspCorrSubarrayComponentManager,
        logger: logging.Logger,
        hps_fsp_corr_controller_fqdn: str,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        # TODO: for Mid.CBF, param hps_fsp_corr_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_corr_controller_fqdn: FQDN of the HPS FSP Correlator controller device
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

        self._hps_fsp_corr_controller_fqdn = hps_fsp_corr_controller_fqdn
        self._proxy_hps_fsp_corr_controller = None

        self._connected = False

        self._vcc_ids = []
        self._freq_band_name = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream1 = 0
        self._frequency_band_offset_stream2 = 0
        self._frequency_slice_id = 0
        self._bandwidth = 0
        self._bandwidth_actual = const.FREQUENCY_SLICE_BW
        self._zoom_window_tuning = 0
        self._integration_factor = 0
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
            "outputPort": [],
        }
        self._fsp_channel_offset = 0

        self._output_link_map = [[0, 0] for i in range(40)]

        self._simulation_mode = simulation_mode

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
    def frequency_band_offset_stream1(
        self: FspCorrSubarrayComponentManager,
    ) -> int:
        """
        Frequency Band Offset Stream 1

        :return: the frequency band offset for stream 1
        :rtype: int
        """
        return self._frequency_band_offset_stream1

    @property
    def frequency_band_offset_stream2(
        self: FspCorrSubarrayComponentManager,
    ) -> int:
        """
        Frequency Band Offset Stream 2

        :return: the frequency band offset for stream 2
        :rtype: int
        """
        return self._frequency_band_offset_stream2

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
    def integration_factor(self: FspCorrSubarrayComponentManager) -> int:
        """
        Integration Factor

        :return: the integration factor
        :rtype: int
        """
        return self._integration_factor

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
    def vcc_ids(self: FspCorrSubarrayComponentManager) -> List[int]:
        """
        Assigned VCC IDs

        :return: list of VCC IDs
        :rtype: List[int]
        """
        return self._vcc_ids

    @property
    def simulation_mode(
        self: FspCorrSubarrayComponentManager,
    ) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(
        self: FspCorrSubarrayComponentManager, value: SimulationMode
    ) -> None:
        """
        Set the simulation mode of the component manager.

        :param value: value to set simulation mode to
        """
        self._simulation_mode = value

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

    def _get_capability_proxies(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

        if not self._simulation_mode:
            if self._proxy_hps_fsp_corr_controller is None:
                self._proxy_hps_fsp_corr_controller = self._get_device_proxy(
                    self._hps_fsp_corr_controller_fqdn
                )
        else:
            self._proxy_hps_fsp_corr_controller = (
                HpsFspCorrControllerSimulator(
                    self._hps_fsp_corr_controller_fqdn
                )
            )

    def _get_device_proxy(
        self: FspCorrSubarrayComponentManager, fqdn_or_name: str
    ) -> CbfDeviceProxy | None:
        """
        Attempt to get a device proxy of the specified device.

        :param fqdn_or_name: FQDN of the device to connect to
            or the name of the group proxy to connect to
        :return: CbfDeviceProxy or None if no connection was made
        """
        try:
            self._logger.info(f"Attempting connection to {fqdn_or_name} ")

            device_proxy = CbfDeviceProxy(
                fqdn=fqdn_or_name, logger=self._logger, connect=False
            )
            device_proxy.connect(max_time=0)  # Make one attempt at connecting
            return device_proxy
        except tango.DevFailed as df:
            for item in df.args:
                self._logger.error(
                    f"Failed connection to {fqdn_or_name} : {item.reason}"
                )
            self.update_component_fault(True)
            return None

    def _assign_vcc(
        self: FspCorrSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Assign specified VCCs to the FSP CORR subarray.

        :param argin: IDs of VCCs to add.
        """
        errs = []  # list of error messages

        for vccID in argin:
            try:
                if vccID not in self._vcc_ids:
                    self._logger.info(f"VCC {vccID} assigned.")
                    self._vcc_ids.append(vccID)
                else:
                    log_msg = f"VCC {vccID} already assigned to current FSP CORR subarray."
                    self._logger.warning(log_msg)

            except KeyError:  # invalid VCC ID
                errs.append(f"Invalid VCC ID: {vccID}")

        if errs:
            msg = "\n".join(errs)
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "_assign_vcc execution",
                tango.ErrSeverity.ERR,
            )

    def _release_vcc(
        self: FspCorrSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Release assigned VCC from the FSP CORR subarray.

        :param argin: IDs of VCCs to remove.
        """
        for vccID in argin:
            if vccID in self._vcc_ids:
                self._logger.info(f"VCC {vccID} released.")
                self._vcc_ids.remove(vccID)
            else:
                log_msg = (
                    "VCC {vccID} not assigned to FSP CORR subarray. Skipping."
                )
                self._logger.warning(log_msg)

    def _release_all_vcc(self: FspCorrSubarrayComponentManager) -> None:
        """Release all assigned VCCs from the FSP CORR subarray"""
        self._release_vcc(self._vcc_ids.copy())

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
        self._frequency_band = freq_band_dict()[self._freq_band_name][
            "band_index"
        ]

        self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset_stream1 = int(
            configuration["frequency_band_offset_stream1"]
        )
        self._frequency_band_offset_stream2 = int(
            configuration["frequency_band_offset_stream2"]
        )

        # release previously assigned VCCs and assign newly specified VCCs
        self._release_all_vcc()
        self._assign_vcc(configuration["corr_vcc_ids"])

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
                ][self._frequency_band] + self._frequency_band_offset_stream1
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
                    + self._frequency_band_offset_stream1
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + (self._frequency_slice_id - 1)
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                    self._stream_tuning[0] * 10**9
                    + self._frequency_band_offset_stream1
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + self._frequency_slice_id
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                )

                frequency_slice_range_2 = (
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream2
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2
                    + (self._frequency_slice_id - 1)
                    * const.FREQUENCY_SLICE_BW
                    * 10**6,
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream2
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

        self._integration_factor = int(configuration["integration_factor"])

        self._fsp_channel_offset = int(configuration["channel_offset"])

        if "output_host" in configuration:
            self._vis_destination_address["outputHost"] = configuration[
                "output_host"
            ]
        elif self._vis_destination_address["outputHost"] == []:
            self._vis_destination_address[
                "outputHost"
            ] = const.DEFAULT_OUTPUT_HOST

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

        # Get the internal parameters from file
        internal_params_file_name = (
            FSP_CORR_PARAM_PATH + "internal_params_fsp_corr_subarray" + ".json"
        )

        with open(internal_params_file_name) as f_in:
            internal_params = f_in.read().replace("\n", "")
        internal_params_obj = json.loads(internal_params)

        # append all internal parameters to the configuration to pass to HPS
        # construct HPS ConfigureScan input
        sample_rates = configuration.pop("fs_sample_rates")
        hps_fsp_configuration = dict({"configure_scan": configuration})
        hps_fsp_configuration.update(internal_params_obj)
        # append the fs_sample_rates to the configuration
        hps_fsp_configuration["fs_sample_rates"] = sample_rates
        log_msg = f"Sample rates added to HPS FSP Corr configuration; fs_sample_rates = {sample_rates}."
        self._logger.debug(log_msg)

        self._get_capability_proxies()

        try:
            self._logger.info(
                f"HPS FSP ConfigureScan input: {json.dumps(hps_fsp_configuration)}"
            )
            self._proxy_hps_fsp_corr_controller.set_timeout_millis(12000)
            self._proxy_hps_fsp_corr_controller.ConfigureScan(
                json.dumps(hps_fsp_configuration)
            )
        except Exception as e:
            self._logger.error(str(e))

        return (
            ResultCode.OK,
            "FspCorrSubarray ConfigureScan command completed OK",
        )

    def scan(
        self: FspCorrSubarrayComponentManager, scan_id: int
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

        self._proxy_hps_fsp_corr_controller.Scan(scan_id)

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

        self._proxy_hps_fsp_corr_controller.EndScan()

        return (ResultCode.OK, "FspCorrSubarray EndScan command completed OK")

    def _deconfigure(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        self._freq_band_name = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream1 = 0
        self._frequency_band_offset_stream2 = 0
        self._frequency_slice_id = 0
        self._bandwidth = 0
        self._bandwidth_actual = const.FREQUENCY_SLICE_BW
        self._zoom_window_tuning = 0
        self._integration_factor = 0
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

        self._release_all_vcc()

        self._proxy_hps_fsp_corr_controller.GoToIdle()

        return (ResultCode.OK, "FspCorrSubarray GoToIdle command completed OK")

    def obsreset(
        self: FspCorrSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the ObsReset() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self._deconfigure()

        self._release_all_vcc()

        # TODO: ObsReset command not implemented for the HPS FSP application, see CIP-1850
        # self._proxy_hps_fsp_corr_controller.ObsReset()
        return (ResultCode.OK, "FspCorrSubarray ObsReset command completed OK")

    def abort(
        self: FspCorrSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        # TODO: Abort command not implemented for the HPS FSP application
        return (ResultCode.OK, "Abort command not implemented")
