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

import logging

# tango imports
import tango

from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import HealthState, AdminMode, SimulationMode
from ska_tango_base.commands import ResultCode

class ControllerComponentManager:
    """A component manager for the CbfController device."""

    def __init__(
        self: ControllerComponentManager,
        fqdn_vcc: str,
        fqdn_fsp: str,
        fqdn_subarray: str,
        fqdn_talon_lru: str,
        talondx_component_manager,
        logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        """

        self._fqdn_vcc = fqdn_vcc
        self._fqdn_fsp = fqdn_fsp
        self._fqdn_subarray = fqdn_subarray
        self._fqdn_talon_lru = fqdn_talon_lru

        self._talondx_component_manager =  talondx_component_manager

        self._proxies = {} 

        self._event_id = {} 

        self.start_communicating(logger=logger)

    
    def start_communicating(
        self: ControllerComponentManager,
        logger: logging.Logger
    ) -> None:

        self._group_vcc = CbfGroupProxy("VCC", logger=logger)
        self._group_vcc.add(self._fqdn_vcc)
        
        self._group_fsp = CbfGroupProxy("FSP", logger=logger)
        self._group_fsp.add(self._fqdn_fsp)

        self._group_subarray = CbfGroupProxy("CBF Subarray", logger=logger)
        self._group_subarray.add(self._fqdn_subarray)

        self._fqdn_talon_lru = self._fqdn_talon_lru

        for fqdn in self._fqdn_vcc + self._fqdn_fsp + self._fqdn_talon_lru + self._fqdn_subarray :
            if fqdn not in self._proxies:
                try:
                    log_msg = "Trying connection to " + fqdn + " device"
                    logger.info(log_msg)
                    device_proxy = CbfDeviceProxy(
                        fqdn=fqdn, 
                        logger=logger
                    )
                    self._proxies[fqdn] = device_proxy
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                        logger.error(log_msg)


    def __state_change_event_callback(
            self: ControllerComponentManager, 
            fqdn,
            name,
            value,
            quality
        ) -> None:

            if value is not None:
                try:
                    if "healthstate" in name:
                        if "subarray" in fqdn:
                            self._report_subarray_health_state[
                                self._fqdn_subarray.index(fqdn)
                            ] = value
                        elif "vcc" in fqdn:
                            self._report_vcc_health_state[
                                self._fqdn_vcc.index(fqdn)
                            ] = value
                        elif "fsp" in fqdn:
                            self._report_fsp_health_state[
                                self._fqdn_fsp.index(fqdn)
                            ] = value
                        elif "talon_lru" in fqdn:
                            self._report_talon_lru_health_state[
                                self._fqdn_talon_lru.index(fqdn)
                                ] = value
                        else:
                            # should NOT happen!
                            log_msg = "Received health state change for unknown device " + \
                                    str(name)
                            logging.warn(log_msg)
                            return
                    elif "state" in name:
                        if "subarray" in fqdn:
                            self._report_subarray_state[
                                self._fqdn_subarray.index(fqdn)
                            ] = value
                        elif "vcc" in fqdn:
                            self._report_vcc_state[
                                self._fqdn_vcc.index(fqdn)
                            ] = value
                        elif "fsp" in fqdn:
                            self._report_fsp_state[
                                self._fqdn_fsp.index(fqdn)
                            ] = value
                        elif "talon_lru" in fqdn:
                            self._report_talon_lru_state[
                                self._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            # should NOT happen!
                            log_msg = "Received state change for unknown device " + \
                                    str(name)
                            logging.warn(log_msg)
                            return
                    elif "adminmode" in name:
                        if "subarray" in fqdn:
                            self._report_subarray_admin_mode[
                                self._fqdn_subarray.index(fqdn)
                            ] = value
                        elif "vcc" in fqdn:
                            self._report_vcc_admin_mode[
                                self._fqdn_vcc.index(fqdn)
                            ] = value
                        elif "fsp" in fqdn:
                            self._report_fsp_admin_mode[
                                self._fqdn_fsp.index(fqdn)
                            ] = value
                        elif "talon_lru" in fqdn:
                            self._report_talon_lru_admin_mode[
                                self._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            # should NOT happen!
                            log_msg = "Received admin mode change for unknown device " + \
                                    str(name)
                            logging.warn(log_msg)
                            return

                    log_msg = "New value for " + str(name) + " of device " + \
                        fqdn + ": " + str(value)
                    logging.info(log_msg)
                except Exception as except_occurred:
                    logging.error(str(except_occurred))
            else:
                logging.warn(
                    "None value for attribute " + str(name) + 
                    " of device " + fqdn
                )

    def __membership_event_callback(
        self: ControllerComponentManager, 
        fqdn,
        name,
        value,
        quality
    ) -> None:

        if value is not None:
            try:
                if "vcc" in fqdn:
                    self._report_vcc_subarray_membership[
                        self._fqdn_vcc.index(fqdn)
                    ] = value
                elif "fsp" in fqdn:
                    if value not in self._report_fsp_subarray_membership[
                        self._fqdn_fsp.index(fqdn)]:
                        logging.warning("{}".format(value))
                        self._report_fsp_subarray_membership[
                            self._fqdn_fsp.index(fqdn)
                        ].append(value)
                else:
                    # should NOT happen!
                    log_msg = "Received event for unknown device " + str(name)
                    logging.warn(log_msg)
                    return

                log_msg = "New value for " + str(name) + " of device " + \
                        fqdn + ": " + str(value)
                logging.info(log_msg)

            except Exception as except_occurred:
                logging.error(str(except_occurred))
        else:
            logging.warn(
                "None value for attribute " + str(name) + 
                " of device " + fqdn
            )

        
    def __config_ID_event_callback(
            self: ControllerComponentManager, 
            fqdn,
            name,
            value,
            quality
    ) -> None:

        if value is not None:
            try:
                self._subarray_config_ID[
                    self._fqdn_subarray.index(fqdn)
                ] = value
                log_msg = "New value for " + str(name) + " of device " + \
                        fqdn + ": " + str(value)
                logging.info(log_msg)
            except Exception as except_occurred:
                logging.error(str(except_occurred))
        else:
            logging.warn(
                "None value for attribute " + str(name) + 
                " of device " + fqdn
            )

    
    def on(      
        self: ControllerComponentManager,
    ) -> None:

        # Try connection with each subarray/capability
        for fqdn, proxy in self._proxies.items():
                try:
                    events = []

                    # subscribe to change events on subarrays/capabilities
                    for attribute_val in ["adminMode", "healthState", "State"]:
                        events.append(
                            proxy.add_change_event_callback(
                                attribute_name=attribute_val,
                                callback=self.__state_change_event_callback,
                                stateless=True
                            )
                        )

                    # subscribe to VCC/FSP subarray membership change events
                    if "vcc" in fqdn or "fsp" in fqdn:
                        events.append(
                            proxy.add_change_event_callback(
                                attribute_name="subarrayMembership",
                                callback=self.__membership_event_callback,
                                stateless=True
                            )
                        )

                    #TODO: re-enable and fix if this is needed?
                    # subscribe to subarray config ID change events
                    if "subarray" in fqdn:
                        events.append(
                            proxy.add_change_event_callback(
                                attribute_name="configID",
                                callback=self.__config_ID_event_callback,
                                stateless=True
                            )
                        )

                    self._event_id[proxy] = events
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                        logging.error(log_msg)

        # Power on all the Talon boards
        for talon_lru_fqdn in self._fqdn_talon_lru:
            self._proxies[talon_lru_fqdn].On()

        # Configure all the Talon boards
        if self._talondx_component_manager.configure_talons() == ResultCode.FAILED:
            logging.error("Failed to configure Talon boards")
            
        self._group_subarray.command_inout("On")
        self._group_vcc.command_inout("On")
        self._group_fsp.command_inout("On")


    def off(      
        self: ControllerComponentManager,
    ) -> None:

        for talon_lru_fqdn in self._fqdn_talon_lru:
                self._proxies[talon_lru_fqdn].Off()

        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")

        for proxy in list(self._event_id.keys()):
            for event_id in self._event_id[proxy]:
                logging.info(
                    "Unsubscribing from event " + str(event_id) +
                    ", device: " + str(proxy._fqdn)
                )
                proxy.unsubscribe_event(event_id)

    def standby(      
        self: ControllerComponentManager,
    ) -> None:

        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")