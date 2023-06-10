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

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerMode,
    SimulationMode,
)
from tango import AttrQuality

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy

CONST_DEFAULT_COUNT_VCC = 197
CONST_DEFAULT_COUNT_FSP = 27
CONST_DEFAULT_COUNT_SUBARRAY = 16


class ControllerComponentManager(CbfComponentManager):
    """A component manager for the CbfController device."""

    def __init__(
        self: ControllerComponentManager,
        get_num_capabilities: Callable[[None], Dict[str, int]],
        subarray_fqdns_all: List[str],
        vcc_fqdns_all: List[str],
        fsp_fqdns_all: List[str],
        talon_lru_fqdns_all: List[str],
        talondx_component_manager: TalonDxComponentManager,
        talondx_config_path: str,
        logger: logging.Logger,
        push_change_event: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable,
    ) -> None:
        """
        Initialise a new instance.

        :param get_num_capabilities: method that returns the controller device's
                maxCapabilities attribute (a dictionary specifying the number of each capability)
        :param subarray_fqdns_all: FQDNS of all the Subarray devices
        :param vcc_fqdns_all: FQDNS of all the Vcc devices
        :param fsp_fqdns_all: FQDNS of all the Fsp devices
        :param talon_lru_fqdns_all: FQDNS of all the Talon LRU devices
        :talondx_component_manager: component manager for the Talon LRU
        :param talondx_config_path: path to the directory containing configuration
                                    files and artifacts for the Talon boards
        :param logger: a logger for this object to use
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

        (
            self._fqdn_vcc,
            self._fqdn_fsp,
            self._fqdn_subarray,
            self._fqdn_talon_lru,
        ) = ([] for i in range(4))

        self._subarray_fqdns_all = subarray_fqdns_all
        self._vcc_fqdns_all = vcc_fqdns_all
        self._fsp_fqdns_all = fsp_fqdns_all
        self._talon_lru_fqdns_all = talon_lru_fqdns_all

        self._get_max_capabilities = get_num_capabilities

        # TODO: component manager should not be passed into component manager
        self._talondx_component_manager = talondx_component_manager

        self._talondx_config_path = talondx_config_path

        self._max_capabilities = ""

        self._proxies = {}
        self._events = {}

        # Initialize attribute values
        self.frequency_offset_k = [0] * CONST_DEFAULT_COUNT_VCC
        self.frequency_offset_delta_f = [0] * CONST_DEFAULT_COUNT_VCC

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    @property
    def report_vcc_state(
        self: ControllerComponentManager,
    ) -> List[tango.DevState]:
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
    def report_vcc_subarray_membership(
        self: ControllerComponentManager,
    ) -> List[int]:
        """
        Get Vcc Subarray Memberships

        :return: report the subarray membership of VCCs (each can only belong to
                 a single subarray), 0 if not assigned
        """

        return self._report_vcc_subarray_membership

    @property
    def report_fsp_state(
        self: ControllerComponentManager,
    ) -> List[tango.DevState]:
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
    def report_fsp_subarray_membership(
        self: ControllerComponentManager,
    ) -> List[int]:
        """
        Get Fsp Subarray Memberships

        :return: Report the subarray membership of FSPs (each can only belong to
                 at most 16 subarrays), 0 if not assigned.
        """

        return self._report_fsp_subarray_membership

    @property
    def report_subarray_state(
        self: ControllerComponentManager,
    ) -> List[tango.DevState]:
        """
        Get Fsp States

        :return: state of all the FSP capabilities in the form of array
        """

        return self._report_fsp_state

    @property
    def report_subarray_health_state(
        self: ControllerComponentManager,
    ) -> List[int]:
        """
        Get Subarray Health States

        :return: subarray healthstate in an array of unsigned short
        """

        return self._report_subarray_health_state

    @property
    def report_subarray_admin_mode(
        self: ControllerComponentManager,
    ) -> List[int]:
        """
        Get Subarray Admin Modes

        :return: Report the administration mode of the Subarray
                 as an array of unsigned short
        """

        return self._report_subarray_admin_mode

    @property
    def report_subarray_config_id(
        self: ControllerComponentManager,
    ) -> List[str]:
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
            self._logger.warning(
                "MaxCapabilities device property not defined - \
                using default value"
            )

        self._fqdn_vcc = list(self._vcc_fqdns_all)[: self._count_vcc]
        self._fqdn_fsp = list(self._fsp_fqdns_all)[: self._count_fsp]
        self._fqdn_subarray = list(self._subarray_fqdns_all)[
            : self._count_subarray
        ]
        self._fqdn_talon_lru = list(self._talon_lru_fqdns_all)

        self._report_vcc_state = [tango.DevState.UNKNOWN] * self._count_vcc
        self._report_vcc_health_state = [
            HealthState.UNKNOWN.value
        ] * self._count_vcc
        self._report_vcc_admin_mode = [
            AdminMode.OFFLINE.value
        ] * self._count_vcc
        self._report_vcc_subarray_membership = [0] * self._count_vcc

        self._report_fsp_state = [tango.DevState.UNKNOWN] * self._count_fsp
        self._report_fsp_health_state = [
            HealthState.UNKNOWN.value
        ] * self._count_fsp
        self._report_fsp_admin_mode = [
            AdminMode.OFFLINE.value
        ] * self._count_fsp
        self._report_fsp_subarray_membership = [
            [] for i in range(self._count_fsp)
        ]

        self._report_subarray_state = [
            tango.DevState.UNKNOWN
        ] * self._count_subarray
        self._report_subarray_health_state = [
            HealthState.UNKNOWN.value
        ] * self._count_subarray
        self._report_subarray_admin_mode = [
            AdminMode.OFFLINE.value
        ] * self._count_subarray
        self._subarray_config_ID = [""] * self._count_subarray

        self._count_talon_lru = len(self._talon_lru_fqdns_all)
        self._report_talon_lru_state = [
            tango.DevState.UNKNOWN
        ] * self._count_talon_lru
        self._report_talon_lru_health_state = [
            HealthState.UNKNOWN.value
        ] * self._count_talon_lru
        self._report_talon_lru_admin_mode = [
            AdminMode.OFFLINE.value
        ] * self._count_talon_lru

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
            self._group_subarray = CbfGroupProxy(
                "CBF Subarray", logger=self._logger
            )
            self._group_subarray.add(self._fqdn_subarray)
        except tango.DevFailed:
            self._connected = False
            log_msg = f"Failure in connection to {self._fqdn_subarray}"
            self._logger.error(log_msg)
            return

        for fqdn in (
            self._fqdn_fsp + self._fqdn_talon_lru + self._fqdn_subarray
        ):
            if fqdn not in self._proxies:
                try:
                    log_msg = f"Trying connection to {fqdn}"
                    self._logger.info(log_msg)
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)

                    if fqdn in self._fqdn_talon_lru:
                        proxy.set_timeout_millis(10000)

                    self._proxies[fqdn] = proxy
                except tango.DevFailed as df:
                    self._connected = False
                    for item in df.args:
                        log_msg = (
                            f"Failure in connection to {fqdn}; {item.reason}"
                        )
                        self._logger.error(log_msg)
                    return

            # establish proxy connection to component
            self._proxies[fqdn].adminMode = AdminMode.ONLINE

        for idx, fqdn in enumerate(self._fqdn_vcc):
            if fqdn not in self._proxies:
                try:
                    log_msg = f"Trying connection to {fqdn} device"
                    self._logger.info(log_msg)
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies[fqdn] = proxy

                    # TODO: for testing purposes;
                    # receptorID assigned to VCCs in order they are processed
                    proxy.receptorID = idx + 1
                    proxy.frequencyOffsetK = self.frequency_offset_k[idx]
                    proxy.frequencyOffsetDeltaF = (
                        self.frequency_offset_delta_f[idx]
                    )
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = (
                            "Failure in connection to "
                            + fqdn
                            + " device: "
                            + str(item.reason)
                        )
                        self._logger.error(log_msg)

            # establish proxy connection to component
            self._proxies[fqdn].adminMode = AdminMode.ONLINE

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

        # set the default frequency offset k and deltaF in the subarrays
        self._update_freq_offset_k(self.frequency_offset_k)
        self._update_freq_offset_deltaF(self.frequency_offset_delta_f)

    def stop_communicating(self: ControllerComponentManager) -> None:
        """Stop communication with the component"""
        self._logger.info(
            "Entering ControllerComponentManager.stop_communicating"
        )
        super().stop_communicating()
        for proxy in self._proxies.values():
            proxy.adminMode = AdminMode.OFFLINE
        self._connected = False

    def _state_change_event_callback(
        self: ControllerComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
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
                        if fqdn in self._fqdn_talon_lru:
                            self._report_talon_lru_health_state[
                                self._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            log_msg = f"LRU {fqdn} is not in list"
                            self._logger.warning(log_msg)
                    else:
                        # should NOT happen!
                        log_msg = (
                            "Received health state change for "
                            f"unknown device {name}"
                        )
                        self._logger.warning(log_msg)
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
                        if fqdn in self._fqdn_talon_lru:
                            self._report_talon_lru_state[
                                self._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            log_msg = f"LRU {fqdn} is not in list"
                            self._logger.warning(log_msg)
                    else:
                        # should NOT happen!
                        log_msg = (
                            "Received state change for unknown device "
                            f"{name}"
                        )
                        self._logger.warning(log_msg)
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
                        if fqdn in self._fqdn_talon_lru:
                            self._report_talon_lru_admin_mode[
                                self._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            log_msg = f"LRU {fqdn} is not in list"
                            self._logger.warning(log_msg)
                    else:
                        # should NOT happen!
                        log_msg = (
                            "Received admin mode change for "
                            f"unknown device {name}"
                        )
                        self._logger.warning(log_msg)
                        return

                log_msg = f"New value for {name} of device {fqdn}: {value}"
                self._logger.info(log_msg)
            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warning(
                f"None value for attribute {name} of device {fqdn}"
            )

    def _membership_event_callback(
        self: ControllerComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
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
                    if (
                        value
                        not in self._report_fsp_subarray_membership[
                            self._fqdn_fsp.index(fqdn)
                        ]
                    ):
                        self._logger.info(f"{value}")
                        self._report_fsp_subarray_membership[
                            self._fqdn_fsp.index(fqdn)
                        ].append(value)
                else:
                    # should NOT happen!
                    log_msg = f"Received event for unknown device {name}"
                    self._logger.warning(log_msg)
                    return

                log_msg = f"New value for {name} of device {fqdn}: {value}"
                self._logger.info(log_msg)

            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warning(
                f"None value for attribute {name} of device {fqdn}"
            )

    def _config_ID_event_callback(
        self: ControllerComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
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
            self._logger.warning(
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
                        events[
                            attribute_val
                        ] = proxy.add_change_event_callback(
                            attribute_name=attribute_val,
                            callback=self._state_change_event_callback,
                            stateless=True,
                        )

                    # subscribe to VCC/FSP subarray membership change events
                    if "vcc" in fqdn or "fsp" in fqdn:
                        events[
                            "subarrayMembership"
                        ] = proxy.add_change_event_callback(
                            attribute_name="subarrayMembership",
                            callback=self._membership_event_callback,
                            stateless=True,
                        )

                    # subscribe to subarray config ID change events
                    if "subarray" in fqdn:
                        events["configID"] = proxy.add_change_event_callback(
                            attribute_name="configurationID",
                            callback=self._config_ID_event_callback,
                            stateless=True,
                        )

                    self._events[proxy] = events
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = (
                            f"Failure in connection to {fqdn}; {item.reason}"
                        )
                        self._logger.error(log_msg)
                        return (ResultCode.FAILED, log_msg)

            # Power on all the Talon boards if not in SimulationMode
            # TODO: There are two VCCs per LRU. Need to check the number of
            #       VCCs turned on against the number of LRUs powered on
            if (
                self._talondx_component_manager.simulation_mode
                == SimulationMode.FALSE
            ):
                # read in list of LRUs from configuration JSON
                self._fqdn_talon_lru = []

                talondx_config_file = open(
                    os.path.join(
                        os.getcwd(),
                        self._talondx_config_path,
                        "talondx-config.json",
                    )
                )

                talondx_config_json = json.load(talondx_config_file)

                talon_lru_fqdn_set = set()
                for config_command in talondx_config_json["config_commands"]:
                    talon_lru_fqdn_set.add(config_command["talon_lru_fqdn"])
                self._logger.info(f"talonlru list = {talon_lru_fqdn_set}")

                # TODO: handle subscribed events for missing LRUs
                self._fqdn_talon_lru = list(talon_lru_fqdn_set)
            else:
                # use a hard-coded example fqdn talon lru for simulation mode
                self._fqdn_talon_lru = {"mid_csp_cbf/talon_lru/001"}

            try:
                for fqdn in self._fqdn_talon_lru:
                    self._proxies[fqdn].On()
            except tango.DevFailed:
                log_msg = "Failed to power on Talon boards"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            # Configure all the Talon boards
            if (
                self._talondx_component_manager.configure_talons()
                == ResultCode.FAILED
            ):
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
            if (
                self._talondx_component_manager.simulation_mode
                == SimulationMode.FALSE
            ):
                if len(self._fqdn_talon_lru) == 0:
                    talondx_config_file = open(
                        os.path.join(
                            os.getcwd(),
                            self._talondx_config_path,
                            "talondx-config.json",
                        )
                    )
                    talondx_config_json = json.load(talondx_config_file)

                    talon_lru_fqdn_set = set()
                    for config_command in talondx_config_json[
                        "config_commands"
                    ]:
                        talon_lru_fqdn_set.add(
                            config_command["talon_lru_fqdn"]
                        )
                    self._logger.info(f"talonlru list = {talon_lru_fqdn_set}")

                    # TODO: handle subscribed events for missing LRUs
                    self._fqdn_talon_lru = list(talon_lru_fqdn_set)
            else:
                # use a hard-coded example fqdn talon lru for simulation mode
                self._fqdn_talon_lru = {"mid_csp_cbf/talon_lru/001"}

            try:
                for fqdn in self._fqdn_talon_lru:
                    self._proxies[fqdn].Off()
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
                self._group_vcc.command_inout("Standby")
                self._group_fsp.command_inout("Standby")
            except tango.DevFailed:
                log_msg = "Failed to turn group proxies to standby"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "CbfController Standby command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    def _update_freq_offset_k(
        self: ControllerComponentManager,
        freq_offset_k: List[int],
    ) -> None:
        # store the attribute
        self.frequency_offset_k = freq_offset_k

        # write the frequency offset k to each of the subarrays
        for fqdn in self._fqdn_subarray:
            self._proxies[fqdn].write_attribute(
                "frequencyOffsetK", freq_offset_k
            )

    def _update_freq_offset_deltaF(
        self: ControllerComponentManager,
        freq_offset_deltaF: List[int],
    ) -> None:
        # store the attribute
        self.frequency_offset_delta_f = freq_offset_deltaF

        # TODO: deltaF is a single value of 1800Hz, and should not be a list of values for each receptor
        for fqdn in self._fqdn_subarray:
            self._proxies[fqdn].write_attribute(
                "frequencyOffsetDeltaF", freq_offset_deltaF[0]
            )
