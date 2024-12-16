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

from ska_mid_cbf_tdc_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import const
from ska_mid_cbf_tdc_mcs.commons.validate_interface import validate_interface
from ska_mid_cbf_tdc_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_tdc_mcs.controller.talondx_component_manager import (
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

        # --- Max Capabilities --- #
        self._count_vcc = max_capabilities["VCC"]
        self._count_fsp = max_capabilities["FSP"]
        self._count_subarray = max_capabilities["Subarray"]
        # --- All FQDNs --- #
        self._subarray_fqdns_all = fqdn_dict["CbfSubarray"]
        self._vcc_fqdns_all = fqdn_dict["VCC"]
        self._fsp_fqdns_all = fqdn_dict["FSP"]
        self._talon_lru_fqdns_all = fqdn_dict["TalonLRU"]
        self._talon_board_fqdns_all = fqdn_dict["TalonBoard"]
        self._power_switch_fqdns_all = fqdn_dict["PowerSwitch"]

        # --- Used FQDNs --- #
        (
            self._vcc_fqdn,
            self._fsp_fqdn,
            self._subarray_fqdn,
            self._talon_lru_fqdn,
            self._talon_board_fqdn,
            self._power_switch_fqdn,
        ) = (set() for _ in range(6))

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

    # -------------
    # Communication
    # -------------

    # --- Start Communicating --- #

    def _filter_all_fqdns(self: ControllerComponentManager) -> None:
        """
        Update the list of all sub-element FQDNs to be used, filter by max capabilities count
        and HW config.

        :update: self._vcc_fqdns_all, self._fsp_fqdns_all, self._subarray_fqdns_all,
                 self._talon_lru_fqdns_all, self._talon_board_fqdns_all, self._power_switch_fqdns_all
        """
        # Observing/capability devices
        self._vcc_fqdns_all = list(self._vcc_fqdns_all)[: self._count_vcc]
        self._fsp_fqdns_all = list(self._fsp_fqdns_all)[: self._count_fsp]
        self._subarray_fqdns_all = list(self._subarray_fqdns_all)[
            : self._count_subarray
        ]

        def _filter_fqdn(all_domains: list[str], config_key: str) -> list[str]:
            return [
                domain
                for domain in all_domains
                if domain.split("/")[-1]
                in list(self._hw_config[config_key].keys())
            ]

        self._talon_lru_fqdns_all = _filter_fqdn(
            self._talon_lru_fqdns_all, "talon_lru"
        )
        self._talon_board_fqdns_all = _filter_fqdn(
            self._talon_board_fqdns_all, "talon_board"
        )
        self._power_switch_fqdns_all = _filter_fqdn(
            self._power_switch_fqdns_all, "power_switch"
        )

        all_fqdns = {
            "VCC": self._vcc_fqdns_all,
            "FSP": self._fsp_fqdns_all,
            "Subarray": self._subarray_fqdns_all,
            "Talon board": self._talon_board_fqdns_all,
            "Talon LRU": self._talon_lru_fqdns_all,
            "Power switch": self._power_switch_fqdns_all,
            "FS SLIM mesh": self._fs_slim_fqdn,
            "VIS SLIM mesh": self._vis_slim_fqdn,
        }

        for name, value in all_fqdns.items():
            self.logger.debug(f"All {name} FQDNs: {value}")

    def _set_used_fqdns(self: ControllerComponentManager) -> None:
        """
        Set the FQDNs of the sub-elements that are used based on talondx config.

        :update: self._talon_lru_fqdn, self._talon_board_fqdn
        """
        # Make these sets so as not to add duplicates
        self._talon_board_fqdn = set()
        self._vcc_fqdn = set()
        self._fsp_fqdn = set()
        self._talon_lru_fqdn = set()
        self._power_switch_fqdn = set()
        self._subarray_fqdn = set(self._subarray_fqdns_all)

        # Find used talon from talondx config, then find corresponding sub-element FQDNs from HW config
        for config_command in self.talondx_config_json["config_commands"]:
            target = config_command["target"]
            for lru_id, lru_config in self._hw_config["talon_lru"].items():
                if target in [
                    lru_config["TalonDxBoard1"],
                    lru_config["TalonDxBoard2"],
                ]:
                    self._talon_board_fqdn.add(
                        f"mid_csp_cbf/talon_board/{int(target):03d}"
                    )
                    self._vcc_fqdn.add(f"mid_csp_cbf/vcc/{int(target):03d}")
                    # TODO: refactor post AA1, once Talon/FPGA indices out-scale FSP indices
                    self._fsp_fqdn.add(f"mid_csp_cbf/fsp/{int(target):02d}")

                    self._talon_lru_fqdn.add(
                        f"mid_csp_cbf/talon_lru/{int(lru_id):03d}"
                    )
                    for power_switch_id in [
                        lru_config["PDU1"],
                        lru_config["PDU2"],
                    ]:
                        self._power_switch_fqdn.add(
                            f"mid_csp_cbf/power_switch/{int(power_switch_id):03d}"
                        )

        used_fqdns = {
            "VCC": self._vcc_fqdn,
            "FSP": self._fsp_fqdn,
            "Subarray": self._subarray_fqdn,
            "Talon board": self._talon_board_fqdn,
            "Talon LRU": self._talon_lru_fqdn,
            "Power switch": self._power_switch_fqdn,
            "FS SLIM mesh": self._fs_slim_fqdn,
            "VIS SLIM mesh": self._vis_slim_fqdn,
        }

        for name, value in used_fqdns.items():
            self.logger.debug(f"Used {name} FQDNs: {value}")

    def _write_hw_config(
        self: ControllerComponentManager,
        fqdn: str,
        device_type: str,
    ) -> bool:
        """
        Write hardware configuration properties to the device

        :param fqdn: FQDN of the device
        :param device_type: Type of the device. Can be one of "power_switch", "talon_lru", or "talon_board".
        :return: True if the hardware configuration properties are successfully written to the device, False otherwise.
        """
        try:
            self.logger.info(
                f"Writing hardware configuration properties to {fqdn}"
            )
            proxy = self._proxies[fqdn]
            device_id = fqdn.split("/")[-1]

            if device_type == "talon_board":
                device_config = {
                    "TalonDxBoardAddress": self._hw_config[device_type][
                        device_id
                    ]
                }
                # Update board's VCC and DISH IDs
                # VCC ID maps one-to-one with Talon board ID
                vcc_id = int(device_id)
                if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                    dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                    try:
                        proxy.vccID = device_id
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
                        f"DISH ID for Talon {device_id} not found in DISH-VCC mapping; "
                        f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                    )
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

    def _set_proxy_not_fitted(
        self: ControllerComponentManager,
        fqdn: str,
    ) -> bool:
        """
        Set the AdminMode of the component device to NOT_FITTED, given the FQDN of the device

        :param fqdn: FQDN of the component device
        :return: True if the AdminMode of the device is successfully set to NOT_FITTED, False otherwise.
        """
        self.logger.info(f"Setting {fqdn} to AdminMode.NOT_FITTED")

        try:
            self._proxies[fqdn].adminMode = AdminMode.NOT_FITTED
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to set AdminMode of {fqdn} to NOT_FITTED: {df}"
            )
            return False

        return True

    def _init_device_proxy(
        self: ControllerComponentManager,
        fqdn: str,
        subscribe_results: bool = False,
        subscribe_state: bool = False,
        hw_device_type: str = None,
    ) -> bool:
        """
        Initialize the device proxy from its FQDN, store the proxy in the _proxies dictionary,
        and set the AdminMode to ONLINE

        :param fqdn: FQDN of the device
        :param subscribe_results: True if should subscribe to the device's longRunningCommandResult attribute;
            defaults to False
        :param subscribe_state: True if should subscribe to the device's state attribute;
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

        if subscribe_results:
            self.attr_event_subscribe(
                proxy=proxy,
                attr_name="longRunningCommandResult",
                callback=self.results_callback,
            )

        if subscribe_state:
            # Set latest stored sub-device state values to UNKNOWN prior to subscription
            with self._attr_event_lock:
                self._op_states[fqdn] = tango.DevState.UNKNOWN
            self.attr_event_subscribe(
                proxy=proxy, attr_name="state", callback=self.op_state_callback
            )

        if hw_device_type is not None:
            if not self._write_hw_config(fqdn, hw_device_type):
                return False

        used_fqdns = self._vcc_fqdn.union(
            self._fsp_fqdn,
            self._subarray_fqdn,
            self._talon_lru_fqdn,
            self._talon_board_fqdn,
            self._power_switch_fqdn,
            {self._fs_slim_fqdn, self._vis_slim_fqdn},
        )

        if fqdn in used_fqdns:
            # TODO: Untangle adminMode init. For now, skip setting FSP/VCC online as should be handled by subarray.
            if fqdn in self._fsp_fqdn | self._vcc_fqdn:
                return True
            return self._set_proxy_online(fqdn)
        else:
            return self._set_proxy_not_fitted(fqdn)

    def _init_device_proxies(self: ControllerComponentManager) -> bool:
        """
        Initialize all device proxies.

        :return: True if the device proxies are all successfully initialized, False otherwise.
        """
        init_success = True

        # Order matters here; must set PDU online before LRU to establish outlet power states
        for fqdn in self._power_switch_fqdns_all:
            if not self._init_device_proxy(
                fqdn=fqdn, hw_device_type="power_switch"
            ):
                init_success = False

        # We subscribe to Talon LRU state in order to check the complete/partial success
        # of the On/Off commands
        for fqdn in self._talon_lru_fqdns_all:
            if not self._init_device_proxy(
                fqdn=fqdn,
                subscribe_results=True,
                subscribe_state=True,
                hw_device_type="talon_lru",
            ):
                init_success = False

        for fqdn in self._subarray_fqdns_all:
            if not self._init_device_proxy(fqdn=fqdn, subscribe_results=True):
                init_success = False

        for fqdn in self._fsp_fqdns_all:
            if not self._init_device_proxy(fqdn=fqdn, subscribe_results=True):
                init_success = False

        for fqdn in self._vcc_fqdns_all:
            if not self._init_device_proxy(fqdn=fqdn):
                init_success = False

        for fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]:
            if not self._init_device_proxy(
                fqdn=fqdn,
                subscribe_results=True,
                subscribe_state=True,
            ):
                init_success = False

        return init_success

    def _set_fsp_function_mode(
        self: ControllerComponentManager, to_idle: bool = False
    ) -> bool:
        """
        Set FSP function mode based on talondx_config JSON

        :param to_idle: set to True if return FSPs to IDLE mode; defaults to False
        :return: True if the FSP function mode is successfully set, False otherwise.
        """
        self.blocking_command_ids = set()
        for config_command in self.talondx_config_json["config_commands"]:
            if to_idle:
                fsp_mode = "IDLE"
            else:
                fsp_mode = config_command["fpga_bitstream_fsp_mode"].upper()
            self.logger.info(f"Setting FSP function mode to {fsp_mode}")

            target = int(config_command["target"])
            fsp_fqdn = f"mid_csp_cbf/fsp/{target:02d}"
            if fsp_fqdn not in self._fsp_fqdn:
                self.logger.error(
                    f"{fsp_fqdn} was requested but is not part of CBF capabilities; available FSPs: {self._fsp_fqdn}"
                )
                return False

            fsp_proxy = self._proxies[fsp_fqdn]

            try:
                [[result_code], [command_id]] = fsp_proxy.SetFunctionMode(
                    fsp_mode
                )
                if result_code == ResultCode.REJECTED:
                    raise tango.DevFailed("SetFunctionMode command rejected")
            except tango.DevFailed as df:
                self.logger.error(f"Error in assigning FSP Mode: {df}")
                return False

            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results()
        if lrc_status != TaskStatus.COMPLETED:
            self.logger.error(
                "All Fsp.SetFunctionMode() LRC calls failed/timed out. Check Fsp logs."
            )
            return False

        self.logger.info("Successfully set all FSP function modes")
        return True

    def _start_communicating(
        self: ControllerComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for start_communicating operation.
        """
        self.logger.info(
            "Entering ControllerComponentManager._start_communicating"
        )

        # Read the HW config YAML
        try:
            with open(self._hw_config_path) as yaml_fd:
                self._hw_config = yaml.safe_load(yaml_fd)
        except FileNotFoundError as e:
            self.logger.error(
                f"Failed to read HW config file at {self._hw_config_path}: {e}"
            )
            return
        self._filter_all_fqdns()  # Filter all FQDNs by hw config and max capabilities

        # Read the talondx config JSON
        self.logger.debug(f"Controller simulationMode: {self.simulation_mode}")
        if not self.simulation_mode:
            try:
                with open(
                    f"{self._talondx_config_path}/talondx-config.json"
                ) as f:
                    self.talondx_config_json = json.load(f)
            except FileNotFoundError as e:
                self.logger.error(
                    f"Failed to read talondx-config file at {self._talondx_config_path}: {e}"
                )
                return
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode talondx-config JSON: {e}")
                return
        else:
            # TODO: Controller hard coded to only be in CORR while in simulation mode. Should use other modes too.
            self.talondx_config_json = {
                "config_commands": [
                    {
                        "target": f"{t+1:03d}",
                        "fpga_bitstream_fsp_mode": "corr",
                    }
                    for t in range(self._count_fsp)
                ]
            }
        self.logger.debug(f"Talon-DX config JSON: {self.talondx_config_json}")

        # Set the used FQDNs by talondx config
        self._set_used_fqdns()

        # Initialize device proxies
        if not self._init_device_proxies():
            self.logger.error("Failed to initialize proxies.")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        self.logger.info(
            f"event_ids after subscribing = {len(self.event_ids)}"
        )

        # Set FSP function mode
        if not self._set_fsp_function_mode():
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

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

        # Set FSPs to IDLE
        if not self._set_fsp_function_mode(to_idle=True):
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        for fqdn, proxy in self._proxies.items():
            try:
                if (
                    fqdn
                    in self._subarray_fqdn
                    | self._fsp_fqdn
                    | self._talon_lru_fqdn
                    | {
                        self._fs_slim_fqdn,
                        self._vis_slim_fqdn,
                    }
                ):
                    self.unsubscribe_all_events(proxy)

                self.logger.info(f"Setting {fqdn} to AdminMode.OFFLINE")
                proxy.adminMode = AdminMode.OFFLINE
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to stop communications with {fqdn}; {df}"
                )
                continue

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

                vcc_proxy = self._proxies[fqdn]
                vcc_id = int(vcc_proxy.get_property("DeviceID")["DeviceID"][0])
                if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                    dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                    vcc_proxy.dishID = dish_id
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
            f"InitSysParam command cannot be issued because the current PowerState ({self.power_state}) is not OFF."
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

    def _turn_on_lrus(
        self: ControllerComponentManager,
        task_abort_event: Optional[Event] = None,
    ) -> tuple[bool, str]:
        """
        Turn on the Talon LRUs

        :param task_abort_event: Event to signal task abort.
        :return: True if any LRUs were successfully turned on, otherwise False
        """
        # Determine which LRUs must be turned on by checking which current states are OFF
        lru_to_power = []
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if (
                    fqdn in self._talon_lru_fqdn
                    and state == tango.DevState.OFF
                ):
                    lru_to_power.append(fqdn)

        self.blocking_command_ids = set()
        for fqdn in lru_to_power:
            self.logger.info(f"Turning on LRU {fqdn}")
            lru = self._proxies[fqdn]
            try:
                [[result_code], [command_id]] = lru.On()
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    raise tango.DevFailed("On command rejected")
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                self.logger.error(
                    f"Nested LRC TalonLru.On() to {fqdn} failed: {df}"
                )
                continue

        if len(self.blocking_command_ids) == 0:
            lrc_status = TaskStatus.FAILED
        else:
            lrc_status = self.wait_for_blocking_results(
                task_abort_event=task_abort_event, partial_success=True
            )
        if lrc_status != TaskStatus.COMPLETED:
            self.logger.error(
                "All TalonLru.On() LRC calls failed/timed out. Check TalonLru logs."
            )
            return False

        # Determine which LRUs were successfully turned on by verifying latest states
        num_lru = 0
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if fqdn in lru_to_power and state == tango.DevState.ON:
                    num_lru += 1
        self.logger.info(
            f"{num_lru} out of {len(lru_to_power)} TalonLru devices successfully turned on"
        )

        return True

    def _configure_slim_devices(
        self: ControllerComponentManager,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Configure the SLIM devices

        :param task_abort_event: Event to signal task abort.
        """
        slim_config_paths = [
            self._fs_slim_config_path,
            self._vis_slim_config_path,
        ]

        self.blocking_command_ids = set()

        slim_to_power = []
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if (
                    fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]
                    and state == tango.DevState.OFF
                ):
                    slim_to_power.append(fqdn)

        for index, fqdn in enumerate(
            [self._fs_slim_fqdn, self._vis_slim_fqdn]
        ):
            try:
                if fqdn in slim_to_power:
                    self.logger.info(f"Turning on SLIM controller {fqdn}")
                    [[result_code], [command_id]] = self._proxies[fqdn].On()
                    # Guard incase LRC was rejected.
                    if result_code == ResultCode.REJECTED:
                        raise tango.DevFailed("On command rejected")
                    self.blocking_command_ids.add(command_id)

                self.logger.info(f"Configuring SLIM controller {fqdn}")
                with open(slim_config_paths[index]) as f:
                    slim_config = f.read()

                [[result_code], [command_id]] = self._proxies[fqdn].Configure(
                    slim_config
                )
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    raise tango.DevFailed("Configure command rejected")
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                self.logger.error(f"Failed to configure {fqdn}: {df}")
                continue
            except (OSError, FileNotFoundError) as e:
                self.logger.error(
                    f"Failed to read SLIM configuration file: {e}"
                )
                continue

        if len(self.blocking_command_ids) == 0:
            lrc_status = TaskStatus.FAILED
        else:
            lrc_status = self.wait_for_blocking_results(
                task_abort_event=task_abort_event, partial_success=True
            )
        if lrc_status != TaskStatus.COMPLETED:
            self.logger.error(
                "All Slim.Configure() LRC calls failed/timed out. Check Slim logs."
            )
        else:
            self.logger.info("Some/all Slim devices successfully configured.")

    def is_on_allowed(self: ControllerComponentManager) -> bool:
        """
        Check if the On command is allowed.

        :return: True if the On command is allowed, else False.
        """
        self.logger.debug("Checking if On is allowed")

        if not self.is_communicating:
            return False
        if self.dish_utils is None:
            self.logger.warning("Dish-VCC mapping has not been provided.")
            return False
        if self.power_state not in [PowerState.ON, PowerState.OFF]:
            self.logger.warning(
                f"Current power state: {self.power_state}; try re-establishing component communications."
            )
            return False

        return True

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
        # 1. Power on all the Talon boards by sending ON command to all the LRUs
        # 2. Configure all the Talon boards
        # 3. Turn TalonBoard devices ONLINE
        # 4. Configure SLIM Mesh devices

        # Turn on all the LRUs with the boards we need
        lru_on_status = self._turn_on_lrus(task_abort_event)
        if lru_on_status:
            # Update state to ON if at least one LRU succeeded in powering on
            self._update_component_state(power=PowerState.ON)
        else:
            # If no LRU succeeds in turning on, this will fail the command
            task_callback(
                result=(ResultCode.FAILED, "Failed to turn on Talon LRU(s)"),
                status=TaskStatus.FAILED,
            )
            return

        # Determine which boards are successfully turned on and ready to configure
        # by checking latest LRU states
        available_talon_targets = []
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if fqdn in self._talon_lru_fqdn and state == tango.DevState.ON:
                    lru_id = fqdn.split("/")[-1]
                    lru_config = self._hw_config["talon_lru"][lru_id]
                    available_talon_targets.append(lru_config["TalonDxBoard1"])
                    available_talon_targets.append(lru_config["TalonDxBoard2"])

        # Configure all the Talon boards; first clears any currently running
        # device processes on the HPS
        if (
            self._talondx_component_manager.configure_talons(
                available_talon_targets
            )
            == ResultCode.FAILED
        ):
            self.logger.error("Failed to configure Talon boards")

        # Start monitoring talon board telemetries and fault status
        for fqdn in self._talon_board_fqdn:
            self._init_device_proxy(
                fqdn=fqdn,
                hw_device_type="talon_board",
            )

        # Configure SLIM Mesh devices
        self._configure_slim_devices(task_abort_event)

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
        (success, message) = (
            True,
            f"{dev_name} successfully set to ObsState.EMPTY",
        )
        self.blocking_command_ids = set()

        try:
            if subarray.obsState in [ObsState.EMPTY]:
                return (success, message)

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
                    raise tango.DevFailed("Abort command rejected")
                self.blocking_command_ids.add(command_id)

            # Restart subarray to send to EMPTY
            [[result_code], [command_id]] = subarray.Restart()
            if result_code == ResultCode.REJECTED:
                raise tango.DevFailed("Restart command rejected")
            self.blocking_command_ids.add(command_id)
        except tango.DevFailed as df:
            message = f"Failed to communicate with subarray {dev_name}; {df}"
            self.logger.error(message)
            success = False

        if len(self.blocking_command_ids) == 0:
            lrc_status = TaskStatus.FAILED
        else:
            lrc_status = self.wait_for_blocking_results()
        if lrc_status != TaskStatus.COMPLETED:
            success = False
            message = "One or more calls to subarray LRC failed/timed out; check subarray logs."
            self.logger.error(message)

        return (success, message)

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

        slim_to_power = []
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if (
                    fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]
                    and state == tango.DevState.ON
                ):
                    slim_to_power.append(fqdn)

        # Turn off Slim devices
        for fqdn, slim in [
            (self._fs_slim_fqdn, self._proxies[self._fs_slim_fqdn]),
            (self._vis_slim_fqdn, self._proxies[self._vis_slim_fqdn]),
        ]:
            try:
                if fqdn in slim_to_power:
                    self.logger.info(f"Turning off SLIM controller {fqdn}")
                    [[result_code], [command_id]] = slim.Off()
                    # Guard incase LRC was rejected.
                    if result_code == ResultCode.REJECTED:
                        raise tango.DevFailed("Off command rejected")
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
            for proxy in [
                self._proxies[fqdn] for fqdn in self._talon_board_fqdn
            ]:
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
            if fqdn in self._talon_lru_fqdn | {self._fs_slim_fqdn} | {
                self._vis_slim_fqdn
            }:
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
        Turn off a given list of Talon LRUs

        :param task_abort_event: Event to signal task abort.
        :return: True if any LRUs were successfully turned off, otherwise False
        """
        # Determine which LRUs must be turned off
        lru_to_power = []
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if fqdn in self._talon_lru_fqdn and state == tango.DevState.ON:
                    lru_to_power.append(fqdn)

        self.blocking_command_ids = set()
        for fqdn in lru_to_power:
            lru = self._proxies[fqdn]
            self.logger.info(f"Turning off LRU {fqdn}")
            try:
                [[result_code], [command_id]] = lru.Off()
                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    raise tango.DevFailed("Off command rejected")
                self.blocking_command_ids.add(command_id)
            except tango.DevFailed as df:
                self.logger.error(
                    f"Nested LRC TalonLru.Off() to {fqdn} failed: {df}"
                )
                continue

        if len(self.blocking_command_ids) == 0:
            lrc_status = TaskStatus.FAILED
        else:
            lrc_status = self.wait_for_blocking_results(
                task_abort_event=task_abort_event, partial_success=True
            )
        if lrc_status != TaskStatus.COMPLETED:
            self.logger.error(
                "All TalonLru.Off() LRC calls failed/timed out. Check TalonLru logs."
            )
            return False

        num_lru = 0
        with self._attr_event_lock:
            for fqdn, state in self._op_states.items():
                if fqdn in lru_to_power and state == tango.DevState.OFF:
                    num_lru += 1
        self.logger.info(
            f"{num_lru} out of {len(lru_to_power)} TalonLru devices successfully turned off"
        )

        return True

    def is_off_allowed(self: ControllerComponentManager) -> bool:
        """
        Check if the Off command is allowed

        :return: True if the Off command is allowed, False otherwise
        """
        self.logger.debug("Checking if Off is allowed")

        if not self.is_communicating:
            return False
        if self.power_state not in [PowerState.ON, PowerState.OFF]:
            self.logger.warning(
                f"Current power state: {self.power_state}; try re-establishing component communications."
            )
            return False

        return True

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
        for fqdn in self._subarray_fqdn:
            (subarray_empty, log_msg) = self._subarray_to_empty(
                self._proxies[fqdn]
            )
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
        lru_off_status = self._turn_off_lrus(task_abort_event)
        if not lru_off_status:
            log_msg = "LRU Off failed."
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
