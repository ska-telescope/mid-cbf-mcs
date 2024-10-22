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
from threading import Event
from typing import Callable, Optional

import tango
import yaml
from polling2 import TimeoutException, poll
from ska_control_model import AdminMode, ObsState, PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_telmodel.data import TMData
from ska_telmodel.schema import validate as telmodel_validate

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.commons.validate_interface import validate_interface
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)


class ControllerComponentManager(CbfComponentManager):
    """
    A component manager for the CbfController device.
    """

    def __init__(
        self: ControllerComponentManager,
        *args: any,
        fqdn_dict: dict[str, list[str]],
        config_path_dict: dict[str, str],
        max_capabilities: dict[str, int],
        talondx_component_manager: TalonDxComponentManager,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param fqdn_dict: dictionary containing FQDNs for the controller's sub-elements
        :param config_path_dict: dictionary containing paths to configuration files
        :param max_capabilities: dictionary containing maximum number of sub-elements
        :param talondx_component_manager: instance of TalonDxComponentManager
        """

        super().__init__(*args, **kwargs)

        self.validate_supported_configuration = True

        (
            self._vcc_fqdn,
            self._fsp_fqdn,
            self._subarray_fqdn,
            self._talon_lru_fqdn,
            self._talon_board_fqdn,
            self._power_switch_fqdn,
        ) = ([] for _ in range(6))

        # --- Max Capabilities --- #
        self._count_vcc = max_capabilities["VCC"]
        self._count_fsp = max_capabilities["FSP"]
        self._count_subarray = max_capabilities["Subarray"]

        # --- FQDNs --- #
        self._subarray_fqdns_all = fqdn_dict["CbfSubarray"]
        self._vcc_fqdns_all = fqdn_dict["VCC"]
        self._fsp_fqdns_all = fqdn_dict["FSP"]
        self._talon_lru_fqdns_all = fqdn_dict["TalonLRU"]
        self._talon_board_fqdns_all = fqdn_dict["TalonBoard"]
        self._power_switch_fqdns_all = fqdn_dict["PowerSwitch"]
        # NOTE: Hard coded to look at first index to handle FsSLIM and VisSLIM as single device
        self._fs_slim_fqdn = fqdn_dict["FsSLIM"][0]
        self._vis_slim_fqdn = fqdn_dict["VisSLIM"][0]

        # --- Config Paths --- #
        self._talondx_config_path = config_path_dict["TalonDxConfigPath"]
        self._hw_config_path = config_path_dict["HWConfigPath"]
        self._fs_slim_config_path = config_path_dict["FsSLIMConfigPath"]
        self._vis_slim_config_path = config_path_dict["VisSLIMConfigPath"]

        self.dish_utils = None
        self.last_init_sys_param = ""
        self.source_init_sys_param = ""
        self._talondx_component_manager = talondx_component_manager
        self._proxies = {}
        self._talon_board_proxies = {}

    # -------------
    # Communication
    # -------------

    # --- Start Communicating --- #

    def _set_fqdns(self: ControllerComponentManager) -> None:
        """
        Set the list of sub-element FQDNs to be used, limited by max capabilities count
        and HW config.

        :update: self._vcc_fqdn, self._fsp_fqdn, self._subarray_fqdn, self._talon_lru_fqdn,
                 self._talon_board_fqdn, self._power_switch_fqdn
        """
        # Observing/capability devices
        self._vcc_fqdn = list(self._vcc_fqdns_all)[: self._count_vcc]
        self._fsp_fqdn = list(self._fsp_fqdns_all)[: self._count_fsp]
        self._subarray_fqdn = list(self._subarray_fqdns_all)[
            : self._count_subarray
        ]

        # Hardware devices
        with open(self._hw_config_path) as yaml_fd:
            self._hw_config = yaml.safe_load(yaml_fd)

        def _filter_fqdn(all_domains: list[str], config_key: str) -> list[str]:
            return [
                domain
                for domain in all_domains
                if domain.split("/")[-1]
                in list(self._hw_config[config_key].keys())
            ]

        self._talon_lru_fqdn = _filter_fqdn(
            self._talon_lru_fqdns_all, "talon_lru"
        )
        self._talon_board_fqdn = _filter_fqdn(
            self._talon_board_fqdns_all, "talon_board"
        )
        self._power_switch_fqdn = _filter_fqdn(
            self._power_switch_fqdns_all, "power_switch"
        )

        fqdn_variables = {
            "VCC": self._vcc_fqdn,
            "FSP": self._fsp_fqdn,
            "Subarray": self._subarray_fqdn,
            "Talon board": self._talon_board_fqdn,
            "Talon LRU": self._talon_lru_fqdn,
            "Power switch": self._power_switch_fqdn,
            "FS SLIM mesh": self._fs_slim_fqdn,
            "VIS SLIM mesh": self._vis_slim_fqdn,
        }

        for name, value in fqdn_variables.items():
            self.logger.debug(f"Active {name} FQDNs: {value}")

    def _write_hw_config(
        self: ControllerComponentManager,
        fqdn: str,
        proxy: context.DeviceProxy,
        device_type: str,
    ) -> bool:
        """
        Write hardware configuration properties to the device

        :param fqdn: FQDN of the device
        :param proxy: Proxy of the device
        :param device_type: Type of the device. Can be one of "power_switch", "talon_lru", or "talon_board".
        :return: True if the hardware configuration properties are successfully written to the device, False otherwise.
        """
        try:
            self.logger.info(
                f"Writing hardware configuration properties to {fqdn}"
            )

            device_id = fqdn.split("/")[-1]
            if device_type == "talon_board":
                device_config = {
                    "TalonDxBoardAddress": self._hw_config[device_type][
                        device_id
                    ]
                }
            else:
                device_config = self._hw_config[device_type][device_id]

            device_config = tango.utils.obj_2_property(device_config)
            proxy.put_property(device_config)
            proxy.Init()

        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to write {fqdn} HW config properties: {df}"
            )
            return False
        return True

    def _set_proxy_online(
        self: ControllerComponentManager,
        fqdn: str,
    ) -> bool:
        """
        Set the AdminMode of the component device to ONLINE, given the FQDN of the device

        :param fqdn: FQDN of the component device
        :return: True if the AdminMode of the device is successfully set to ONLINE, False otherwise.
        """
        self.logger.info(
            f"Setting {fqdn} to SimulationMode {self.simulation_mode} and AdminMode.ONLINE"
        )

        try:
            self._proxies[fqdn].simulationMode = self.simulation_mode
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to set SimulationMode of {fqdn} to {self.simulation_mode}: {df}"
            )
            return False

        try:
            self._proxies[fqdn].adminMode = AdminMode.ONLINE
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to set AdminMode of {fqdn} to ONLINE: {df}"
            )
            return False

        return True

    def _init_device_proxy(
        self: ControllerComponentManager,
        fqdn: str,
        subscribe: bool = False,
        hw_device_type: str = None,
    ) -> bool:
        """
        Initialize the device proxy from its FQDN, store the proxy in the _proxies dictionary,
        and set the AdminMode to ONLINE

        :param fqdn: FQDN of the device
        :param subscribe: True if should subscribe to the device's longRunningCommandResult attribute;
            defaults to False
        :param hw_device_type: if not default value of None, indicates the type of hardware-connected
            device to initialize
        :return: True if the device proxy is successfully initialized, False otherwise.
        """
        if fqdn not in self._proxies:
            try:
                self.logger.debug(f"Trying connection to {fqdn}")
                dp = context.DeviceProxy(device_name=fqdn)
            except tango.DevFailed as df:
                self.logger.error(f"Failure in connection to {fqdn}: {df}")
                return False
            self._proxies[fqdn] = dp

        proxy = self._proxies[fqdn]

        if subscribe:
            self.subscribe_command_results(proxy)

        if hw_device_type is not None:
            if not self._write_hw_config(fqdn, proxy, hw_device_type):
                return False

        return self._set_proxy_online(fqdn)

    def _init_device_proxies(self: ControllerComponentManager) -> bool:
        """
        Initialize all device proxies.

        :return: True if the device proxies are all successfully initialized, False otherwise.
        """
        init_success = True

        # Order matters here; must set PDU online before LRU to establish outlet power states
        for fqdn in self._power_switch_fqdn:
            if not self._init_device_proxy(
                fqdn=fqdn, hw_device_type="power_switch"
            ):
                init_success = False

        for fqdn in self._talon_lru_fqdn:
            if not self._init_device_proxy(
                fqdn=fqdn, subscribe=True, hw_device_type="talon_lru"
            ):
                init_success = False

        for fqdn in self._subarray_fqdn:
            if not self._init_device_proxy(fqdn=fqdn, subscribe=True):
                init_success = False

        for fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]:
            if not self._init_device_proxy(fqdn=fqdn, subscribe=True):
                init_success = False

        return init_success

    def _start_communicating(
        self: ControllerComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for start_communicating operation.
        """
        self.logger.debug(
            "Entering ControllerComponentManager._start_communicating"
        )

        self._set_fqdns()

        if not self._init_device_proxies():
            self.logger.error("Failed to initialize proxies.")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        self.logger.info(
            f"event_ids after subscribing = {len(self.event_ids)}"
        )

        super()._start_communicating()
        self._update_component_state(power=PowerState.OFF)

    def _stop_communicating(
        self: ControllerComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for stop_communicating operation.
        """
        self.logger.debug(
            "Entering ControllerComponentManager._stop_communicating"
        )
        for fqdn, proxy in self._proxies.items():
            try:
                if fqdn in (
                    self._subarray_fqdn
                    + self._talon_lru_fqdn
                    + [self._fs_slim_fqdn, self._vis_slim_fqdn]
                ):
                    self.unsubscribe_command_results(proxy)
                self.logger.info(f"Setting {fqdn} to AdminMode.OFFLINE")
                proxy.adminMode = AdminMode.OFFLINE
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to stop communications with {fqdn}; {df}"
                )
                continue
        self.blocking_commands = set()

        super()._stop_communicating()

    # -------------
    # Fast Commands
    # -------------

    # None so far.

    # ---------------------
    # Long Running Commands
    # ---------------------

    # --- InitSysParam Command --- #

    def _validate_init_sys_param(
        self: ControllerComponentManager,
        params: dict,
    ) -> bool:
        """
        Validate the InitSysParam against the ska-telmodel schema

        :param params: The InitSysParam parameters
        :return: True if the InitSysParam parameters are valid, False otherwise
        """
        # Validate supported interface passed in the JSON string
        (valid, msg) = validate_interface(json.dumps(params), "initsysparam")
        if not valid:
            self.logger.error(msg)
            return False
        # Validate init_sys_param against the telescope model
        try:
            telmodel_validate(
                version=params["interface"], config=params, strictness=2
            )
            self.logger.info(
                "InitSysParam validation against ska-telmodel schema was successful!"
            )
        except ValueError as e:
            self.logger.error(
                f"InitSysParam validation against ska-telmodel schema failed with exception:\n {str(e)}"
            )
            return False
        return True

    def _retrieve_sys_param_file(
        self: ControllerComponentManager,
        init_sys_param_json: dict,
    ) -> tuple[bool, dict]:
        """
        Retrieve the sys_param file from the Telescope Model

        :param init_sys_param_json: The InitSysParam parameters
        """
        # The uri was provided in the input string, therefore the mapping from Dish ID to
        # VCC and frequency offset k needs to be retrieved using the Telescope Model
        tm_data_sources = init_sys_param_json["tm_data_sources"][0]
        tm_data_filepath = init_sys_param_json["tm_data_filepath"]
        try:
            mid_cbf_param_dict = TMData([tm_data_sources])[
                tm_data_filepath
            ].get_dict()
            self.logger.info(
                f"Successfully retrieved json data from {tm_data_filepath} in {tm_data_sources}"
            )
        except (ValueError, KeyError) as e:
            self.logger.error(
                f"Retrieving the init_sys_param file failed with exception: \n {str(e)}"
            )
            return (False, None)
        return (True, mid_cbf_param_dict)

    def _update_init_sys_param(
        self: ControllerComponentManager,
        params: str,
    ) -> bool:
        """
        Update the InitSysParam parameters in the subarrays and VCCs as well as the talon boards

        :param params: The InitSysParam parameters
        :return: True if the InitSysParam parameters are successfully updated, False otherwise
        """
        # Write the init_sys_param to each of the subarrays
        for fqdn in self._subarray_fqdn:
            try:
                self._proxies[fqdn].sysParam = params
            except tango.DevFailed as df:
                self.logger.error(f"Failure in connection to {fqdn}; {df}")
                return False

        # Set VCC values
        for fqdn in self._vcc_fqdn:
            try:
                self.logger.debug(f"Trying connection to {fqdn}")
                self._proxies[fqdn] = context.DeviceProxy(device_name=fqdn)

                proxy = self._proxies[fqdn]
                vcc_id = int(proxy.get_property("DeviceID")["DeviceID"][0])
                if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                    dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                    proxy.dishID = dish_id
                    self.logger.info(
                        f"Assigned DISH ID {dish_id} to VCC {vcc_id}"
                    )
                else:
                    self.logger.error(
                        f"DISH ID for VCC {vcc_id} not found in DISH-VCC mapping; "
                        f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                    )
                    return False
            except tango.DevFailed as df:
                self.logger.error(f"Failure in connection to {fqdn}; {df}")
                return False

        return True

    def is_init_sys_param_allowed(self: ControllerComponentManager) -> bool:
        """
        Check if the InitSysParam command is allowed

        :return: True if the InitSysParam command is allowed, False otherwise
        """
        self.logger.debug("Checking if init_sys_param is allowed")
        if not self.is_communicating:
            return False
        if self.power_state == PowerState.OFF:
            return True
        self.logger.warning(
            "InitSysParam command cannot be issued because the current PowerState is not 'off'."
        )
        return False

    def _init_sys_param(
        self: ControllerComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Validate and save the Dish ID - VCC ID mapping and k values.

        :param argin: the Dish ID - VCC ID mapping and k values in a
                        json string.
        :param task_callback: Callback function to update task status
        :param task_abort_event: Event to signal task abort.
        """
        self.logger.debug(f"Received sys params {argin}")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "InitSysParam", task_callback, task_abort_event
        ):
            return

        def raise_on_duplicate_keys(pairs):
            data = {}
            for key, value in pairs:
                if key in data:
                    raise ValueError(f"duplicated key: {key}")
                else:
                    data[key] = value
            return data

        try:
            init_sys_param_json = json.loads(
                argin, object_pairs_hook=raise_on_duplicate_keys
            )
        except ValueError as e:
            self.logger.error(e)
            task_callback(
                result=(
                    ResultCode.FAILED,
                    "Duplicated Dish ID in the init_sys_param json",
                ),
                status=TaskStatus.FAILED,
            )
            return

        if not self._validate_init_sys_param(init_sys_param_json):
            task_callback(
                result=(
                    ResultCode.FAILED,
                    "Validating init_sys_param file against ska-telmodel schema failed",
                ),
                status=TaskStatus.FAILED,
            )
            return

        # If tm_data_filepath is provided, then we need to retrieve the
        # init sys param file from CAR via the telescope model
        if "tm_data_filepath" in init_sys_param_json:
            passed, init_sys_param_json = self._retrieve_sys_param_file(
                init_sys_param_json
            )
            if not passed:
                task_callback(
                    result=(
                        ResultCode.FAILED,
                        "Retrieving the init_sys_param file failed",
                    ),
                    status=TaskStatus.FAILED,
                )
                return
            if not self._validate_init_sys_param(init_sys_param_json):
                task_callback(
                    result=(
                        ResultCode.FAILED,
                        "Validating init_sys_param file retrieved from tm_data_filepath against ska-telmodel schema failed",
                    ),
                    status=TaskStatus.FAILED,
                )
                return
            self.source_init_sys_param = argin
            self.last_init_sys_param = json.dumps(init_sys_param_json)
        else:
            self.source_init_sys_param = ""
            self.last_init_sys_param = argin

        # Store the attribute
        self.dish_utils = DISHUtils(init_sys_param_json)

        # Send init_sys_param to the subarrays and VCCs.
        if not self._update_init_sys_param(self.last_init_sys_param):
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                result=(
                    ResultCode.FAILED,
                    "Failed to update subarrays and/or VCCs with init_sys_param",
                ),
                status=TaskStatus.FAILED,
            )
            return

        task_callback(
            result=(
                ResultCode.OK,
                "InitSysParam completed OK",
            ),
            status=TaskStatus.COMPLETED,
        )
        return

    def init_sys_param(
        self: ControllerComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit init_sys_param operation method to task executor queue.

        :param argin: the Dish ID - VCC ID mapping and k values in a
                        json string.
        :param task_callback: Callback function to update task status
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._init_sys_param,
            args=[argin],
            is_cmd_allowed=self.is_init_sys_param_allowed,
            task_callback=task_callback,
        )

    # --- On Command --- #

    def _init_talon_boards(self: ControllerComponentManager):
        """
        Initialize TalonBoard devices.
        """
        for fqdn in self._talon_board_fqdn:
            if fqdn not in self._talon_board_proxies:
                try:
                    self.logger.debug(f"Trying connection to {fqdn}")
                    proxy = context.DeviceProxy(device_name=fqdn)
                except tango.DevFailed as df:
                    self.logger.error(f"Failure in connection to {fqdn}: {df}")
                    continue
                self._talon_board_proxies[fqdn] = proxy
            else:
                proxy = self._talon_board_proxies[fqdn]

            if not self._write_hw_config(fqdn, proxy, "talon_board"):
                self.logger.error(f"Failed to update HW config for {fqdn}")
                continue

            self.logger.info(
                f"Setting {fqdn} to SimulationMode {self.simulation_mode} and AdminMode.ONLINE"
            )
            try:
                proxy.simulationMode = self.simulation_mode
                proxy.adminMode = AdminMode.ONLINE

                board_ip = proxy.get_property("TalonDxBoardAddress")[
                    "TalonDxBoardAddress"
                ][0]
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to set AdminMode of {fqdn} to ONLINE: {df}"
                )

            # Update talon board HW config. The VCC ID to IP address mapping comes
            # from hw_config.yaml
            for vcc_id_str, ip in self._hw_config["talon_board"].items():
                if board_ip == ip:
                    vcc_id = int(vcc_id_str)
                    if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                        dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                        try:
                            proxy.vccID = vcc_id_str
                            proxy.dishID = dish_id
                            self.logger.info(
                                f"Assigned DISH ID {dish_id} and VCC ID {vcc_id} to {fqdn}"
                            )
                        except tango.DevFailed as df:
                            self.logger.error(
                                f"Failed to update {fqdn} with VCC ID and DISH ID; {df}"
                            )
                    else:
                        self.logger.warning(
                            f"DISH ID for VCC {vcc_id} not found in DISH-VCC mapping; "
                            f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                        )

    def _get_talon_fqdns(self: ControllerComponentManager) -> list[str]:
        """
        Get the FQDNs of the Talon LRU and board devices that are connected to hardware
        from the configuration JSON.

        :return: True if the FQDNs were found, False otherwise
        """
        # Read in list of LRUs from configuration JSON
        with open(f"{self._talondx_config_path}/talondx-config.json") as f:
            talondx_config_json = json.load(f)

        # Make these sets so as not to add duplicates
        fqdn_talon_lru = set()
        fqdn_talon_board = set()
        for config_command in talondx_config_json["config_commands"]:
            target = config_command["target"]
            for lru_id, lru_config in self._hw_config["talon_lru"].items():
                if target in [
                    lru_config["TalonDxBoard1"],
                    lru_config["TalonDxBoard2"],
                ]:
                    fqdn_talon_lru.add(f"mid_csp_cbf/talon_lru/{lru_id}")
                    fqdn_talon_board.add(f"mid_csp_cbf/talon_board/{target}")

        self._talon_lru_fqdn = list(fqdn_talon_lru)
        self._talon_board_fqdn = list(fqdn_talon_board)

    def _turn_on_lrus(
        self: ControllerComponentManager,
        task_abort_event: Optional[Event] = None,
    ) -> tuple[bool, str]:
        """
        Turn on all of the Talon LRUs

        :param task_abort_event: Event to signal task abort.
        :return: A tuple containing a boolean indicating success and a string with the FQDN of the LRUs that failed to turn on
        """
        success = True
        self.blocking_command_ids = set()
        for fqdn in self._talon_lru_fqdn:
            self.logger.info(f"Turning on LRU {fqdn}")
            lru = self._proxies[fqdn]
            try:
                [[result_code], [command_id]] = lru.On()
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    message = f"Nested LRC TalonLru.On() to {fqdn} rejected"
                    self.logger.error(message)
                    success = False
                    continue
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                message = f"Nested LRC TalonLru.On() to {fqdn} failed: {df}"
                self.logger.error(message)
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                success = False

            lrc_status = self.wait_for_blocking_results(
                task_abort_event=task_abort_event
            )
            if lrc_status != TaskStatus.COMPLETED:
                message = "One or more calls to nested LRC TalonLru.On() failed/timed out. Check TalonLru logs."
                self.logger.error(message)
                success = False
                break
            else:
                message = f"{len(self._talon_lru_fqdn)} TalonLru devices successfully turned on"
                self.logger.info(message)

        return (success, message)

    def _configure_slim_devices(
        self: ControllerComponentManager,
        task_abort_event: Optional[Event] = None,
    ) -> bool:
        """
        Configure the SLIM devices

        :param task_abort_event: Event to signal task abort.
        :return: True if the SLIM devices were successfully configured, False otherwise
        """
        self.logger.info(
            f"Setting SLIM simulation mode to {self.simulation_mode}"
        )
        success = True
        slim_config_paths = [
            self._fs_slim_config_path,
            self._vis_slim_config_path,
        ]
        self.blocking_command_ids = set()
        for i, fqdn in enumerate([self._fs_slim_fqdn, self._vis_slim_fqdn]):
            try:
                self._proxies[fqdn].simulationMode = self.simulation_mode
                [[result_code], [command_id]] = self._proxies[fqdn].On()
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    message = f"Nested LRC Slim.On() to {fqdn} rejected"
                    self.logger.error(message)
                    success = False
                    continue
                self.blocking_command_ids.add(command_id)

                with open(slim_config_paths[i]) as f:
                    slim_config = f.read()

                [[result_code], [command_id]] = self._proxies[fqdn].Configure(
                    slim_config
                )
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    message = f"Nested LRC Slim.Configure() to {fqdn} rejected"
                    self.logger.error(message)
                    success = False
                    continue
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                message = f"Failed to configure SLIM: {df}"
                self.logger.error(message)
                success = False
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
            except (OSError, FileNotFoundError) as e:
                message = f"Failed to read SLIM configuration file: {e}"
                self.logger.error(message)
                success = False
                # TODO: healthState instead of fault
                self._update_component_state(fault=True)

        lrc_status = self.wait_for_blocking_results(
            task_abort_event=task_abort_event
        )
        if lrc_status != TaskStatus.COMPLETED:
            message = "One or more calls to nested LRC Slim.Configure() failed/timed out. Check Slim logs."
            self.logger.error(message)
            success = False
        else:
            message = f"{len(slim_config_paths)} Slim devices successfully configured"
            self.logger.info(message)

        return (success, message)

    def is_on_allowed(self: ControllerComponentManager) -> bool:
        """
        Check if the On command is allowed.

        :return: True if the On command is allowed, else False.
        """
        self.logger.debug("Checking if on is allowed")

        if not self.is_communicating:
            return False
        if self.dish_utils is None:
            self.logger.warning("Dish-VCC mapping has not been provided.")
            return False
        if self.power_state == PowerState.OFF:
            return True

        self.logger.warning("Already on, do not need to turn on.")
        return False

    def _on(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Turn on the controller and its subordinate devices

        :param task_callback: Callback function to update task status.
        :param task_abort_event: Event to signal task abort.
        """

        self.logger.debug("Entering ControllerComponentManager.on")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        # The order of the following operations for ON is important:
        # 1. Power on all the Talon boards by
        #    i.  Get the FQDNs of the LRUs
        #    ii. Sending ON command to all the LRUs
        # 2. Configure all the Talon boards
        # 3. Turn TalonBoard devices ONLINE
        # 4. Configure SLIM Mesh devices

        # Get FQDNs of Talon devices with hardware targets
        if not self.simulation_mode:
            self._get_talon_fqdns()
        else:
            # Use a hard-coded example fqdn talon lru for simulationMode
            self._talon_lru_fqdn = [
                "mid_csp_cbf/talon_lru/001",
                "mid_csp_cbf/talon_lru/002",
            ]

        # Turn on all the LRUs with the boards we need
        lru_on_status, msg = self._turn_on_lrus(task_abort_event)
        if not lru_on_status:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                result=(ResultCode.FAILED, msg),
                status=TaskStatus.FAILED,
            )
            return

        # Configure all the Talon boards
        # Clears process inside the Talon Board to make it a clean state
        # Also sets the simulation mode of the Talon Boards based on TalonDx Component Manager's SimulationMode Attribute
        if (
            self._talondx_component_manager.configure_talons()
            == ResultCode.FAILED
        ):
            msg = "Failed to configure Talon boards"
            self.logger.error(msg)
            task_callback(
                result=(ResultCode.FAILED, msg),
                status=TaskStatus.FAILED,
            )
            return

        # Start monitoring talon board telemetries and fault status
        # Failure here won't cause On command failure
        self._init_talon_boards()

        # Configure SLIM Mesh devices
        slim_configure_status, msg = self._configure_slim_devices(
            task_abort_event
        )
        if not slim_configure_status:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                result=(ResultCode.FAILED, msg),
                status=TaskStatus.FAILED,
            )
            return

        self._update_component_state(power=PowerState.ON)
        task_callback(
            result=(ResultCode.OK, "On completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def on(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit on operation method to task executor queue.

        :param task_callback: Callback function to update task status
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._on,
            is_cmd_allowed=self.is_on_allowed,
            task_callback=task_callback,
        )

    # --- Off Command --- #

    def _subarray_to_empty(
        self: ControllerComponentManager,
        subarray: context.DeviceProxy,
    ) -> tuple[bool, str]:
        """
        Restart subarray observing state model to ObsState.EMPTY

        :param subarray: DeviceProxy of the subarray
        :return: A tuple containing a boolean indicating success and a string message
        """
        dev_name = subarray.dev_name()
        success, message = (
            True,
            f"{dev_name} successfully set to ObsState.EMPTY",
        )
        self.blocking_command_ids = set()

        try:
            if subarray.obsState in [ObsState.EMPTY]:
                return success, message

            # Can issue Abort if subarray is in any of the following states:
            if subarray.obsState in [
                ObsState.RESOURCING,
                ObsState.IDLE,
                ObsState.CONFIGURING,
                ObsState.READY,
                ObsState.SCANNING,
                ObsState.RESETTING,
            ]:
                [[result_code], [command_id]] = subarray.Abort()
                if result_code == ResultCode.REJECTED:
                    success = False
                    message = f"{subarray.dev_name()} Abort command rejected."
                    self.logger.error(message)
                else:
                    self.blocking_command_ids.add(command_id)

            # Restart subarray to send to EMPTY
            [[result_code], [command_id]] = subarray.Restart()
            if result_code == ResultCode.REJECTED:
                success = False
                message = f"{subarray.dev_name()} Restart command rejected."
                self.logger.error(message)
            else:
                self.blocking_command_ids.add(command_id)
        except tango.DevFailed as df:
            message = f"Failed to communicate with subarray {dev_name}; {df}"
            self.logger.error(message)
            success = False

        lrc_status = self.wait_for_blocking_results()
        if lrc_status != TaskStatus.COMPLETED:
            success = False
            message = "One or more calls to subarray LRC failed/timed out; check subarray logs."
            self.logger.error(message)

        return success, message

    def _turn_off_subelements(
        self: ControllerComponentManager,
        task_abort_event: Optional[Event] = None,
    ) -> tuple[bool, list[str]]:
        """
        Turn off all subelements of the controller

        :param task_abort_event: Event to signal task abort
        :return: A tuple containing a boolean indicating success and a list of messages
        """
        success = True
        message = []
        self.blocking_command_ids = set()

        # Turn off Slim devices
        for fqdn, slim in [
            (self._fs_slim_fqdn, self._proxies[self._fs_slim_fqdn]),
            (self._vis_slim_fqdn, self._proxies[self._vis_slim_fqdn]),
        ]:
            self.logger.info(f"Turning off SLIM controller {fqdn}")
            try:
                [[result_code], [command_id]] = slim.Off()
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    log_msg = f"Nested LRC Slim.Off() to {fqdn} rejected"
                    self.logger.error(log_msg)
                    message.append(log_msg)
                    success = False
                    continue
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                log_msg = f"Nested LRC Slim.Off() to {fqdn} failed: {df}"
                self.logger.error(log_msg)
                message.append(log_msg)
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                success = False

        lrc_status = self.wait_for_blocking_results(
            task_abort_event=task_abort_event
        )
        if lrc_status != TaskStatus.COMPLETED:
            log_msg = "One or more calls to nested LRC Off() failed/timed out. Check Slim logs."
            self.logger.error(log_msg)
            message.append(log_msg)
            success = False

        # Turn off TalonBoard devices.
        # NOTE: a failure here won't cause Controller.Off() to fail.
        try:
            for proxy in self._talon_board_proxies.values():
                proxy.adminMode = AdminMode.OFFLINE
        except tango.DevFailed as df:
            # Log a warning, but continue when the talon board fails to turn off
            log_msg = f"Failed to turn off Talon proxy; {df}"
            self.logger.warning(log_msg)
            message.append(log_msg)

        if success:
            message.append("Successfully issued Off() to all subelements.")
        return (success, message)

    def _check_subelements_off(
        self: ControllerComponentManager,
    ) -> tuple[list[str], list[str]]:
        """
        Verify that the subelements are in DevState.OFF, ObsState.EMPTY/IDLE

        :return: A tuple containing a list of subelements that are not in DevState.OFF and a list of subelements that are not in ObsState.EMPTY/IDLE
        """
        op_state_error_list = []
        obs_state_error_list = []
        for fqdn, proxy in self._proxies.items():
            self.logger.debug(f"Checking final state of device {fqdn}")
            # For some components under controller monitoring, including subarray,
            # power switch and VCC devices, they are in DevState.ON when
            # communicating with their component (AdminMode.ONLINE),
            # and in DevState.DISABLE when not (AdminMode.OFFLINE).

            # The following devices implement power On/Off commands:
            if fqdn in self._talon_lru_fqdn + [
                self._fs_slim_fqdn,
                self._vis_slim_fqdn,
            ]:
                try:
                    # TODO: CIP-1899 The controller is sometimes
                    # unable to read the State() of the talon_lru
                    # device server due to an error trying to
                    # acquire the serialization monitor. As a temporary
                    # workaround, the controller will log these
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

            if fqdn in self._subarray_fqdn:
                obs_state = proxy.obsState
                if obs_state != ObsState.EMPTY:
                    obs_state_error_list.append((fqdn, obs_state))

            if fqdn in self._vcc_fqdn:
                obs_state = proxy.obsState
                if obs_state != ObsState.IDLE:
                    obs_state_error_list.append((fqdn, obs_state))

        return (op_state_error_list, obs_state_error_list)

    def _turn_off_lrus(
        self: ControllerComponentManager,
        task_abort_event: Optional[Event] = None,
    ) -> tuple[bool, str]:
        """
        Turn off all of the Talon LRUs

        :param task_abort_event: Event to signal task abort
        :return: A tuple containing a boolean indicating success and a string with the FQDN of the LRUs that failed to turn off
        """
        success = True
        self.blocking_command_ids = set()
        for fqdn in self._talon_lru_fqdn:
            lru = self._proxies[fqdn]
            self.logger.info(f"Turning off LRU {fqdn}")
            try:
                [[result_code], [command_id]] = lru.Off()
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    message = f"Nested LRC TalonLru.Off() to {fqdn} rejected"
                    self.logger.error(message)
                    success = False
                    continue
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                message = f"Nested LRC TalonLru.Off() to {fqdn} failed: {df}"
                self.logger.error(message)
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                success = False

            lrc_status = self.wait_for_blocking_results(
                task_abort_event=task_abort_event
            )

            if lrc_status != TaskStatus.COMPLETED:
                message = "One or more calls to nested LRC TalonLru.Off() failed/timed out. Check TalonLru logs."
                self.logger.error(message)
                success = False
            else:
                message = f"{len(self._talon_lru_fqdn)} TalonLru devices successfully turned off"
                self.logger.info(message)

        return (success, message)

    def is_off_allowed(self: ControllerComponentManager) -> bool:
        """
        Check if the Off command is allowed

        :return: True if the Off command is allowed, False otherwise
        """
        self.logger.debug("Checking if off is allowed")
        if not self.is_communicating:
            return False
        if self.power_state == PowerState.ON:
            return True
        self.logger.info("Already off, do not need to turn off.")
        return False

    def _off(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Turn off the controller and its subordinate devices

        :param task_callback: Callback function to update task status
        :param task_abort_event: Event to signal task abort.
        """
        self.logger.debug("Entering ControllerComponentManager.off")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        (result_code, message) = (ResultCode.OK, [])

        # reset subarray observing state to EMPTY
        for subarray in [self._proxies[fqdn] for fqdn in self._subarray_fqdn]:
            (subarray_empty, log_msg) = self._subarray_to_empty(subarray)
            if not subarray_empty:
                self.logger.error(log_msg)
                message.append(log_msg)
                result_code = ResultCode.FAILED

        # turn off subelements
        (subelement_off, log_msg) = self._turn_off_subelements()
        message.extend(log_msg)
        if not subelement_off:
            result_code = ResultCode.FAILED

        # HPS master shutdown
        result = self._talondx_component_manager.shutdown()
        if result == ResultCode.FAILED:
            # if HPS master shutdown failed, continue with attempting to
            # shut off power outlets via LRU device
            log_msg = "HPS Master shutdown failed."
            self.logger.warning(log_msg)
            message.append(log_msg)

        # TalonLRU Off
        lru_off_status, log_msg = self._turn_off_lrus(task_abort_event)
        if not lru_off_status:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            message.append(log_msg)
            result_code = ResultCode.FAILED

        # Check final device states, log any errors
        (
            op_state_error_list,
            obs_state_error_list,
        ) = self._check_subelements_off()

        if len(op_state_error_list) > 0:
            for fqdn, state in op_state_error_list:
                log_msg = f"{fqdn} failed to turn OFF, current state: {state}"
                self.logger.error(log_msg)
                message.append(log_msg)
            result_code = ResultCode.FAILED

        if len(obs_state_error_list) > 0:
            for fqdn, obs_state in obs_state_error_list:
                log_msg = (
                    f"{fqdn} failed to restart, current obsState: {obs_state}"
                )
                self.logger.error(log_msg)
                message.append(log_msg)
            result_code = ResultCode.FAILED

        if result_code == ResultCode.OK:
            self._update_component_state(power=PowerState.OFF)
            task_callback(
                result=(ResultCode.OK, "Off completed OK"),
                status=TaskStatus.COMPLETED,
            )
        else:
            task_callback(
                result=(ResultCode.FAILED, "; ".join(message)),
                status=TaskStatus.COMPLETED,
            )
        return

    def off(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit off operation method to task executor queue.

        :param task_callback: Callback function to update task status
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )
