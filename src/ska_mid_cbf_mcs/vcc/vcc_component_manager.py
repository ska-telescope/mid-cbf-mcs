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
from ska_tango_base import obs

# tango imports
import tango
from tango.server import BaseDevice, Device, run
from tango.server import attribute, command
from tango.server import device_property
from tango import DevFailed, DebugIt, DevState, AttrWriteType

# SKA Specific imports

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager, CommunicationStatus
)

from ska_tango_base.control_model import ObsState, SimulationMode, PowerMode
from ska_tango_base.csp.obs import CspObsComponentManager
from ska_tango_base.commands import ResultCode

__all__ = ["VccComponentManager"]


class VccComponentManager(CbfComponentManager, CspObsComponentManager):
    """Component manager for Vcc class."""

    def __init__(
        self: VccComponentManager,
        simulation_mode: SimulationMode,
        vcc_band: List[str],
        search_window: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        connect: bool = True
    ) -> None:
        """
        Initialize a new instance.

        :param simulation_mode: simulation mode identifies if the real VCC HPS
                          applications or the simulator should be connected
        :param vcc_band: FQDNs of VCC band devices
        :param search_window: FQDNs of VCC search windows
        :param logger: a logger for this object to use
        :param connect: whether to connect automatically upon initialization
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        """
        self._simulation_mode = simulation_mode

        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self._logger = logger

        self.connected = False

        # initialize attribute values
        self.receptor_id = 0

        self.frequency_band = 0
        self.stream_tuning = (0, 0)
        self.frequency_band_offset_stream_1 = 0
        self.frequency_band_offset_stream_2 = 0
        self.rfi_flagging_mask = ""
        self.scfo_band_1 = 0
        self.scfo_band_2 = 0
        self.scfo_band_3 = 0
        self.scfo_band_4 = 0
        self.scfo_band_5a = 0
        self.scfo_band_5b = 0

        # initialize list of band proxies and band -> index translation;
        # entry for each of: band 1 & 2, band 3, band 4, band 5
        self._band_proxies = []
        self._freq_band_index = dict(zip(
            freq_band_dict().keys(), 
            [0, 0, 1, 2, 3, 3]
        ))

        self._sw_proxies = []

        if connect:
            self.start_communicating()

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=None,
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
                raise ConnectionError(
                    f"Error in proxy connection."
                ) from dev_failed

        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)


    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()

        self.connected = False


    @property
    def simulation_mode(self: VccComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode


    def turn_on_band_device(
        self: VccComponentManager,
        freq_band_name: str
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the corresponding band device and disable all the others.

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "VccComponentManager.turn_on_band_device(" + freq_band_name + ")"
        )
        (result_code, msg) = (ResultCode.OK, "TurnOnBandDevice completed OK.")
        try:
            for idx, band in enumerate(self._band_proxies):
                if idx == self._freq_band_index[freq_band_name]:
                    self._logger.debug(f"Turning on band device index {idx}")
                    band.On()
                else:
                    self._logger.debug(f"Disabling band device index {idx}")
                    band.Disable()
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            (result_code, msg) = (ResultCode.FAILED, "TurnOnBandDevice failed.")
        return (result_code, msg)


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
        (result_code, msg) = (ResultCode.OK, "TurnOffBandDevice completed OK.")
        try:
            for idx, band in enumerate(self._band_proxies):
                if idx == self._freq_band_index[freq_band_name]:
                    self._logger.debug(f"Turning off band device index {idx}")
                    band.Off()
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            (result_code, msg) = (ResultCode.FAILED, "TurnOffBandDevice failed.")
        return (result_code, msg)


    def deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self.frequency_band_offset_stream_2 = 0
        self.frequency_band_offset_stream_1 = 0
        self.stream_tuning = (0, 0)
        self.frequency_band = 0
        self.config_id = ""
        self.scan_id = 0
        self.scfo_band_5b = 0
        self.scfo_band_5a = 0
        self.scfo_band_4 = 0
        self.scfo_band_3 = 0
        self.scfo_band_2 = 0
        self.scfo_band_1 = 0
        self.rfi_flagging_mask = ""

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
        self.config_id = configuration["config_id"]

        # TODO: The frequency band attribute is optional but 
        # if not specified the previous frequency band set should be used 
        # (see Mid.CBF Scan Configuration in ICD). Therefore, the previous frequency 
        # band value needs to be stored, and if the frequency band is not
        # set in the config it should be replaced with the previous value.
        self.frequency_band = freq_band_dict()[configuration["frequency_band"]]
        self.frequency_band = freq_band_dict()[configuration["frequency_band"]]
        self._freq_band_name = configuration["frequency_band"]
        if self.frequency_band in [4, 5]:
                self.stream_tuning = \
                    configuration["band_5_tuning"]

        self.frequency_band_offset_stream_1 = \
            int(configuration["frequency_band_offset_stream_1"])
        self.frequency_band_offset_stream_2 = \
            int(configuration["frequency_band_offset_stream_2"])
        
        if "rfi_flagging_mask" in configuration:
            self.rfi_flagging_mask = str(configuration["rfi_flagging_mask"])
        else:
            self._logger.warn("'rfiFlaggingMask' not given. Proceeding.")

        if "scfo_band_1" in configuration:
            self.scfo_band_1 = int(configuration["scfo_band_1"])
        else:
            self.scfo_band_1 = 0
            self._logger.warn("'scfoBand1' not specified. Defaulting to 0.")

        if "scfo_band_2" in configuration:
            self.scfo_band_2 = int(configuration["scfo_band_2"])
        else:
            self.scfo_band_2 = 0
            self._logger.warn("'scfoBand2' not specified. Defaulting to 0.")

        if "scfo_band_3" in configuration:
            self.scfo_band_3 = int(configuration["scfo_band_3"])
        else:
            self.scfo_band_3 = 0
            self._logger.warn("'scfoBand3' not specified. Defaulting to 0.")

        if "scfo_band_4" in configuration:
            self.scfo_band_4 = configuration["scfo_band_4"]
        else:
            self.scfo_band_4 = 0
            self._logger.warn("'scfoBand4' not specified. Defaulting to 0.")

        if "scfo_band_5a" in configuration:
            self.scfo_band_5a = int(configuration["scfo_band_5a"])
        else:
            self.scfo_band_5a = 0
            self._logger.warn("'scfoBand5a' not specified. Defaulting to 0.")

        if "scfo_band_5b" in configuration:
            self.scfo_band_5b = int(configuration["scfo_band_5b"])
        else:
            self.scfo_band_5b = 0
            self._logger.warn("'scfoBand5b' not specified. Defaulting to 0.")

        return (ResultCode.OK, "Vcc ScanCommand completed OK")

    def scan(self: VccComponentManager, scan_id: int) -> Tuple[ResultCode, str]:

        """
        Begin scan operation.

        :param argin: scan ID integer

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        self.scan_id = scan_id
        return (ResultCode.STARTED, "Vcc ScanCommand completed OK")

    def end_scan(self: VccComponentManager) -> Tuple[ResultCode, str]:

        """
        End scan operation.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        return (ResultCode.OK, "Vcc EndScanCommand completed OK")


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
            if self.frequency_band in list(range(4)):  # frequency band is not band 5
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ
                ][self.frequency_band]

                if start_freq_Hz + self.frequency_band_offset_stream_1 + \
                        const.SEARCH_WINDOW_BW_HZ / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        stop_freq_Hz + self.frequency_band_offset_stream_1 - \
                        const.SEARCH_WINDOW_BW_HZ / 2:
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
                    self._logger.warn(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                frequency_band_range_1 = (
                    self.stream_tuning[0] * 10 ** 9 + self.frequency_band_offset_stream_1 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self.stream_tuning[0] * 10 ** 9 + self.frequency_band_offset_stream_1 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                frequency_band_range_2 = (
                    self.stream_tuning[1] * 10 ** 9 + self.frequency_band_offset_stream_2 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self.stream_tuning[1] * 10 ** 9 + self.frequency_band_offset_stream_2 + \
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
                    self._logger.warn(log_msg)

                # Configure tdcEnable.
                proxy_sw.tdcEnable = argin["tdc_enable"]
                if argin["tdc_enable"]:
                    proxy_sw.On()
                else:
                    proxy_sw.Disable()

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
                    self._logger.warn(log_msg)

                # Configure tdcPeriodAfterEpoch.
                if "tdc_period_after_epoch" in argin:
                    proxy_sw.tdcPeriodAfterEpoch = int(argin["tdc_period_after_epoch"])
                else:
                    proxy_sw.tdcPeriodAfterEpoch = 22
                    log_msg = "Search window specified, but 'tdcPeriodAfterEpoch' not given. " \
                            "Defaulting to 22."
                    self._logger.warn(log_msg)

                # Configure tdcDestinationAddress.
                if argin["tdc_enable"]:
                    for receptor in argin["tdc_destination_address"]:
                        if receptor["receptor_id"] == self.receptor_id:
                            # TODO: validate input
                            proxy_sw.tdcDestinationAddress = \
                                receptor["tdc_destination_address"]
                            break

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            (result_code, msg) = (ResultCode.FAILED, "Error configuring search window.")

        return (result_code, msg)
