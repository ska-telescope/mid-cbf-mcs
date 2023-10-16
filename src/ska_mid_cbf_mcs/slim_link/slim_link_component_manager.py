# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, Tuple

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode
from tango import AttrQuality

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

NUM_COUNTERS = 7
NUM_REG_COUNTERS_RX = 4
NUM_COUNTERS_TX = 3
BLOCK_LOST_COUNT_INDEX = 4
CDR_LOST_COUNT_INDEX = 5
NUM_LOST_COUNTERS = 2


class SlimLinkComponentManager(CbfComponentManager):
    """
    A component manager for a slim link.
    """
    
    @property
    def tx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the tx device the link is associated with.

        :return: the tx device name
        """
        return self._tx_device_name

    @tx_device_name.setter
    def tx_device_name(
        self: SlimLinkComponentManager, tx_device_name: str
    ) -> None:
        """
        Set the tx device name value.

        :param tx_device_name: The tx device name
        """
        self._tx_device_name = tx_device_name

    @property
    def rx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the rx device the link is associated with.

        :return: the rx device name
        """
        return self._rx_device_name

    @rx_device_name.setter
    def rx_device_name(
        self: SlimLinkComponentManager, rx_device_name: str
    ) -> None:
        """
        Set the rx device name value.

        :param rx_device_name: The rx device name
        """
        self._rx_device_name = rx_device_name


    def __init__(
        self:SlimLinkComponentManager,
        tx_device_name: str,
        rx_device_name: str,
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialize a new instance.

        :param tx_device_name: a string containing the tx device's fqdn
        :param rx_device_name: a string containing the rx device's fqdn
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        
        self._logger.debug("SLIMLink  -  initDevice()  - " + self._device_name)
        
        self.connected = False
        
        self._tx_device_name = tx_device_name
        self._rx_device_name = rx_device_name
        
        self._tx_device_proxy = None
        self._rx_device_proxy = None
        
        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )
        
        self._logger.info(f"Linking {tx_device_name} to {rx_device_name}")


    def start_communicating(self: SlimLinkComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        self._logger.debug("SLIMLink  -  startCommunicating()  - " + self._device_name)
        
        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()
        
        try:
            self._tx_device_proxy = CbfDeviceProxy(
                fqdn=self._tx_device_fqdn, logger=self._logger
            )
            self._rx_device_proxy = CbfDeviceProxy(
                fqdn=self._rx_device_fqdn, logger=self._logger
            )
        except tango.DevFailed:
            self.update_component_fault(True)
            self._logger.error("Error in proxy connection")
            return
            
        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.ON)
        self.update_component_fault(False)


    def stop_communicating(self: SlimLinkComponentManager) -> None:
        """Stop communication with the component."""
        self._logger.debug("SLIMLink  -  stopCommunicating()  - " + self._device_name)
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = False
        
    def connect_to_slim_tx(self: SlimLinkComponentManager, tx_device: CbfDeviceProxy) -> None:
        self._logger.debug("SLIMLink  -  connectToSlimTx()  - " + self._device_name)
        try:
            ping = tx_device.ping()
            
            _logger.info("Connection to SLIM TX Tango DS successful. tx_device_name: " +
                        _tx_device_name + "; device ping took " + ping + " microseconds")
        except tango.DevFailed:
            self._logger.error("Connection to SLIM TX Tango DS failed: " + _tx_device_name)
            self.update_component_fault(True)
            # throw exception
            
    def connect_to_slim_rx(self: SlimLinkComponentManager, rx_device: CbfDeviceProxy) -> None:
        self._logger.debug("SLIMLink  -  connectToSlimRx()  - " + self._device_name)
        try:
            disconnectFromSLIMRx()
            ping = rx_device.ping()
            
            serial_loopback_enable = False
            rx_device.initialize_connection(serial_loopback_enable)
            
            _logger.info("Connection to SLIM RX Tango DS successful. rx_device_name: " +
                        _rx_device_name + "; device ping took " + ping + " microseconds")
        except tango.DevFailed:
            self._logger.error("Connection to SLIM RX Tango DS failed: " + _rx_device_name)
            self.update_component_fault(True)
            # throw exception
            
    def verify_connection(self: SlimLinkComponentManager) -> bool:
        connected = false
        self._logger.debug("SLIMLink  -  verifyConnection()  - " + self._device_name)
        
        if self._tx_device_proxy and self._rx_device_proxy:
            connected = True
            result_msg = "Valid connection between TX and RX device! "
            error_msg = ""
            
            try:
                expected_idle_ctrl_word = self._tx_device_proxy.read_attribute("idle_ctrl_word")
                rx_idle_ctrl_word = self._rx_device_proxy.read_attribute("idle_ctrl_word")
                counters = self._rx_device_proxy.read_attribute("read_counters")
                block_lost_count = counters[BLOCK_LOST_COUNT_INDEX]
                cdr_lost_count = counters[CDR_LOST_COUNT_INDEX]
                
                if rx_idle_ctrl_word != expected_idle_ctrl_word:
                    connected = False
			        result_msg = "Invalid connection between TX and RX device! "
			        err_msg += "Expected and received idle control word do not match. "
                if block_lost_count != 0:
                    connected = False
			        result_msg = "Invalid connection between TX and RX device! "
			        err_msg += "block_lost_count not zero. "
                if cdr_lost_count != 0:
                    connected = False
			        result_msg = "Invalid connection between TX and RX device! "
			        err_msg += "cdr_lost_count not zero. "
           
                self._logger.debug("SLIMLink  -  verifyConnection()  - " + result_msg + err_msg)
            except tango.DevFailed:
                # tango.except.print_exception()
                # exit(-1)
        else:
            self._logger.error("Must connect Tx and Rx device!")
            
        return connected
            
        # TODO: This is where I made it to
