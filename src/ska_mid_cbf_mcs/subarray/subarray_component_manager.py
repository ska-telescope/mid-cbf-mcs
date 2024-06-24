# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
CbfSubarray
Sub-element subarray device for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

import concurrent.futures
import copy
import functools
import json
import sys
from threading import Event, Lock, Thread
from typing import Callable, Optional

# Tango imports
import tango
from ska_control_model import (
    AdminMode,
    CommunicationStatus,
    ObsState,
    PowerState,
    ResultCode,
    TaskStatus,
)
from ska_tango_base.base.base_component_manager import check_communicating
from ska_tango_testing import context
from ska_telmodel.schema import validate as telmodel_validate

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import (
    FspModes,
    const,
    freq_band_dict,
    mhz_to_hz,
    vcc_oversampling_factor,
)
from ska_mid_cbf_mcs.component.obs_component_manager import (
    CbfObsComponentManager,
)


class CbfSubarrayComponentManager(CbfObsComponentManager):
    """A component manager for the CbfSubarray class."""

    def __init__(
        self: CbfSubarrayComponentManager,
        *args: any,
        subarray_id: int,
        controller: str,
        vcc: list[str],
        fsp: list[str],
        fsp_corr_sub: list[str],
        talon_board: list[str],
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param subarray_id: ID of subarray
        :param controller: FQDN of controller device
        :param vcc: FQDNs of subordinate VCC devices
        :param fsp: FQDNs of subordinate FSP devices
        :param fsp_corr_sub: FQDNs of subordinate FSP CORR subarray devices
        :param talon_board: FQDNs of talon board devices
        """
        super().__init__(*args, **kwargs)

        self.obs_state = ObsState.EMPTY

        self._dish_utils = None

        self.subarray_id = subarray_id
        self._fqdn_controller = controller
        self._fqdn_vcc = vcc
        self._fqdn_fsp = fsp
        self._fqdn_fsp_corr_subarray_device = fsp_corr_sub
        self._fqdn_talon_board_device = talon_board

        # initialize attribute values
        self._sys_param_str = ""
        self.dish_ids = set()
        self.vcc_ids = set()
        self.frequency_band = 0

        # store list of fsp configurations being used for each function mode
        self._corr_config = []

        self._last_received_delay_model = ""

        self._delay_model_lock = Lock()

        # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
        self._events_telstate = {}

        # for easy device-reference
        self.rfi_flagging_mask = {}
        self.frequency_band_offset_stream1 = 0
        self.frequency_band_offset_stream2 = 0
        self._stream_tuning = [0, 0]

        # device proxy for easy reference to CBF controller
        self._proxy_cbf_controller = None
        self._controller_max_capabilities = {}
        self._count_vcc = 0
        self._count_fsp = 0

        # proxies to subordinate devices
        self._all_vcc_proxies = []
        self._assigned_vcc_proxies = set()
        self._proxies_fsp = []
        self._proxies_fsp_corr_subarray_device = []
        self._proxies_talon_board_device = []

        # group proxies to subordinate devices
        # Note: VCC connected both individual and in group
        self._assigned_fsp_proxies = set()
        self._assigned_fsp_corr_proxies = set()

    def _init_controller_proxy(self: CbfSubarrayComponentManager) -> bool:
        """
        Initialize proxy to controller device, read MaxCapabilities property

        :return: True if initialization failed, otherwise False
        """
        try:
            if self._proxy_cbf_controller is None:
                self._proxy_cbf_controller = context.DeviceProxy(
                    device_name=self._fqdn_controller
                )
                # TODO: can read max capabilities attribute?
                self._controller_max_capabilities = dict(
                    pair.split(":")
                    for pair in self._proxy_cbf_controller.get_property(
                        "MaxCapabilities"
                    )["MaxCapabilities"]
                )
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return True

        self._count_vcc = int(self._controller_max_capabilities["VCC"])
        self._count_fsp = int(self._controller_max_capabilities["FSP"])

        self._fqdn_vcc = self._fqdn_vcc[: self._count_vcc]
        self._fqdn_fsp = self._fqdn_fsp[: self._count_fsp]
        self._fqdn_fsp_corr_subarray_device = (
            self._fqdn_fsp_corr_subarray_device[: self._count_fsp]
        )

        return False

    def _init_subelement_proxies(self: CbfSubarrayComponentManager) -> bool:
        """
        Initialize proxies to FSP and VCC subelements

        :return: True if initialization failed, otherwise False
        """
        try:
            if len(self._all_vcc_proxies) == 0:
                self._all_vcc_proxies = [
                    context.DeviceProxy(device_name=fqdn)
                    for fqdn in self._fqdn_vcc
                ]

            if len(self._proxies_fsp) == 0:
                self._proxies_fsp = [
                    context.DeviceProxy(device_name=fqdn)
                    for fqdn in self._fqdn_fsp
                ]

            if len(self._proxies_fsp_corr_subarray_device) == 0:
                for fqdn in self._fqdn_fsp_corr_subarray_device:
                    proxy = context.DeviceProxy(device_name=fqdn)
                    self._proxies_fsp_corr_subarray_device.append(proxy)

            if len(self._proxies_talon_board_device) == 0:
                for fqdn in self._fqdn_talon_board_device:
                    proxy = context.DeviceProxy(device_name=fqdn)
                    self._proxies_talon_board_device.append(proxy)

            for proxy in self._proxies_fsp_corr_subarray_device:
                proxy.adminMode = AdminMode.ONLINE

        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return True

        return False

    def start_communicating(self: CbfSubarrayComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        self.logger.debug(
            "Entering CbfSubarrayComponentManager.start_communicating"
        )

        if self.is_communicating:
            self.logger.info("Already connected.")
            return

        controller_failure = self._init_controller_proxy()
        if controller_failure:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        subelement_failure = self._init_subelement_proxies()
        if subelement_failure:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        super().start_communicating()
        self._update_component_state(power=PowerState.OFF)

    def stop_communicating(self: CbfSubarrayComponentManager) -> None:
        """Stop communication with the component."""
        self.logger.debug(
            "Entering CbfSubarrayComponentManager.stop_communicating"
        )
        try:
            for proxy in self._proxies_fsp_corr_subarray_device:
                proxy.adminMode = AdminMode.OFFLINE
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        super().stop_communicating()

    @check_communicating
    def on(self: CbfSubarrayComponentManager) -> None:
        """
        Turn on FSP function mode subarray devices
        """
        on_failure = False
        for result_code, msg in self._issue_group_command(
            command_name="On", proxies=self._proxies_fsp_corr_subarray_device
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                on_failure = True

        if on_failure:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return (ResultCode.FAILED, "Failed to turn on FSP CORR devices")

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    @check_communicating
    def off(self: CbfSubarrayComponentManager) -> None:
        """
        Turn off FSP function mode subarray devices
        """
        off_failure = False
        for result_code, msg in self._issue_group_command(
            command_name="Off", proxies=self._proxies_fsp_corr_subarray_device
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                off_failure = True

        if off_failure:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return (ResultCode.FAILED, "Failed to turn off FSP CORR devices")

        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off completed OK")

    def update_sys_param(
        self: CbfSubarrayComponentManager, sys_param_str: str
    ) -> None:
        """
        Reload sys param from input JSON

        :param sys_param_str: sys params JSON string
        """
        self.logger.debug(f"Received sys param: {sys_param_str}")
        self._sys_param_str = sys_param_str
        sys_param = json.loads(sys_param_str)
        self._dish_utils = DISHUtils(sys_param)
        self.logger.info(
            "Updated DISH ID to VCC ID and frequency offset k mapping"
        )

    def _update_delay_model(
        self: CbfSubarrayComponentManager, model: str
    ) -> None:
        """
        Update FSP and VCC delay models.

        :param model: delay model JSON string
        """
        # This method is always called on a separate thread
        self.logger.info(f"Updating delay model ...{model}")

        # we lock the mutex, forward the configuration, then immediately unlock it
        with self._delay_model_lock:
            results_vcc = self._issue_group_command(
                command_name="UpdateDelayModel",
                proxies=list(self._assigned_vcc_proxies),
                argin=model,
            )
            results_fsp = self._issue_group_command(
                command_name="UpdateDelayModel",
                proxies=list(self._assigned_fsp_proxies),
                argin=model,
            )

        for result_code, msg in results_vcc + results_fsp:
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)

    @check_communicating
    def _delay_model_event_callback(
        self: CbfSubarrayComponentManager, event_data: tango.EventData
    ) -> None:
        """ "
        Callback for delayModel change event subscription.

        :param event_data: the received change event data
        """
        self.logger.debug("Entering _delay_model_event_callback()")

        value = event_data.attr_value.value

        if value is None:
            self.logger.error(
                f"Delay model callback: None value received; {event_data}"
            )
            return
        if self.obs_state != ObsState.READY:
            log_msg = f"Ignoring delay model (obsState not correct). Delay model being passed in is: {value}"
            self.logger.warning(log_msg)
            return

        try:
            self.logger.info("Received delay model update.")

            if value == self._last_received_delay_model:
                log_msg = "Ignoring delay model (identical to previous)."
                self.logger.warning(log_msg)
                return

            self._last_received_delay_model = value
            delay_model_json = json.loads(value)

            # Validate delay_model_json against the telescope model
            self.logger.info(
                f"Attempting to validate the following json against the telescope model: {delay_model_json}"
            )
            try:
                telmodel_validate(
                    version=delay_model_json["interface"],
                    config=delay_model_json,
                    strictness=1,
                )
                self.logger.info("Delay model is valid!")
            except ValueError as e:
                self.logger.error(
                    f"Delay model validation against the telescope model failed with the following exception:\n {e}."
                )
                # TODO: should this cause obs fault, or just ignore and move on?
                # self._update_component_state(obsfault=True)

            # pass DISH ID as VCC ID integer to FSPs and VCCs
            for delay_detail in delay_model_json["receptor_delays"]:
                dish_id = delay_detail["receptor"]
                delay_detail["receptor"] = self._dish_utils.dish_id_to_vcc_id[
                    dish_id
                ]
            t = Thread(
                target=self._update_delay_model,
                args=(json.dumps(delay_model_json),),
            )
            t.start()
        except Exception as e:
            self.logger.error(str(e))

    #####################
    # Resourcing Commands
    #####################

    def _get_talon_proxy_from_dish_id(
        self: CbfSubarrayComponentManager,
        dish_id: str,
    ) -> context.DeviceProxy:
        """
        Return Talon board device proxy matching input DISH ID

        :param dish_id: the DISH ID
        :return: proxy to Talon board device, or None if failed to initialize proxy
        """
        for proxy in self._proxies_talon_board_device:
            board_dish_id = proxy.dishID
            if board_dish_id == dish_id:
                return proxy
        self.logger.error(
            f"Couldn't find Talon board device with DISH ID {dish_id}; "
            + "unable to update TalonBoard device subarrayID for this DISH."
        )
        # Talon board proxy not essential to scan operation, so we log an error
        # but don't cause a failure
        # return None here to fail conditionals later
        return None

    def is_assign_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """Check if AddReceptors command is allowed in current state"""
        self.logger.debug("Checking if AddReceptors is allowed.")
        if self.obs_state not in [ObsState.EMPTY, ObsState.IDLE]:
            self.logger.warning(
                f"AddReceptors not allowed in ObsState {self.obs_state}; "
                + "must be in ObsState.EMPTY or IDLE"
            )
            return False
        return True

    def _assign_vcc_thread(
        self: CbfSubarrayComponentManager,
        vcc_proxy: context.DeviceProxy,
        talon_proxy: context.DeviceProxy,
    ) -> bool:
        """
        Thread to perform individual VCC assignment.

        :param vcc_proxy: proxy to VCC
        :param talon_proxy: proxy to Talon board device with matching DISH ID
        :return: True if successfully assigned VCC proxy, otherwise False
        """
        try:
            # Setting simulation mode of VCC proxies based on simulation mode of subarray
            vcc_fqdn = vcc_proxy.dev_name()
            self.logger.info(
                f"Writing {vcc_fqdn} simulation mode to: {self.simulation_mode}"
            )
            vcc_proxy.adminMode = AdminMode.OFFLINE
            vcc_proxy.simulationMode = self.simulation_mode
            vcc_proxy.adminMode = AdminMode.ONLINE
            vcc_proxy.On()

            # change subarray membership of vcc
            vcc_proxy.subarrayMembership = self.subarray_id
            self.logger.debug(
                f"{vcc_fqdn}.subarrayMembership: "
                + f"{vcc_proxy.subarrayMembership}"
            )

            # assign the subarray ID to the talon board with the matching DISH ID
            if talon_proxy is not None:
                talon_proxy.subarrayID = str(self.subarray_id)

            return True
        except tango.DevFailed as df:
            self.logger.error(f"Failed to assign VCC; {df}")
            return False

    def _assign_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Add receptors/dishes to subarray.

        :param argin: The list of DISH (receptor) IDs to be assigned
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "AddReceptors", task_callback, task_abort_event
        ):
            return

        input_dish_valid, msg = self._dish_utils.are_Valid_DISH_Ids(argin)
        if not input_dish_valid:
            task_callback(
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, msg),
            )
            return

        # build list of VCCs to assign
        vcc_proxies = []
        talon_proxies = []
        dish_ids_to_add = []
        vcc_ids_to_add = []
        for dish_id in argin:
            self.logger.debug(f"Attempting to add receptor {dish_id}")

            if dish_id in self._dish_utils.dish_id_to_vcc_id.keys():
                vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            else:
                self.logger.warning(
                    f"Skipping {dish_id}, outside of Mid.CBF max capabilities."
                )
                continue

            vcc_proxy = self._all_vcc_proxies[vcc_id - 1]
            vcc_subarray_id = vcc_proxy.subarrayMembership

            # only add VCC if it does not already belong to a subarray
            if vcc_subarray_id != 0:
                self.logger.warning(
                    f"Skipping {dish_id}, already assigned to subarray {vcc_subarray_id}"
                )
                continue

            vcc_proxies.append(vcc_proxy)
            talon_proxy = self._get_talon_proxy_from_dish_id(dish_id)
            talon_proxies.append(talon_proxy)
            dish_ids_to_add.append(dish_id)
            vcc_ids_to_add.append(vcc_id)

        successes = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                self._assign_vcc_thread, vcc_proxies, talon_proxies
            ):
                successes.append(result)

        if not all(successes):
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to assign all requested VCCs.",
                ),
            )
            return

        # Update obsState callback if previously unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=True)

        self.dish_ids.update(dish_ids_to_add)
        receptors_push_val = list(self.dish_ids.copy())
        receptors_push_val.sort()
        self._device_attr_change_callback("receptors", receptors_push_val)
        self._device_attr_archive_callback("receptors", receptors_push_val)

        self.vcc_ids.update(vcc_ids_to_add)
        self._assigned_vcc_proxies.update(vcc_proxies)

        self.logger.info(f"Receptors after adding: {self.dish_ids}")

        task_callback(
            result=(ResultCode.OK, "AddReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def assign_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit AddReceptors operation method to task executor queue.

        :param argin: The list of DISH (receptor) IDs to be assigned
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="assign",
                command_thread=self._assign_vcc,
            ),
            args=[argin],
            is_cmd_allowed=self.is_assign_vcc_allowed,
            task_callback=task_callback,
        )

    def is_release_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """Check if RemoveReceptors command is allowed in current state"""
        self.logger.debug("Checking if RemoveReceptors is allowed.")
        if self.obs_state not in [ObsState.IDLE]:
            self.logger.warning(
                f"RemoveReceptors not allowed in ObsState {self.obs_state}; "
                + "must be in ObsState.IDLE"
            )
            return False
        return True

    def _release_vcc_thread(
        self: CbfSubarrayComponentManager,
        vcc_proxy: context.DeviceProxy,
        talon_proxy: context.DeviceProxy,
    ) -> bool:
        """
        Thread to perform individual VCC release.

        :param vcc_proxy: proxy to VCC
        :param talon_proxy: proxy to Talon board device with matching DISH ID
        :return: True if successfully assigned VCC proxy, otherwise False
        """
        try:
            vcc_fqdn = vcc_proxy.dev_name()
            # reset subarrayMembership Vcc attribute:
            vcc_proxy.subarrayMembership = 0
            self.logger.debug(
                f"{vcc_fqdn}.subarrayMembership: "
                + f"{vcc_proxy.subarrayMembership}"
            )
            vcc_proxy.Off()
            vcc_proxy.adminMode = AdminMode.OFFLINE

            # clear the subarray ID off the talon board with the matching DISH ID
            if talon_proxy is not None:
                talon_proxy.subarrayID = ""

            return True
        except tango.DevFailed as df:
            self.logger.error(f"Failed to release VCC; {df}")
            return False

    def _release_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Remove receptors/dishes from subarray.

        :param argin: The list of DISH (receptor) IDs to be removed
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "RemoveReceptors", task_callback, task_abort_event
        ):
            return

        input_dish_valid, msg = self._dish_utils.are_Valid_DISH_Ids(argin)
        if not input_dish_valid:
            task_callback(
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, msg),
            )
            return

        # TODO: shouldn't happen
        if len(self.dish_ids) == 0:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Subarray does not currently have any assigned receptors.",
                ),
            )
            return

        # build list of VCCs to remove
        vcc_proxies = []
        talon_proxies = []
        dish_ids_to_remove = []
        vcc_ids_to_remove = []
        for dish_id in argin:
            self.logger.debug(f"Attempting to remove {dish_id}")

            if dish_id in self._dish_utils.dish_id_to_vcc_id.keys():
                vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            else:
                self.logger.warning(
                    f"Skipping {dish_id}, outside of Mid.CBF max capabilities."
                )
                continue

            if dish_id not in self.dish_ids:
                self.logger.warning(
                    f"Skipping receptor {dish_id} as it is not currently assigned to this subarray."
                )
                continue

            vcc_proxy = self._all_vcc_proxies[vcc_id - 1]
            vcc_proxies.append(vcc_proxy)
            talon_proxy = self._get_talon_proxy_from_dish_id(dish_id)
            talon_proxies.append(talon_proxy)
            dish_ids_to_remove.append(dish_id)
            vcc_ids_to_remove.append(vcc_id)

        successes = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                self._release_vcc_thread, vcc_proxies, talon_proxies
            ):
                successes.append(result)

        if not all(successes):
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to remove all requested VCCs.",
                ),
            )
            return

        self.dish_ids.difference_update(dish_ids_to_remove)
        receptors_push_val = list(self.dish_ids.copy())
        receptors_push_val.sort()
        self._device_attr_change_callback("receptors", receptors_push_val)
        self._device_attr_archive_callback("receptors", receptors_push_val)

        self.vcc_ids.difference_update(vcc_ids_to_remove)
        self._assigned_vcc_proxies.difference_update(vcc_proxies)

        self.logger.info(f"Receptors after removal: {self.dish_ids}")

        # Update obsState callback if now unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=False)

        task_callback(
            result=(ResultCode.OK, "RemoveReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def release_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveReceptors operation method to task executor queue.

        :param argin: The list of DISH (receptor) IDs to be removed
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="release",
                command_thread=self._release_vcc,
            ),
            args=[argin],
            is_cmd_allowed=self.is_release_vcc_allowed,
            task_callback=task_callback,
        )

    @check_communicating
    def release_all_vcc(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveAllReceptors operation method to task executor queue.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="release",
                command_thread=self._release_vcc,
            ),
            args=[list(self.dish_ids.copy())],
            is_cmd_allowed=self.is_release_vcc_allowed,
            task_callback=task_callback,
        )

    #####################
    # Scan Commands
    #####################

    def _issue_command_all_assigned_resources(
        self: CbfSubarrayComponentManager,
        command_name: str,
        argin: Optional[any] = None,
    ) -> bool:
        """
        Issue command to all subarray-assigned resources

        :param command_name: name of command to issue to proxy group
        :param argin: optional command input argument
        :return: True if any command failed to be issued, otherwise False
        """
        assigned_resources = list(self._assigned_vcc_proxies) + list(
            self._assigned_fsp_corr_proxies
        )
        failure = False
        for result_code, msg in self._issue_group_command(
            command_name=command_name, proxies=assigned_resources, argin=argin
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                failure = True
        return failure

    def _deconfigure(
        self: CbfSubarrayComponentManager,
    ) -> bool:
        """
        Completely deconfigure the subarray; all initialization performed by the
        ConfigureScan command must be 'undone' here.

        :return: True if failed to deconfigure, otherwise False
        """
        # component_manager._deconfigure is invoked by GoToIdle, ConfigureScan,
        # ObsReset and Restart here in the CbfSubarray
        deconfigure_failure = False
        if len(self._assigned_fsp_proxies) > 0:
            # change FSP subarray membership
            for result_code, msg in self._issue_group_command(
                command_name="RemoveSubarrayMembership",
                proxies=list(self._assigned_fsp_proxies),
            ):
                if result_code == ResultCode.FAILED:
                    self.logger.error(msg)
                    deconfigure_failure = True
            self._assigned_fsp_proxies = set()

        if len(self._assigned_fsp_corr_proxies) > 0:
            self._assigned_fsp_corr_proxies = set()

        try:
            # unsubscribe from TMC events
            for event_id in list(self._events_telstate.keys()):
                self._events_telstate[event_id].remove_event(event_id)
                del self._events_telstate[event_id]
        except tango.DevFailed as df:
            self.logger.error(f"Error in unsubscribing from TM events; {df}")
            deconfigure_failure = True

        # reset all private data to their initialization values
        self._corr_config = []
        self.scan_id = 0
        self.config_id = ""
        self.frequency_band = 0
        self._last_received_delay_model = ""

        return deconfigure_failure

    def _validate_input(
        self: CbfSubarrayComponentManager, argin: str
    ) -> tuple[bool, str]:
        """
        Validate scan configuration.

        :param argin: The configuration as JSON formatted string.

        :return: A tuple containing a boolean indicating if the configuration
            is valid and a string message. The message is for information
            purpose only.
        :rtype: (bool, str)
        """
        # try to deserialize input string to a JSON object
        try:
            full_configuration = json.loads(argin)
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
        except json.JSONDecodeError as je:  # argument not a valid JSON object
            self.logger.error(
                f"Scan configuration object is not a valid JSON object; {je}"
            )
            return False

        # Validate full_configuration against the telescope model
        try:
            telmodel_validate(
                version=full_configuration["interface"],
                config=full_configuration,
                strictness=2,
            )
            self.logger.info("Scan configuration is valid!")
        except ValueError as ve:
            self.logger.error(
                f"ConfigureScan JSON validation against the telescope model schema failed;\n {ve}."
            )
            return False

        # TODO: return additional validation as needed

        # At this point, everything has been validated.
        return (True, "Scan configuration is valid.")

    def _calculate_dish_sample_rate(
        self: CbfSubarrayComponentManager,
        freq_band_info: dict,
        freq_offset_k: int,
    ) -> int:
        """
        Calculate frequency slice sample rate

        :param freq_band_info: constants pertaining to a given frequency band
        :param freq_offset_k: DISH frequency offset k value
        :return: DISH sample rate
        """
        base_dish_sample_rate_MH = freq_band_info["base_dish_sample_rate_MHz"]
        sample_rate_const = freq_band_info["sample_rate_const"]

        return (base_dish_sample_rate_MH * mhz_to_hz) + (
            sample_rate_const * freq_offset_k * const.DELTA_F
        )

    def _calculate_fs_sample_rate(
        self: CbfSubarrayComponentManager, freq_band: str, dish: str
    ) -> dict:
        """
        Calculate frequency slice sample rate for a given DISH

        :param freq_band: target frequency band
        :param dish: target DISH ID
        :return: VCC output sample rate
        """
        log_msg = (
            f"Calculate fs_sample_rate for freq_band:{freq_band} and {dish}"
        )
        self.logger.info(log_msg)

        # convert the DISH ID to a VCC ID integer using DISHUtils
        vcc_id = self._dish_utils.dish_id_to_vcc_id[dish]

        # find the k value for this DISH
        freq_offset_k = self._dish_utils.dish_id_to_k[dish]
        freq_band_info = freq_band_dict()[freq_band]

        total_num_fs = freq_band_info["total_num_FSs"]

        dish_sample_rate = self._calculate_dish_sample_rate(
            freq_band_info, freq_offset_k
        )

        log_msg = f"dish_sample_rate: {dish_sample_rate}"
        self.logger.debug(log_msg)
        fs_sample_rate = int(
            dish_sample_rate * vcc_oversampling_factor / total_num_fs
        )
        fs_sample_rate_for_band = {
            "vcc_id": vcc_id,
            "fs_sample_rate": fs_sample_rate,
        }
        log_msg = f"fs_sample_rate_for_band: {fs_sample_rate_for_band}"
        self.logger.info(log_msg)

        return fs_sample_rate_for_band

    def _calculate_fs_sample_rates(
        self: CbfSubarrayComponentManager, freq_band: str
    ) -> list[dict]:
        """
        Calculate frequency slice sample rate for all assigned DISH

        :param freq_band: target frequency band
        :return: list of assigned VCC output sample rates
        """
        output_sample_rates = []
        for dish in self.dish_ids:
            output_sample_rates.append(
                self._calculate_fs_sample_rate(freq_band, dish)
            )

        return output_sample_rates

    def _vcc_configure_band(
        self: CbfSubarrayComponentManager,
        configuration: dict[any],
    ) -> bool:
        """
        Issue Vcc ConfigureBand command

        :param configuration: scan configuration dict
        :return: True if VCC ConfigureBand command failed, otherwise False
        """
        # Prepare args for ConfigureBand
        vcc_failure = False
        for dish_id in self.dish_ids:
            # Fetch K-value based on dish_id
            vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            vcc_proxy = self._all_vcc_proxies[vcc_id - 1]
            freq_offset_k = self._dish_utils.dish_id_to_k[dish_id]
            # Calculate dish sample rate
            dish_sample_rate = self._calculate_dish_sample_rate(
                freq_band_dict()[configuration["frequency_band"]],
                freq_offset_k,
            )
            # Fetch samples per frame for this freq band
            samples_per_frame = freq_band_dict()[
                configuration["frequency_band"]
            ]["num_samples_per_frame"]

            result_code, msg = vcc_proxy.ConfigureBand(
                json.dumps(
                    {
                        "frequency_band": configuration["frequency_band"],
                        "dish_sample_rate": int(dish_sample_rate),
                        "samples_per_frame": int(samples_per_frame),
                    }
                )
            )

            if result_code == ResultCode.FAILED:
                vcc_failure = True
                self.logger.error(msg)

        return vcc_failure

    def _vcc_configure_scan(
        self: CbfSubarrayComponentManager,
        common_configuration: dict[any],
        configuration: dict[any],
    ) -> bool:
        """
        Issue Vcc ConfigureScan command

        :param common_configuration: common Mid.CSP scan configuration dict
        :param configuration: Mid.CBF scan configuration dict
        :return: True if VCC ConfigureScan command failed, otherwise False
        """

        # Configure band5Tuning, if frequencyBand is 5a or 5b.
        self.frequency_band = freq_band_dict()[
            common_configuration["frequency_band"]
        ]["band_index"]
        if self.frequency_band in [4, 5]:
            self._stream_tuning = [
                *map(float, common_configuration["band_5_tuning"])
            ]
        else:
            self._stream_tuning = [0, 0]
            self.logger.warning(
                "'band_5_tuning' not specified. Defaulting to [0, 0]."
            )

        # Configure frequency_band_offset_stream1 and 2
        # If not given, use a default value.
        if "frequency_band_offset_stream1" in configuration:
            self.frequency_band_offset_stream1 = int(
                configuration["frequency_band_offset_stream1"]
            )
        else:
            self.frequency_band_offset_stream1 = 0
            self.logger.warning(
                "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            )
        if "frequency_band_offset_stream2" in configuration:
            self.frequency_band_offset_stream2 = int(
                configuration["frequency_band_offset_stream2"]
            )
        else:
            self.frequency_band_offset_stream2 = 0
            self.logger.warning(
                "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
            )

        # Configure rfi_flagging_mask
        # If not given, use a default value.
        if "rfi_flagging_mask" in configuration:
            self.rfi_flagging_mask = configuration["rfi_flagging_mask"]
        else:
            self.rfi_flagging_mask = {}
            self.logger.warning(
                "'rfi_flagging_mask' not specified. Defaulting to none."
            )

        config_dict = {
            "config_id": self.config_id,
            "frequency_band": common_configuration["frequency_band"],
            "band_5_tuning": self._stream_tuning,
            "frequency_band_offset_stream1": self.frequency_band_offset_stream1,
            "frequency_band_offset_stream2": self.frequency_band_offset_stream2,
            "rfi_flagging_mask": self.rfi_flagging_mask,
        }

        # Add subset of FSP configuration to the VCC configure scan argument
        reduced_fsp = []
        for fsp in configuration["fsp"]:
            function_mode = fsp["function_mode"]
            fsp_cfg = {"fsp_id": fsp["fsp_id"], "function_mode": function_mode}
            if function_mode == "CORR":
                fsp_cfg["frequency_slice_id"] = fsp["frequency_slice_id"]
            reduced_fsp.append(fsp_cfg)
        config_dict["fsp"] = reduced_fsp

        vcc_failure = False
        for result_code, msg in self._issue_group_command(
            command_name="ConfigureScan",
            proxies=list(self._assigned_vcc_proxies),
            argin=json.dumps(config_dict),
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                vcc_failure = True

        return vcc_failure

    def _fsp_configure_scan(
        self: CbfSubarrayComponentManager,
        common_configuration: dict[any],
        configuration: dict[any],
    ) -> bool:
        """
        Issue FSP function mode subarray ConfigureScan command

        :param common_configuration: common Mid.CSP scan configuration dict
        :param configuration: Mid.CBF scan configuration dict
        :return: True if FSP ConfigureScan command failed, otherwise False
        """
        fsp_failure = False
        for fsp_config in configuration["fsp"]:
            # Configure fsp_id.
            fsp_id = int(fsp_config["fsp_id"])
            fsp_proxy = self._proxies_fsp[fsp_id - 1]
            fsp_corr_proxy = self._proxies_fsp_corr_subarray_device[fsp_id - 1]

            self._assigned_fsp_proxies.add(fsp_proxy)
            self._assigned_fsp_corr_proxies.add(fsp_corr_proxy)

            # Add configID, frequency_band, band_5_tuning, and sub_id to fsp. They are not included in the "FSP" portion in configScan JSON
            fsp_config["config_id"] = common_configuration["config_id"]
            fsp_config["sub_id"] = common_configuration["subarray_id"]
            fsp_config["frequency_band"] = common_configuration[
                "frequency_band"
            ]
            fsp_config["band_5_tuning"] = self._stream_tuning
            fsp_config[
                "frequency_band_offset_stream1"
            ] = self.frequency_band_offset_stream1
            fsp_config[
                "frequency_band_offset_stream2"
            ] = self.frequency_band_offset_stream2

            # Add channel_offset if it was omitted from the configuration (it is optional).
            if "channel_offset" not in fsp_config:
                self.logger.warning(
                    "channel_offset not defined in configuration. Assigning default of 1."
                )
                fsp_config["channel_offset"] = 1

            # Add the fs_sample_rate for all dishes
            fsp_config["fs_sample_rates"] = self._calculate_fs_sample_rates(
                common_configuration["frequency_band"]
            )

            # Add all DISH IDs for subarray and for correlation to fsp
            # Parameter named "subarray_vcc_ids" used by HPS contains all the
            # VCCs assigned to the subarray
            # Parameter named "corr_vcc_ids" used by HPS contains the
            # subset of the subarray VCCs for which the correlation results
            # are requested to be used in Mid.CBF output products (visibilities)
            fsp_config["subarray_vcc_ids"] = []
            for dish in self.dish_ids:
                fsp_config["subarray_vcc_ids"].append(
                    self._dish_utils.dish_id_to_vcc_id[dish]
                )

            match fsp_config["function_mode"]:
                case "CORR":
                    # dishes may not be specified in the
                    # configuration at all, or the list may be empty
                    fsp_config["corr_vcc_ids"] = []
                    if (
                        "receptors" not in fsp_config
                        or len(fsp_config["receptors"]) == 0
                    ):
                        # In this case by the ICD, all subarray allocated resources should be used.
                        fsp_config["corr_vcc_ids"] = fsp_config[
                            "subarray_vcc_ids"
                        ].copy()
                    else:
                        for dish in fsp_config["receptors"]:
                            fsp_config["corr_vcc_ids"].append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )

                    self._corr_config.append(fsp_config)
                case _:
                    self.logger.error(
                        f"Function mode {fsp_config['function_mode']} currently unsupported."
                    )
                    fsp_failure = True

        if fsp_failure:
            return True

        assigned_fsp_group = list(self._assigned_fsp_proxies) + list(
            self._assigned_fsp_corr_proxies
        )

        # Set simulation mode of FSPs to subarray sim mode
        self.logger.info(
            f"Setting Simulation Mode of FSP {fsp_id} proxies to: {self.simulation_mode} and turning them on."
        )
        if not self._write_group_attribute(
            attr_name="adminMode",
            value=AdminMode.OFFLINE,
            proxies=assigned_fsp_group,
        ):
            return True
        if not self._write_group_attribute(
            attr_name="simulationMode",
            value=self.simulation_mode,
            proxies=assigned_fsp_group,
        ):
            return True
        if not self._write_group_attribute(
            attr_name="adminMode",
            value=AdminMode.ONLINE,
            proxies=assigned_fsp_group,
        ):
            return True

        for result_code, msg in self._issue_group_command(
            command_name="On", proxies=list(assigned_fsp_group)
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                fsp_failure = True
        if fsp_failure:
            return True

        # Configure functionMode if IDLE
        # if fsp_proxy.functionMode == FspModes.IDLE.value:
        #     fsp_proxy.SetFunctionMode(fsp["function_mode"])
        for result_code, msg in self._issue_group_command(
            command_name="SetFunctionMode",
            proxies=list(self._assigned_fsp_proxies),
            argin=fsp_config["function_mode"],
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                fsp_failure = True
        if fsp_failure:
            return True

        # change FSP subarray membership
        for result_code, msg in self._issue_group_command(
            command_name="AddSubarrayMembership",
            proxies=list(self._assigned_fsp_proxies),
            argin=self.subarray_id,
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                fsp_failure = True
        if fsp_failure:
            return True

        # Call ConfigureScan for all FSP function mode subarray devices
        # NOTE:_corr_config is a list of fsp config JSON objects, each
        #      augmented by a number of vcc-fsp common parameters
        if len(self._corr_config) != 0:
            for fsp_config in self._corr_config:
                try:
                    self.logger.debug(f"fsp_config: {json.dumps(fsp_config)}")
                    fsp_corr_proxy = self._proxies_fsp_corr_subarray_device[
                        int(fsp_config["fsp_id"]) - 1
                    ]
                    fsp_corr_proxy.set_timeout_millis(12000)
                    fsp_corr_proxy.ConfigureScan(json.dumps(fsp_config))

                except tango.DevFailed as df:
                    self.logger.error(
                        "Failed to issue ConfigureScan to FSP CORR subarray device "
                        + f"{fsp_corr_proxy.dev_name()}; {df}"
                    )
                    fsp_failure = True

        return fsp_failure

    def _subscribe_tm_event(
        self: CbfSubarrayComponentManager,
        subscription_point: str,
        callback: Callable,
    ) -> bool:
        """
        Subscribe to change events on TM-published data subscription point

        :param subscription_point: FQDN of TM data subscription point
        :param callback: callback for event subscription
        :return: True if VCC ConfigureScan command failed, otherwise False
        """
        # split delay_model_subscription_point between device FQDN and attribute name
        subscription_point_split = subscription_point.split("/")
        fqdn = "/".join(subscription_point_split[:-1])
        attr_name = subscription_point_split[-1]

        try:
            proxy = context.DeviceProxy(device_name=fqdn)
            event_id = proxy.subscribe_event(
                attr_name,
                tango.EventType.CHANGE_EVENT,
                callback,
            )
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to subscribe to change events for {subscription_point}; {df}"
            )
            return True

        self.logger.info(
            f"Subscribed to {subscription_point}; event ID: {event_id}"
        )
        self._events_telstate[event_id] = proxy
        return False

    def _configure_scan(
        self: CbfSubarrayComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute configure scan operation.

        :param argin: JSON string with the configure scan parameters
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ConfigureScan", task_callback, task_abort_event
        ):
            return

        validation_failure = self._validate_input(argin)
        if validation_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to validate ConfigureScan input JSON",
                ),
            )
            return

        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_failure = self._deconfigure()
        if deconfigure_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        full_configuration = json.loads(argin)
        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["cbf"])

        # store configID
        self.config_id = str(common_configuration["config_id"])

        vcc_configure_band_failure = self._vcc_configure_band(
            configuration=common_configuration
        )
        if vcc_configure_band_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureBand command to VCC",
                ),
            )
            return

        vcc_configure_scan_failure = self._vcc_configure_scan(
            common_configuration=common_configuration,
            configuration=configuration,
        )
        if vcc_configure_scan_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureScan command to VCC",
                ),
            )
            return

        # Configure delayModel subscription point
        delay_model_failure = self._subscribe_tm_event(
            subscription_point=configuration["delay_model_subscription_point"],
            callback=self._delay_model_event_callback,
        )
        if delay_model_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to subscribe to delayModel attribute",
                ),
            )
            return

        fsp_configure_scan_failure = self._fsp_configure_scan(
            common_configuration=common_configuration,
            configuration=configuration,
        )
        if fsp_configure_scan_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureScan command to FSP",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(configured=True)

        task_callback(
            result=(ResultCode.OK, "ConfigureScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _scan(
        self: CbfSubarrayComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Start subarray Scan operation.

        :param argin: The scan ID as JSON formatted string.
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Scan", task_callback, task_abort_event
        ):
            return

        scan = json.loads(argin)

        # Validate scan_json against the telescope model
        try:
            telmodel_validate(
                version=scan["interface"], config=scan, strictness=1
            )
            self.logger.info("Scan is valid!")
        except ValueError as ve:
            self.logger.error(
                f"Scan validation against ska-telmodel schema failed with exception:\n {ve}"
            )
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to validate Scan input JSON",
                ),
            )
            return

        # issue Scan to assigned resources
        scan_id = scan["scan_id"]
        scan_failure = self._issue_command_all_assigned_resources(
            command_name="Scan", argin=scan_id
        )
        if scan_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Scan command to VCC/FSP",
                ),
            )
            return

        self.scan_id = scan_id

        # Update obsState callback
        self._update_component_state(scanning=True)

        task_callback(
            result=(ResultCode.OK, "Scan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _end_scan(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        End scan operation.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "EndScan", task_callback, task_abort_event
        ):
            return

        # issue EndScan to assigned resources
        end_scan_failure = self._issue_command_all_assigned_resources(
            command_name="EndScan"
        )
        if end_scan_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue EndScan command to VCC/FSP",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "EndScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _go_to_idle(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "GoToIdle", task_callback, task_abort_event
        ):
            return

        # issue GoToIdle to assigned resources
        idle_failure = self._issue_command_all_assigned_resources(
            command_name="GoToIdle"
        )
        if idle_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue GoToIdle command to VCC/FSP",
                ),
            )
            return

        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_failure = self._deconfigure()
        if deconfigure_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(configured=False)

        task_callback(
            result=(ResultCode.OK, "GoToIdle completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _abort_scan(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Abort the current scan operation.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Abort", task_callback, task_abort_event
        ):
            return

        # issue Abort to assigned resources
        abort_failure = self._issue_command_all_assigned_resources(
            command_name="Abort"
        )
        if abort_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Abort command to VCC/FSP",
                ),
            )
            return

        task_callback(
            result=(ResultCode.OK, "Abort completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _obs_reset(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset the scan operation to IDLE from ABORTED or FAULT.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ObsReset", task_callback, task_abort_event
        ):
            return

        # if subarray is in FAULT, we must first abort VCC and FSP operation
        # this will allow us to call ObsReset on them even if they are not in FAULT
        if self._component_state["obsfault"]:
            abort_failure = self._issue_command_all_assigned_resources(
                command_name="Abort"
            )
            if abort_failure:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Abort command to VCC/FSP",
                    ),
                )
                return

        obsreset_failure = self._issue_command_all_assigned_resources(
            command_name="ObsReset"
        )
        if obsreset_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ObsReset command to VCC/FSP",
                ),
            )
            return

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_failure = self._deconfigure()
        if deconfigure_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        task_callback(
            result=(ResultCode.OK, "ObsReset completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def is_restart_allowed(self: CbfSubarrayComponentManager) -> bool:
        """Check if Restart command is allowed in current state"""
        self.logger.debug("Checking if Restart is allowed.")
        if self.obs_state not in [ObsState.ABORTED, ObsState.FAULT]:
            self.logger.warning(
                f"Restart not allowed in ObsState {self.obs_state}; "
                + "must be in ObsState.ABORTED or FAULT"
            )
            return False
        return True

    def _restart(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset the scan operation to EMPTY from ABORTED or FAULT.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Restart", task_callback, task_abort_event
        ):
            return

        # if subarray is in FAULT, we must first abort VCC and FSP operation
        # this will allow us to call ObsReset on them even if they are not in FAULT
        if self._component_state["obsfault"]:
            abort_failure = self._issue_command_all_assigned_resources(
                command_name="Abort"
            )
            if abort_failure:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Abort command to VCC/FSP",
                    ),
                )
                return

        obsreset_failure = self._issue_command_all_assigned_resources(
            command_name="ObsReset"
        )
        if obsreset_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ObsReset command to VCC/FSP",
                ),
            )
            return

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_failure = self._deconfigure()
        if deconfigure_failure:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        # remove all assigned VCCs to return to EMPTY
        # TODO cant release all vcc like this
        self._release_vcc(
            task_callback=task_callback, argin=list(self.dish_ids.copy())
        )

        task_callback(
            result=(ResultCode.OK, "Restart completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def restart(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit Restart operation method to task executor queue.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="restart",
                command_thread=self._restart,
            ),
            is_cmd_allowed=self.is_restart_allowed,
            task_callback=task_callback,
        )
