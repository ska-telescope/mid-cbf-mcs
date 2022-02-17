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

class FspPstSubarrayComponentManager(CbfComponentManager, CspObsComponentManager):
    """A component manager for the FspPstSubarray device."""

    def __init__(
        self: FspPstSubarrayComponentManager,
        logger: logging.Logger,
        fsp_id: int,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param cbf_controller_address: address of the cbf controller device
        :param vcc_fqdns_all: list of all vcc fqdns
        :param subarray_id: the id indicating the subarray membership 
            of the fsp pss subarray device
        :param fsp_id: the id of the corresponding fsp device
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

        self._fsp_id = fsp_id
        self._receptors = []
        self._timing_beams = []
        self._timing_beam_id = []
        self._scan_id = 0
        self._output_enable = 0


        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None
        )
    
    @property
    def fsp_id(self: FspPstSubarrayComponentManager) -> int:
        """
        Fsp ID

        :return: the fsp id
        :rtype: int
        """
        return self._fsp_id
    
    @property
    def timing_beams(self: FspPstSubarrayComponentManager) -> List[str]:
        """
        Timing Beams

        :return: the timing beams
        :rtype: List[str]
        """
        return self._timing_beams
    
    @property
    def timing_beam_id(self: FspPstSubarrayComponentManager) -> List[int]:
        """
        Timing Beam ID

        :return: list of timing beam ids
        :rtype: List[int]
        """
        return self._timing_beam_id
    
    @property
    def receptors(self: FspPstSubarrayComponentManager) -> List[int]:
        """
        Receptors

        :return: list of receptor ids
        :rtype: List[int]
        """
        return self._receptors
    
    @property
    def scan_id(self: FspPstSubarrayComponentManager) -> int:
        """
        Scan ID

        :return: the scan id
        :rtype: int
        """
        return self._scan_id
    
    @property
    def output_enable(self: FspPstSubarrayComponentManager) -> bool:
        """
        Output Enable

        :return: output enable
        :rtype: bool
        """
        return self._output_enable
    
    def start_communicating(
        self: FspPstSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)
    
    def stop_communicating(self: FspPstSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False
    
    def _add_receptors(
        self: FspPstSubarrayComponentManager, 
        argin: List[int]
        ) -> None:
        """
        Add specified receptors to the subarray.

        :param argin: ids of receptors to add. 
        """
        errs = []  # list of error messages
        for receptorID in argin:
            try:
                if receptorID not in self._receptors:
                    self._receptors.append(receptorID)
                else:
                    log_msg = "Receptor {} already assigned to current FSP subarray.".format(
                        str(receptorID))
                    self._logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self._logger.error(msg)
    
    def _remove_receptors(
        self: FspPstSubarrayComponentManager, 
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
    
    def _remove_all_receptors(self: FspPstSubarrayComponentManager) -> None:
        """ Remove all receptors from the subarray."""
        self._remove_receptors(self._receptors[:])
    
    def validate_input(
        self: FspPstSubarrayComponentManager, 
        configuration: str
    ) -> Tuple[ResultCode, str]:
            """
            Validate the configuration parameters against allowed values, as needed.

            :param configuration: The JSON formatted string with configuration for the device.
            :type configuration: 'DevString'
            :return: A tuple containing a return code and a string message.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return (ResultCode.OK, "ConfigureScan arguments validation successfull") 
    
    def configure_scan(
        self: FspPstSubarrayComponentManager,
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

        #TODO: call validate input with self.validate_input 

        if self._fsp_id != configuration["fsp_id"]:
            self._logger.warning(
                "The Fsp ID from ConfigureScan {} does not equal the Fsp ID from the self properties {}"
                .format(self._fsp_id, configuration["fsp_id"]))

        self._fsp_id = configuration["fsp_id"]
        self._timing_beams = []
        self._timing_beam_id = []
        self._receptors = []

        for timingBeam in configuration["timing_beam"]:
            self._add_receptors(map(int, timingBeam["receptor_ids"]))
            self._timing_beams.append(json.dumps(timingBeam))
            self._timing_beam_id.append(int(timingBeam["timing_beam_id"])) 

        return (ResultCode.OK, "FspPstSubarray ConfigureScan command completed OK")
    
    def scan(
        self: FspPstSubarrayComponentManager,
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

        return (ResultCode.OK, "FspPstSubarray Scan command completed OK")
    
    def end_scan(
        self: FspPstSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the EndScan() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        return (ResultCode.OK, "FspPstSubarray EndScan command completed OK")
    
    def go_to_idle(
        self: FspPstSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the GoToIdle() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self._timing_beams = []
        self._timing_beam_id = []
        self._output_enable = 0
        self._remove_all_receptors()
        
        return (ResultCode.OK, "FspPstSubarray GoToIdle command completed OK")
    
   