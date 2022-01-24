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

from typing import List, Tuple

import logging
import json

# tango imports
import tango
from tango.server import BaseDevice, Device, run
from tango.server import attribute, command
from tango.server import device_property
from tango import DevFailed, DebugIt, DevState, AttrWriteType

# SKA Specific imports

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

from ska_tango_base.control_model import ObsState, SimulationMode
from ska_tango_base import SKAObsDevice, CspSubElementObsDevice
from ska_tango_base.commands import ResultCode

class VccComponentManager:
    """Component manager for Vcc class."""

    def __init__(
        self: VccComponentManager,
        simulation_mode: SimulationMode,
        vcc_id: int,
        vcc_band: List[str],
        search_window: List[str],
        logger: logging.Logger,
        connect: bool = True
    ) -> None:
        """
        Initialize a new instance.

        :param simulation_mode: simulation mode identifies if the real VCC HPS
                          applications or the simulator should be connected
        :param vcc_id: ID of VCC
        :param vcc_band: FQDNs of VCC band devices
        :param search_window: FQDNs of VCC search windows
        :param logger: a logger for this object to use
        :param connect: whether to connect automatically upon initialization
        """
        self._simulation_mode = simulation_mode

        self._vcc_id = vcc_id
        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self._logger = logger

        self.connected = False

        # initialize attribute values
        self._receptor_ID = 0
        self._freq_band_name = ""
        self._frequency_band = 0
        self._subarray_membership = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._doppler_phase_correction = (0, 
        0, 0, 0)
        self._rfi_flagging_mask = ""
        self._scfo_band_1 = 0
        self._scfo_band_2 = 0
        self._scfo_band_3 = 0
        self._scfo_band_4 = 0
        self._scfo_band_5a = 0
        self._scfo_band_5b = 0
        self._delay_model = [[0] * 6 for i in range(26)]
        self._jones_matrix = [[0] * 16 for i in range(26)]

        self._scan_id = ""
        self._config_id = ""

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


    def start_communicating(self: VccComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        if self.connected:
            self._logger.info("Already connected.")
            return
        
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


    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
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
    ) -> None:
        """
        Turn on the corresponding band device and disable all the others.

        :param freq_band_name: the frequency band name
        """
        for idx, band in enumerate(self._band_proxies):
            if idx == self._freq_band_index[freq_band_name]:
                band.On()
            else:
                band.Disable()


    def turn_off_band_device(
        self:VccComponentManager,
        freq_band_name: str
    ) -> None:
        """
        Send OFF signal to the corresponding band

        :param freq_band_name: the frequency band name
        """
        for idx, band in enumerate(self._band_proxies):
            if idx == self._freq_band_index[freq_band_name]:
                band.Off()


    def configure_search_window(
        self:VccComponentManager,
        argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure a search window by sending parameters from the input(JSON) to 
        SearchWindow device. This function is called by the subarray after the 
        configuration has already been validated, so the checks here have been 
        removed to reduce overhead.

        :param argin: JSON string with the search window parameters
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
                    self._logger.warn(log_msg)
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
                        if int(receptor["receptor_id"]) == self._receptor_ID:
                            # TODO: validate input
                            proxy_sw.tdcDestinationAddress = \
                                receptor["tdc_destination_address"]
                            break
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            (result_code, msg) = (ResultCode.FAILED, "Error configuring search window.")
        
        return (result_code, msg)
