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

import concurrent.futures
import json
import logging
import os
from typing import Callable, Dict, List, Optional, Tuple

import tango
import yaml
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, PowerMode, SimulationMode

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy


class ControllerComponentManager(CbfComponentManager):
    """A component manager for the CbfController device."""

    def __init__(
        self: ControllerComponentManager,
        get_num_capabilities: Callable[[None], Dict[str, int]],
        subarray_fqdns_all: List[str],
        vcc_fqdns_all: List[str],
        fsp_fqdns_all: List[str],
        talon_lru_fqdns_all: List[str],
        talon_board_fqdns_all: List[str],
        power_switch_fqdns_all: List[str],
        lru_timeout: int,
        talondx_component_manager: TalonDxComponentManager,
        talondx_config_path: str,
        hw_config_path: str,
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
        :param talon_board_fqdns_all: FQDNS of all the Talon board devices
        :param power_switch_fqdns_all: FQDNS of all the power switch devices
        :param lru_timeout: Timeout in seconds for Talon LRU device proxies
        :talondx_component_manager: component manager for the Talon LRU
        :param talondx_config_path: path to the directory containing configuration
                                    files and artifacts for the Talon boards
        :param hw_config_path: path to the directory containing the hardware
                               configuration file
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

        self._connected = False  # to device proxies

        # TODO: CIP-1569
        # Temporarily commenting out the self._on
        # self._on = False  # CBF controller itself

        (
            self._fqdn_vcc,
            self._fqdn_fsp,
            self._fqdn_subarray,
            self._fqdn_talon_lru,
            self._fqdn_talon_board,
            self._fqdn_power_switch,
        ) = ([] for i in range(6))

        self._subarray_fqdns_all = subarray_fqdns_all
        self._vcc_fqdns_all = vcc_fqdns_all
        self._fsp_fqdns_all = fsp_fqdns_all
        self._talon_lru_fqdns_all = talon_lru_fqdns_all
        self._talon_board_fqdns_all = talon_board_fqdns_all
        self._power_switch_fqdns_all = power_switch_fqdns_all
        self._lru_timeout = lru_timeout

        self._get_max_capabilities = get_num_capabilities

        self._vcc_to_receptor = {}

        # TODO: component manager should not be passed into component manager ?
        self._talondx_component_manager = talondx_component_manager

        self._talondx_config_path = talondx_config_path
        self._hw_config_path = hw_config_path

        self._max_capabilities = ""

        self._proxies = {}

        # Initialize attribute values
        self.frequency_offset_k = [0] * const.DEFAULT_COUNT_VCC
        self.frequency_offset_delta_f = [0] * const.DEFAULT_COUNT_VCC

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

        with open(self._hw_config_path) as yaml_fd:
            self._hw_config = yaml.safe_load(yaml_fd)

        self._max_capabilities = self._get_max_capabilities()
        if self._max_capabilities:
            try:
                self._count_vcc = self._max_capabilities["VCC"]
            except KeyError:  # not found in DB
                self._count_vcc = const.DEFAULT_COUNT_VCC

            try:
                self._count_fsp = self._max_capabilities["FSP"]
            except KeyError:  # not found in DB
                self._count_fsp = const.DEFAULT_COUNT_FSP

            try:
                self._count_subarray = self._max_capabilities["Subarray"]
            except KeyError:  # not found in DB
                self._count_subarray = const.DEFAULT_COUNT_SUBARRAY
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

        self._fqdn_talon_lru = [
            fqdn
            for fqdn in self._talon_lru_fqdns_all
            if fqdn.split("/")[-1] in list(self._hw_config["talon_lru"].keys())
        ]
        self._fqdn_talon_board = [
            fqdn
            for fqdn in self._talon_board_fqdns_all
            if fqdn.split("/")[-1]
            in list(self._hw_config["talon_board"].keys())
        ]
        self._fqdn_power_switch = [
            fqdn
            for fqdn in self._power_switch_fqdns_all
            if fqdn.split("/")[-1]
            in list(self._hw_config["power_switch"].keys())
        ]

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
            self._fqdn_fsp
            + self._fqdn_talon_lru
            + self._fqdn_talon_board
            + self._fqdn_power_switch
            + self._fqdn_subarray
        ):
            if fqdn not in self._proxies:
                try:
                    log_msg = f"Trying connection to {fqdn}"
                    self._logger.debug(log_msg)
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)

                    if fqdn in self._fqdn_talon_lru:
                        self._logger.debug(
                            f"Writing hardware configuration properties to {fqdn}"
                        )
                        lru_id = fqdn.split("/")[-1]
                        lru_config = tango.utils.obj_2_property(
                            self._hw_config["talon_lru"][lru_id]
                        )
                        proxy.put_property(lru_config)
                        proxy.Init()
                        proxy.set_timeout_millis(self._lru_timeout * 1000)

                    elif fqdn in self._fqdn_talon_board:
                        self._logger.debug(
                            f"Writing hardware configuration properties to {fqdn}"
                        )
                        board_id = fqdn.split("/")[-1]
                        board_config = tango.utils.obj_2_property(
                            {
                                "TalonDxBoardAddress": self._hw_config[
                                    "talon_board"
                                ][board_id]
                            }
                        )
                        proxy.put_property(board_config)
                        proxy.Init()

                    elif fqdn in self._fqdn_power_switch:
                        self._logger.debug(
                            f"Writing hardware configuration properties to {fqdn}"
                        )
                        switch_id = fqdn.split("/")[-1]
                        switch_config = tango.utils.obj_2_property(
                            self._hw_config["power_switch"][switch_id]
                        )
                        proxy.put_property(switch_config)
                        proxy.Init()

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

        # Check if connection to device proxies has been established
        if self._connected:
            # Check if CBF Controller is already on
            # TODO: CIP-1569
            # Temporarily commenting out check for redundant ON command
            # until the Off command is fully implemented.
            # Uncomment the "if not self._on:" and indent everything after it
            # until the corresponding else for CIP-1569.
            #
            # if not self._on:
            #

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
                with open(
                    os.path.join(
                        os.getcwd(),
                        self._talondx_config_path,
                        "talondx-config.json",
                    )
                ) as f:
                    talondx_config_json = json.load(f)

                self._fqdn_talon_lru = []
                for config_command in talondx_config_json["config_commands"]:
                    target = config_command["target"]
                    for lru_id, lru_config in self._hw_config[
                        "talon_lru"
                    ].items():
                        lru_fqdn = f"mid_csp_cbf/talon_lru/{lru_id}"
                        talon1 = lru_config["TalonDxBoard1"]
                        talon2 = lru_config["TalonDxBoard2"]
                        if (
                            target in [talon1, talon2]
                            and lru_fqdn not in self._fqdn_talon_lru
                        ):
                            self._fqdn_talon_lru.append(lru_fqdn)

                # TODO: handle subscribed events for missing LRUs
            else:
                # use a hard-coded example fqdn talon lru for simulation mode
                self._fqdn_talon_lru = ["mid_csp_cbf/talon_lru/001"]

            # Turn on all the LRUs with the boards we need
            lru_on_status, log_msg = self._bulk_lru_on()
            if not lru_on_status:
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

            # TODO: CIP-1569
            # Uncomment out the "self._on = True" when OFF command implemented.
            # self._on = True
            message = "CbfController On command completed OK"
            return (ResultCode.OK, message)

            # TODO: CIP-1569
            # Corresponding ELSE to handle redundant ON command.
            # Uncomment out the following 4 lines when OFF command implemented.
            # else:
            #    log_msg = "CbfController is already ON. Disregarding redundant command."
            #    self._logger.warning(log_msg)
            #    return (ResultCode.OK, log_msg)

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

        # Check if connection to device proxies has been established
        if self._connected:
            # Check if CBF Controller is on
            # TODO: CIP-1569
            # Temporarily commenting out check for redundant Off command
            # until the Off command is fully implemented.
            # Uncomment the "if self._on:" and indent everything after it
            # until the corresponding else for CIP-1569.
            #
            # if self._on:
            #

            if (
                self._talondx_component_manager.simulation_mode
                == SimulationMode.FALSE
            ):
                if len(self._fqdn_talon_lru) == 0:
                    with open(
                        os.path.join(
                            os.getcwd(),
                            self._talondx_config_path,
                            "talondx-config.json",
                        )
                    ) as f:
                        talondx_config_json = json.load(f)

                    for config_command in talondx_config_json[
                        "config_commands"
                    ]:
                        target = config_command["target"]
                        for lru_id, lru_config in self._hw_config[
                            "talon_lru"
                        ].items():
                            talon1 = lru_config["TalonDxBoard1"]
                            talon2 = lru_config["TalonDxBoard2"]
                            if target in [talon1, talon2]:
                                self._fqdn_talon_lru.append(
                                    f"mid_csp_cbf/talon_lru/{lru_id}"
                                )

                    # TODO: handle subscribed events for missing LRUs
            else:
                # use a hard-coded example fqdn talon lru for simulation mode
                self._fqdn_talon_lru = ["mid_csp_cbf/talon_lru/001"]

            try:
                self._logger.info(f"Turning off LRUs: {self._fqdn_talon_lru}")
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

            # TODO: CIP-1569
            # Uncomment out the "self._on = False" when OFF command implemented.
            # self._on = False
            message = "CbfController Off command completed OK"
            return (ResultCode.OK, message)

            # TODO: CIP-1569
            # Corresponding ELSE to handle redundant OFF command.
            # Uncomment out the following 4 lines when OFF command fully implemented.
            # else:
            #    log_msg = "CbfController is already OFF. Disregarding redundant command."
            #    self._logger.warning(log_msg)
            #    return (ResultCode.OK, log_msg)

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

    def init_sys_param(
        self: ControllerComponentManager,
        params: str,
    ) -> Tuple[ResultCode, str]:
        """
        Validate and save the Dish ID - VCC ID mapping and k values.

        :param argin: the Dish ID - VCC ID mapping and k values in a
                        json string.
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        status, msg = self._validate_sys_param(params)
        if status is not ResultCode.OK:
            return (status, msg)
        return (
            ResultCode.OK,
            "CbfController InitSysParam command completed OK",
        )

    def _validate_sys_param(
        self: ControllerComponentManager,
        params: str,
    ) -> Tuple[ResultCode, str]:
        if not self._validate_sys_param_schemas(params):
            return (
                ResultCode.FAILED,
                "Failed to validate against json schema",
            )
        params_json = json.loads(params)
        dish_dict = params_json["dish_parameters"]
        dish_id_set = set()
        vcc_id_set = set()
        for dish_id, v in dish_dict.items():
            # Dish ID must be SKA001-133, MKT000-063
            if dish_id[0:3] == "SKA":
                id = int(dish_id[3:])
                if id < 1 or id > 133:
                    return (ResultCode.FAILED, "Invalid Dish ID")
            elif dish_id[0:3] == "MKT":
                id = int(dish_id[3:])
                if id < 0 or id > 63:
                    return (ResultCode.FAILED, "Invalid Dish ID")
            else:
                return (ResultCode.FAILED, "Invalid Dish ID")

            # Dish ID must be unique
            if dish_id not in dish_id_set:
                dish_id_set.add(dish_id)
            else:
                return (ResultCode.FAILED, f"Duplicated Dish ID {dish_id}")

            # VCC ID must be an integer in 1 - 197 (TODO: confirm)
            if v["vcc"] < 1 or v["vcc"] > 197:
                return (ResultCode.FAILED, f"Invalid VCC ID {v['vcc']}")

            # VCC ID must be unique
            if v["vcc"] not in vcc_id_set:
                vcc_id_set.add(v["vcc"])
            else:
                return (ResultCode.FAILED, f"Duplicated VCC ID {v['vcc']}")

            # k values must be an integer in 1 - 2222
            if v["k"] < 1 or v["k"] > 2222:
                return (ResultCode.FAILED, f"Invalid k value {v['k']}")
        return (ResultCode.OK, "")

    def _validate_sys_param_schemas(
        self: ControllerComponentManager,
        params: str,
    ) -> bool:
        # TODO
        return True

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

    def _lru_on_thread(self, proxy, sim_mode, lru_fqdn) -> (bool, str):
        try:
            self._logger.info(f"Turning on LRU {lru_fqdn}")
            proxy.write_attribute("adminMode", AdminMode.OFFLINE)
            proxy.write_attribute("simulationMode", sim_mode)
            proxy.write_attribute("adminMode", AdminMode.ONLINE)
            proxy.On()
        except tango.DevFailed as e:
            self._logger.error(e)
            return (False, lru_fqdn)

        self._logger.info(f"LRU successfully turned on: {lru_fqdn}")
        return (True, None)

    def _bulk_lru_on(
        self: ControllerComponentManager,
    ) -> (bool, str):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self._lru_on_thread,
                    self._proxies[fqdn],
                    self._talondx_component_manager.simulation_mode,
                    fqdn,
                )
                for fqdn in self._fqdn_talon_lru
            ]
            results = [f.result() for f in futures]

        failed_lrus = []
        out_status = True
        for status, fqdn in results:
            if not status:
                failed_lrus.append(fqdn)
                out_status = False
        return (out_status, f"Failed to power on Talon LRUs: {failed_lrus}")
