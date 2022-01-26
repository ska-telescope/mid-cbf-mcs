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
from typing import Any, List, Tuple, Callable, Optional, Dict

import tango
from tango import AttrQuality

import logging

from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import HealthState, AdminMode, PowerMode
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.controller.talondx_component_manager import TalonDxComponentManager

from ska_mid_cbf_mcs.component.component_manager import (
    CommunicationStatus,
    CbfComponentManager,
)

CONST_DEFAULT_COUNT_VCC = 197
CONST_DEFAULT_COUNT_FSP = 27
CONST_DEFAULT_COUNT_SUBARRAY = 16

class ControllerComponentManager(CbfComponentManager):
    """A component manager for the CbfController device."""

    def __init__(
        self: ControllerComponentManager,
        get_num_capabilities : Callable[[None], Dict[str, int]],
        vcc_fqdns_all: List[str],
        fsp_fqdns_all: List[str],
        talon_lru_fqdns_all: List[str],
        talondx_component_manager: TalonDxComponentManager,
        logger: logging.Logger,
        push_change_event: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
    ) -> None:
        """
        Initialise a new instance.

        :param get_num_capabilities: method that returns the controller device's 
                maxCapabilities attribute (a dictionary specifying the number of each capability)    
        :param vcc_fqdns_all: FQDNS of all the Vcc devices
        :param fsp_fqdns_all: FQDNS of all the Fsp devices
        :param talon_lru_fqdns_all: FQDNS of all the Talon LRU devices
        :talondx_component_manager: component manager for the Talon LRU 
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

        self._fqdn_vcc, self._fqdn_fsp, self._fqdn_subarray, self._fqdn_talon_lru  \
            = ([] for i in range(4))

        self._vcc_fqdns_all = vcc_fqdns_all
        self._fsp_fqdns_all = fsp_fqdns_all
        self._talon_lru_fqdns_all = talon_lru_fqdns_all
        self._get_max_capabilities = get_num_capabilities

        # TODO: component manager should not be passed into component manager
        self._talondx_component_manager =  talondx_component_manager

        self._max_capabilities = ""

        self._proxies = {}
        self._events = {} 

        super().__init__(
            logger,
            push_change_event,
            communication_status_changed_callback,
            component_power_mode_changed_callback,
            None,
        )
    
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

        super().start_communicating()

        self._max_capabilities = self._get_max_capabilities()
        if self._max_capabilities:
                try:
                    self._count_vcc = self._max_capabilities["VCC"]
                except KeyError:  # not found in DB
                    self._count_vcc = CONST_DEFAULT_COUNT_VCC

                try:
                    self._count_fsp = self._max_capabilities["FSP"]
                except KeyError:  # not found in DB
                    self._count_fsp = CONST_DEFAULT_COUNT_FSP

                try:
                    self._count_subarray = self._max_capabilities["Subarray"]
                except KeyError:  # not found in DB
                    self._count_subarray = CONST_DEFAULT_COUNT_SUBARRAY
        else:
            self._logger.warn("MaxCapabilities device property not defined - \
                using default value")
        
        self._fqdn_vcc = list(self._vcc_fqdns_all)[:self._count_vcc]
        self._fqdn_fsp = list(self._fsp_fqdns_all)[:self._count_fsp]
        self._fqdn_subarray = list(self._fsp_fqdns_all)[:self._count_subarray]
        self._fqdn_talon_lru = list(self._talon_lru_fqdns_all)
        
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

        self._count_talon_lru = len(self._talon_lru_fqdns_all)
        self._report_talon_lru_state = [tango.DevState.UNKNOWN] * self._count_talon_lru
        self._report_talon_lru_health_state = [HealthState.UNKNOWN.value] * self._count_talon_lru
        self._report_talon_lru_admin_mode = [AdminMode.ONLINE.value] * self._count_talon_lru

        try:
            self._group_vcc = CbfGroupProxy("VCC", logger=self._logger)
            self._group_vcc.add(self._fqdn_vcc)
        except tango.DevFailed:
            self._connected = False
            log_msg = f"Failure in connection to {self._fqdn_vcc}"
            self._logger.error(log_msg)
            return
        
        try:
            self._group_fsp = CbfGroupProxy("FSP", logger=self._logger)
            self._group_fsp.add(self._fqdn_fsp)
        except tango.DevFailed:
            self._connected = False
            log_msg = f"Failure in connection to {self._fqdn_fsp}"
            self._logger.error(log_msg)
            return

        try:
            self._group_subarray = CbfGroupProxy("CBF Subarray", logger=self._logger)
            self._group_subarray.add(self._fqdn_subarray)
        except tango.DevFailed:
            self._connected = False
            log_msg = f"Failure in connection to {self._fqdn_subarray}"
            self._logger.error(log_msg)
            return

        self._fqdn_talon_lru = self._fqdn_talon_lru

        for idx, fqdn in enumerate(self._fqdn_vcc):
            if fqdn not in self._proxies:
                try:
                    log_msg = "Trying connection to " + fqdn + " device"
                    self._logger.info(log_msg)
                    proxy = CbfDeviceProxy(
                        fqdn=fqdn, 
                        logger=self._logger
                    )
                    self._proxies[fqdn] = proxy
                    # TODO: for testing purposes;
                    # receptorID assigned to VCCs in order they are processed
                    proxy.receptorID = idx + 1
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + \
                            " device: " + str(item.reason)
                        self._logger.error(log_msg)

        for fqdn in self._fqdn_fsp + self._fqdn_talon_lru + self._fqdn_subarray:
            if fqdn not in self._proxies:
                try:
                    log_msg = f"Trying connection to {fqdn}"
                    self._logger.info(log_msg)
                    proxy = CbfDeviceProxy(
                        fqdn=fqdn, 
                        logger=self._logger
                    )

                    if fqdn in self._fqdn_talon_lru:
                        proxy.set_timeout_millis(10000)
                        
                    self._proxies[fqdn] = proxy
                except tango.DevFailed as df:
                    self._connected = False
                    for item in df.args:
                        log_msg = f"Failure in connection to {fqdn}; {item.reason}"
                        self._logger.error(log_msg)
                    return
        
        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: ControllerComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False

    def __state_change_event_callback(
        self: ControllerComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """
        Callback for state/healthState change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
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
                        log_msg = (
                            "Received health state change for "
                            f"unknown device {name}"
                        )
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
                        log_msg = (
                            "Received state change for unknown device "
                            f"{name}"
                        )
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
                        log_msg = (
                            "Received admin mode change for "
                            f"unknown device {name}"
                        )
                        self._logger.warn(log_msg)
                        return

                log_msg = f"New value for {name} of device {fqdn}: {value}"
                self._logger.info(log_msg)
            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warn(
                f"None value for attribute {name} of device {fqdn}"
            )


    def __membership_event_callback(
        self: ControllerComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """
        Callback for subarrayMembership change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        if value is not None:
            try:
                if "vcc" in fqdn:
                    self._report_vcc_subarray_membership[
                        self._fqdn_vcc.index(fqdn)
                    ] = value
                elif "fsp" in fqdn:
                    if value not in self._report_fsp_subarray_membership[
                        self._fqdn_fsp.index(fqdn)
                    ]:
                        self._logger.info(f"{value}")
                        self._report_fsp_subarray_membership[
                            self._fqdn_fsp.index(fqdn)
                        ].append(value)
                else:
                    # should NOT happen!
                    log_msg = f"Received event for unknown device {name}"
                    self._logger.warn(log_msg)
                    return

                log_msg = f"New value for {name} of device {fqdn}: {value}"
                self._logger.info(log_msg)

            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warn(
                f"None value for attribute {name} of device {fqdn}"
            )

        
    def __config_ID_event_callback(
        self: ControllerComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """
        Callback for configID change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """

        if value is not None:
            try:
                self._subarray_config_ID[
                    self._fqdn_subarray.index(fqdn)
                ] = value
                log_msg = f"New value for {name} of device {fqdn}: {value}"
                self._logger.info(log_msg)
            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warn(
                f"None value for attribute {name} of device {fqdn}"
            )

    def on(      
        self: ControllerComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the controller and its subordinate devices 

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:

            # Try connection with each subarray/capability
            for fqdn, proxy in self._proxies.items():
                    try:
                        events = {}

                        # subscribe to change events on subarrays/capabilities
                        for attribute_val in ["adminMode", "healthState", "State"]:
                            events[attribute_val] = proxy.add_change_event_callback(
                                    attribute_name=attribute_val,
                                    callback=self.__state_change_event_callback,
                                    stateless=True
                            )

                        # subscribe to VCC/FSP subarray membership change events
                        if "vcc" in fqdn or "fsp" in fqdn:
                            events["subarrayMembership"] = proxy.add_change_event_callback(
                                    attribute_name="subarrayMembership",
                                    callback=self.__membership_event_callback,
                                    stateless=True
                            )

                        # subscribe to subarray config ID change events
                        if "subarray" in fqdn:
                            events["configID"] = proxy.add_change_event_callback(
                                    attribute_name="configID",
                                    callback=self.__config_ID_event_callback,
                                    stateless=True
                                )

                        self._events[proxy] = events
                    except tango.DevFailed as df:
                        for item in df.args:
                            log_msg = f"Failure in connection to {fqdn}; {item.reason}"
                            self._logger.error(log_msg)
                            return (ResultCode.FAILED, log_msg)
            
            # Power On subordinate devices will not work until they are updated to v0.11.3
            # TODO: remove the following lines when update to v0.11.3 complete
            message = "CbfController On command completed OK"
            return (ResultCode.OK, message)

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
        """
        Turn off the controller and its subordinate devices 

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:

            # Power Off subordinate devices will not work until they are updated to v0.11.3
            # TODO: remove the following lines when update to v0.11.3 complete
            message = "CbfController On command completed OK"
            return (ResultCode.OK, message)
            
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
                for proxy, events in self._events.items():
                    for name, id in events.items():
                        self._logger.info(
                            f"Unsubscribing from event {id}, device: {proxy._fqdn}"
                        )
                        proxy.remove_event(name, id)
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
        """
        Turn the controller into low power standby mode

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

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