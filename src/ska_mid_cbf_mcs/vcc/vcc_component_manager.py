# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
VccComponentManager
Sub-element VCC component manager for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

import copy
import json
import logging
from typing import Callable, List, Optional, Tuple

# tango imports
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode
from ska_tango_base.csp.obs import CspObsComponentManager

from ska_mid_cbf_mcs.commons.gain_utils import GAINUtils
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.vcc.vcc_band_simulator import VccBandSimulator
from ska_mid_cbf_mcs.vcc.vcc_controller_simulator import VccControllerSimulator

# SKA Specific imports


__all__ = ["VccComponentManager"]

VCC_PARAM_PATH = "mnt/vcc_param/"


class VccComponentManager(CbfComponentManager, CspObsComponentManager):
    """Component manager for Vcc class."""

    @property
    def config_id(self: VccComponentManager) -> str:
        """
        Configuration ID

        :return: the configuration ID
        """
        return self._config_id

    @config_id.setter
    def config_id(self: VccComponentManager, config_id: str) -> None:
        """
        Set the configuration ID.

        :param config_id: Configuration ID
        """
        self._config_id = config_id

    @property
    def scan_id(self: VccComponentManager) -> int:
        """
        Scan ID

        :return: the scan ID
        """
        return self._scan_id

    @scan_id.setter
    def scan_id(self: VccComponentManager, scan_id: int) -> None:
        """
        Set the scan ID.

        :param scan_id: Scan ID
        """
        self._scan_id = scan_id

    @property
    def dish_id(self: VccComponentManager) -> str:
        """
        DISH ID

        :return: the DISH ID
        """
        return self._dish_id

    @dish_id.setter
    def dish_id(self: VccComponentManager, dish_id: str) -> None:
        """
        Set the DISH ID.

        :param dish_id: DISH ID
        """
        self._dish_id = dish_id

    @property
    def frequency_band(self: VccComponentManager) -> int:
        """
        Frequency Band

        :return: the frequency band as the integer index in an array
                of frequency band labels: ["1", "2", "3", "4", "5a", "5b"]
        """
        return self._frequency_band

    @property
    def stream_tuning(self: VccComponentManager) -> List[float]:
        """
        Band 5 Stream Tuning

        :return: the band 5 stream tuning
        """
        return self._stream_tuning

    @property
    def frequency_band_offset_stream1(self: VccComponentManager) -> int:
        """
        Frequency Band Offset Stream 1

        :return: the frequency band offset for stream 1
        """
        return self._frequency_band_offset_stream1

    @property
    def frequency_band_offset_stream2(self: VccComponentManager) -> int:
        """
        Frequency Band Offset Stream 2

        :return: the frequency band offset for stream 2, this
                is only use when band 5 is active
        """
        return self._frequency_band_offset_stream2

    @property
    def channel_offset(self: VccComponentManager) -> int:
        """
        Channel offset

        :return: the channel offset
        """
        return self._channel_offset

    @property
    def rfi_flagging_mask(self: VccComponentManager) -> str:
        """
        RFI Flagging Mask

        :return: the RFI flagging mask
        """
        return self._rfi_flagging_mask

    @property
    def jones_matrix(self: VccComponentManager) -> str:
        """
        Jones Matrix

        :return: the last received Jones matrix
        """
        return self._jones_matrix

    @property
    def delay_model(self: VccComponentManager) -> str:
        """
        Delay Model

        :return: the last received delay model
        """
        return self._delay_model

    @property
    def doppler_phase_correction(self: VccComponentManager) -> List[float]:
        """
        Doppler Phase Correction

        :return: the last received Doppler phase correction array
        """
        return self._doppler_phase_correction

    def __init__(
        self: VccComponentManager,
        vcc_id: int,
        talon_lru: str,
        vcc_controller: str,
        vcc_band: List[str],
        search_window: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable,
        component_obs_fault_callback: Callable,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
    ) -> None:
        """
        Initialize a new instance.

        :param vcc_id: integer ID of this VCC
        :param talon_lru: FQDN of the TalonLRU device
        :param vcc_controller: FQDN of the HPS VCC controller device
        :param vcc_band: FQDNs of HPS VCC band devices
        :param search_window: FQDNs of VCC search windows
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between the
            component manager and its component changes
        :param component_power_mode_changed_callback: callback to be called when
            the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault (for op state model)
        :param component_obs_fault_callback: callback to be called in event of
            component fault (for obs state model)
        :param simulation_mode: simulation mode identifies if the real VCC HPS
            applications or the simulator should be connected
        """
        self._logger = logger

        self._simulation_mode = simulation_mode

        self._vcc_id = vcc_id
        self._talon_lru_fqdn = talon_lru
        self._vcc_controller_fqdn = vcc_controller
        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self.connected = False
        self._ready = False

        self.obs_faulty = False

        self._component_obs_fault_callback = component_obs_fault_callback

        # Initialize attribute values
        self._dish_id = ""

        self._scan_id = 0
        self._config_id = ""

        self._frequency_band = 0
        self._freq_band_name = ""
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream1 = 0
        self._frequency_band_offset_stream2 = 0
        self._channel_offset = 0
        self._rfi_flagging_mask = ""

        self._jones_matrix = ""
        self._delay_model = ""
        self._doppler_phase_correction = [0 for _ in range(4)]

        # Initialize list of band proxies and band -> index translation;
        # entry for each of: band 1 & 2, band 3, band 4, band 5
        self._band_proxies = []
        self._freq_band_index = dict(
            zip(freq_band_dict().keys(), [0, 0, 1, 2, 3, 3])
        )

        self._sw_proxies = []
        self._talon_lru_proxy = None
        self._vcc_controller_proxy = None

        # Create simulators
        self._band_simulators = [
            VccBandSimulator(vcc_band[0]),
            VccBandSimulator(vcc_band[1]),
            VccBandSimulator(vcc_band[2]),
            VccBandSimulator(vcc_band[3]),
        ]
        self._vcc_controller_simulator = VccControllerSimulator(
            vcc_controller,
            self._band_simulators[0],
            self._band_simulators[1],
            self._band_simulators[2],
            self._band_simulators[3],
        )

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )

    @property
    def simulation_mode(self: VccComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(
        self: VccComponentManager, value: SimulationMode
    ) -> None:
        """
        Set the simulation mode of the component manager.

        :param value: value to set simulation mode to
        """
        self._simulation_mode = value

    def start_communicating(self: VccComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        if self.connected:
            self._logger.info("Already connected.")
            return

        super().start_communicating()

        try:
            self._talon_lru_proxy = CbfDeviceProxy(
                fqdn=self._talon_lru_fqdn, logger=self._logger
            )

            self._sw_proxies = [
                CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                for fqdn in self._search_window_fqdn
            ]
        except tango.DevFailed:
            self.update_component_fault(True)
            self._logger.error("Error in proxy connection")
            return

        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(self._get_power_mode())
        self.update_component_fault(False)

    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False

    def _get_power_mode(self: VccComponentManager) -> PowerMode:
        """
        Get the power mode of this VCC based on the current power
        mode of the LRU this VCC belongs to.

        :return: VCC power mode
        """
        try:
            return self._talon_lru_proxy.LRUPowerMode
        except tango.DevFailed:
            self._logger.error("Could not connect to Talon LRU device")
            self.update_component_fault(True)
            return PowerMode.UNKNOWN

    def on(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn on VCC component. This attempts to establish communication
        with the VCC devices on the HPS.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)

        :raise ConnectionError: if unable to connect to HPS VCC devices
        """
        self._logger.info("Entering VccComponentManager.on")
        try:
            # Try to connect to HPS devices, they should be running at this point
            if not self._simulation_mode:
                self._logger.info(
                    "Connecting to HPS VCC controller and band devices"
                )

                self._vcc_controller_proxy = CbfDeviceProxy(
                    fqdn=self._vcc_controller_fqdn, logger=self._logger
                )

                self._band_proxies = [
                    CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    for fqdn in self._vcc_band_fqdn
                ]

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            self.update_component_fault(True)
            return (ResultCode.FAILED, "Failed to connect to HPS VCC devices")

        self._logger.info("Completed VccComponentManager.on")
        self.update_component_power_mode(PowerMode.ON)
        return (ResultCode.OK, "On command completed OK")

    def off(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn off VCC component; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.update_component_power_mode(PowerMode.OFF)
        return (ResultCode.OK, "Off command completed OK")

    def standby(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn VCC component to standby; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.update_component_power_mode(PowerMode.STANDBY)
        return (ResultCode.OK, "Standby command completed OK")

    def configure_band(
        self: VccComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure the corresponding band. At the HPS level, this reconfigures the
        FPGA to the correct bitstream and enables the respective band device. All
        other band devices are disabled.

        :param argin: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        (result_code, msg) = (ResultCode.OK, "ConfigureBand completed OK.")

        try:
            band_config = json.loads(argin)
            freq_band_name = band_config["frequency_band"]

            # Configure the band via the VCC Controller device
            self._logger.info(f"Configuring VCC band {freq_band_name}")
            frequency_band = freq_band_dict()[freq_band_name]["band_index"]
            self._freq_band_name = freq_band_name
            if self._simulation_mode:
                self._vcc_controller_simulator.ConfigureBand(frequency_band)
            else:
                self._vcc_controller_proxy.ConfigureBand(frequency_band)

            # Set internal params for the configured band
            self._logger.info(
                f"Configuring internal parameters for VCC band {freq_band_name}"
            )

            internal_params_file_name = f"{VCC_PARAM_PATH}internal_params_receptor{self._dish_id}_band{freq_band_name}.json"
            self._logger.debug(
                f"Using parameters stored in {internal_params_file_name}"
            )
            try:
                with open(internal_params_file_name, "r") as f:
                    json_string = f.read()
            except FileNotFoundError:
                self._logger.info(
                    f"Could not find internal parameters file for receptor {self._dish_id}, band {freq_band_name}; using default."
                )
                with open(
                    f"{VCC_PARAM_PATH}internal_params_default.json", "r"
                ) as f:
                    json_string = f.read()

            self._logger.info(f"VCC internal parameters: {json_string}")

            args = json.loads(json_string)

            log_string = str(args["vcc_gain"])
            self._logger.info(f"Pre VCC gain values: {log_string}")

            gain_corrections = GAINUtils.get_vcc_ripple_correction(
                self._logger
            )
            
            # Apply Gain Correction to parameters
            gain_index = 0

            # Use a default channel_offset of 0 if not passed in
            if 'channel_offset' in band_config.keys():
                channel_index = band_config["channel_offset"]
            else:
                channel_index = 0

            self._logger.info(f"channel_offset: {channel_index}")
            for gain in args["vcc_gain"]:
                gain = gain * gain_corrections[channel_index + gain_index]
                args["vcc_gain"][gain_index] = gain
                gain_index = gain_index + 1

            log_string = str(args["vcc_gain"])
            self._logger.info(f"Post VCC gain values: {log_string}")
            args.update({"dish_sample_rate": band_config["dish_sample_rate"]})
            args.update(
                {"samples_per_frame": band_config["samples_per_frame"]}
            )
            json_string = json.dumps(args)

            idx = self._freq_band_index[self._freq_band_name]
            if self._simulation_mode:
                self._band_simulators[idx].SetInternalParameters(json_string)
            else:
                self._band_proxies[idx].SetInternalParameters(json_string)

            self._frequency_band = frequency_band
            self._push_change_event("frequencyBand", self._frequency_band)

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            self._component_obs_fault_callback(True)
            (result_code, msg) = (
                ResultCode.FAILED,
                "Failed to connect to HPS VCC devices.",
            )
        except FileNotFoundError:
            self._logger.error(
                "Could not find default internal parameters file."
            )
            (result_code, msg) = (
                ResultCode.FAILED,
                "Missing default internal parameters file.",
            )

        return (result_code, msg)

    def deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self._doppler_phase_correction = [0 for _ in range(4)]
        self._jones_matrix = ""
        self._delay_model = ""
        self._rfi_flagging_mask = ""
        self._frequency_band_offset_stream2 = 0
        self._frequency_band_offset_stream1 = 0
        self._channel_offset = 0
        self._stream_tuning = (0, 0)
        self._frequency_band = 0
        self._push_change_event("frequencyBand", self._frequency_band)
        self._freq_band_name = ""
        self._config_id = ""
        self._scan_id = 0

        if self._ready:
            if self._simulation_mode:
                self._vcc_controller_simulator.Unconfigure()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._vcc_controller_proxy.Unconfigure()
                except tango.DevFailed as df:
                    self._logger.error(str(df.args[0].desc))
                    self._component_obs_fault_callback(True)
            self._ready = False

    def configure_scan(
        self: VccComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Execute configure scan operation.

        :param argin: JSON string with the configure scan parameters

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        configuration = json.loads(argin)
        self._config_id = configuration["config_id"]

        # TODO: The frequency band attribute is optional but
        # if not specified the previous frequency band set should be used
        # (see Mid.CBF Scan Configuration in ICD). Therefore, the previous frequency
        # band value needs to be stored, and if the frequency band is not
        # set in the config it should be replaced with the previous value.
        freq_band = freq_band_dict()[configuration["frequency_band"]][
            "band_index"
        ]
        if self._frequency_band != freq_band:
            return (
                ResultCode.FAILED,
                f"Error in Vcc.ConfigureScan; scan configuration frequency band {freq_band} "
                + f"not the same as enabled band device {self._frequency_band}",
            )

        if self._frequency_band in [4, 5]:
            self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset_stream1 = int(
            configuration["frequency_band_offset_stream1"]
        )
        self._frequency_band_offset_stream2 = int(
            configuration["frequency_band_offset_stream2"]
        )
        self._channel_offset = int(configuration["channel_offset"])

        if "rfi_flagging_mask" in configuration:
            self._rfi_flagging_mask = str(configuration["rfi_flagging_mask"])
        else:
            self._logger.warning("'rfiFlaggingMask' not given. Proceeding.")

        # Send the ConfigureScan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self._simulation_mode:
            self._band_simulators[idx].ConfigureScan(argin)
        else:
            try:
                self._band_proxies[idx].ConfigureScan(argin)
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self._component_obs_fault_callback(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
                )

        self._ready = True
        return (ResultCode.OK, "Vcc ConfigureScanCommand completed OK")

    def scan(
        self: VccComponentManager, scan_id: int
    ) -> Tuple[ResultCode, str]:
        """
        Begin scan operation.

        :param argin: scan ID integer

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.info("Starting scan")
        self._scan_id = scan_id

        # Send the Scan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self._simulation_mode:
            self._band_simulators[idx].Scan(scan_id)
        else:
            try:
                self._band_proxies[idx].Scan(scan_id)
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self._component_obs_fault_callback(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
                )

        return (ResultCode.STARTED, "Vcc ScanCommand completed OK")

    def end_scan(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        End scan operation.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.info("Ending scan")

        # Send the EndScan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self._simulation_mode:
            self._band_simulators[idx].EndScan()
        else:
            try:
                self._band_proxies[idx].EndScan()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self._component_obs_fault_callback(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
                )

        return (ResultCode.OK, "Vcc EndScanCommand completed OK")

    def abort(self):
        """Tell the current VCC band device to abort whatever it was doing."""
        if self._freq_band_name != "":
            idx = self._freq_band_index[self._freq_band_name]
            if self._simulation_mode:
                self._band_simulators[idx].Abort()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._vcc_controller_proxy.Unconfigure()
                    # self._band_proxies[idx].Abort()
                except tango.DevFailed as df:
                    self._logger.error(str(df.args[0].desc))
                    self._component_obs_fault_callback(True)
                    return (
                        ResultCode.FAILED,
                        "Failed to connect to VCC band device",
                    )
                # If the VCC has been aborted from READY, update accordingly.
                if self._ready:
                    self._ready = False
        else:
            # if no value for _freq_band_name, assume in IDLE state,
            # either from initialization or after deconfigure has been called
            self._logger.info(
                "Aborting from IDLE; not issuing Abort command to VCC band devices"
            )

        return (ResultCode.OK, "Vcc Abort command completed OK")

    def obsreset(self):
        """Reset the configuration."""
        if self._freq_band_name != "":
            idx = self._freq_band_index[self._freq_band_name]
            if self._simulation_mode:
                self._band_simulators[idx].ObsReset()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._band_proxies[idx].ObsReset()
                except tango.DevFailed as df:
                    self._logger.error(str(df.args[0].desc))
                    self._component_obs_fault_callback(True)
                    return (
                        ResultCode.FAILED,
                        "Failed to connect to VCC band device",
                    )
        else:
            # if no value for _freq_band_name, assume in IDLE state,
            # either from initialization or after deconfigure has been called
            self._logger.info(
                "Aborted from IDLE; not issuing ObsReset command to VCC band devices"
            )

        return (ResultCode.OK, "Vcc ObsReset command completed OK")

    def configure_search_window(
        self: VccComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure a search window by sending parameters from the input(JSON) to
        SearchWindow self. This function is called by the subarray after the
        configuration has already been validated, so the checks here have been
        removed to reduce overhead.

        :param argin: JSON string with the search window parameters

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        result_code = ResultCode.OK
        msg = "ConfigureSearchWindow completed OK"

        argin = json.loads(argin)
        self._logger.debug(f"vcc argin: {json.dumps(argin)}")

        # variable to use as SW proxy
        proxy_sw = None
        # Configure searchWindowID.
        if int(argin["search_window_id"]) == 1:
            proxy_sw = self._sw_proxies[0]
        elif int(argin["search_window_id"]) == 2:
            proxy_sw = self._sw_proxies[1]

        self._logger.debug(f"search_window_id == {argin['search_window_id']}")

        try:
            # Configure searchWindowTuning.
            if self._frequency_band in list(
                range(4)
            ):  # frequency band is not band 5
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ,
                ][self._frequency_band]

                if (
                    start_freq_Hz
                    + self._frequency_band_offset_stream1
                    + const.SEARCH_WINDOW_BW_HZ / 2
                    <= int(argin["search_window_tuning"])
                    <= stop_freq_Hz
                    + self._frequency_band_offset_stream1
                    - const.SEARCH_WINDOW_BW_HZ / 2
                ):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = (
                        "'searchWindowTuning' partially out of observed band. "
                        "Proceeding."
                    )
                    self._logger.warning(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                frequency_band_range_1 = (
                    self._stream_tuning[0] * 10**9
                    + self._frequency_band_offset_stream1
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                    self._stream_tuning[0] * 10**9
                    + self._frequency_band_offset_stream1
                    + const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                )

                frequency_band_range_2 = (
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream2
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream2
                    + const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                )

                if (
                    frequency_band_range_1[0]
                    + const.SEARCH_WINDOW_BW * 10**6 / 2
                    <= int(argin["search_window_tuning"])
                    <= frequency_band_range_1[1]
                    - const.SEARCH_WINDOW_BW * 10**6 / 2
                ) or (
                    frequency_band_range_2[0]
                    + const.SEARCH_WINDOW_BW * 10**6 / 2
                    <= int(argin["search_window_tuning"])
                    <= frequency_band_range_2[1]
                    - const.SEARCH_WINDOW_BW * 10**6 / 2
                ):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = (
                        "'searchWindowTuning' partially out of observed band. "
                        "Proceeding."
                    )
                    self._logger.warning(log_msg)

                # Configure tdcEnable.
                proxy_sw.tdcEnable = argin["tdc_enable"]
                # if argin["tdc_enable"]:
                #     proxy_sw.On()
                # else:
                #     proxy_sw.Off()

                # Configure tdcNumBits.
                if argin["tdc_enable"]:
                    proxy_sw.tdcNumBits = int(argin["tdc_num_bits"])

                # Configure tdcPeriodBeforeEpoch.
                if "tdc_period_before_epoch" in argin:
                    proxy_sw.tdcPeriodBeforeEpoch = int(
                        argin["tdc_period_before_epoch"]
                    )
                else:
                    proxy_sw.tdcPeriodBeforeEpoch = 2
                    log_msg = (
                        "Search window specified, but 'tdcPeriodBeforeEpoch' not given. "
                        "Defaulting to 2."
                    )
                    self._logger.warning(log_msg)

                # Configure tdcPeriodAfterEpoch.
                if "tdc_period_after_epoch" in argin:
                    proxy_sw.tdcPeriodAfterEpoch = int(
                        argin["tdc_period_after_epoch"]
                    )
                else:
                    proxy_sw.tdcPeriodAfterEpoch = 22
                    log_msg = (
                        "Search window specified, but 'tdcPeriodAfterEpoch' not given. "
                        "Defaulting to 22."
                    )
                    self._logger.warning(log_msg)

                # Configure tdcDestinationAddress.
                # Note: subarray has translated DISH IDs to VCC IDs in the JSON at this point
                if argin["tdc_enable"]:
                    for tdc_dest in argin["tdc_destination_address"]:
                        if tdc_dest["receptor_id"] == self._vcc_id:
                            # TODO: validate input
                            proxy_sw.tdcDestinationAddress = tdc_dest[
                                "tdc_destination_address"
                            ]
                            break

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            self._component_obs_fault_callback(True)
            (result_code, msg) = (
                ResultCode.FAILED,
                "Error configuring search window.",
            )

        return (result_code, msg)

    def update_doppler_phase_correction(
        self: VccComponentManager, argin: str
    ) -> None:
        """
        Update Vcc's doppler phase correction

        :param argin: the doppler phase correction JSON string
        """
        argin = json.loads(argin)

        # Note: subarray has translated DISH IDs to VCC IDs in the JSON at this point
        for dopplerDetails in argin:
            if dopplerDetails["receptor"] == self._vcc_id:
                coeff = dopplerDetails["dopplerCoeff"]
                if len(coeff) == 4:
                    self._doppler_phase_correction = coeff.copy()
                else:
                    log_msg = "Invalid length for 'dopplerCoeff' "
                    self._logger.error(log_msg)

    def update_delay_model(self: VccComponentManager, argin: str) -> None:
        """
        Update Vcc's delay model

        :param argin: the delay model JSON string
        """
        delay_model_obj = json.loads(argin)

        # Find the delay model that applies to this VCC's DISH ID and store it
        dm_found = False

        # The delay model schema allows for a set of dishes to be included.
        # Even though there will only be one entryfor a VCC, there should still
        # be a list with a single entry so that the schema is followed.
        # Set up the delay model to be a list.

        # Note: subarray has translated DISH IDs to VCC IDs in the JSON at this point
        list_of_entries = []
        for entry in delay_model_obj["delay_details"]:
            self._logger.debug(
                f"Received delay model for VCC {entry['receptor']}"
            )
            if entry["receptor"] == self._vcc_id:
                self._logger.debug("Updating delay model for this VCC")
                list_of_entries.append(copy.deepcopy(entry))
                self._delay_model = json.dumps(
                    {"delay_details": list_of_entries}
                )
                dm_found = True
                break
        if not dm_found:
            log_msg = f"Delay Model for VCC (DISH: {self._dish_id}) not found"
            self._logger.error(log_msg)

    def update_jones_matrix(self: VccComponentManager, argin: str) -> None:
        """
        Update Vcc's jones matrix

        :param argin: the jones matrix JSON string
        """
        matrix = json.loads(argin)

        # Find the Jones matrix that applies to this VCC's DISH ID and store it
        jm_found = False

        # The Jones matrix schema allows for a set of receptors/dishes to be included.
        # Even though there will only be one entry for a VCC, there should still
        # be a list with a single entry so that the schema is followed.
        # Set up the Jones matrix to be a list.

        # Note: subarray has translated DISH IDs to VCC IDs in the JSON at this point
        list_of_entries = []
        for entry in matrix["jones_matrix"]:
            self._logger.debug(
                f"Received Jones matrix for VCC {entry['receptor']}"
            )
            if entry["receptor"] == self._vcc_id:
                self._logger.debug("Updating Jones Matrix for this VCC")
                list_of_entries.append(copy.deepcopy(entry))
                self._jones_matrix = json.dumps(
                    {"jones_matrix": list_of_entries}
                )
                jm_found = True
                break

        if not jm_found:
            log_msg = f"Jones matrix for VCC (DISH: {self._dish_id}) not found"
            self._logger.error(log_msg)
