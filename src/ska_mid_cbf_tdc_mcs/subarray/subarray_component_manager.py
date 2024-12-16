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
import copy
import json
from functools import partial
from threading import Event, Lock, Thread
from typing import Callable, Optional

import tango
from ska_control_model import (
    AdminMode,
    CommunicationStatus,
    ObsState,
    PowerState,
    ResultCode,
    TaskStatus,
)
from ska_tango_testing import context

# isort: off
# ska_telmodel.schema before ska_telmodel.csp due to circular dependency
from ska_telmodel.schema import validate as telmodel_validate

# isort: on


from ska_mid_cbf_tdc_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import (
    FspModes,
    calculate_dish_sample_rate,
    const,
    freq_band_dict,
)
from ska_mid_cbf_tdc_mcs.commons.validate_interface import validate_interface
from ska_mid_cbf_tdc_mcs.component.obs_component_manager import (
    CbfObsComponentManager,
)
from ska_mid_cbf_tdc_mcs.subarray.fsp_scan_configuration_builder.builder import (
    FspScanConfigurationBuilder,
)
from ska_mid_cbf_tdc_mcs.subarray.scan_configuration_validator.validator import (
    SubarrayScanConfigurationValidator,
)
from ska_mid_cbf_tdc_mcs.visibility_transport.visibility_transport import (
    VisibilityTransport,
)


class CbfSubarrayComponentManager(CbfObsComponentManager):
    """
    A component manager for the CbfSubarray device.
    """

    def __init__(
        self: CbfSubarrayComponentManager,
        *args: any,
        subarray_id: int,
        controller: str,
        vcc: list[str],
        fsp: list[str],
        fsp_corr_sub: list[str],
        talon_board: list[str],
        vis_slim: str,
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
        :param vis_slim: FQDN of the visibility SLIM device
        """
        super().__init__(*args, **kwargs)

        self.obs_state = ObsState.EMPTY

        self._dish_utils = None

        self._subarray_id = subarray_id
        self._fqdn_controller = controller
        self._proxy_controller = None

        self._fqdn_vcc_all = vcc
        self._fqdn_fsp_all = fsp
        self._fqdn_fsp_corr_all = fsp_corr_sub
        self._fqdn_vcc = []
        self._fqdn_fsp = []
        self._fqdn_fsp_corr = []

        self._fqdn_talon_board_device = talon_board
        self._fqdn_vis_slim_device = vis_slim

        # initialize attribute values
        self._sys_param_str = ""
        self.dish_ids = set()
        self.frequency_band = 0

        self.last_received_delay_model = ""

        self._delay_model_lock = Lock()

        # store the subscribed TM event IDs and device proxies
        self._tm_events = {}

        # for easy device-reference
        self._rfi_flagging_mask = {}
        self._frequency_band_offset_stream1 = 0
        self._frequency_band_offset_stream2 = 0
        self._stream_tuning = [0, 0]

        # Controls the visibility transport from FSP outputs to SDP
        self._vis_transport = VisibilityTransport(
            logger=self.logger,
        )

        # Store a list of FSP parameters used to configure the visibility transport
        self._vis_fsp_config = []

        # Store maxCapabilities from controller for easy reference
        self._controller_max_capabilities = {}
        self._max_count_vcc = 0
        self._max_count_fsp = 0

        # proxies to subelement devices
        self._all_vcc_proxies = {}
        self._assigned_vcc_proxies = set()

        self._fsp_ids = set()
        self._all_fsp_proxies = {}
        self._all_fsp_corr_proxies = {}
        self._assigned_fsp_proxies = set()
        self._assigned_fsp_corr_proxies = set()

        self._all_talon_board_proxies = []

        # subarray does not control the visibility SLIM. It only
        # queries the config to figure out how to route the visibilities,
        # and updates the scan configuration accordingly.
        self._proxy_vis_slim = None

    @property
    def vcc_ids(self: CbfSubarrayComponentManager) -> list[int]:
        """
        Return the list of assigned VCC IDs

        :return: list of assigned VCC IDs
        """
        if self._dish_utils is not None:
            return [
                self._dish_utils.dish_id_to_vcc_id[dish]
                for dish in self.dish_ids
            ]
        self.logger.error(
            "Unable to return VCC IDs as system parameters have not yet been provided."
        )
        return []

    @property
    def fsp_ids(self: CbfSubarrayComponentManager) -> list[int]:
        """
        Return the list of assigned FSP IDs

        :return: list of assigned VCC IDs
        """
        return list(self._fsp_ids)

    # -------------
    # Communication
    # -------------

    def _init_controller_proxy(self: CbfSubarrayComponentManager) -> bool:
        """
        Initialize proxy to controller device, read MaxCapabilities property

        :return: True if max capabilities initialization succeeded, otherwise False
        """
        try:
            self._proxy_controller = context.DeviceProxy(
                device_name=self._fqdn_controller
            )
            self._controller_max_capabilities = dict(
                pair.split(":")
                for pair in self._proxy_controller.maxCapabilities
            )
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        self.logger.info(
            f"Max capabilities: {self._controller_max_capabilities}"
        )

        self._max_count_vcc = int(self._controller_max_capabilities["VCC"])
        self._max_count_fsp = int(self._controller_max_capabilities["FSP"])

        self._fqdn_vcc = self._fqdn_vcc_all[: self._max_count_vcc]
        self._fqdn_fsp = self._fqdn_fsp_all[: self._max_count_fsp]
        self._fqdn_fsp_corr = self._fqdn_fsp_corr_all[: self._max_count_fsp]

        self.logger.debug(f"Active VCC FQDNs: {self._fqdn_vcc}")
        self.logger.debug(f"Active FSP FQDNs: {self._fqdn_fsp}")
        self.logger.debug(f"Active FSP CORR FQDNs: {self._fqdn_fsp_corr}")

        return True

    def _init_subelement_proxies(self: CbfSubarrayComponentManager) -> bool:
        """
        Initialize proxies to FSP and VCC subelements

        :return: True if proxy initialization succeed, otherwise False
        """
        try:
            for fqdn in self._fqdn_vcc:
                vcc_id = int(fqdn.split("/")[2])
                self._all_vcc_proxies[vcc_id] = context.DeviceProxy(
                    device_name=fqdn
                )

            for fsp_id, (fsp_fqdn, fsp_corr_fqdn) in enumerate(
                zip(self._fqdn_fsp, self._fqdn_fsp_corr), 1
            ):
                self._all_fsp_proxies[fsp_id] = context.DeviceProxy(
                    device_name=fsp_fqdn
                )
                self._all_fsp_corr_proxies[fsp_id] = context.DeviceProxy(
                    device_name=fsp_corr_fqdn
                )

            for fqdn in self._fqdn_talon_board_device:
                proxy = context.DeviceProxy(device_name=fqdn)
                self._all_talon_board_proxies.append(proxy)

            self._proxy_vis_slim = context.DeviceProxy(
                device_name=self._fqdn_vis_slim_device
            )

        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        return True

    def _start_communicating(
        self: CbfSubarrayComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for start_communicating operation.
        """
        controller_success = self._init_controller_proxy()
        if not controller_success:
            self.logger.error(
                "Failed to initialize max capabilities from controller."
            )
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        subelement_success = self._init_subelement_proxies()
        if not subelement_success:
            self.logger.error("Failed to initialize subelement proxies.")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    # --------
    # sysParam
    # --------

    def _update_sys_param(
        self: CbfSubarrayComponentManager, sys_param_str: str, *args, **kwargs
    ) -> None:
        """
        Reload sys param from input JSON

        :param sys_param_str: sys params JSON string
        """
        sys_param = json.loads(sys_param_str)
        self._dish_utils = DISHUtils(sys_param)
        self._sys_param_str = sys_param_str
        self.device_attr_change_callback("sysParam", self._sys_param_str)
        self.device_attr_archive_callback("sysParam", self._sys_param_str)
        self.logger.info(
            f"Updated DISH ID to VCC ID and frequency offset k mapping {self._sys_param_str}"
        )

    def update_sys_param(
        self: CbfSubarrayComponentManager, sys_param_str: str
    ) -> None:
        """
        Submit reload sys param operation to task executor queue

        :param sys_param_str: sys params JSON string
        """
        self.logger.debug(f"Received sys param: {sys_param_str}")

        task_status, message = self.submit_task(
            partial(self._update_sys_param, sys_param_str=sys_param_str)
        )
        if task_status == TaskStatus.REJECTED:
            self.logger.error(f"update_sys_param thread rejected; {message}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )

    # ----------------------
    # Subscription callbacks
    # ----------------------

    def _update_delay_model(
        self: CbfSubarrayComponentManager, event_data: tango.EventData
    ) -> None:
        """
        Update FSP delay models.
        This method is always started in a separate thread.

        :param event_data: the received change event data (delay model JSON string)
        """
        if event_data.attr_value is None:
            return
        model = event_data.attr_value.value
        if not self.is_communicating or model is None or model == "":
            return

        # Subscription starts during the configure scan command. Need to include the
        # CONFIGURING state or we risk throwing away the first polynomial. Subscription should
        # also be done after FSPs have been configured so that RDTs are ready to receive them.
        if self.obs_state not in [
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
        ]:
            log_msg = f"Ignoring delay model received in {self.obs_state} (must be READY or SCANNING)."
            self.logger.warning(log_msg)
            return

        if model == self.last_received_delay_model:
            self.logger.warning(
                "Ignoring delay model (identical to previous)."
            )
            return

        try:
            delay_model_json = json.loads(model)

            self.logger.debug(
                f"Attempting to validate the following delay model JSON against the telescope model: {delay_model_json}"
            )
            telmodel_validate(
                version=delay_model_json["interface"],
                config=delay_model_json,
                strictness=1,
            )
            self.logger.debug("Delay model is valid!")
        except json.JSONDecodeError as je:
            self.logger.error(
                f"Delay model object is not a valid JSON object; {je}"
            )
            return
        except ValueError as ve:
            self.logger.error(
                f"Delay model JSON validation against the telescope model schema failed, ignoring delay model;\n {ve}."
            )
            return

        # Validate DISH IDs, then convert them to VCC ID integers for FSPs
        for delay_detail in delay_model_json["receptor_delays"]:
            dish_id = delay_detail["receptor"]
            if dish_id not in self.dish_ids:
                self.logger.error(
                    f"Delay model contains data for DISH ID {dish_id} not belonging to this subarray, ignoring delay model."
                )
                return
            delay_detail["receptor"] = self._dish_utils.dish_id_to_vcc_id[
                dish_id
            ]

        self.logger.debug(f"Updating delay model; {delay_model_json}")
        # we lock the mutex while forwarding the configuration to fsp_corr devices
        with self._delay_model_lock:
            # TODO: for AA2+ update _max_count_fsp to take into account the number of FPGAs per FSP-UNIT
            results_fsp = self.issue_group_command(
                command_name="UpdateDelayModel",
                proxies=list(self._assigned_fsp_corr_proxies),
                max_workers=self._max_count_fsp,
                argin=json.dumps(delay_model_json),
            )

            for result_code, _ in results_fsp:
                if result_code == ResultCode.FAILED:
                    self.logger.error(
                        "Failed to issue UpdateDelayModel command to FSP devices"
                    )

            self.last_received_delay_model = model

    def _delay_model_event_callback(
        self: CbfSubarrayComponentManager, event_data: tango.EventData
    ) -> None:
        """ "
        Callback for delayModel change event subscription.

        :param event_data: the received change event data
        """
        self.logger.debug("Entering _delay_model_event_callback()")

        Thread(target=self._update_delay_model, args=(event_data,)).start()

    # -------------------
    # Resourcing Commands
    # -------------------

    # --- AddReceptors Command --- #

    def _get_talon_proxy_from_dish_id(
        self: CbfSubarrayComponentManager,
        dish_id: str,
    ) -> context.DeviceProxy:
        """
        Return the TalonBoard device proxy that matches the DISH ID parameter.

        :param dish_id: the DISH ID
        :return: proxy to Talon board device, or None if failed to initialize proxy
        """
        for proxy in self._all_talon_board_proxies:
            if proxy.dishID == dish_id:
                return proxy

        # Talon board proxy not essential to scan operation, so we log an error
        # but don't cause a failure
        # return None here to fail conditionals later
        self.logger.error(
            f"Couldn't find TalonBoard device with DISH ID {dish_id}; "
            + "unable to update TalonBoard device subarrayID for this DISH."
        )
        return None

    def is_assign_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """
        Check if AddReceptors command is allowed in current state

        :return: True if command is allowed, otherwise False
        """
        self.logger.debug("Checking if AddReceptors is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.EMPTY, ObsState.IDLE]:
            self.logger.warning(
                f"AddReceptors not allowed in ObsState {self.obs_state}"
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
            # Guard against AdminMode.NOT_FITTED VCCs
            if vcc_proxy.adminMode == AdminMode.NOT_FITTED:
                self.logger.debug(
                    f"Skipping {vcc_proxy.dev_name()}, AdminMode is NOT_FITTED"
                )
                return False

            # Setting simulation mode of VCC proxies based on simulation mode of subarray
            vcc_fqdn = vcc_proxy.dev_name()
            self.logger.info(
                f"Writing {vcc_fqdn} simulation mode to: {self.simulation_mode}"
            )
            vcc_proxy.simulationMode = self.simulation_mode
            vcc_proxy.adminMode = AdminMode.ONLINE

            # change subarray membership of vcc
            vcc_proxy.subarrayMembership = self._subarray_id
            self.logger.debug(
                f"{vcc_fqdn}.subarrayMembership: "
                + f"{vcc_proxy.subarrayMembership}"
            )

            # assign the subarray ID to the talon board with the matching DISH ID
            if talon_proxy is not None:
                talon_proxy.subarrayID = str(self._subarray_id)

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

        # build list of VCCs to assign
        vcc_proxies = []
        talon_proxies = []
        dish_ids_to_add = []
        for dish_id in argin:
            self.logger.debug(f"Attempting to add receptor {dish_id}")

            try:
                vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
                if 0 >= vcc_id > self._max_count_vcc:
                    raise KeyError(
                        f"VCC ID {vcc_id} not in current capabilities."
                    )
            except KeyError as ke:
                self.logger.error(f"Invalid DISH ID {dish_id} provided; {ke}")
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(ResultCode.FAILED, f"Invalid DISH ID {dish_id}"),
                )
                return

            vcc_proxy = self._all_vcc_proxies[vcc_id]
            vcc_subarray_id = vcc_proxy.subarrayMembership

            # only add VCC if it does not already belong to a subarray
            if vcc_subarray_id != 0:
                self.logger.warning(
                    f"Skipping {dish_id}, already assigned to subarray {vcc_subarray_id}"
                )
                continue

            vcc_proxies.append(vcc_proxy)
            talon_proxies.append(self._get_talon_proxy_from_dish_id(dish_id))
            dish_ids_to_add.append(dish_id)

        if len(dish_ids_to_add) == 0:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "No valid DISH IDs were provided",
                ),
            )
            return

        successes = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                self._assign_vcc_thread, vcc_proxies, talon_proxies
            ):
                successes.append(result)

        if not all(successes):
            message = "Failed to assign all requested VCCs."
            self.logger.error(message)
            task_callback(
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, message),
            )
            return

        # Update obsState callback if previously unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=True)

        self.dish_ids.update(dish_ids_to_add)
        receptors_push_val = list(self.dish_ids)
        receptors_push_val.sort()
        self.device_attr_change_callback("receptors", receptors_push_val)
        self.device_attr_archive_callback("receptors", receptors_push_val)

        self._assigned_vcc_proxies.update(vcc_proxies)

        # subscribe to LRC results during the VCC scan operation
        for vcc_proxy in vcc_proxies:
            self.attr_event_subscribe(
                proxy=vcc_proxy,
                attr_name="longRunningCommandResult",
                callback=self.results_callback,
            )

        self.logger.info(f"Receptors after adding: {self.dish_ids}")

        task_callback(
            result=(ResultCode.OK, "AddReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

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
            func=partial(
                self._obs_command_with_callback,
                hook="assign",
                command_thread=self._assign_vcc,
            ),
            args=[argin],
            is_cmd_allowed=self.is_assign_vcc_allowed,
            task_callback=task_callback,
        )

    # --- RemoveReceptors Command --- #

    def is_release_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """
        Check if RemoveReceptors command is allowed in current state

        :return: True if command is allowed, otherwise False
        """
        self.logger.debug("Checking if RemoveReceptors is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.IDLE]:
            self.logger.warning(
                f"RemoveReceptors not allowed in ObsState {self.obs_state}"
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
            vcc_proxy.adminMode = AdminMode.OFFLINE

            # clear the subarray ID off the talon board with the matching DISH ID
            if talon_proxy is not None:
                talon_proxy.subarrayID = ""

            return True
        except tango.DevFailed as df:
            self.logger.error(f"Failed to release VCC; {df}")
            return False

    def _release_vcc_resources(
        self: CbfSubarrayComponentManager, dish_ids: list[str]
    ) -> bool:
        """
        Main loop for use in releasing VCC resources, shared between resource-releasing
        commands and Restart command

        :param dish_ids: list of DISH IDs
        :return: False if unsuccessful in releasing VCCs, otherwise True
        """
        # build list of VCCs to remove
        vcc_proxies = []
        talon_proxies = []
        dish_ids_to_remove = []
        for dish_id in dish_ids:
            self.logger.debug(f"Attempting to remove {dish_id}")

            if dish_id not in self.dish_ids:
                self.logger.warning(
                    f"Skipping receptor {dish_id} as it is not currently assigned to this subarray."
                )
                continue

            vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            vcc_proxy = self._all_vcc_proxies[vcc_id]
            vcc_proxies.append(vcc_proxy)
            talon_proxies.append(self._get_talon_proxy_from_dish_id(dish_id))
            dish_ids_to_remove.append(dish_id)

        if len(dish_ids_to_remove) == 0:
            self.logger.info(
                f"Did not find any receptors to remove; argin: {dish_ids}"
            )
            return True

        successes = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                self._release_vcc_thread, vcc_proxies, talon_proxies
            ):
                successes.append(result)

        if not all(successes):
            message = "Failed to release all requested VCCs."
            self.logger.error(message)
            return False

        self.dish_ids.difference_update(dish_ids_to_remove)
        receptors_push_val = list(self.dish_ids)
        receptors_push_val.sort()
        self.device_attr_change_callback("receptors", receptors_push_val)
        self.device_attr_archive_callback("receptors", receptors_push_val)

        self._assigned_vcc_proxies.difference_update(vcc_proxies)

        # unsubscribe from VCC LRC results
        for vcc_proxy in vcc_proxies:
            self.unsubscribe_all_events(vcc_proxy)

        self.logger.info(f"Receptors after removal: {self.dish_ids}")

        return True

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

        release_success = self._release_vcc_resources(dish_ids=argin)
        if not release_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to remove receptors.",
                ),
            )
            return

        # Update obsState callback if now unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=False)

        task_callback(
            result=(ResultCode.OK, "RemoveReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

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
            func=partial(
                self._obs_command_with_callback,
                hook="release",
                command_thread=self._release_vcc,
            ),
            args=[argin],
            is_cmd_allowed=self.is_release_vcc_allowed,
            task_callback=task_callback,
        )

    def is_release_all_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """
        Check if RemoveAllReceptors command is allowed in current state

        :return: True if command is allowed, otherwise False
        """
        self.logger.debug("Checking if RemoveAllReceptors is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.IDLE]:
            self.logger.warning(
                f"RemoveAllReceptors not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _release_all_vcc(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Remove all receptors/dishes from subarray.

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

        release_success = self._release_vcc_resources(
            dish_ids=list(self.dish_ids)
        )
        if not release_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to remove receptors.",
                ),
            )
            return

        # Update obsState callback if now unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=False)

        task_callback(
            result=(ResultCode.OK, "RemoveAllReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

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
            func=partial(
                self._obs_command_with_callback,
                hook="release",
                command_thread=self._release_all_vcc,
            ),
            is_cmd_allowed=self.is_release_all_vcc_allowed,
            task_callback=task_callback,
        )

    # -------------
    # Scan Commands
    # -------------

    # --- ConfigureScan Command --- #

    def _issue_lrc_all_assigned_resources(
        self: CbfSubarrayComponentManager,
        command_name: str,
        argin: Optional[any] = None,
        task_abort_event: Optional[Event] = None,
    ) -> TaskStatus:
        """
        Issue command to all subarray-assigned resources

        :param command_name: name of command to issue to proxy group
        :param argin: optional command input argument
        :param task_abort_event: event indicating AbortCommands has been issued

        :return: TaskStatus
        """
        self.logger.info(
            f"Issuing {command_name} command to all assigned resources..."
        )
        # TODO: support more function modes
        assigned_resources = (
            self._assigned_vcc_proxies | self._assigned_fsp_corr_proxies
        )
        if len(assigned_resources) == 0:
            self.logger.info("No resources currently assigned.")
            return TaskStatus.COMPLETED

        self.blocking_command_ids = set()
        for [[result_code], [command_id]] in self.issue_group_command(
            command_name=command_name,
            proxies=list(assigned_resources),
            max_workers=self._max_count_vcc + self._max_count_fsp,
            argin=argin,
        ):
            if result_code in [ResultCode.REJECTED, ResultCode.FAILED]:
                self.logger.error(
                    f"Failed to issue {command_name} command to assigned resources; {result_code}"
                )
                return TaskStatus.FAILED
            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results(
            task_abort_event=task_abort_event
        )
        if lrc_status == TaskStatus.FAILED:
            self.logger.error("One or more command calls failed/timed out.")
            return lrc_status
        if lrc_status == TaskStatus.ABORTED:
            self.logger.warning(
                f"{command_name} command aborted by task executor abort event."
            )
            return lrc_status

        return TaskStatus.COMPLETED

    def _validate_configure_scan_input(
        self: CbfSubarrayComponentManager, argin: str
    ) -> bool:
        """
        Validate scan configuration JSON.

        :param argin: The configuration as JSON formatted string.

        :return: False if validation failed, otherwise True
        """
        self.logger.info("Validating ConfigureScan input JSON...")

        (valid, msg) = validate_interface(argin, "configurescan")
        if not valid:
            self.logger.error(msg)
            return False

        # Validate full_configuration against the telescope model
        try:
            full_configuration = json.loads(argin)
            telmodel_validate(
                version=full_configuration["interface"],
                config=full_configuration,
                strictness=2,
            )
            self.logger.info("Scan configuration is valid against telmodel!")
        except json.JSONDecodeError as je:  # argument not a valid JSON object
            self.logger.error(
                f"Scan configuration object is not a valid JSON object; {je}"
            )
            return False
        except ValueError as ve:
            self.logger.error(
                f"ConfigureScan JSON validation against the telescope model schema failed;\n {ve}."
            )
            return False

        # At this point, validate FSP, VCC, subscription parameters
        controller_validateSupportedConfiguration = (
            self._proxy_controller.validateSupportedConfiguration
        )
        # MCS Scan Configuration Validation
        if controller_validateSupportedConfiguration is True:
            validator = SubarrayScanConfigurationValidator(
                scan_configuration=argin,
                dish_ids=list(self.dish_ids),
                subarray_id=self._subarray_id,
                logger=self.logger,
                count_fsp=self._max_count_fsp,
            )
            success, msg = validator.validate_input()
            if success:
                self.logger.info(msg)
            else:
                self.logger.error(msg)
            return success
        else:
            self.logger.info(
                "Skipping MCS supported configuration validation."
            )

        return True

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

        dish_sample_rate = calculate_dish_sample_rate(
            freq_band_info, freq_offset_k
        )

        log_msg = f"dish_sample_rate: {dish_sample_rate}"
        self.logger.debug(log_msg)
        fs_sample_rate = int(
            dish_sample_rate * const.VCC_OVERSAMPLING_FACTOR / total_num_fs
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

        :return: True if VCC ConfigureBand was successful, otherwise False
        """
        self.logger.info("Configuring VCC band...")

        self.blocking_command_ids = set()
        for dish_id in self.dish_ids:
            # Prepare args for ConfigureBand
            vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            vcc_proxy = self._all_vcc_proxies[vcc_id]

            # Fetch K-value based on dish_id, calculate dish sample rate
            dish_sample_rate = calculate_dish_sample_rate(
                freq_band_info=freq_band_dict()[
                    configuration["frequency_band"]
                ],
                freq_offset_k=self._dish_utils.dish_id_to_k[dish_id],
            )
            # Fetch samples per frame for this freq band
            samples_per_frame = freq_band_dict()[
                configuration["frequency_band"]
            ]["num_samples_per_frame"]

            try:
                [[result_code], [command_id]] = vcc_proxy.ConfigureBand(
                    json.dumps(
                        {
                            "frequency_band": configuration["frequency_band"],
                            "dish_sample_rate": int(dish_sample_rate),
                            "samples_per_frame": int(samples_per_frame),
                        }
                    )
                )

            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to issue ConfigureBand to {vcc_proxy.dev_name()}; {df}"
                )
                return False

            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"{vcc_proxy.dev_name()} ConfigureBand command rejected"
                )
                return False

            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results()
        if lrc_status == TaskStatus.FAILED:
            self.logger.error(
                "One or more calls to VCC ConfigureBand command failed/timed out."
            )
            return False

        return True

    def _vcc_configure_scan(
        self: CbfSubarrayComponentManager,
        common_configuration: dict[any],
        configuration: dict[any],
        fsp_configurations: list[dict[any]],
    ) -> bool:
        """
        Issue Vcc ConfigureScan command

        :param common_configuration: common Mid.CSP scan configuration dict
        :param configuration: Mid.CBF scan configuration dict
        :param fsp_configurations: FSP configuration list

        :return: True if VCC ConfigureScan was successful, otherwise False
        """
        self.logger.info("Configuring VCC for scan...")
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
            self._frequency_band_offset_stream1 = int(
                configuration["frequency_band_offset_stream1"]
            )
        else:
            self._frequency_band_offset_stream1 = 0
            self.logger.warning(
                "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            )
        if "frequency_band_offset_stream2" in configuration:
            self._frequency_band_offset_stream2 = int(
                configuration["frequency_band_offset_stream2"]
            )
        else:
            self._frequency_band_offset_stream2 = 0
            self.logger.warning(
                "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
            )

        # Configure rfi_flagging_mask
        # If not given, use a default value.
        if "rfi_flagging_mask" in configuration:
            self._rfi_flagging_mask = configuration["rfi_flagging_mask"]
        else:
            self._rfi_flagging_mask = {}
            self.logger.warning(
                "'rfi_flagging_mask' not specified. Defaulting to none."
            )

        config_dict = {
            "config_id": self.config_id,
            "frequency_band": common_configuration["frequency_band"],
            "band_5_tuning": self._stream_tuning,
            "frequency_band_offset_stream1": self._frequency_band_offset_stream1,
            "frequency_band_offset_stream2": self._frequency_band_offset_stream2,
            "rfi_flagging_mask": self._rfi_flagging_mask,
        }

        # Add subset of FSP configuration to the VCC configure scan argument
        reduced_fsp = []
        for fsp in fsp_configurations:
            function_mode = fsp["function_mode"]
            fsp_cfg = {"fsp_id": fsp["fsp_id"], "function_mode": function_mode}
            if function_mode == "CORR":
                fsp_cfg["frequency_slice_id"] = fsp["frequency_slice_id"]
            reduced_fsp.append(fsp_cfg)
        config_dict["fsp"] = reduced_fsp

        # issue ConfigureScan to assigned VCCs
        self.blocking_command_ids = set()
        for vcc_proxy in self._assigned_vcc_proxies:
            try:
                [[result_code], [command_id]] = vcc_proxy.ConfigureScan(
                    json.dumps(config_dict)
                )
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to issue ConfigureScan to {vcc_proxy.dev_name()}; {df}"
                )
                return False
            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"{vcc_proxy.dev_name()} ConfigureScan command rejected"
                )
                return False

            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results()
        if lrc_status == TaskStatus.FAILED:
            self.logger.error(
                "One or more calls to VCC ConfigureScan command failed/timed out."
            )
            return False

        return True

    def _convert_pr_configs_to_fsp_configs(
        self: CbfSubarrayComponentManager,
        configuration: dict[any],
        common_configuration: dict[any],
    ) -> list[dict[any]]:
        """
        go through the different function modes' (CORR, PST, etc.) processing
        regions and convert to individual FSP configurations.

        :param configuration: The Mid.CSP Function specific configurations
        :raises ValueError: if there is an exception processing any processing
        regions
        :return: list of Individual FSP configurations
        """

        all_fsp_configs = []

        # CORR
        if "correlation" in configuration:
            corr_config = configuration["correlation"]

            # TODO: set wideband shift when ready for implementation
            fsp_config_builder = FspScanConfigurationBuilder(
                function_mode=FspModes.CORR,
                function_configuration=corr_config,
                dish_utils=self._dish_utils,
                subarray_dish_ids=self.dish_ids,
                wideband_shift=0,
                frequency_band=common_configuration["frequency_band"],
            )
            try:
                corr_fsp_configs = fsp_config_builder.build()
            except ValueError as ve:
                msg = f"Failure processing correlation configuration: {ve}"
                self.logger.error(msg)
                raise ValueError(msg)

            all_fsp_configs.extend(corr_fsp_configs)

        # TODO: build PST fsp configs and add to all_fsp_configs

        return all_fsp_configs

    def _build_fsp_config(
        self: CbfSubarrayComponentManager,
        fsp_config: dict[any],
        common_configuration: dict[any],
    ) -> dict[any]:
        """
        Build FSP function mode ConfigureScan input JSON dict.
        Adds the following parameters missing from the "fsp" portion of the JSON:
        config_id, sub_id, frequency_band, band_5_tuning, frequency_band_offset_stream1,
        frequency_band_offset_stream2, channel_offset, fs_sample_rates, subarray_vcc_ids

        :param fsp_config: Mid.CBF FSP scan configuration dict
        :param common_configuration: common Mid.CSP scan configuration dict
        :return: FSP function mode ConfigureScan input dict
        """
        fsp_config["config_id"] = common_configuration["config_id"]
        fsp_config["sub_id"] = common_configuration["subarray_id"]
        fsp_config["frequency_band"] = common_configuration["frequency_band"]
        fsp_config["band_5_tuning"] = self._stream_tuning
        fsp_config[
            "frequency_band_offset_stream1"
        ] = self._frequency_band_offset_stream1
        fsp_config[
            "frequency_band_offset_stream2"
        ] = self._frequency_band_offset_stream2

        fsp_config["fs_sample_rates"] = self._calculate_fs_sample_rates(
            common_configuration["frequency_band"]
        )

        # Parameter named "subarray_vcc_ids" used by HPS contains all the VCCs
        # assigned to the subarray. This needs to be sorted by receptor ID first
        # to ensure the baselines in visibilities come out in the expected order.
        fsp_config["subarray_vcc_ids"] = []
        dish_ids_sorted = sorted(self.dish_ids)
        for dish in dish_ids_sorted:
            fsp_config["subarray_vcc_ids"].append(
                self._dish_utils.dish_id_to_vcc_id[dish]
            )

        self.logger.debug(f"{fsp_config}")

        return fsp_config

    def _assign_fsp(
        self: CbfSubarrayComponentManager,
        fsp_proxy: context.DeviceProxy,
        function_mode: str,
    ) -> bool:
        """
        Set FSP function mode and add subarray membership

        :param fsp_id: ID of FSP to assign
        :param function_mode: target FSP function mode
        :return: True if successfully assigned FSP device, otherwise False
        """
        self.logger.info(
            f"Assigning FSP {fsp_proxy.dev_name()} to subarray..."
        )

        try:
            if fsp_proxy.adminMode == AdminMode.NOT_FITTED:
                self.logger.debug(
                    f"{fsp_proxy.dev_name()} is not fitted; skipping assignment."
                )
                return False
            # Only set function mode if FSP is both IDLE and not configured for
            # another mode
            current_function_mode = fsp_proxy.functionMode
            if current_function_mode != FspModes[function_mode].value:
                if current_function_mode != FspModes.IDLE.value:
                    self.logger.error(
                        f"Unable to configure FSP {fsp_proxy.dev_name()} for function mode {function_mode}, as it is currently configured for function mode {current_function_mode}"
                    )
                    return False

                # If FSP function mode is IDLE, turn on FSP and set function mode
                fsp_proxy.simulationMode = self.simulation_mode
                fsp_proxy.adminMode = AdminMode.ONLINE

                [[result_code], [command_id]] = fsp_proxy.SetFunctionMode(
                    function_mode
                )
                if result_code == ResultCode.REJECTED:
                    self.logger.error(
                        f"{fsp_proxy.dev_name()} SetFunctionMode command rejected"
                    )
                    return False

                self.blocking_command_ids.add(command_id)

            # Add subarray membership, which powers on this FSP's function mode devices
            [[result_code], [command_id]] = fsp_proxy.AddSubarrayMembership(
                self._subarray_id
            )
            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"{fsp_proxy.dev_name()} AddSubarrayMembership command rejected"
                )
                return False

            self.blocking_command_ids.add(command_id)
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        return True

    def _fsp_configure_scan(
        self: CbfSubarrayComponentManager,
        common_configuration: dict[any],
        fsp_configurations: list[dict[any]],
    ) -> bool:
        """
        Issue FSP function mode subarray ConfigureScan command

        :param common_configuration: common Mid.CSP scan configuration dict
        :param fsp_configuration: FSP scan configuration dict

        :return: True if successfully configured all FSP devices, otherwise False
        """
        self.logger.info("Configuring FSPs for scan...")

        # build FSP configuration JSONs, add FSP
        all_fsp_config = []
        self._vis_fsp_config = []
        self.blocking_command_ids = set()

        for config in fsp_configurations:
            fsp_config = self._build_fsp_config(
                fsp_config=copy.deepcopy(config),
                common_configuration=copy.deepcopy(common_configuration),
            )

            fsp_id = fsp_config["fsp_id"]
            match fsp_config["function_mode"]:
                case "CORR":
                    # set function mode and add subarray membership
                    fsp_proxy = self._all_fsp_proxies[fsp_id]
                    self.attr_event_subscribe(
                        proxy=fsp_proxy,
                        attr_name="longRunningCommandResult",
                        callback=self.results_callback,
                    )
                    self._assigned_fsp_proxies.add(fsp_proxy)
                    self._fsp_ids.add(fsp_id)

                    fsp_success = self._assign_fsp(fsp_proxy, "CORR")
                    if not fsp_success:
                        return False

                    # Parameter named "corr_vcc_ids" used by HPS contains the
                    # subset of the subarray VCCs for which the correlation
                    # results are requested to be used in Mid.CBF output
                    # products (visibilities); dishes may not be specified in
                    # the configuration at all, or the list may be empty
                    fsp_config["corr_vcc_ids"] = []
                    if (
                        "receptors" not in fsp_config
                        or len(fsp_config["receptors"]) == 0
                    ):
                        # In this case by the ICD, all subarray allocated
                        # resources should be used.
                        fsp_config["corr_vcc_ids"] = fsp_config[
                            "subarray_vcc_ids"
                        ].copy()
                    else:
                        for dish in sorted(fsp_config["receptors"]):
                            fsp_config["corr_vcc_ids"].append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )

                    # Prepare CORR proxy and its configuration
                    fsp_corr_proxy = self._all_fsp_corr_proxies[fsp_id]
                    all_fsp_config.append(
                        (fsp_corr_proxy, json.dumps(fsp_config))
                    )

                    # Store FSP parameters to configure visibility transport
                    self._vis_fsp_config.append(fsp_config)
                case _:
                    self.logger.error(
                        f"Function mode {fsp_config['function_mode']} currently unsupported."
                    )

        lrc_status = self.wait_for_blocking_results()
        if lrc_status == TaskStatus.FAILED:
            self.logger.error(
                "One or more calls to FSP SetFunctionMode/AddSubarrayMembership commands failed/timed out."
            )
            return False

        # Call ConfigureScan for all FSP function mode subarray devices
        # TODO: refactor for other function modes
        self.blocking_command_ids = set()
        for fsp_mode_proxy, fsp_config_str in all_fsp_config:
            try:
                self.attr_event_subscribe(
                    proxy=fsp_mode_proxy,
                    attr_name="longRunningCommandResult",
                    callback=self.results_callback,
                )

                self.logger.debug(f"fsp_config: {fsp_config_str}")
                [[result_code], [command_id]] = fsp_mode_proxy.ConfigureScan(
                    fsp_config_str
                )
                if result_code == ResultCode.REJECTED:
                    self.logger.error(
                        f"{fsp_mode_proxy.dev_name()} ConfigureScan command rejected"
                    )
                    return False
                self.blocking_command_ids.add(command_id)
                self._assigned_fsp_corr_proxies.add(fsp_mode_proxy)
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to issue ConfigureScan to {fsp_mode_proxy.dev_name()}; {df}"
                )
                return False

        lrc_status = self.wait_for_blocking_results()
        if lrc_status == TaskStatus.FAILED:
            self.logger.error(
                "One or more calls to FSP ConfigureScan command failed/timed out."
            )
            return False

        return True

    def _subscribe_tm_event(
        self: CbfSubarrayComponentManager,
        subscription_point: str,
        callback: Callable,
    ) -> bool:
        """
        Subscribe to change events on TM-published data subscription point

        :param subscription_point: FQDN of TM data subscription point
        :param callback: callback for event subscription
        :return: False if VCC ConfigureScan command failed, otherwise True
        """
        self.logger.info(f"Attempting subscription to {subscription_point}")

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
            return False

        self.logger.info(
            f"Subscribed to {subscription_point}; event ID: {event_id}"
        )
        self._tm_events[event_id] = proxy
        return True

    def _release_all_fsp(self: CbfSubarrayComponentManager) -> bool:
        """
        Remove subarray membership and return FSP to IDLE state if possible

        :return: False if failed to release FSP device, True otherwise
        """
        self.logger.info("Releasing all FSP from subarray...")

        # Remove subarray membership from assigned FSP
        self.blocking_command_ids = set()
        # TODO: for AA2+ update _max_count_fsp to take into account the number of FPGAs per FSP-UNIT
        for [[result_code], [command_id]] in self.issue_group_command(
            command_name="RemoveSubarrayMembership",
            proxies=list(self._assigned_fsp_proxies),
            max_workers=self._max_count_fsp,
            argin=self._subarray_id,
        ):
            if result_code in [ResultCode.REJECTED, ResultCode.FAILED]:
                self.logger.error(
                    "FSP RemoveSubarrayMembership command failed"
                )
                return False
            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results()
        if lrc_status == TaskStatus.FAILED:
            self.logger.error(
                "One or more calls to FSP RemoveSubarrayMembership command failed/timed out."
            )
            return False

        for proxy in self._assigned_fsp_corr_proxies:
            try:
                self.unsubscribe_all_events(proxy)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                return False

        for proxy in self._assigned_fsp_proxies:
            try:
                self.unsubscribe_all_events(proxy)
                # If FSP subarrayMembership is empty, set it OFFLINE
                if len(proxy.subarrayMembership) == 0:
                    proxy.adminMode = AdminMode.OFFLINE
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                return False

        self._fsp_ids = set()
        self._assigned_fsp_proxies = set()
        self._assigned_fsp_corr_proxies = set()
        return True

    # TODO: split up deconfigure for safer flow in event of partial command failure
    def _deconfigure(
        self: CbfSubarrayComponentManager,
    ) -> bool:
        """
        Completely deconfigure the subarray; all initialization performed by the
        ConfigureScan command must be 'undone' here.
        This method is invoked by GoToIdle, ConfigureScan, ObsReset and Restart
        in CbfSubarray

        :return: False if failed to deconfigure, otherwise True
        """
        self.logger.info("Deconfiguring subarray...")

        if len(self._assigned_fsp_proxies) > 0:
            fsp_success = self._release_all_fsp()
            if not fsp_success:
                return False

        try:
            # unsubscribe from TMC events
            for event_id, proxy in self._tm_events.items():
                proxy.unsubscribe_event(event_id)
        except tango.DevFailed as df:
            self.logger.error(f"Error in unsubscribing from TM events; {df}")
            return False

        self._tm_events = {}
        self.scan_id = 0
        self.config_id = ""
        self.frequency_band = 0
        self._last_received_delay_model = ""

        return True

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

        validation_success = self._validate_configure_scan_input(argin)
        if not validation_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to validate ConfigureScan input JSON",
                ),
            )
            return

        full_configuration = json.loads(argin)

        self.logger.debug(
            f"Subarray ConfigureScan Configuration: {full_configuration}"
        )

        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["midcbf"])

        # When configuring from READY, send any function mode subarrays in READY to IDLE
        self.blocking_command_ids = set()
        # TODO: for AA2+ update _max_count_fsp to take into account the number of FPGAs per FSP-UNIT
        for [[result_code], [command_id]] in self.issue_group_command(
            command_name="GoToIdle",
            proxies=list(self._assigned_fsp_corr_proxies),
            max_workers=self._max_count_fsp,
        ):
            if result_code in [ResultCode.REJECTED, ResultCode.FAILED]:
                self.logger.error("FSP GoToIdle command failed")
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "FSP GoToIdle command failed",
                    ),
                )
                return
            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results()
        if lrc_status == TaskStatus.FAILED:
            self.logger.error(
                "One or more calls to FSP GoToIdle command failed/timed out."
            )
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "One or more calls to FSP GoToIdle command failed/timed out.",
                ),
            )
            return

        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        # store configID
        self.config_id = str(common_configuration["config_id"])

        # --- Convert Processing Regions to FSP configs --- #
        try:
            fsp_configs = self._convert_pr_configs_to_fsp_configs(
                configuration=configuration,
                common_configuration=common_configuration,
            )
        except ValueError as ve:
            msg = f"Failure to build FSP configurations from processing regions: {ve}"
            self.logger.error(msg)
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    msg,
                ),
            )
            return

        # --- Configure VCC --- #

        # TODO: think about what to do about abort events here
        vcc_configure_band_success = self._vcc_configure_band(
            configuration=common_configuration,
        )
        if not vcc_configure_band_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureBand command to VCC",
                ),
            )
            return

        vcc_configure_scan_success = self._vcc_configure_scan(
            common_configuration=common_configuration,
            configuration=configuration,
            fsp_configurations=fsp_configs,
        )
        if not vcc_configure_scan_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureScan command to VCC",
                ),
            )
            return

        # --- Configure FSP --- #

        fsp_configure_scan_success = self._fsp_configure_scan(
            common_configuration=common_configuration,
            fsp_configurations=fsp_configs,
        )
        if not fsp_configure_scan_success:
            # If unsuccessful, reset all assigned FSP devices
            for proxy in (
                self._assigned_fsp_corr_proxies | self._assigned_fsp_proxies
            ):
                self.unsubscribe_all_events(proxy)
            self._fsp_ids = set()
            self._assigned_fsp_corr_proxies = set()
            self._assigned_fsp_proxies = set()
            self.blocking_command_ids = set()
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureScan command to FSP",
                ),
            )
            return

        # Configure delayModel subscription point
        delay_model_success = self._subscribe_tm_event(
            subscription_point=configuration["delay_model_subscription_point"],
            callback=self._delay_model_event_callback,
        )
        if not delay_model_success:
            self.logger.error("Failed to subscribe to TM events.")
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to subscribe to delayModel attribute",
                ),
            )
            return

        # --- Configure Visibility Transport --- #

        # TODO
        # Route visibilities from each FSP to the outputting board
        if not self.simulation_mode:
            self.logger.info("Configuring visibility transport")
            vis_slim_yaml = self._proxy_vis_slim.meshConfiguration
            self._vis_transport.configure(
                subarray_id=self._subarray_id,
                fsp_config=self._vis_fsp_config,
                vis_slim_yaml=vis_slim_yaml,
            )

        # Update obsState callback
        self._update_component_state(configured=True)

        task_callback(
            result=(ResultCode.OK, "ConfigureScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    # --- Scan Command --- #

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

        (valid, msg) = validate_interface(argin, "scan")
        if not valid:
            self.logger.error(msg)
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to validate schema for Scan input JSON",
                ),
            )

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

        scan_id = int(scan["scan_id"])

        # Issue Scan command to assigned resources
        scan_status = self._issue_lrc_all_assigned_resources(
            command_name="Scan",
            argin=scan_id,
            task_abort_event=task_abort_event,
        )
        if scan_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Scan command to VCC/FSP",
                ),
            )
            return
        elif scan_status == TaskStatus.ABORTED:
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Scan command aborted by task executor abort event.",
                ),
            )
            return

        # Enable visibility transport output
        if not self.simulation_mode:
            self.logger.info("Visibility transport enable output")
            self._vis_transport.enable_output(self._subarray_id)

        self.scan_id = scan_id

        # Update obsState callback
        self._update_component_state(scanning=True)

        task_callback(
            result=(ResultCode.OK, "Scan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    # --- EndScan Command --- #

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
        end_scan_status = self._issue_lrc_all_assigned_resources(
            command_name="EndScan", task_abort_event=task_abort_event
        )
        if end_scan_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue EndScan command to VCC/FSP",
                ),
            )
            return
        elif end_scan_status == TaskStatus.ABORTED:
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "EndScan command aborted by task executor abort event.",
                ),
            )
            return

        if not self.simulation_mode:
            self.logger.info("Visibility transport disable output")
            self._vis_transport.disable_output()

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "EndScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    # --- GoToIdle Command --- #

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
        go_to_idle_status = self._issue_lrc_all_assigned_resources(
            command_name="GoToIdle",
            task_abort_event=task_abort_event,
        )
        if go_to_idle_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue GoToIdle command to VCC/FSP",
                ),
            )
            return
        elif go_to_idle_status == TaskStatus.ABORTED:
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "GoToIdle command aborted by task executor abort event.",
                ),
            )
            return

        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
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

    # --------------
    # Abort Commands
    # --------------

    # --- Abort Command --- #

    def _abort(
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
        abort_status = self._issue_lrc_all_assigned_resources(
            command_name="Abort", task_abort_event=task_abort_event
        )
        if abort_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Abort command to VCC/FSP",
                ),
            )
            return
        elif abort_status == TaskStatus.ABORTED:
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Abort command aborted by task executor abort event.",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "Abort completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    # --- ObsReset Command --- #

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
            abort_status = self._issue_lrc_all_assigned_resources(
                command_name="Abort",
                task_abort_event=task_abort_event,
            )
            if abort_status == TaskStatus.FAILED:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Abort command to VCC/FSP",
                    ),
                )
                return
            elif abort_status == TaskStatus.ABORTED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result=(
                        ResultCode.ABORTED,
                        "Abort command aborted by task executor abort event.",
                    ),
                )
                return

        obs_reset_status = self._issue_lrc_all_assigned_resources(
            command_name="ObsReset",
            task_abort_event=task_abort_event,
        )
        if obs_reset_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ObsReset command to VCC/FSP",
                ),
            )
            return
        elif obs_reset_status == TaskStatus.ABORTED:
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "ObsReset command aborted by task executor abort event.",
                ),
            )
            return

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        # Update obsState callback
        # There is no obsfault == False action implemented, however,
        # we reset it it False so that obsfault == True may be triggered in the future,
        # by updating the component state dict in BaseComponentManager.
        self._update_component_state(configured=False, obsfault=False)

        task_callback(
            result=(ResultCode.OK, "ObsReset completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    # --- Restart Command --- #

    def is_restart_allowed(self: CbfSubarrayComponentManager) -> bool:
        """
        Check if Restart command is allowed in current state

        :return: True if command is allowed, otherwise False
        """
        self.logger.debug("Checking if Restart is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.ABORTED, ObsState.FAULT]:
            self.logger.warning(
                f"Restart not allowed in ObsState {self.obs_state}"
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
            abort_status = self._issue_lrc_all_assigned_resources(
                command_name="Abort",
                task_abort_event=task_abort_event,
            )
            if abort_status == TaskStatus.FAILED:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Abort command to VCC/FSP",
                    ),
                )
                return
            elif abort_status == TaskStatus.ABORTED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result=(
                        ResultCode.ABORTED,
                        "Abort command aborted by task executor abort event.",
                    ),
                )
                return

        obs_reset_status = self._issue_lrc_all_assigned_resources(
            command_name="ObsReset",
            task_abort_event=task_abort_event,
        )
        if obs_reset_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ObsReset command to VCC/FSP",
                ),
            )
            return
        elif obs_reset_status == TaskStatus.ABORTED:
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "ObsReset command aborted by task executor abort event.",
                ),
            )
            return

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
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

        # remove all assigned VCCs to return to EMPTY
        release_success = self._release_vcc_resources(
            dish_ids=list(self.dish_ids)
        )
        if not release_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to remove receptors.",
                ),
            )
            return

        # Update obsState callback
        # There is no obsfault == False action implemented, however,
        # we reset it it False so that obsfault == True may be triggered in the future,
        # by updating the component state dict in BaseComponentManager.
        self._update_component_state(resourced=False, obsfault=False)

        task_callback(
            result=(ResultCode.OK, "Restart completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

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
            func=partial(
                self._obs_command_with_callback,
                hook="restart",
                command_thread=self._restart,
            ),
            is_cmd_allowed=self.is_restart_allowed,
            task_callback=task_callback,
        )
