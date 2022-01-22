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
from typing import Callable, Optional

import logging

from ska_mid_cbf_mcs.component.component_manager import (
    CommunicationStatus,
    CbfComponentManager,
)
from ska_tango_base.control_model import PowerMode

class FspCorrSubarrayComponentManager(CbfComponentManager):
    """A component manager for the FspCorrSubarray device."""

    def __init__(
        self: FspCorrSubarrayComponentManager,
        logger: logging.Logger,
        push_change_event: Optional[Callable],
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

        super().__init__(
            logger,
            push_change_event,
            communication_status_changed_callback,
            component_power_mode_changed_callback,
            None,
        )
    
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
    
    def stop_communicating(self: CbfComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False
        self.update_communication_status(CommunicationStatus.DISABLED)