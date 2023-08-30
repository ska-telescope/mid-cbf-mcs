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
from time import sleep
from typing import Callable, Dict, List, Optional, Tuple

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    ObsState,
    PowerMode,
    SimulationMode,
)

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

CONST_WAIT_TIME = 4


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

        self._vcc_to_receptor = {}

        # TODO: component manager should not be passed into component manager
        self._talondx_component_manager = talondx_component_manager

        self._talondx_config_path = talondx_config_path

        self._max_capabilities = ""

        self._proxies = {}

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

        self._logger.info("Trying to execute ON Command")

        if self._connected:
            # set VCC values
            for fqdn, proxy in self._proxies.items():
                if "vcc" in fqdn:
                    try:
                        vcc_id = int(proxy.get_property("VccID")["VccID"][0])
                        rec_id = self._vcc_to_receptor[vcc_id]
                        self._logger.info(
                            f"Assigning receptor ID {rec_id} to VCC {vcc_id}"
                        )
                        proxy.receptorID = self._vcc_to_receptor[vcc_id]
                        proxy.frequencyOffsetK = self.frequency_offset_k[
                            vcc_id
                        ]
                        proxy.frequencyOffsetDeltaF = (
                            self.frequency_offset_delta_f[vcc_id]
                        )
                    except tango.DevFailed as df:
                        for item in df.args:
                            log_msg = f"Failure in connection to {fqdn}; {item.reason}"
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
                    self._proxies[fqdn].write_attribute(
                        "adminMode", AdminMode.OFFLINE
                    )
                    self._proxies[fqdn].write_attribute(
                        "simulationMode",
                        self._talondx_component_manager.simulation_mode,
                    )
                    self._proxies[fqdn].write_attribute(
                        "adminMode", AdminMode.ONLINE
                    )
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
                # Set the Simulation mode of the Subarray to the simulation mode of the controller
                self._group_subarray.write_attribute(
                    "simulationMode",
                    self._talondx_component_manager.simulation_mode,
                )
                self._group_subarray.command_inout("On")
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

            # To ensure that the subarray, vcc, and fsps
            # can be turned on again, we need to ensure that the
            # observing state is cleaned up
            # TODO: what type of except should this catch?
            try:
                self._set_subarrays_obs_state_to_empty
            except tango.DevFailed:
                log_msg = "Failed to set subarray obs state to EMPTY"
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

    def _set_subarrays_obs_state_to_empty(
        self: ControllerComponentManager,
    ) -> None:
        """
        Helper method for the OFF command to ensure that
        - the Subarrays ObsState is EMPTY
        which in turn ensures that
        - the VCC ObsState is IDLE
        - the FSP <func> Subarrays ObsState is IDLE
        so that when the Controller is commanded
        to turn On again, the observing state of
        all the controlled MCS software is ready to
        be turned On again

        :return: None
        """
        subarray_obs_state = None
        counter = 1

        log_msg = "Entering _set_subarrays_obs_state_to_empty"
        self._logger.info(log_msg)

        # TBD - we have 3 subarrays, we are only using 1 - will the others
        # be in EMPTY? This should be the case, but needs to be checked
        for fqdn in self._fqdn_subarray:
            # Move the subarray through the observing model to get to
            # EMPTY. If it is in one of the transition states that
            # occurs while moving from one state to another (like RESOURCING)
            # just wait for the completion and then move
            # This assumes that subarray won't get stuck in
            # a transition state, will have to find another option if we
            # find that it can get stuck in a transition state since
            # there aren't commands to move it out of those states. Instead
            # we would need to "perform an action" on the obs state model.
            while subarray_obs_state != ObsState.EMPTY and counter < 10:
                subarray_obs_state = self._proxies[fqdn].read_attribute(
                    "obsState"
                )
                log_msg = f"Inside while loop subarray {self._proxies[fqdn].SubID} counter: {counter}"
                self._logger.info(log_msg)
                if subarray_obs_state == ObsState.EMPTY:
                    # this is the state we want, nothing to do
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.EMPTY"
                    self._logger.info(log_msg)
                    break
                elif subarray_obs_state == ObsState.RESOURCING:
                    # wait for this to complete
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.RESOURCING"
                    self._logger.info(log_msg)
                elif subarray_obs_state == ObsState.IDLE:
                    # send Abort command
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.IDLE"
                    self._logger.info(log_msg)
                    self._proxies[fqdn].Abort()
                elif subarray_obs_state == ObsState.CONFIGURING:
                    # send Abort command
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.CONFIGURING"
                    self._logger.info(log_msg)
                    self._proxies[fqdn].Abort()
                elif subarray_obs_state == ObsState.READY:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.READY"
                    self._logger.info(log_msg)
                    # send Abort command
                    self._proxies[fqdn].Abort()
                elif subarray_obs_state == ObsState.SCANNING:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.SCANNING"
                    self._logger.info(log_msg)
                    # send Abort command
                    self._proxies[fqdn].Abort()
                elif subarray_obs_state == ObsState.ABORTING:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.ABORTING"
                    self._logger.info(log_msg)
                    # wait for this to complete
                    pass
                elif subarray_obs_state == ObsState.RESETTING:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.RESETTING"
                    self._logger.info(log_msg)
                    # wait for this to complete
                    pass
                elif subarray_obs_state == ObsState.ABORTED:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.ABORTED"
                    self._logger.info(log_msg)
                    # send Restart command
                    self._proxies[fqdn].Restart()
                elif subarray_obs_state == ObsState.FAULT:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.FAULT"
                    self._logger.info(log_msg)
                    # send Restart command
                    self._proxies[fqdn].Restart()
                elif subarray_obs_state == ObsState.RESTARTING:
                    log_msg = f"Obs state for subarray {self._proxies[fqdn].SubID} is ObsState.RESTARTING"
                    self._logger.info(log_msg)
                    # wait for this to complete and check again
                    pass
                else:
                    # log message that the state isn't known
                    log_msg = f"State of subarray {self._proxies[fqdn].SubID} is not recognized: {subarray_obs_state}"
                    self._logger.error(log_msg)
                    # TBD raise an exception
                # add a delay to allow time for commands to complete
                sleep(CONST_WAIT_TIME)
                counter = counter + 1
            if subarray_obs_state != ObsState.EMPTY:
                log_msg = "Unable to transition subarray to ObsState.EMPTY. ObsState is {subarray_obs_state}; counter = {counter}"
                self._logger.error(log_msg)
                # TBD raise exception
            log_msg = f"Exiting update state of subarray {self._proxies[fqdn].SubID}. Counter: {counter}"
            self._logger.info(log_msg)

        log_msg = "Exiting _set_subarrays_obs_state_to_empty"
        self._logger.info(log_msg)
