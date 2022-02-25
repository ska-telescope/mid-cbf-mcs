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

from typing import List, Tuple, Callable, Optional

import logging
import json
from pyrsistent import v

# tango imports
import tango
from tango import DevState

# SKA Specific imports

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager, CommunicationStatus
)

from ska_tango_base.control_model import SimulationMode, PowerMode
from ska_tango_base.csp.obs import CspObsComponentManager
from ska_tango_base.commands import ResultCode

__all__ = ["VccComponentManager"]


class VccComponentManager(CbfComponentManager, CspObsComponentManager):
    """Component manager for Vcc class."""

    @property
    def config_id(self: VccComponentManager) -> str:
        """Return the configuration id."""
        return self._config_id

    @config_id.setter
    def config_id(self: VccComponentManager, config_id: str):
        """Set the configuration ID."""
        self._config_id = config_id

    @property
    def scan_id(self: VccComponentManager) -> int:
        """Return the scan id."""
        return self._scan_id

    @scan_id.setter
    def scan_id(self: VccComponentManager, scan_id: int) -> None:
        """Set the scan ID."""
        self._scan_id = scan_id

    @property
    def receptor_id(self: VccComponentManager) -> int:
        return self._receptor_id

    @receptor_id.setter
    def receptor_id(self, receptor_id: int):
        """Set the receptor ID."""
        self._receptor_id = receptor_id

    @property
    def frequency_band(self: VccComponentManager) -> Optional[int]:
        return self._frequency_band

    @property
    def stream_tuning(self: VccComponentManager) -> Tuple[int]:
        return self._stream_tuning

    @property
    def frequency_band_offset_stream_1(self: VccComponentManager) -> int:
        return self._frequency_band_offset_stream_1

    @property
    def frequency_band_offset_stream_2(self: VccComponentManager) -> int:
        return self._frequency_band_offset_stream_2

    @property
    def rfi_flagging_mask(self: VccComponentManager) -> str:
        return self._rfi_flagging_mask

    @property
    def scfo_band_1(self: VccComponentManager) -> int:
        return self._scfo_band_1

    @property
    def scfo_band_2(self: VccComponentManager) -> int:
        return self._scfo_band_2

    @property
    def scfo_band_3(self: VccComponentManager) -> int:
        return self._scfo_band_3

    @property
    def scfo_band_4(self: VccComponentManager) -> int:
        return self._scfo_band_4

    @property
    def scfo_band_5a(self: VccComponentManager) -> int:
        return self._scfo_band_5a

    @property
    def scfo_band_5b(self: VccComponentManager) -> int:
        return self._scfo_band_5b

    @property
    def jones_matrix(self: VccComponentManager) -> List[List[float]]:
        return self._jones_matrix

    @property
    def delay_model(self: VccComponentManager) -> List[List[float]]:
        return self._delay_model

    @property
    def doppler_phase_correction(self: VccComponentManager) -> List[float]:
        return self._doppler_phase_correction


    def __init__(
        self: VccComponentManager,
        simulation_mode: SimulationMode,
        vcc_band: List[str],
        search_window: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable
    ) -> None:
        """
        Initialize a new instance.

        :param simulation_mode: simulation mode identifies if the real VCC HPS
                          applications or the simulator should be connected
        :param vcc_band: FQDNs of VCC band devices
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
        """
        self._logger = logger

        self._simulation_mode = simulation_mode

        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self.connected = False

        # initialize attribute values
        self._receptor_id = 0

        self._scan_id = 0
        self._config_id = ""

        self._frequency_band = None
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._rfi_flagging_mask = ""
        self._scfo_band_1 = 0
        self._scfo_band_2 = 0
        self._scfo_band_3 = 0
        self._scfo_band_4 = 0
        self._scfo_band_5a = 0
        self._scfo_band_5b = 0

        self._jones_matrix = [[0] * 16 for _ in range(26)]
        self._delay_model = [[0] * 6 for _ in range(26)]
        self._doppler_phase_correction = [0 for _ in range(4)]

        # initialize list of band proxies and band -> index translation;
        # entry for each of: band 1 & 2, band 3, band 4, band 5
        self._band_proxies = []
        self._freq_band_index = dict(zip(
            freq_band_dict().keys(), 
            [0, 0, 1, 2, 3, 3]
        ))

        self._sw_proxies = []

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None
        )


    def start_communicating(self: VccComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        if self.connected:
            self._logger.info("Already connected.")
            return

        super().start_communicating()

        if not self._simulation_mode:
            try:
                self._band_proxies = [CbfDeviceProxy(fqdn=fqdn, logger=self._logger
                    ) for fqdn in self._vcc_band_fqdn]
                self._sw_proxies = [CbfDeviceProxy(fqdn=fqdn, logger=self._logger
                ) for fqdn in self._search_window_fqdn]

            except tango.DevFailed as dev_failed:
                self.update_component_power_mode(PowerMode.UNKNOWN)
                self.update_communication_status(CommunicationStatus.NOT_ESTABLISHED)
                self.update_component_fault(True)
                raise ConnectionError(
                    f"Error in proxy connection."
                ) from dev_failed

        self.connected = True
        self.update_component_power_mode(PowerMode.ON)
        self.update_communication_status(CommunicationStatus.ESTABLISHED)


    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False


    @property
    def simulation_mode(self: VccComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode


    def on(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn on VCC component; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
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


    def turn_on_band_device(
        self: VccComponentManager,
        freq_band_name: str
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the corresponding band device and turn off all the others.

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "VccComponentManager.turn_on_band_device(" + freq_band_name + ")"
        )
        self._frequency_band = freq_band_dict()[freq_band_name]
        self._logger.info("VCC assigned frequency band: " + freq_band_name)
        try:
            for idx, band in enumerate(self._band_proxies):
                self._logger.debug(self._vcc_band_fqdn[idx] + f" state: {band.state()}")
                if idx == self._freq_band_index[freq_band_name] and (
                    band.state() == DevState.DISABLE or band.state() == DevState.OFF):
                    band.On()
                elif band.state() == DevState.DISABLE or band.state() == DevState.ON:
                    band.Off()
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            return (ResultCode.FAILED, "TurnOnBandDevice failed.")
        return (ResultCode.OK, "TurnOnBandDevice completed OK.")


    def turn_off_band_device(
        self:VccComponentManager,
        freq_band_name: str
    ) -> Tuple[ResultCode, str]:
        """
        Send OFF signal to the corresponding band

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "VccComponentManager.turn_off_band_device(" + freq_band_name + ")"
        )
        self._frequency_band = None
        self._logger.info("VCC frequency band unassigned")
        try:
            for idx, band in enumerate(self._band_proxies):
                self._logger.debug(self._vcc_band_fqdn[idx] + f" state: {band.state()}")
                if idx == self._freq_band_index[freq_band_name] and (
                    band.state() == DevState.ON or band.state() == DevState.DISABLE):
                    band.Off()
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            return (ResultCode.FAILED, "TurnOffBandDevice failed.")
        return (ResultCode.OK, "TurnOffBandDevice completed OK.")


    def deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self._doppler_phase_correction = [0 for _ in range(4)]
        self._jones_matrix = [[0] * 16 for _ in range(26)]
        self._delay_model = [[0] * 6 for _ in range(26)]
        self._rfi_flagging_mask = ""
        self._scfo_band_5b = 0
        self._scfo_band_5a = 0
        self._scfo_band_4 = 0
        self._scfo_band_3 = 0
        self._scfo_band_2 = 0
        self._scfo_band_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._frequency_band_offset_stream_1 = 0
        self._stream_tuning = (0, 0)
        self._config_id = ""
        self._scan_id = 0

    def configure_scan(self: VccComponentManager, argin: str) -> Tuple[ResultCode, str]:

        """
        Begin scan operation.

        :param argin: JSON string with the search window parameters

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
                f"Error in Vcc.ConfigureScan; scan configuration frequency band {freq_band} " + \
                f"not the same as enabled band device {self._frequency_band}"
            )
        self._freq_band_name = configuration["frequency_band"]
        if self._frequency_band in [4, 5]:
                self._stream_tuning = \
                    configuration["band_5_tuning"]

        self._frequency_band_offset_stream_1 = \
            int(configuration["frequency_band_offset_stream_1"])
        self._frequency_band_offset_stream_2 = \
            int(configuration["frequency_band_offset_stream_2"])
        
        if "rfi_flagging_mask" in configuration:
            self._rfi_flagging_mask = str(configuration["rfi_flagging_mask"])
        else:
            self._logger.warning("'rfiFlaggingMask' not given. Proceeding.")

        if "scfo_band_1" in configuration:
            self._scfo_band_1 = int(configuration["scfo_band_1"])
        else:
            self._scfo_band_1 = 0
            self._logger.warning("'scfoBand1' not specified. Defaulting to 0.")

        if "scfo_band_2" in configuration:
            self._scfo_band_2 = int(configuration["scfo_band_2"])
        else:
            self._scfo_band_2 = 0
            self._logger.warning("'scfoBand2' not specified. Defaulting to 0.")

        if "scfo_band_3" in configuration:
            self._scfo_band_3 = int(configuration["scfo_band_3"])
        else:
            self._scfo_band_3 = 0
            self._logger.warning("'scfoBand3' not specified. Defaulting to 0.")

        if "scfo_band_4" in configuration:
            self._scfo_band_4 = configuration["scfo_band_4"]
        else:
            self._scfo_band_4 = 0
            self._logger.warning("'scfoBand4' not specified. Defaulting to 0.")

        if "scfo_band_5a" in configuration:
            self._scfo_band_5a = int(configuration["scfo_band_5a"])
        else:
            self._scfo_band_5a = 0
            self._logger.warning("'scfoBand5a' not specified. Defaulting to 0.")

        if "scfo_band_5b" in configuration:
            self._scfo_band_5b = int(configuration["scfo_band_5b"])
        else:
            self._scfo_band_5b = 0
            self._logger.warning("'scfoBand5b' not specified. Defaulting to 0.")

        return (ResultCode.OK, "Vcc ConfigureScan command completed OK")

    def scan(self: VccComponentManager, scan_id: int) -> Tuple[ResultCode, str]:

        """
        Begin scan operation.

        :param argin: scan ID integer

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        self._scan_id = scan_id
        return (ResultCode.STARTED, "Vcc Scan command completed OK")

    def end_scan(self: VccComponentManager) -> Tuple[ResultCode, str]:

        """
        End scan operation.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        return (ResultCode.OK, "Vcc EndScan command completed OK")


    def configure_search_window(
        self:VccComponentManager,
        argin: str
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
        msg = "ConfigureSearchWindwo completed OK"

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
            if self._frequency_band in list(range(4)):  # frequency band is not band 5
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ
                ][self._frequency_band]

                if start_freq_Hz + self._frequency_band_offset_stream_1 + \
                        const.SEARCH_WINDOW_BW_HZ / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        stop_freq_Hz + self._frequency_band_offset_stream_1 - \
                        const.SEARCH_WINDOW_BW_HZ / 2:
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
                    self._logger.warning(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                frequency_band_range_1 = (
                    self._stream_tuning[0] * 10 ** 9 + self._frequency_band_offset_stream_1 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self._stream_tuning[0] * 10 ** 9 + self._frequency_band_offset_stream_1 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                frequency_band_range_2 = (
                    self._stream_tuning[1] * 10 ** 9 + self._frequency_band_offset_stream_2 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self._stream_tuning[1] * 10 ** 9 + self._frequency_band_offset_stream_2 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                if (frequency_band_range_1[0] + \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                    int(argin["search_window_tuning"]) <= \
                    frequency_band_range_1[1] - \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2) or \
                        (frequency_band_range_2[0] + \
                        const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        frequency_band_range_2[1] - \
                        const.SEARCH_WINDOW_BW * 10 ** 6 / 2):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
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
                    proxy_sw.tdcPeriodBeforeEpoch = int(argin["tdc_period_before_epoch"])
                else:
                    proxy_sw.tdcPeriodBeforeEpoch = 2
                    log_msg = "Search window specified, but 'tdcPeriodBeforeEpoch' not given. " \
                            "Defaulting to 2."
                    self._logger.warning(log_msg)

                # Configure tdcPeriodAfterEpoch.
                if "tdc_period_after_epoch" in argin:
                    proxy_sw.tdcPeriodAfterEpoch = int(argin["tdc_period_after_epoch"])
                else:
                    proxy_sw.tdcPeriodAfterEpoch = 22
                    log_msg = "Search window specified, but 'tdcPeriodAfterEpoch' not given. " \
                            "Defaulting to 22."
                    self._logger.warning(log_msg)

                # Configure tdcDestinationAddress.
                if argin["tdc_enable"]:
                    for receptor in argin["tdc_destination_address"]:
                        if receptor["receptor_id"] == self._receptor_id:
                            # TODO: validate input
                            proxy_sw.tdcDestinationAddress = \
                                receptor["tdc_destination_address"]
                            break

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            (result_code, msg) = (ResultCode.FAILED, "Error configuring search window.")

        return (result_code, msg)


    def update_doppler_phase_correction(self: VccComponentManager, argin: str) -> None:
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
        argin = json.loads(argin)

        for delayDetails in argin:
            if delayDetails["receptor"] == self._receptor_id:
                for frequency_slice in delayDetails["receptorDelayDetails"]:
                    fsid = frequency_slice["fsid"]
                    coeff = frequency_slice["delayCoeff"]
                    if 1 <= fsid <= 26:
                        if len(coeff) == 6:
                            self._delay_model[fsid - 1] = coeff.copy()
                        else:
                            log_msg = "'delayCoeff' not valid for frequency slice " + \
                                f"{fsid} of receptor {self._receptor_id}"
                            self._logger.error(log_msg)
                    else:
                        log_msg = f"'fsid' {fsid} not valid for receptor {self._receptor_id}"
                        self._logger.error(log_msg)


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
                            self._jones_matrix[fs_id-1] = matrix.copy()
                        else:
                            log_msg = f"'matrix' not valid for frequency slice {fs_id} " + \
                                        f" of receptor {self._receptor_id}"
                            self._logger.error(log_msg)
                    else:
                        log_msg = f"'fsid' {fs_id} not valid for receptor {self._receptor_id}"
                        self._logger.error(log_msg)
