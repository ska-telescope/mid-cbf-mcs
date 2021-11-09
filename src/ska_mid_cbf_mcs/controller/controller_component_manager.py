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
from typing import List, Tuple

from random import randint

# tango imports
import tango
import logging

from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import HealthState, AdminMode, SimulationMode
from ska_tango_base.commands import ResultCode

class ControllerComponentManager:
    """A component manager for the CbfController device."""

    def __init__(
        self: ControllerComponentManager,
        fqdns: List[str],
        dev_counts: List[int],
        talondx_component_manager,
        logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        """

        self._logger = logger

        self._connected = False

        self._fqdn_vcc, self._fqdn_fsp, self._fqdn_subarray, self._fqdn_talon_lru, = \
            [fqdns[i] for i in range(len(fqdns))]

        self._count_vcc, self._count_fsp, self._count_subarray, self._count_talon_lru, = \
            [dev_counts[i] for i in range(len(dev_counts))]

        # TODO: component manager should not be passed into component manager
        self._talondx_component_manager =  talondx_component_manager

        self._report_vcc_state = [tango.DevState.UNKNOWN] * self._count_vcc
        self._report_vcc_health_state = [HealthState.UNKNOWN.value] * self._count_vcc
        self._report_vcc_admin_mode = [AdminMode.ONLINE.value] * self._count_vcc
        self._report_vcc_subarray_membership = [0] * self._count_vcc

        self._report_fsp_state = [tango.DevState.UNKNOWN] * self._count_fsp
        self._report_fsp_health_state = [HealthState.UNKNOWN.value] * self._count_fsp
        self._report_fsp_admin_mode = [AdminMode.ONLINE.value] * self._count_fsp
        self._report_fsp_subarray_membership = [[] for i in range(self._count_fsp)]

        self._report_subarray_state = [tango.DevState.UNKNOWN] * self._count_subarray
        self._report_subarray_health_state = [HealthState.UNKNOWN.value] * self._count_subarray
        self._report_subarray_admin_mode = [AdminMode.ONLINE.value] * self._count_subarray
        self._subarray_config_ID = [""] * self._count_subarray

        self._report_talon_lru_state = [tango.DevState.UNKNOWN] * self._count_talon_lru
        self._report_talon_lru_health_state = [HealthState.UNKNOWN.value] * self._count_talon_lru
        self._report_talon_lru_admin_mode = [AdminMode.ONLINE.value] * self._count_talon_lru

        self._proxies = {}
        self._event_id = {} 

        self._receptor_to_vcc = []
        self._vcc_to_receptor = []

        self.start_communicating()

    @property
    def receptor_to_vcc(self: ControllerComponentManager) -> List[str]:
        """
        Get Receptor to Vcc

        :return: receptorID:vccID
        """

        return self._receptor_to_vcc
    
    @property
    def vcc_to_receptor(self: ControllerComponentManager) -> List[str]:
        """
        Get Vcc to Receptor

        :return: vccID:receptorID
        """

        return self._vcc_to_receptor
    
    @property
    def report_vcc_state(self: ControllerComponentManager) -> List[tango.DevState]:
        """
        Get Vcc States

        :return: the state of the VCC capabilities as an array of DevState
        """

        return self._report_vcc_state
    
    @property
    def report_vcc_health_state(self: ControllerComponentManager) -> List[int]:
        """
        Get Vcc Health States

        :return: health status of VCC capabilities as an array of unsigned short
        """

        return self._report_vcc_health_state
    
    @property
    def report_vcc_admin_mode(self: ControllerComponentManager) -> List[int]:
        """
        Get Vcc Admin Modes

        :return: report the administration mode of the 
                 VCC capabilities as an array of unsigned short
        """

        return self._report_vcc_admin_mode
    
    @property
    def report_vcc_subarray_membership(self: ControllerComponentManager) -> List[int]:
        """
        Get Vcc Subarray Memberships

        :return: report the subarray membership of VCCs (each can only belong to 
                 a single subarray), 0 if not assigned
        """

        return self._report_vcc_subarray_membership
    
    @property
    def report_fsp_state(self: ControllerComponentManager) -> List[tango.DevState]:
        """
        Get Subarray States

        :return: report the state of the Subarray with an array of DevState
        """

        return self._report_subarray_state
    
    @property
    def report_fsp_health_state(self: ControllerComponentManager) -> List[int]:
        """
        Get Fsp Health States

        :return: Report the health status of the FSP capabilities
        """

        return self._report_fsp_health_state
    
    @property
    def report_fsp_admin_mode(self: ControllerComponentManager) -> List[int]:
        """
        Get Fsp Admin Modes

        :return: Report the administration mode of the FSP capabilities 
                 as an array of unsigned short
        """

        return self._report_fsp_admin_mode
    
    @property
    def report_fsp_subarray_membership(self: ControllerComponentManager) -> List[int]:
        """
        Get Fsp Subarray Memberships

        :return: Report the subarray membership of FSPs (each can only belong to 
                 at most 16 subarrays), 0 if not assigned.
        """

        return self._report_fsp_subarray_membership
    
    @property
    def report_subarray_state(self: ControllerComponentManager) -> List[tango.DevState]:
        """
        Get Fsp States

        :return: state of all the FSP capabilities in the form of array
        """

        return self._report_fsp_state
    
    @property
    def report_subarray_health_state(self: ControllerComponentManager) -> List[int]:
        """
        Get Subarray Health States

        :return: subarray healthstate in an array of unsigned short
        """

        return self._report_subarray_health_state

    @property
    def report_subarray_admin_mode(self: ControllerComponentManager) -> List[int]:
        """
        Get Subarray Admin Modes

        :return: Report the administration mode of the Subarray 
                 as an array of unsigned short
        """

        return self._report_subarray_admin_mode
    
    @property
    def report_subarray_config_id(self: ControllerComponentManager) -> List[str]:
        """
        Get Subarray Config Id

        :return: ID of subarray config. Used for debug purposes. 
                 Empty string if subarray is not configured for a scan.
        """

        return self._report_subarray_config_id

    
    def start_communicating(
        self: ControllerComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        remaining = list(range(1, self._count_vcc + 1))
        for i in range(1, self._count_vcc + 1):
            receptorIDIndex = randint(0, len(remaining) - 1)
            receptorID = remaining[receptorIDIndex]
            self._receptor_to_vcc.append("{}:{}".format(receptorID, i))
            self._vcc_to_receptor.append("{}:{}".format(i, receptorID))
            vcc_proxy = CbfDeviceProxy(
                fqdn=self._fqdn_vcc[i - 1], 
                logger=self._logger
            )
            vcc_proxy.receptorID = receptorID
            del remaining[receptorIDIndex]

        try:
            self._group_vcc = CbfGroupProxy("VCC", logger=self._logger)
            self._group_vcc.add(self._fqdn_vcc)
        except tango.DevFailed:
            self._connected = False
            log_msg = "Failure in connection to " + self._fqdn_vcc + " device"
            self._logger.error(log_msg)
            return
        
        try:
            self._group_fsp = CbfGroupProxy("FSP", logger=self._logger)
            self._group_fsp.add(self._fqdn_fsp)
        except tango.DevFailed:
            self._connected = False
            log_msg = "Failure in connection to " + self._fqdn_fsp + " device"
            self._logger.error(log_msg)
            return

        try:
            self._group_subarray = CbfGroupProxy("CBF Subarray", logger=self._logger)
            self._group_subarray.add(self._fqdn_subarray)
        except tango.DevFailed:
            self._connected = False
            log_msg = "Failure in connection to " + self._fqdn_subarray + " device"
            self._logger.error(log_msg)
            return

        self._fqdn_talon_lru = self._fqdn_talon_lru

        for fqdn in self._fqdn_vcc + self._fqdn_fsp + self._fqdn_talon_lru + self._fqdn_subarray :
            if fqdn not in self._proxies:
                try:
                    log_msg = "Trying connection to " + fqdn + " device"
                    self._logger.info(log_msg)
                    device_proxy = CbfDeviceProxy(
                        fqdn=fqdn, 
                        logger=self._logger
                    )
                    self._proxies[fqdn] = device_proxy
                except tango.DevFailed as df:
                    self._connected = False
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                        self._logger.error(log_msg)
                    return
        
        self._connected = True


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
                            self._logger.warn(log_msg)
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
                            self._logger.warn(log_msg)
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
                            self._logger.warn(log_msg)
                            return

                    log_msg = "New value for " + str(name) + " of device " + \
                        fqdn + ": " + str(value)
                    self._logger.info(log_msg)
                except Exception as except_occurred:
                    self._logger.error(str(except_occurred))
            else:
                self._logger.warn(
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
                        self._logger.warning("{}".format(value))
                        self._report_fsp_subarray_membership[
                            self._fqdn_fsp.index(fqdn)
                        ].append(value)
                else:
                    # should NOT happen!
                    log_msg = "Received event for unknown device " + str(name)
                    self._logger.warn(log_msg)
                    return

                log_msg = "New value for " + str(name) + " of device " + \
                        fqdn + ": " + str(value)
                self._logger.info(log_msg)

            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warn(
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
                self._logger.info(log_msg)
            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warn(
                "None value for attribute " + str(name) + 
                " of device " + fqdn
            )

    
    def on(      
        self: ControllerComponentManager,
    ) -> Tuple[ResultCode, str]:

        if self._connected:

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
                            self._logger.error(log_msg)
                            return (ResultCode.FAILED, log_msg)

            # Power on all the Talon boards
            # TODO: There are two VCCs per LRU. Need to check the number of 
            #       VCCs turned on against the number of LRUs powered on 
            try: 
                for fqdn in self._fqdn_talon_lru:
                    self._proxies[fqdn].On()
            except tango.DevFailed:
                log_msg = "Failed to power on Talon boards"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            # Configure all the Talon boards
            if self._talondx_component_manager.configure_talons() == ResultCode.FAILED:
                log_msg = "Failed to configure Talon boards"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)
    
            try:
                self._group_subarray.command_inout("On")
                self._group_vcc.command_inout("On")
                self._group_fsp.command_inout("On")
            except tango.DevFailed:
                log_msg = "Failed to turn on group proxies"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "CbfController On command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    def off(      
        self: ControllerComponentManager,
    ) -> Tuple[ResultCode, str]:

        if self._connected:

            try:
                for talon_lru_fqdn in self._fqdn_talon_lru:
                        self._proxies[talon_lru_fqdn].Off()
            except tango.DevFailed:
                log_msg = "Failed to power off Talon boards"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            try:
                self._group_subarray.command_inout("Off")
                self._group_vcc.command_inout("Off")
                self._group_fsp.command_inout("Off")
            except tango.DevFailed:
                log_msg = "Failed to turn off group proxies"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            try:
                for proxy in list(self._event_id.keys()):
                    for event_id in self._event_id[proxy]:
                        self._logger.info(
                            "Unsubscribing from event " + str(event_id) +
                            ", device: " + str(proxy._fqdn)
                        )
                        proxy.unsubscribe_event(event_id)
            except tango.DevFailed:
                log_msg = "Failed to unsubscribe to events"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)
            
            message = "CbfController Off command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    def standby(      
        self: ControllerComponentManager,
    ) -> Tuple[ResultCode, str]:

        if self._connected:

            try: 
                self._group_subarray.command_inout("Off")
                self._group_vcc.command_inout("Off")
                self._group_fsp.command_inout("Off")
            except tango.DevFailed:
                log_msg = "Failed to turn off group proxies"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "CbfController Standby command completed OK"
            return (ResultCode.OK, message)
        
        else:
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)