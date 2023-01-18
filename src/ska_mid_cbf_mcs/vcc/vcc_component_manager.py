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
    def receptor_id(self: VccComponentManager) -> int:
        """
        Receptor ID

        :return: the receptor ID
        """
        return self._receptor_id

    @receptor_id.setter
    def receptor_id(self: VccComponentManager, receptor_id: int) -> None:
        """
        Set the receptor ID.

        :param receptor_id: Receptor ID
        """
        self._receptor_id = receptor_id

    @property
    def frequency_offset_k(self: VccComponentManager) -> int:
        """
        Frequency Offset K-value for this receptor

        :return: the frequency offset k-value
        """
        return self._frequency_offset_k

    @frequency_offset_k.setter
    def frequency_offset_k(
        self: VccComponentManager, frequency_offset_k: int
    ) -> None:
        """
        Set the frequency offset k-value.

        :param frequency_offset_k: Frequency offset k-value
        """
        self._frequency_offset_k = frequency_offset_k

    @property
    def frequency_offset_delta_f(self: VccComponentManager) -> int:
        """
        Frequency Offset Delta-F Value for this receptor

        :return: the frequency offset delta-f value
        """
        return self._frequency_offset_delta_f

    @frequency_offset_delta_f.setter
    def frequency_offset_delta_f(
        self: VccComponentManager, frequency_offset_delta_f: int
    ) -> None:
        """
        Set the frequency offset delta-f value.

        :param frequency_offset_delta_f: Frequency offset delta-f value
        """
        self._frequency_offset_delta_f = frequency_offset_delta_f

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
    def frequency_band_offset_stream_1(self: VccComponentManager) -> int:
        """
        Frequency Band Offset Stream 1

        :return: the frequency band offset for stream 1
        """
        return self._frequency_band_offset_stream_1

    @property
    def frequency_band_offset_stream_2(self: VccComponentManager) -> int:
        """
        Frequency Band Offset Stream 2

        :return: the frequency band offset for stream 2, this
                is only use when band 5 is active
        """
        return self._frequency_band_offset_stream_2

    @property
    def rfi_flagging_mask(self: VccComponentManager) -> str:
        """
        RFI Flagging Mask

        :return: the RFI flagging mask
        """
        return self._rfi_flagging_mask

    @property
    def jones_matrix(self: VccComponentManager) -> List[List[float]]:
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
        simulation_mode: SimulationMode = SimulationMode.TRUE,
    ) -> None:
        """
        Initialize a new instance.

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
            component fault
        :param simulation_mode: simulation mode identifies if the real VCC HPS
            applications or the simulator should be connected
        """
        self._logger = logger

        self._simulation_mode = simulation_mode

        self._talon_lru_fqdn = talon_lru
        self._vcc_controller_fqdn = vcc_controller
        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self.connected = False

        # Initialize attribute values
        self._receptor_id = 0
        self._frequency_offset_k = 0
        self._frequency_offset_delta_f = 0

        self._scan_id = 0
        self._config_id = ""

        self._frequency_band = 0
        self._freq_band_name = ""
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._rfi_flagging_mask = ""

        self._jones_matrix = [[0] * 16 for _ in range(26)]
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
            pdu1_power_mode = self._talon_lru_proxy.PDU1PowerMode
            pdu2_power_mode = self._talon_lru_proxy.PDU2PowerMode

            if (
                pdu1_power_mode == PowerMode.ON
                or pdu2_power_mode == PowerMode.ON
            ):
                return PowerMode.ON
            elif (
                pdu1_power_mode == PowerMode.OFF
                and pdu2_power_mode == PowerMode.OFF
            ):
                return PowerMode.OFF
            else:
                return PowerMode.UNKNOWN
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

            self._init_vcc_controller_parameters()
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            self.update_component_fault(True)
            return (ResultCode.FAILED, "Failed to connect to HPS VCC devices")

        self._logger.info("Completed VccComponentManager.on")
        self.update_component_power_mode(PowerMode.ON)
        return (ResultCode.OK, "On command completed OK")

    def _init_vcc_controller_parameters(self: VccComponentManager) -> None:
        """
        Initialize the set of parameters in the VCC Controller device that
        are common to all bands and will not change during scan configuration.
        """
        param_init = {
            "frequency_offset_k": self._frequency_offset_k,
            "frequency_offset_delta_f": self._frequency_offset_delta_f,
        }

        if self._simulation_mode:
            self._logger.info(
                "Initializing VCC Controller constant parameters"
            )
            self._vcc_controller_simulator.InitCommonParameters(
                json.dumps(param_init)
            )
        else:
            # Skip this if the device has already been initialized
            if self._vcc_controller_proxy.State() != tango.DevState.INIT:
                self._logger.info(
                    "VCC Controller parameters already initialized"
                )
                return

            self._logger.info(
                "Initializing VCC Controller constant parameters"
            )
            self._vcc_controller_proxy.InitCommonParameters(
                json.dumps(param_init)
            )

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
        self: VccComponentManager, freq_band_name: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure the corresponding band. At the HPS level, this reconfigures the
        FPGA to the correct bitstream and enables the respective band device. All
        other band devices are disabled.

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        (result_code, msg) = (ResultCode.OK, "ConfigureBand completed OK.")

        try:
            # Configure the band via the VCC Controller device
            self._logger.info(f"Configuring VCC band {freq_band_name}")
            self._frequency_band = freq_band_dict()[freq_band_name]
            self._freq_band_name = freq_band_name
            if self._simulation_mode:
                self._vcc_controller_simulator.ConfigureBand(
                    self._frequency_band
                )
            else:
                self._vcc_controller_proxy.ConfigureBand(self._frequency_band)

            # Set internal params for the configured band
            self._logger.info(
                f"Configuring internal parameters for VCC band {freq_band_name}"
            )

            internal_params_file_name = (
                VCC_PARAM_PATH
                + "internal_params_receptor"
                + str(self._receptor_id)
                + "_band"
                + freq_band_name
                + ".json"
            )
            self._logger.debug(
                f"Using parameters stored in {internal_params_file_name}"
            )

            with open(internal_params_file_name, "r") as f:
                json_string = f.read()
                idx = self._freq_band_index[self._freq_band_name]
                if self._simulation_mode:
                    self._band_simulators[idx].SetInternalParameters(
                        json_string
                    )
                else:
                    self._band_proxies[idx].SetInternalParameters(json_string)
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            self.update_component_fault(True)
            (result_code, msg) = (
                ResultCode.FAILED,
                "Failed to connect to HPS VCC devices",
            )
        except FileNotFoundError:
            self._logger.error(
                f"Could not find internal parameters file for \
                receptor {self._receptor_id}, band {freq_band_name}"
            )
            (result_code, msg) = (
                ResultCode.FAILED,
                "Invalid internal parameters file name",
            )

        return (result_code, msg)

    def deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self._doppler_phase_correction = [0 for _ in range(4)]
        self._jones_matrix = [[0] * 16 for _ in range(26)]
        self._delay_model = ""
        self._rfi_flagging_mask = ""
        self._frequency_band_offset_stream_2 = 0
        self._frequency_band_offset_stream_1 = 0
        self._stream_tuning = (0, 0)
        self._frequency_band = 0
        self._freq_band_name = ""
        self._config_id = ""
        self._scan_id = 0

        if self._simulation_mode:
            self._vcc_controller_simulator.Unconfigure()
        else:
            try:
                self._vcc_controller_proxy.Unconfigure()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self.update_component_fault(True)

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
        freq_band = freq_band_dict()[configuration["frequency_band"]]
        if self._frequency_band != freq_band:
            return (
                ResultCode.FAILED,
                f"Error in Vcc.ConfigureScan; scan configuration frequency band {freq_band} "
                + f"not the same as enabled band device {self._frequency_band}",
            )

        if self._frequency_band in [4, 5]:
            self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset_stream_1 = int(
            configuration["frequency_band_offset_stream_1"]
        )
        self._frequency_band_offset_stream_2 = int(
            configuration["frequency_band_offset_stream_2"]
        )

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
                self.update_component_fault(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
                )

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
                self.update_component_fault(True)
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
        self._logger.info("Edning scan")

        # Send the EndScan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self._simulation_mode:
            self._band_simulators[idx].EndScan()
        else:
            try:
                self._band_proxies[idx].EndScan()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self.update_component_fault(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
                )

        return (ResultCode.OK, "Vcc EndScanCommand completed OK")

    def abort(self):
        """Tell the current VCC band device to abort whatever it was doing."""
        idx = self._freq_band_index[self._freq_band_name]
        if self._simulation_mode:
            self._band_simulators[idx].Abort()
        else:
            try:
                self._band_proxies[idx].Abort()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self.update_component_fault(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
                )

        return (ResultCode.OK, "Vcc Abort command completed OK")

    def obsreset(self):
        """Reset the configuration."""
        idx = self._freq_band_index[self._freq_band_name]
        if self._simulation_mode:
            self._band_simulators[idx].ObsReset()
        else:
            try:
                self._band_proxies[idx].ObsReset()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                self.update_component_fault(True)
                return (
                    ResultCode.FAILED,
                    "Failed to connect to VCC band device",
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

        # variable to use as SW proxy
        proxy_sw = None
        # Configure searchWindowID.
        if int(argin["search_window_id"]) == 1:
            proxy_sw = self._sw_proxies[0]
        elif int(argin["search_window_id"]) == 2:
            proxy_sw = self._sw_proxies[1]

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
                    + self._frequency_band_offset_stream_1
                    + const.SEARCH_WINDOW_BW_HZ / 2
                    <= int(argin["search_window_tuning"])
                    <= stop_freq_Hz
                    + self._frequency_band_offset_stream_1
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
                    + self._frequency_band_offset_stream_1
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                    self._stream_tuning[0] * 10**9
                    + self._frequency_band_offset_stream_1
                    + const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                )

                frequency_band_range_2 = (
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream_2
                    - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                    self._stream_tuning[1] * 10**9
                    + self._frequency_band_offset_stream_2
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
                if argin["tdc_enable"]:
                    for receptor in argin["tdc_destination_address"]:
                        if receptor["receptor_id"] == self._receptor_id:
                            # TODO: validate input
                            proxy_sw.tdcDestinationAddress = receptor[
                                "tdc_destination_address"
                            ]
                            break

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
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

        for dopplerDetails in argin:
            if dopplerDetails["receptor"] == self._receptor_id:
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

        print(f"*****self._receptor_id: {self._receptor_id}")
        print(f"*****vcc_update_delay_model: {delay_model_obj}")

        # find the delay model that applies to this vcc's
        # receptor and store it
        for entry in delay_model_obj["delayModel"]:
            if entry["receptor"] == self._receptor_id:
                self._delay_model = json.dumps(
                    {"delayModel": (copy.deepcopy(entry))}
                )
                break

        print(f"*****self._delay_model: {self._delay_model}")

    def update_jones_matrix(self: VccComponentManager, argin: str) -> None:
        """
        Update Vcc's jones matrix

        :param argin: the jones matrix JSON string
        """
        argin = json.loads(argin)

        for receptor in argin:
            if receptor["receptor"] == self._receptor_id:
                for frequency_slice in receptor["receptorMatrix"]:
                    fs_id = frequency_slice["fsid"]
                    matrix = frequency_slice["matrix"]
                    if 1 <= fs_id <= 26:
                        if len(matrix) == 16:
                            self._jones_matrix[fs_id - 1] = matrix.copy()
                        else:
                            log_msg = (
                                f"'matrix' not valid for frequency slice {fs_id} "
                                + f" of receptor {self._receptor_id}"
                            )
                            self._logger.error(log_msg)
                    else:
                        log_msg = f"'fsid' {fs_id} not valid for receptor {self._receptor_id}"
                        self._logger.error(log_msg)
