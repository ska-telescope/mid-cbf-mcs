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
    
    def start_communicating(
        self: FspPssSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)
    
    def stop_communicating(self: FspPssSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False
    
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