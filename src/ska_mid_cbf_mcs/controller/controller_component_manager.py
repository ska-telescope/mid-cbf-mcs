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
from typing import Callable, Dict, List, Optional, Tuple

import tango
import yaml
from polling2 import TimeoutException, poll
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    ObsState,
    PowerMode,
    SimulationMode,
)
from ska_telmodel.data import TMData
from ska_telmodel.schema import validate as telmodel_validate

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
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
        fs_slim_fqdn: str,
        vis_slim_fqdn: str,
        lru_timeout: int,
        talondx_component_manager: TalonDxComponentManager,
        talondx_config_path: str,
        hw_config_path: str,
        fs_slim_config_path: str,
        vis_slim_config_path: str,
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
        :param fs_slim_fqdn: FQDN of the frequency slice SLIM
        :param vis_slim_fqdn: FQDN of the visibilities SLIM
        :param lru_timeout: Timeout in seconds for Talon LRU device proxies
        :param talondx_component_manager: component manager for the Talon LRU
        :param talondx_config_path: path to the directory containing configuration
                                    files and artifacts for the Talon boards
        :param hw_config_path: path to the yaml file containing the hardware
                               configuration
        :param fs_slim_config_path: path to the yaml file containing the
                                    frequency slice SLIM configuration files
        :param vis_slim_config_path: path to the yaml file containing the
                                    visibilities SLIM configuration files
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

        (
            self._fqdn_vcc,
            self._fqdn_fsp,
            self._fqdn_subarray,
            self._fqdn_talon_lru,
            self._fqdn_talon_board,
            self._fqdn_power_switch,
        ) = ([] for i in range(6))

        # init sub-element count to default
        self._count_vcc = const.DEFAULT_COUNT_VCC
        self._count_fsp = const.DEFAULT_COUNT_FSP
        self._count_subarray = const.DEFAULT_COUNT_SUBARRAY

        # init sub-element FQDNs to all
        self._subarray_fqdns_all = subarray_fqdns_all
        self._vcc_fqdns_all = vcc_fqdns_all
        self._fsp_fqdns_all = fsp_fqdns_all
        self._talon_lru_fqdns_all = talon_lru_fqdns_all
        self._talon_board_fqdns_all = talon_board_fqdns_all
        self._power_switch_fqdns_all = power_switch_fqdns_all
        self._fs_slim_fqdn = fs_slim_fqdn
        self._vis_slim_fqdn = vis_slim_fqdn
        self._lru_timeout = lru_timeout

        self._get_max_capabilities = get_num_capabilities

        self._init_sys_param = ""
        self._source_init_sys_param = ""
        self.dish_utils = None

        # TODO: component manager should not be passed into component manager ?
        self._talondx_component_manager = talondx_component_manager

        self._talondx_config_path = talondx_config_path
        self._hw_config_path = hw_config_path
        self._fs_slim_config_path = fs_slim_config_path
        self._vis_slim_config_path = vis_slim_config_path

        self._max_capabilities = ""

        self._proxies = {}

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
                self._logger.warning(
                    f"MaxCapabilities VCC count KeyError - \
                    using default value of {const.DEFAULT_COUNT_VCC}"
                )

            try:
                self._count_fsp = self._max_capabilities["FSP"]
            except KeyError:  # not found in DB
                self._logger.warning(
                    f"MaxCapabilities FSP count KeyError - \
                    using default value of {const.DEFAULT_COUNT_FSP}"
                )

            try:
                self._count_subarray = self._max_capabilities["Subarray"]
            except KeyError:  # not found in DB
                self._logger.warning(
                    f"MaxCapabilities subarray count KeyError - \
                    using default value of {const.DEFAULT_COUNT_SUBARRAY}"
                )
        else:
            self._logger.warning(
                "MaxCapabilities device property not defined - \
                using default values"
            )

        # limit list of sub-element FQDNs to max capabilities count
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

        self._logger.debug(f"fqdn VCC: {self._fqdn_vcc}")
        self._logger.debug(f"fqdn FSP: {self._fqdn_fsp}")
        self._logger.debug(f"fqdn subarray: {self._fqdn_subarray}")
        self._logger.debug(f"fqdn Talon board: {self._fqdn_talon_board}")
        self._logger.debug(f"fqdn Talon LRU: {self._fqdn_talon_lru}")
        self._logger.debug(f"fqdn power switch: {self._fqdn_power_switch}")
        self._logger.debug(f"fqdn FS SLIM mesh: {self._fs_slim_fqdn}")
        self._logger.debug(f"fqdn VIS SLIM mesh: {self._vis_slim_fqdn}")

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

        # NOTE: order matters here
        # - must set PDU online before LRU to establish outlet power states
        # - must set VCC online after LRU to establish LRU power state
        # TODO: evaluate ordering and add further comments
        for fqdn in (
            self._fqdn_power_switch
            + self._fqdn_talon_lru
            + self._fqdn_talon_board
            + self._fqdn_subarray
            + self._fqdn_fsp
            + self._fqdn_vcc
            + [self._fs_slim_fqdn, self._vis_slim_fqdn]
        ):
            if fqdn not in self._proxies:
                try:
                    self._logger.debug(f"Trying connection to {fqdn}")
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                except tango.DevFailed as df:
                    self._connected = False
                    for item in df.args:
                        self._logger.error(
                            f"Failure in connection to {fqdn}: {item.reason}"
                        )
                    return

                # add proxy to proxies list
                self._proxies[fqdn] = proxy

            else:
                proxy = self._proxies[fqdn]

            try:
                # write hardware configuration properties to PDU devices
                if fqdn in self._fqdn_power_switch:
                    self._logger.debug(
                        f"Writing hardware configuration properties to {fqdn}"
                    )
                    switch_id = fqdn.split("/")[-1]
                    switch_config = tango.utils.obj_2_property(
                        self._hw_config["power_switch"][switch_id]
                    )
                    proxy.put_property(switch_config)
                    proxy.Init()

                # write hardware configuration properties to Talon LRU devices
                elif fqdn in self._fqdn_talon_lru:
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

                # write hardware configuration properties to Talon board devices
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

            except tango.DevFailed as df:
                self._connected = False
                for item in df.args:
                    self._logger.error(
                        f"Failed to write {fqdn} HW config properties: {item.reason}"
                    )
                return

            try:
                # establish proxy connection to component
                self._logger.info(f"Setting {fqdn} to AdminMode.ONLINE")
                self._proxies[fqdn].adminMode = AdminMode.ONLINE
            except tango.DevFailed as df:
                self._connected = False
                for item in df.args:
                    self._logger.error(
                        f"Failed to set AdminMode of {fqdn} to ONLINE: {item.reason}"
                    )
                return

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

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

        if self.dish_utils is None:
            log_msg = "Dish-VCC mapping has not been provided."
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

        # Check if connection to device proxies has been established
        if self._connected:
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

            # Read the Talon board configuration
            if (
                self._talondx_component_manager.read_config()
                == ResultCode.FAILED
            ):
                log_msg = "Failed to read Talon board configuration"
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            # Turn on all the LRUs with the boards we need
            lru_on_status, log_msg = self._turn_on_lrus()
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
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = f"Failed to turn on group proxies; {item.reason}"
                    self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            # Configure SLIM Mesh devices
            try:
                self._logger.info(
                    f"Setting SLIM simulation mode to {self._talondx_component_manager.simulation_mode}"
                )
                for fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]:
                    self._proxies[fqdn].write_attribute(
                        "simulationMode",
                        self._talondx_component_manager.simulation_mode,
                    )
                    self._proxies[fqdn].command_inout("On")

                # longer timeout may be needed because the links need to wait
                # for Tx/Rx to be ready. From experience this can be as late
                # as around 5s after HPS master completes configure.
                with open(self._fs_slim_config_path) as f:
                    fs_slim_config = f.read()
                self._proxies[self._fs_slim_fqdn].set_timeout_millis(10000)
                self._proxies[self._fs_slim_fqdn].command_inout(
                    "Configure", fs_slim_config
                )

                with open(self._vis_slim_config_path) as f:
                    vis_slim_config = f.read()
                self._proxies[self._vis_slim_fqdn].set_timeout_millis(10000)
                self._proxies[self._vis_slim_fqdn].command_inout(
                    "Configure", vis_slim_config
                )

                # restore default timeout
                self._proxies[self._fs_slim_fqdn].set_timeout_millis(3000)
                self._proxies[self._vis_slim_fqdn].set_timeout_millis(3000)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = f"Failed to configure SLIM (mesh): {item.reason}"
                    self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)
            except OSError as e:
                log_msg = f"Failed to read SLIM configuration file: {e}"
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

        # Check if connection to device proxies has been established
        if self._connected:
            (result_code, message) = (ResultCode.OK, [])

            # reset subarray observing state to EMPTY
            for subarray in [
                self._proxies[fqdn] for fqdn in self._fqdn_subarray
            ]:
                (subarray_empty, log_msg) = self._subarray_to_empty(subarray)
                if not subarray_empty:
                    self._logger.error(log_msg)
                    message.append(log_msg)
                    result_code = ResultCode.FAILED

            # turn off subelements
            (subelement_off, log_msg) = self._turn_off_subelements()
            message.extend(log_msg)
            if not subelement_off:
                result_code = ResultCode.FAILED

            # HPS master shutdown
            result = self._talondx_component_manager.shutdown(3)
            if result == ResultCode.FAILED:
                # if HPS master shutdown failed, continue with attempting to
                # shut off power outlets via LRU device
                log_msg = "HPS Master shutdown failed."
                self._logger.warning(log_msg)
                message.append(log_msg)

            # Turn off all the LRUs currently in use
            (lru_off, log_msg) = self._turn_off_lrus()
            if not lru_off:
                message.append(log_msg)
                result_code = ResultCode.FAILED

            # check final device states
            (
                op_state_error_list,
                obs_state_error_list,
            ) = self._check_subelements_off()

            if len(op_state_error_list) > 0:
                for fqdn, state in op_state_error_list:
                    log_msg = (
                        f"{fqdn} failed to turn OFF, current state: {state}"
                    )
                    self._logger.error(log_msg)
                    message.append(log_msg)
                result_code = ResultCode.FAILED

            if len(obs_state_error_list) > 0:
                for fqdn, obs_state in obs_state_error_list:
                    log_msg = f"{fqdn} failed to restart, current obsState: {obs_state}"
                    self._logger.error(log_msg)
                    message.append(log_msg)
                result_code = ResultCode.FAILED

            if result_code == ResultCode.OK:
                message.append("CbfController Off command completed OK")
            return (result_code, "; ".join(message))
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
        self._logger.debug(f"Received sys params {params}")

        def raise_on_duplicate_keys(pairs):
            d = {}
            for k, v in pairs:
                if k in d:
                    raise ValueError(f"duplicated key: {k}")
                else:
                    d[k] = v
            return d

        try:
            init_sys_param_json = json.loads(
                params, object_pairs_hook=raise_on_duplicate_keys
            )
        except ValueError as e:
            self._logger.error(e)
            return (
                ResultCode.FAILED,
                "Duplicated Dish ID in the init_sys_param json",
            )

        passed, msg = self._validate_init_sys_param(init_sys_param_json)
        if not passed:
            return (
                ResultCode.FAILED,
                msg,
            )
        # If tm_data_filepath is provided, then we need to retrieve the
        # init sys param file from CAR via the telescope model
        if "tm_data_filepath" in init_sys_param_json:
            passed, msg, init_sys_param_json = self._retrieve_sys_param_file(
                init_sys_param_json
            )
            if not passed:
                return (ResultCode.FAILED, msg)
            passed, msg = self._validate_init_sys_param(init_sys_param_json)
            if not passed:
                return (
                    ResultCode.FAILED,
                    msg,
                )
            self._source_init_sys_param = params
            self._init_sys_param = json.dumps(init_sys_param_json)
        else:
            self._source_init_sys_param = ""
            self._init_sys_param = params

        # store the attribute
        self.dish_utils = DISHUtils(init_sys_param_json)

        # send init_sys_param to the subarrays
        try:
            self._update_init_sys_param(self._init_sys_param)
        except tango.DevFailed as e:
            self._logger.error(e)
            return (
                ResultCode.FAILED,
                "Failed to update subarrays with init_sys_param",
            )

        self._logger.info("Updated subarrays with init_sys_param")

        return (
            ResultCode.OK,
            "CbfController InitSysParam command completed OK",
        )

    def _retrieve_sys_param_file(self, init_sys_param_json) -> Tuple:
        # The uri was provided in the input string, therefore the mapping from Dish ID to
        # VCC and frequency offset k needs to be retrieved using the Telescope Model
        tm_data_sources = init_sys_param_json["tm_data_sources"][0]
        tm_data_filepath = init_sys_param_json["tm_data_filepath"]
        try:
            mid_cbf_param_dict = TMData([tm_data_sources])[
                tm_data_filepath
            ].get_dict()
            msg = f"Successfully retrieved json data from {tm_data_filepath} in {tm_data_sources}"
            self._logger.info(msg)
        except (ValueError, KeyError) as e:
            msg = f"Retrieving the init_sys_param file failed with exception: \n {str(e)}"
            self._logger.error(msg)
            return (False, msg, None)
        return (True, msg, mid_cbf_param_dict)

    def _validate_init_sys_param(
        self: ControllerComponentManager,
        params: dict,
    ) -> Tuple:
        # Validate init_sys_param against the telescope model
        try:
            telmodel_validate(
                version=params["interface"], config=params, strictness=2
            )
            msg = "init_sys_param validation against ska-telmodel schema was successful!"
            self._logger.info(msg)
        except ValueError as e:
            msg = f"init_sys_param validation against ska-telmodel schema failed with exception:\n {str(e)}"
            self._logger.error(msg)
            return (False, msg)
        return (True, msg)

    def _update_init_sys_param(
        self: ControllerComponentManager,
        params: str,
    ) -> None:
        # write the init_sys_param to each of the subarrays
        for fqdn in self._fqdn_subarray:
            self._proxies[fqdn].write_attribute("sysParam", params)

        # set VCC values
        for fqdn in self._fqdn_vcc:
            try:
                proxy = self._proxies[fqdn]
                vcc_id = int(proxy.get_property("VccID")["VccID"][0])
                if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                    dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                    proxy.dishID = dish_id
                    self._logger.info(
                        f"Assigned DISH ID {dish_id} to VCC {vcc_id}"
                    )
                else:
                    log_msg = (
                        f"DISH ID for VCC {vcc_id} not found in DISH-VCC mapping; "
                        f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                    )
                    self._logger.warning(log_msg)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = f"Failure in connection to {fqdn}; {item.reason}"
                    self._logger.error(log_msg)
                    return (ResultCode.FAILED, log_msg)

        # update talon boards. The VCC ID to IP address mapping comes
        # from hw_config. Then map VCC ID to DISH ID.
        for vcc_id_str, ip in self._hw_config["talon_board"].items():
            for fqdn in self._fqdn_talon_board:
                try:
                    proxy = self._proxies[fqdn]
                    board_ip = proxy.get_property("TalonDxBoardAddress")[
                        "TalonDxBoardAddress"
                    ][0]
                    if board_ip == ip:
                        vcc_id = int(vcc_id_str)
                        proxy.write_attribute("vccID", str(vcc_id))
                        if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                            dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                            proxy.write_attribute("dishID", dish_id)
                        else:
                            log_msg = (
                                f"DISH ID for VCC {vcc_id} not found in DISH-VCC mapping; "
                                f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                            )
                            self._logger.warning(log_msg)
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = f"Failed to update {fqdn} with VCC ID and DISH ID; {item.reason}"
                        self._logger.error(log_msg)
                        return (ResultCode.FAILED, log_msg)

    def _lru_on(self, proxy, sim_mode, lru_fqdn) -> Tuple[bool, str]:
        try:
            self._logger.info(f"Turning on LRU {lru_fqdn}")
            proxy.write_attribute("adminMode", AdminMode.OFFLINE)
            proxy.write_attribute("simulationMode", sim_mode)
            proxy.write_attribute("adminMode", AdminMode.ONLINE)

            lru_powermode = proxy.read_attribute("LRUPowerMode").value
            self._logger.info(f"LRU power mode: {lru_powermode}")
            
            if True:
                self._logger.info(
                    f"LRU {lru_fqdn} already ON, rebooting Talon DX Board to clear state"
                )
                result = self._talondx_component_manager.reboot()
                if result == ResultCode.FAILED:
                    self._logger.error("Failed to reboot Talon DX Board")
                    return (False, lru_fqdn)
            
            proxy.On()
        except tango.DevFailed as e:
            self._logger.error(e)
            return (False, lru_fqdn)

        self._logger.info(f"LRU successfully turned on: {lru_fqdn}")
        return (True, None)

    def _turn_on_lrus(
        self: ControllerComponentManager,
    ) -> Tuple[bool, str]:
        results = [
            self._lru_on(
                self._proxies[fqdn],
                self._talondx_component_manager.simulation_mode,
                fqdn,
            )
            for fqdn in self._fqdn_talon_lru
        ]

        failed_lrus = []
        out_status = True
        for status, fqdn in results:
            if not status:
                failed_lrus.append(fqdn)
                out_status = False
        return (out_status, f"Failed to power on Talon LRUs: {failed_lrus}")

    def _lru_off(self, proxy, lru_fqdn) -> Tuple[bool, str]:
        try:
            self._logger.info(f"Turning off LRU {lru_fqdn}")
            proxy.Off()
        except tango.DevFailed as e:
            self._logger.error(e)
            return (False, lru_fqdn)

        self._logger.info(f"LRU successfully turned off: {lru_fqdn}")
        return (True, None)

    def _turn_off_lrus(
        self: ControllerComponentManager,
    ) -> Tuple[bool, str]:
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

                for config_command in talondx_config_json["config_commands"]:
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

        # turn off LRUs
        results = [
            self._lru_off(
                self._proxies[fqdn],
                fqdn,
            )
            for fqdn in self._fqdn_talon_lru
        ]

        failed_lrus = []
        out_status = True
        for status, fqdn in results:
            if not status:
                failed_lrus.append(fqdn)
                out_status = False
        return (out_status, f"Failed to power off Talon LRUs: {failed_lrus}")

    def _subarray_to_empty(
        self: ControllerComponentManager, subarray: CbfDeviceProxy
    ) -> Tuple[bool, str]:
        """
        Restart subarray observing state model to ObsState.EMPTY
        """
        # if subarray is READY go to IDLE
        if subarray.obsState == ObsState.READY:
            subarray.GoToIdle()
            if subarray.obsState != ObsState.IDLE:
                try:
                    poll(
                        lambda: subarray.obsState == ObsState.IDLE,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit RESTARTING
                    log_msg = f"Failed to send subarray {subarray} to idle, currently in {subarray.obsState}"
                    self._logger.error(log_msg)
                    return (False, log_msg)

        # if subarray is IDLE go to EMPTY by removing all receptors
        if subarray.obsState == ObsState.IDLE:
            subarray.RemoveAllReceptors()
            if subarray.obsState != ObsState.EMPTY:
                try:
                    poll(
                        lambda: subarray.obsState == ObsState.EMPTY,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit RESTARTING
                    log_msg = f"Failed to remove all receptors from subarray {subarray}, currently in {subarray.obsState}"
                    self._logger.error(log_msg)
                    return (False, log_msg)

        # wait if subarray is in the middle of RESOURCING/RESTARTING, as it may return to EMPTY
        if subarray.obsState in [
            ObsState.RESOURCING,
            ObsState.RESTARTING,
        ]:
            try:
                poll(
                    lambda: subarray.obsState
                    not in [
                        ObsState.RESOURCING,
                        ObsState.RESTARTING,
                    ],
                    timeout=const.DEFAULT_TIMEOUT,
                    step=0.5,
                )
            except TimeoutException:
                # raise exception if timed out waiting to exit RESOURCING/RESTARTING
                log_msg = f"Timed out waiting for {subarray} to exit {subarray.obsState}"
                self._logger.error(log_msg)
                return (False, log_msg)

        # if subarray not in EMPTY then we need to ABORT and RESTART
        if subarray.obsState != ObsState.EMPTY:
            # if subarray is in the middle of ABORTING/RESETTING, wait before issuing RESTART/ABORT
            if subarray.obsState in [
                ObsState.ABORTING,
                ObsState.RESETTING,
            ]:
                try:
                    poll(
                        lambda: subarray.obsState
                        not in [
                            ObsState.ABORTING,
                            ObsState.RESETTING,
                        ],
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit ABORTING/RESETTING
                    log_msg = f"Timed out waiting for {subarray} to exit {subarray.obsState}"
                    self._logger.error(log_msg)
                    return (False, log_msg)

            # if subarray not yet in FAULT/ABORTED, issue Abort command to enable Restart
            if subarray.obsState not in [
                ObsState.FAULT,
                ObsState.ABORTED,
            ]:
                subarray.Abort()
                if subarray.obsState != ObsState.ABORTED:
                    try:
                        poll(
                            lambda: subarray.obsState == ObsState.ABORTED,
                            timeout=const.DEFAULT_TIMEOUT,
                            step=0.5,
                        )
                    except TimeoutException:
                        # raise exception if timed out waiting to exit ABORTING
                        log_msg = f"Failed to send {subarray} to ObsState.ABORTED, currently in {subarray.obsState}"
                        self._logger.error(log_msg)
                        return (False, log_msg)

            # finally, subarray may be restarted to EMPTY
            subarray.Restart()
            if subarray.obsState != ObsState.EMPTY:
                try:
                    poll(
                        lambda: subarray.obsState == ObsState.EMPTY,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit RESTARTING
                    log_msg = f"Failed to restart {subarray}, currently in {subarray.obsState}"
                    self._logger.error(log_msg)
                    return (False, log_msg)

        return (
            True,
            f"Subarray {subarray} succesfully set to ObsState.EMPTY; subarray.obsState = {subarray.obsState}",
        )

    def _turn_off_subelements(
        self: ControllerComponentManager,
    ) -> (bool, List[str]):
        result = True
        message = []
        try:
            self._group_subarray.command_inout("Off")
        except tango.DevFailed as df:
            for item in df.args:
                log_msg = (
                    f"Failed to turn off subarray group proxy; {item.reason}"
                )
                self._logger.error(log_msg)
                message.append(log_msg)
            result = False

        try:
            self._group_vcc.command_inout("Off")
        except tango.DevFailed as df:
            for item in df.args:
                log_msg = f"Failed to turn off VCC group proxy; {item.reason}"
                self._logger.error(log_msg)
                message.append(log_msg)
            result = False

        try:
            self._group_fsp.command_inout("Off")
        except tango.DevFailed as df:
            for item in df.args:
                log_msg = f"Failed to turn off FSP group proxy; {item.reason}"
                self._logger.error(log_msg)
                message.append(log_msg)
            result = False

        try:
            for fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]:
                self._proxies[fqdn].command_inout("Off")
        except tango.DevFailed as df:
            for item in df.args:
                log_msg = f"Failed to turn off SLIM proxy; {item.reason}"
                self._logger.error(log_msg)
                message.append(log_msg)
            result = False

        if result:
            message.append(
                "Successfully issued off command to all subelements."
            )
        return (result, message)

    def _check_subelements_off(
        self: ControllerComponentManager,
    ) -> (List[str], List[str]):
        """
        Verify that the subelements are in DevState.OFF, ObsState.EMPTY/IDLE
        """
        op_state_error_list = []
        obs_state_error_list = []
        for fqdn, proxy in self._proxies.items():
            self._logger.debug(f"Checking final state of device {fqdn}")
            # power switch device state is always ON as long as it is
            # communicating and monitoring the PDU; does not implement
            # On/Off commands, rather TurnOn/OffOutlet commands to
            # target specific outlets
            if fqdn not in self._fqdn_power_switch:
                try:
                    # TODO CIP-1899 The cbfcontroller is sometimes
                    # unable to read the State() of the talon_lru
                    # device server due to an error trying to
                    # acquire the serialization monitor. As a temporary
                    # workaround, the cbfcontroller will log these
                    # errors if they occur but continue polling.
                    poll(
                        lambda: proxy.State() == tango.DevState.OFF,
                        ignore_exceptions=(tango.DevFailed),
                        log_error=logging.WARNING,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                # If the poll timed out while waiting
                # for proxy.State() == tango.DevState.OFF,
                # it throws a TimeoutException
                except TimeoutException:
                    op_state_error_list.append([fqdn, proxy.State()])

            if fqdn in self._fqdn_subarray:
                obs_state = proxy.obsState
                if obs_state != ObsState.EMPTY:
                    obs_state_error_list.append((fqdn, obs_state))

            if fqdn in self._fqdn_vcc:
                obs_state = proxy.obsState
                if obs_state != ObsState.IDLE:
                    obs_state_error_list.append((fqdn, obs_state))

        return (op_state_error_list, obs_state_error_list)
