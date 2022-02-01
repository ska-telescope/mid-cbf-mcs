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
from typing import Callable, Optional, Tuple, List

import logging
import json

import tango

from ska_mid_cbf_mcs.component.component_manager import (
    CommunicationStatus,
    CbfComponentManager,
)
from ska_tango_base.control_model import PowerMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

class FspPssSubarrayComponentManager(CbfComponentManager, CspObsComponentManager):
    """A component manager for the FspPssSubarray device."""

    def __init__(
        self: FspPssSubarrayComponentManager,
        logger: logging.Logger,
        cbf_controller_address: str,
        vcc_fqdns_all: List[str],
        subarray_id: int,
        fsp_id: int,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
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
        """
        self._logger = logger
        
        self._connected = False

        self._scan_id = 0
        self._output_enable = 0
        self._config_id = ""
        self._fsp_id = fsp_id
        self._subarray_id = subarray_id
        self._search_beams = []
        self._receptors = []
        self._search_beam_id = []
        self._cbf_controller_address = cbf_controller_address
        self._vcc_fqdns_all = vcc_fqdns_all
        self._proxy_cbf_controller = None
        self._proxies_vcc = None

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=None,
            obs_state_model=None
        )
    
    @property
    def scan_id(self: FspPssSubarrayComponentManager) -> int:
        """
        Scan ID

        :return: the scan id
        :rtype: int
        """
        return self._scan_id
    
    @property
    def config_id(self: FspPssSubarrayComponentManager) -> str:
        """
        Config ID

        :return: the config id
        :rtype: str
        """
        return self._config_id
    
    @property
    def fsp_id(self: FspPssSubarrayComponentManager) -> int:
        """
        Fsp ID

        :return: the fsp id
        :rtype: int
        """
        return self._fsp_id
    
    @property
    def search_window_id(self: FspPssSubarrayComponentManager) -> List[int]:
        """
        Search Window ID

        :return: the search window id
        :rtype: List[int]
        """
        return self._search_window_id
    
    @property
    def search_beams(self: FspPssSubarrayComponentManager) -> List[str]:
        """
        Search Beams

        :return: search beams
        :rtype: List[str]
        """
        return self._search_beams
    
    @property
    def search_beam_id(self: FspPssSubarrayComponentManager) -> List[int]:
        """
        Search Beam ID

        :return: search beam id
        :rtype: List[int]
        """
        return self._search_beam_id
    
    @property
    def output_enable(self: FspPssSubarrayComponentManager) -> bool:
        """
        Output Enable

        :return: output enable
        :rtype: bool
        """
        return self._output_enable
    
    def start_communicating(
        self: FspPssSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._proxy_cbf_controller = CbfDeviceProxy(
            fqdn=self._cbf_controller_address,
            logger=self._logger
        )
        self._controller_max_capabilities = dict(
            pair.split(":") for pair in 
            self._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
        )

        self._count_vcc = int(self._controller_max_capabilities["VCC"])
        self._fqdn_vcc = list(self._vcc_fqdns_all)[:self._count_vcc]
        self._proxies_vcc = [
            CbfDeviceProxy(
                logger=self._logger, 
                fqdn=address) for address in self._fqdn_vcc
        ]

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)
    
    def stop_communicating(self: FspPssSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False
    
    def _add_receptors(
        self: FspPssSubarrayComponentManager, 
        argin: List[int]
        ) -> None:
        """
            Add specified receptors to the subarray.

            :param argin: ids of receptors to add. 
        """
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                subarrayID = self._proxies_vcc[vccID - 1].subarrayMembership

                # only add receptor if it belongs to the CBF subarray
                if subarrayID != self._subarray_id:
                    errs.append("Receptor {} does not belong to subarray {}.".format(
                        str(receptorID), str(self._subarray_id)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)
                    else:
                        # TODO: this is not true if more receptors can be 
                        #       specified for the same search beam
                        log_msg = "Receptor {} already assigned to current FSP subarray.".format(
                            str(receptorID))
                        self._logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self._logger.error(msg)
    
    def _remove_receptors(
        self: FspPssSubarrayComponentManager, 
        argin: List[int]
        )-> None:
        """
            Remove specified receptors from the subarray.

            :param argin: ids of receptors to remove. 
        """

        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self._logger.warn(log_msg)
    
    def _remove_all_receptors(self: FspPssSubarrayComponentManager) -> None:
        """ Remove all receptors from the subarray."""
        self._remove_receptors(self._receptors[:])
    
    def configure_scan(
        self: FspPssSubarrayComponentManager,
        configuration: str
    ) -> Tuple[ResultCode, str]:
        """
        Performs the ConfigureScan() command functionality

        :param configuration: The configuration as JSON formatted string 
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        
        configuration = json.loads(configuration)


        # TODO: Why are we overwriting the device property fsp ID
        #       with the argument in the ConfigureScan json file
        if self._fsp_id != configuration["fsp_id"]:
            self._logger.warning(
                "The Fsp ID from ConfigureScan {} does not equal the Fsp ID from the device properties {}"
                .format(self._fsp_id, configuration["fsp_id"]))
        self._fsp_id = configuration["fsp_id"]
        self._search_window_id = int(configuration["search_window_id"])

        for searchBeam in configuration["search_beam"]:

            if len(searchBeam["receptor_ids"]) != 1:
                # TODO - to add support for multiple receptors
                msg = "Currently only 1 receptor per searchBeam is supported"
                self._logger.error(msg) 
                return (ResultCode.FAILED, msg)

            self._add_receptors(map(int, searchBeam["receptor_ids"]))
            self._search_beams.append(json.dumps(searchBeam))
            self._search_beam_id.append(int(searchBeam["search_beam_id"]))

        return (ResultCode.OK, "FspPssSubarray ConfigureScan command completed OK")
    
    def scan(
        self: FspPssSubarrayComponentManager,
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

        return (ResultCode.OK, "FspPssSubarray Scan command completed OK")
    
    def end_scan(
        self: FspPssSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the EndScan() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        return (ResultCode.OK, "FspPssSubarray EndScan command completed OK")
    
    def go_to_idle(
        self: FspPssSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the GoToIdle() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self._search_beams = []
        self._search_window_id = 0
        self._search_beam_id = []
        self._output_enable = 0
        self._scan_id = 0
        self._config_id = ""

        self._remove_all_receptors()
        
        return (ResultCode.OK, "FspPssSubarray GoToIdle command completed OK")