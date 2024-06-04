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
from typing import Any, Callable, Optional

# Tango imports
import tango
from ska_control_model import (
    AdminMode,
    CommunicationStatus,
    ObsState,
    PowerState,
    ResultCode,
    SimulationMode,
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
        *args: Any,
        subarray_id: int,
        controller: str,
        vcc: list[str],
        fsp: list[str],
        fsp_corr_sub: list[str],
        talon_board: list[str],
        **kwargs: Any,
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
        # store list of fsp being used for each function mode
        self._corr_fsp_list = []

        self._last_received_delay_model = ""

        self._delay_model_lock = Lock()

        # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
        self._events_telstate = {}

        # for easy device-reference
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
        self._group_fsp = None
        self._group_fsp_corr_subarray = None

    def start_communicating(self: CbfSubarrayComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        self.logger.debug(
            "Entering CbfSubarrayComponentManager.start_communicating"
        )

        if self.is_communicating:
            self.logger.info("Already connected.")
            return

        try:
            if self._proxy_cbf_controller is None:
                self._proxy_cbf_controller = context.DeviceProxy(
                    device_name=self._fqdn_controller
                )
                self._controller_max_capabilities = dict(
                    pair.split(":")
                    for pair in self._proxy_cbf_controller.get_property(
                        "MaxCapabilities"
                    )["MaxCapabilities"]
                )
                self._count_vcc = int(self._controller_max_capabilities["VCC"])
                self._count_fsp = int(self._controller_max_capabilities["FSP"])

                self._fqdn_vcc = self._fqdn_vcc[: self._count_vcc]
                self._fqdn_fsp = self._fqdn_fsp[: self._count_fsp]
                self._fqdn_fsp_corr_subarray_device = (
                    self._fqdn_fsp_corr_subarray_device[: self._count_fsp]
                )

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
        for proxy in self._proxies_fsp_corr_subarray_device:
            try:
                proxy.On()
            except tango.DevFailed as df:
                msg = f"Failed to turn on {proxy.dev_name()}; {df}"
                self.logger.error(msg)
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (ResultCode.FAILED, msg)

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    @check_communicating
    def off(self: CbfSubarrayComponentManager) -> None:
        for proxy in self._proxies_fsp_corr_subarray_device:
            try:
                proxy.Off()
            except tango.DevFailed as df:
                msg = f"Failed to turn off {proxy.dev_name()}; {df}"
                self.logger.error(msg)
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (ResultCode.FAILED, msg)

        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off completed OK")

    def update_sys_param(
        self: CbfSubarrayComponentManager, sys_param_str: str
    ) -> None:
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

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param model: delay model
        """
        # This method is always called on a separate thread
        self.logger.info(f"Updating delay model ...{model}")

        data = tango.DeviceData()
        data.insert(tango.DevString, model)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._delay_model_lock.acquire()
        results_vcc = self._issue_group_command(
            command_name="UpdateDelayModel",
            proxies=list(self._assigned_vcc_proxies),
            argin=data,
        )
        self._group_vcc.command_inout("UpdateDelayModel", data)
        self._group_fsp.command_inout("UpdateDelayModel", data)
        self._delay_model_lock.release()

    @check_communicating
    def _delay_model_event_callback(
        self: CbfSubarrayComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: tango.AttrQuality,
    ) -> None:
        """ "
        Callback for delayModel change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self.logger.debug("Entering _delay_model_event_callback()")

        if value is not None:
            if not self._ready:
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
                    delay_detail[
                        "receptor"
                    ] = self._dish_utils.dish_id_to_vcc_id[dish_id]
                t = Thread(
                    target=self._update_delay_model,
                    args=(json.dumps(delay_model_json),),
                )
                t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            self.logger.warning(f"None value for {fqdn}")

    def validate_ip(self: CbfSubarrayComponentManager, ip: str) -> bool:
        """
        Validate IP address format.

        :param ip: IP address to be evaluated

        :return: whether or not the IP address format is valid
        :rtype: bool
        """
        splitip = ip.split(".")
        if len(splitip) != 4:
            return False
        for ipparts in splitip:
            if not ipparts.isdigit():
                return False
            ipval = int(ipparts)
            if ipval < 0 or ipval > 255:
                return False
        return True

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
        :return: proxy to Talon board device
        """
        for proxy in self._proxies_talon_board_device:
            board_dish_id = proxy.read_attribute("dishID").value
            if board_dish_id == dish_id:
                return proxy
        self.logger.error(
            f"Couldn't find Talon board device with DISH ID {dish_id}; \
                unable to update TalonBoard device subarrayID for this DISH."
        )
        # Talon board proxy not essential to scan operation, so we log an error
        # but don't cause a failure
        # return False here to fail conditionals later
        return False

    def is_assign_vcc_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if AddReceptors is allowed.")
        if self.obs_state not in [ObsState.EMPTY, ObsState.IDLE]:
            self.logger.warning(
                f"AddReceptors not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.EMPTY or IDLE"
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
            if talon_proxy:
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
        **kwargs,
    ) -> None:
        """
        Add receptors/dishes to subarray.

        :param argin: The list of DISH (receptor) IDs to be assigned
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
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

        self.dish_ids.update(dish_ids_to_add)
        receptors_push_val = list(self.dish_ids.copy())
        receptors_push_val.sort()
        self._device_attr_change_callback("receptors", receptors_push_val)
        self._device_attr_archive_callback("receptors", receptors_push_val)

        self.vcc_ids.update(vcc_ids_to_add)
        self._assigned_vcc_proxies.update(vcc_proxies)

        self.logger.info(f"Receptors after adding: {self.dish_ids}")

        # Update obsState callback if previously unresourced
        self._update_component_state(resourced=True)

        task_callback(
            result=(ResultCode.OK, "AddReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def assign_vcc(
        self: CbfObsComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[TaskStatus, str]:
        """
        Submit AddReceptors operation method to task executor queue.

        :param argin: The list of DISH (receptor) IDs to be assigned

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

    def is_release_vcc_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if RemoveReceptors is allowed.")
        if self.obs_state not in [ObsState.IDLE]:
            self.logger.warning(
                f"RemoveReceptors not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.IDLE"
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
            if talon_proxy:
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
        **kwargs,
    ) -> None:
        """
        Remove receptors/dishes from subarray.

        :param argin: The list of DISH (receptor) IDs to be removed
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
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

        if len(self.dish_ids) == 0:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(
                    ResultCode.OK,
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
        self._update_component_state(resourced=False)

        task_callback(
            result=(ResultCode.OK, "RemoveReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def release_vcc(
        self: CbfObsComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveReceptors operation method to task executor queue.

        :param argin: The list of DISH (receptor) IDs to be removed

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
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveAllReceptors operation method to task executor queue.

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

    @check_communicating
    def _deconfigure(
        self: CbfSubarrayComponentManager,
    ) -> None:
        """Completely deconfigure the subarray; all initialization performed
        by by the ConfigureScan command must be 'undone' here."""
        # component_manager._deconfigure is invoked by GoToIdle, ConfigureScan,
        # ObsReset and Restart here in the CbfSubarray

        if self._ready:
            if self._group_fsp.get_size() > 0:
                # change FSP subarray membership
                data = tango.DeviceData()
                data.insert(tango.DevUShort, self.subarray_id)
                self.logger.debug(data)
                self._group_fsp.command_inout("RemoveSubarrayMembership", data)
                self._group_fsp.remove_all()

            for group in [
                self._group_fsp_corr_subarray,
            ]:
                if group.get_size() > 0:
                    group.remove_all()

        try:
            # unsubscribe from TMC events
            for event_id in list(self._events_telstate.keys()):
                self._events_telstate[event_id].remove_event(event_id)
                del self._events_telstate[event_id]
        except tango.DevFailed:
            self._component_obs_fault_callback(True)

        # reset all private data to their initialization values
        self._corr_fsp_list = []
        self._corr_config = []
        self.scan_id = 0
        self.config_id = ""
        self.frequency_band = 0
        self._last_received_delay_model = ""

    def go_to_idle(
        self: CbfSubarrayComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Send subarray from READY to IDLE.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._deconfigure()

        # issue GoToIdle to assigned VCCs
        if self._group_vcc.get_size() > 0:
            results = self._group_vcc.command_inout("GoToIdle")
            self.logger.info("Results from VCC GoToIdle:")
            for res in results:
                self.logger.info(res.get_data())

        self.update_component_configuration(False)

        return (ResultCode.OK, "GoToIdle command completed OK")

    @check_communicating
    def validate_input(
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
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = f"Scan configuration object is not a valid JSON object. Aborting configuration. argin is: {argin}"
            return (False, msg)

        # Validate delayModelSubscriptionPoint.
        # if "delay_model_subscription_point" in configuration:
        #     try:
        #         attribute_proxy = CbfAttributeProxy(
        #             fqdn=configuration["delay_model_subscription_point"],
        #             logger=self.logger,
        #         )
        #         attribute_proxy.ping()
        #     except (
        #         tango.DevFailed
        #     ):  # attribute doesn't exist or is not set up correctly
        #         msg = (
        #             f"Attribute {configuration['delay_model_subscription_point']}"
        #             " not found or not set up correctly for "
        #             "'delayModelSubscriptionPoint'. Aborting configuration."
        #         )
        #         return (False, msg)

        for dish_id, proxy in self._proxies_assigned_vcc.items():
            if proxy.State() != tango.DevState.ON:
                msg = f"VCC {self._all_vcc_proxies.index(proxy) + 1} is not ON. Aborting configuration."
                return (False, msg)

        # Validate searchWindow.
        if "search_window" in configuration:
            # check if searchWindow is an array of maximum length 2
            if len(configuration["search_window"]) > 2:
                msg = (
                    "'searchWindow' must be an array of maximum length 2. "
                    "Aborting configuration."
                )
                return (False, msg)
            for sw in configuration["search_window"]:
                if sw["tdc_enable"]:
                    for receptor in sw["tdc_destination_address"]:
                        dish = receptor["receptor_id"]
                        if dish not in self.dish_ids:
                            msg = (
                                f"'searchWindow' DISH ID {dish} "
                                + "not assigned to subarray. Aborting configuration."
                            )
                            return (False, msg)
        else:
            pass

        # Validate fsp.
        for fsp in configuration["fsp"]:
            try:
                # Validate fsp_id.
                if int(fsp["fsp_id"]) in list(range(1, self._count_fsp + 1)):
                    fsp_id = int(fsp["fsp_id"])
                    fsp_proxy = self._proxies_fsp[fsp_id - 1]
                else:
                    msg = (
                        f"'fsp_id' must be an integer in the range [1, {self._count_fsp}]."
                        " Aborting configuration."
                    )
                    return (False, msg)

                # Validate functionMode.
                valid_function_modes = [
                    "IDLE",
                    "CORR",
                    "PSS-BF",
                    "PST-BF",
                    "VLBI",
                ]
                try:
                    function_mode_value = valid_function_modes.index(
                        fsp["function_mode"]
                    )
                except ValueError:
                    return (
                        False,
                        f"{fsp['function_mode']} is not a valid FSP function mode.",
                    )
                fsp_function_mode = fsp_proxy.functionMode
                if fsp_function_mode not in [
                    FspModes.IDLE.value,
                    function_mode_value,
                ]:
                    msg = f"FSP {fsp_id} currently set to function mode {valid_function_modes.index(fsp_function_mode)}, \
                            cannot be used for {fsp['function_mode']} \
                            until it is returned to IDLE."
                    return (False, msg)

                # TODO - why add these keys to the fsp dict - not good practice!
                # TODO - create a new dict from a deep copy of the fsp dict.
                fsp["frequency_band"] = common_configuration["frequency_band"]
                if "frequency_band_offset_stream1" in configuration:
                    fsp["frequency_band_offset_stream1"] = configuration[
                        "frequency_band_offset_stream1"
                    ]
                if "frequency_band_offset_stream2" in configuration:
                    fsp["frequency_band_offset_stream2"] = configuration[
                        "frequency_band_offset_stream2"
                    ]
                if fsp["frequency_band"] in ["5a", "5b"]:
                    fsp["band_5_tuning"] = common_configuration[
                        "band_5_tuning"
                    ]

                # CORR #

                if fsp["function_mode"] == "CORR":
                    # dishes may not be specified in the
                    # configuration at all, or the list may be empty
                    if "receptors" in fsp and len(fsp["receptors"]) > 0:
                        self.logger.debug(
                            f"list of receptors: {self.dish_ids}"
                        )
                        for dish in fsp["receptors"]:
                            if dish not in self.dish_ids:
                                msg = (
                                    f"Receptor {dish} does not belong to "
                                    f"subarray {self.subarray_id}."
                                )
                                self.logger.error(msg)
                                return (False, msg)
                    else:
                        msg = (
                            "'receptors' not specified for Fsp CORR config."
                            "Per ICD all receptors allocated to subarray are used"
                        )
                        self.logger.info(msg)

                    frequencyBand = freq_band_dict()[fsp["frequency_band"]][
                        "band_index"
                    ]
                    # Validate frequencySliceID.
                    # TODO: move these to consts
                    # See for ex. Fig 8-2 in the Mid.CBF DDD
                    num_frequency_slices = [4, 5, 7, 12, 26, 26]
                    if int(fsp["frequency_slice_id"]) in list(
                        range(1, num_frequency_slices[frequencyBand] + 1)
                    ):
                        pass
                    else:
                        msg = (
                            "'frequencySliceID' must be an integer in the range "
                            f"[1, {num_frequency_slices[frequencyBand]}] "
                            f"for a 'frequencyBand' of {fsp['frequency_band']}."
                        )
                        self.logger.error(msg)
                        return (False, msg)

                    # Validate zoom_factor.
                    if int(fsp["zoom_factor"]) in list(range(7)):
                        pass
                    else:
                        msg = "'zoom_factor' must be an integer in the range [0, 6]."
                        # this is a fatal error
                        self.logger.error(msg)
                        return (False, msg)

                    # Validate zoomWindowTuning.
                    if (
                        int(fsp["zoom_factor"]) > 0
                    ):  # zoomWindowTuning is required
                        if "zoom_window_tuning" in fsp:
                            if fsp["frequency_band"] not in [
                                "5a",
                                "5b",
                            ]:  # frequency band is not band 5
                                frequencyBand = [
                                    "1",
                                    "2",
                                    "3",
                                    "4",
                                    "5a",
                                    "5b",
                                ].index(fsp["frequency_band"])
                                frequency_band_start = [
                                    *map(
                                        lambda j: j[0] * 10**9,
                                        [
                                            const.FREQUENCY_BAND_1_RANGE,
                                            const.FREQUENCY_BAND_2_RANGE,
                                            const.FREQUENCY_BAND_3_RANGE,
                                            const.FREQUENCY_BAND_4_RANGE,
                                        ],
                                    )
                                ][frequencyBand] + fsp[
                                    "frequency_band_offset_stream1"
                                ]

                                frequency_slice_range = (
                                    frequency_band_start
                                    + (fsp["frequency_slice_id"] - 1)
                                    * const.FREQUENCY_SLICE_BW
                                    * 10**6,
                                    frequency_band_start
                                    + fsp["frequency_slice_id"]
                                    * const.FREQUENCY_SLICE_BW
                                    * 10**6,
                                )

                                if (
                                    frequency_slice_range[0]
                                    <= int(fsp["zoom_window_tuning"]) * 10**3
                                    <= frequency_slice_range[1]
                                ):
                                    pass
                                else:
                                    msg = "'zoomWindowTuning' must be within observed frequency slice."
                                    self.logger.error(msg)
                                    return (False, msg)
                            # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                            else:
                                if common_configuration["band_5_tuning"] == [
                                    0,
                                    0,
                                ]:  # band5Tuning not specified
                                    pass
                                else:
                                    # TODO: these validations of BW range are done many times
                                    # in many places - use a common function; also may be possible
                                    # to do them only once (ex. for band5Tuning)

                                    frequency_slice_range_1 = (
                                        fsp["band_5_tuning"][0] * 10**9
                                        + fsp["frequency_band_offset_stream1"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + (fsp["frequency_slice_id"] - 1)
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                        fsp["band_5_tuning"][0] * 10**9
                                        + fsp["frequency_band_offset_stream1"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + fsp["frequency_slice_id"]
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                    )

                                    frequency_slice_range_2 = (
                                        fsp["band_5_tuning"][1] * 10**9
                                        + fsp["frequency_band_offset_stream2"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + (fsp["frequency_slice_id"] - 1)
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                        fsp["band_5_tuning"][1] * 10**9
                                        + fsp["frequency_band_offset_stream2"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + fsp["frequency_slice_id"]
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                    )

                                    if (
                                        frequency_slice_range_1[0]
                                        <= int(fsp["zoom_window_tuning"])
                                        * 10**3
                                        <= frequency_slice_range_1[1]
                                    ) or (
                                        frequency_slice_range_2[0]
                                        <= int(fsp["zoom_window_tuning"])
                                        * 10**3
                                        <= frequency_slice_range_2[1]
                                    ):
                                        pass
                                    else:
                                        msg = "'zoomWindowTuning' must be within observed frequency slice."
                                        self.logger.error(msg)
                                        return (False, msg)
                        else:
                            msg = "FSP specified, but 'zoomWindowTuning' not given."
                            self.logger.error(msg)
                            return (False, msg)

                    # Validate integrationTime.
                    if int(fsp["integration_factor"]) in list(
                        range(
                            const.MIN_INT_TIME,
                            10 * const.MIN_INT_TIME + 1,
                            const.MIN_INT_TIME,
                        )
                    ):
                        pass
                    else:
                        msg = (
                            "'integrationTime' must be an integer in the range"
                            f" [1, 10] multiplied by {const.MIN_INT_TIME}."
                        )
                        self.logger.error(msg)
                        return (False, msg)

                    # Validate fspChannelOffset
                    try:
                        if "channel_offset" in fsp:
                            if int(fsp["channel_offset"]) >= 0:
                                pass
                            # TODO has to be a multiple of 14880
                            else:
                                msg = "fspChannelOffset must be greater than or equal to zero"
                                self.logger.error(msg)
                                return (False, msg)
                    except (TypeError, ValueError):
                        msg = "fspChannelOffset must be an integer"
                        self.logger.error(msg)
                        return (False, msg)

                    # validate outputlink
                    # check the format
                    try:
                        for element in fsp["output_link_map"]:
                            (int(element[0]), int(element[1]))
                    except (TypeError, ValueError, IndexError):
                        msg = "'outputLinkMap' format not correct."
                        self.logger.error(msg)
                        return (False, msg)

                    # Validate channelAveragingMap.
                    if "channel_averaging_map" in fsp:
                        try:
                            # validate dimensions
                            for i in range(
                                0, len(fsp["channel_averaging_map"])
                            ):
                                assert (
                                    len(fsp["channel_averaging_map"][i]) == 2
                                )

                            # validate averaging factor
                            for i in range(
                                0, len(fsp["channel_averaging_map"])
                            ):
                                # validate channel ID of first channel in group
                                if (
                                    int(fsp["channel_averaging_map"][i][0])
                                    == i
                                    * const.NUM_FINE_CHANNELS
                                    / const.NUM_CHANNEL_GROUPS
                                ):
                                    pass  # the default value is already correct
                                else:
                                    msg = (
                                        f"'channelAveragingMap'[{i}][0] is not the channel ID of the "
                                        f"first channel in a group (received {fsp['channel_averaging_map'][i][0]})."
                                    )
                                    self.logger.error(msg)
                                    return (False, msg)

                                # validate averaging factor
                                if int(fsp["channel_averaging_map"][i][1]) in [
                                    0,
                                    1,
                                    2,
                                    3,
                                    4,
                                    6,
                                    8,
                                ]:
                                    pass
                                else:
                                    msg = (
                                        f"'channelAveragingMap'[{i}][1] must be one of "
                                        f"[0, 1, 2, 3, 4, 6, 8] (received {fsp['channel_averaging_map'][i][1]})."
                                    )
                                    self.logger.error(msg)
                                    return (False, msg)
                        except (
                            TypeError,
                            AssertionError,
                        ):  # dimensions not correct
                            msg = (
                                "channel Averaging Map dimensions not correct"
                            )
                            self.logger.error(msg)
                            return (False, msg)

                    # TODO: validate destination addresses: outputHost, outputPort

            except tango.DevFailed:  # exception in ConfigureScan
                msg = (
                    "An exception occurred while configuring FSPs:"
                    f"\n{sys.exc_info()[1].args[0].desc}\n"
                    "Aborting configuration"
                )
                return (False, msg)

        # At this point, everything has been validated.
        return (True, "Scan configuration is valid.")

    @check_communicating
    def configure_scan(
        self: CbfSubarrayComponentManager, argin: str
    ) -> tuple[ResultCode, str]:
        """
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        # deconfigure to reset assigned FSPs and unsubscribe to events.
        self._deconfigure()

        full_configuration = json.loads(argin)
        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["cbf"])

        # Configure configID.
        self.config_id = str(common_configuration["config_id"])
        self.logger.debug(f"config_id: {self.config_id}")

        # Configure frequencyBand.
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        self.frequency_band = frequency_bands.index(
            common_configuration["frequency_band"]
        )
        self.logger.debug(f"frequency_band: {self.frequency_band}")

        # Prepare args for ConfigureBand
        for dish_id in self.dish_ids:
            if dish_id in self._dish_utils.dish_id_to_vcc_id.keys():
                # Fetch K-value based on dish_id
                vcc_proxy = self._all_vcc_proxies[dish_id]
                freq_offset_k = self._dish_utils.dish_id_to_k[dish_id]
                # Calculate dish sample rate
                dish_sample_rate = self._calculate_dish_sample_rate(
                    freq_band_dict()[common_configuration["frequency_band"]],
                    freq_offset_k,
                )
                # Fetch samples per frame for this freq band
                samples_per_frame = freq_band_dict()[
                    common_configuration["frequency_band"]
                ]["num_samples_per_frame"]

                args = {
                    "frequency_band": common_configuration["frequency_band"],
                    "dish_sample_rate": int(dish_sample_rate),
                    "samples_per_frame": int(samples_per_frame),
                }
                data = tango.DeviceData()
                data.insert(tango.DevString, json.dumps(args))
                vcc_proxy.command_inout("ConfigureBand", data)
            else:
                return (
                    ResultCode.FAILED,
                    f"Invalid receptor {dish_id}. ConfigureScan command failed.",
                )

        # Configure band5Tuning, if frequencyBand is 5a or 5b.
        if self.frequency_band in [4, 5]:
            stream_tuning = [
                *map(float, common_configuration["band_5_tuning"])
            ]
            self._stream_tuning = stream_tuning

        # Configure frequencyBandOffsetStream1.
        if "frequency_band_offset_stream1" in configuration:
            self.frequency_band_offset_stream1 = int(
                configuration["frequency_band_offset_stream1"]
            )
        else:
            self.frequency_band_offset_stream1 = 0
            log_msg = (
                "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            )
            self.logger.warning(log_msg)

        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "frequency_band_offset_stream2" in configuration:
            self.frequency_band_offset_stream2 = int(
                configuration["frequency_band_offset_stream2"]
            )
        else:
            self.frequency_band_offset_stream2 = 0
            log_msg = (
                "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
            )
            self.logger.warn(log_msg)

        config_dict = {
            "config_id": self.config_id,
            "frequency_band": common_configuration["frequency_band"],
            "band_5_tuning": self._stream_tuning,
            "frequency_band_offset_stream1": self.frequency_band_offset_stream1,
            "frequency_band_offset_stream2": self.frequency_band_offset_stream2,
            "rfi_flagging_mask": configuration["rfi_flagging_mask"],
        }

        # Add subset of FSP configuration to the VCC configure scan argument
        # TODO determine necessary parameters to send to VCC for each function mode
        # TODO VLBI
        reduced_fsp = []
        for fsp in configuration["fsp"]:
            function_mode = fsp["function_mode"]
            fsp_cfg = {"fsp_id": fsp["fsp_id"], "function_mode": function_mode}
            if function_mode == "CORR":
                fsp_cfg["frequency_slice_id"] = fsp["frequency_slice_id"]
            reduced_fsp.append(fsp_cfg)
        config_dict["fsp"] = reduced_fsp

        json_str = json.dumps(config_dict)
        data = tango.DeviceData()
        data.insert(tango.DevString, json_str)
        self._group_vcc.command_inout("ConfigureScan", data)

        # Configure delayModelSubscriptionPoint.
        if "delay_model_subscription_point" in configuration:
            # split delay_model_subscription_point between device FQDN and attribute name
            dm_subscription_point_split = configuration[
                "delay_model_subscription_point"
            ].split("/")
            dm_fqdn = "/".join(dm_subscription_point_split[:-1])
            dm_attr = dm_subscription_point_split[-1]

            dm_proxy = context.DeviceProxy(device_name=dm_fqdn)
            event_id = dm_proxy.subscribe_event(
                attr_name=dm_attr,
                event_type=tango.EventType.CHANGE_EVENT,
                callback=self._delay_model_event_callback,
            )

            self.logger.info(f"Subscribed to delay model event ID {event_id}")
            self._events_telstate[event_id] = dm_proxy

        # Configure searchWindow.
        if "search_window" in configuration:
            for search_window in configuration["search_window"]:
                search_window["frequency_band"] = common_configuration[
                    "frequency_band"
                ]
                search_window[
                    "frequency_band_offset_stream1"
                ] = self.frequency_band_offset_stream1
                search_window[
                    "frequency_band_offset_stream2"
                ] = self.frequency_band_offset_stream2
                if search_window["frequency_band"] in ["5a", "5b"]:
                    search_window["band_5_tuning"] = common_configuration[
                        "band_5_tuning"
                    ]
                # pass DISH ID as VCC ID integer to VCCs
                if search_window["tdc_enable"]:
                    for tdc_dest in search_window["tdc_destination_address"]:
                        tdc_dest[
                            "receptor_id"
                        ] = self._dish_utils.dish_id_to_vcc_id[
                            tdc_dest["receptor_id"]
                        ]
                # pass on configuration to VCC
                data = tango.DeviceData()
                data.insert(tango.DevString, json.dumps(search_window))
                self.logger.debug(
                    f"configuring search window: {json.dumps(search_window)}"
                )
                self._group_vcc.command_inout("ConfigureSearchWindow", data)
        else:
            log_msg = "'searchWindow' not given."
            self.logger.warning(log_msg)

        # TODO: the entire vcc configuration should move to Vcc
        # for now, run ConfigScan only wih the following data, so that
        # the obsState are properly (implicitly) updated by the command
        # (And not manually by SetObservingState as before) - relevant???

        # FSP ##################################################################
        # Configure FSP.
        # TODO add VLBI once implemented

        for fsp in configuration["fsp"]:
            # Configure fsp_id.
            fsp_id = int(fsp["fsp_id"])
            fsp_proxy = self._proxies_fsp[fsp_id - 1]
            fsp_corr_proxy = self._proxies_fsp_corr_subarray_device[fsp_id - 1]

            self._group_fsp.add(self._fqdn_fsp[fsp_id - 1])

            # Set simulation mode of FSPs to subarray sim mode
            self.logger.info(
                f"Setting Simulation Mode of FSP {fsp_id} proxies to: {self.simulation_mode} and turning them on."
            )
            for proxy in [
                fsp_proxy,
                fsp_corr_proxy,
            ]:
                proxy.write_attribute("adminMode", AdminMode.OFFLINE)
                proxy.write_attribute("simulationMode", self.simulation_mode)
                proxy.write_attribute("adminMode", AdminMode.ONLINE)
                proxy.command_inout("On")

            # Configure functionMode if IDLE
            if fsp_proxy.functionMode == FspModes.IDLE.value:
                fsp_proxy.SetFunctionMode(fsp["function_mode"])

            # change FSP subarray membership
            fsp_proxy.AddSubarrayMembership(self.subarray_id)

            # Add configID, frequency_band, band_5_tuning, and sub_id to fsp. They are not included in the "FSP" portion in configScan JSON
            fsp["config_id"] = common_configuration["config_id"]
            fsp["sub_id"] = common_configuration["subarray_id"]
            fsp["frequency_band"] = common_configuration["frequency_band"]
            if fsp["frequency_band"] in ["5a", "5b"]:
                fsp["band_5_tuning"] = common_configuration["band_5_tuning"]
            if "frequency_band_offset_stream1" in configuration:
                fsp[
                    "frequency_band_offset_stream1"
                ] = self.frequency_band_offset_stream1
            if "frequency_band_offset_stream2" in configuration:
                fsp[
                    "frequency_band_offset_stream2"
                ] = self.frequency_band_offset_stream2

            # Add channel_offset if it was omitted from the configuration (it is optional).
            if "channel_offset" not in fsp:
                self.logger.warning(
                    "channel_offset not defined in configuration. Assigning default of 1."
                )
                fsp["channel_offset"] = 1

            # Add all DISH IDs for subarray and for correlation to fsp
            # Parameter named "subarray_vcc_ids" used by HPS contains all the
            # VCCs assigned to the subarray
            # Parameter named "corr_vcc_ids" used by HPS contains the
            # subset of the subarray VCCs for which the correlation results
            # are requested to be used in Mid.CBF output products (visibilities)

            fsp["subarray_vcc_ids"] = []
            for dish in self.dish_ids:
                fsp["subarray_vcc_ids"].append(
                    self._dish_utils.dish_id_to_vcc_id[dish]
                )

            # Add the fs_sample_rate for all dishes
            fsp["fs_sample_rates"] = self._calculate_fs_sample_rates(
                common_configuration["frequency_band"]
            )

            match fsp["function_mode"]:
                case "CORR":
                    # dishes may not be specified in the
                    # configuration at all, or the list may be empty
                    fsp["corr_vcc_ids"] = []
                    if "receptors" not in fsp or len(fsp["receptors"]) == 0:
                        # In this case by the ICD, all subarray allocated resources should be used.
                        fsp["corr_vcc_ids"] = fsp["subarray_vcc_ids"].copy()
                    else:
                        for dish in fsp["receptors"]:
                            fsp["corr_vcc_ids"].append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )

                    self._corr_config.append(fsp)
                    self._corr_fsp_list.append(fsp["fsp_id"])
                    self._group_fsp_corr_subarray.add(
                        self._fqdn_fsp_corr_subarray_device[fsp_id - 1]
                    )

        # Call ConfigureScan for all FSP function mode subarray devices
        # NOTE:_corr_config is a list of fsp config JSON objects, each
        #      augmented by a number of vcc-fsp common parameters
        if len(self._corr_config) != 0:
            for this_fsp in self._corr_config:
                try:
                    this_proxy = self._proxies_fsp_corr_subarray_device[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.set_timeout_millis(12000)
                    this_proxy.ConfigureScan(json.dumps(this_fsp))

                    self.logger.info(
                        f"cbf_subarray this_fsp: {json.dumps(this_fsp)}"
                    )

                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring "
                        "FspCorrSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        self.update_component_configuration(True)

        return (ResultCode.OK, "ConfigureScan command completed OK")

    @check_communicating
    def scan(
        self: CbfSubarrayComponentManager, argin: dict[Any]
    ) -> tuple[ResultCode, str]:
        """
        Start subarray Scan operation.

        :param argin: The scan ID as JSON formatted string.
        :type argin: str
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        # Validate scan_json against the telescope model
        try:
            telmodel_validate(
                version=argin["interface"], config=argin, strictness=1
            )
            self.logger.info("Scan is valid!")
        except ValueError as e:
            msg = f"Scan validation against ska-telmodel schema failed with exception:\n {str(e)}"
            return (False, msg)

        scan_id = argin["scan_id"]
        data = tango.DeviceData()
        data.insert(tango.DevShort, scan_id)
        for group in [
            self._group_vcc,
            self._group_fsp_corr_subarray,
        ]:
            if group.get_size() > 0:
                results = group.command_inout("Scan", data)
                self.logger.info("Results from Scan:")
                for res in results:
                    self.logger.info(res.get_data())

        self.scan_id = scan_id
        self._component_scanning_callback(True)
        return (ResultCode.STARTED, "Scan command successful")

    @check_communicating
    def end_scan(self: CbfSubarrayComponentManager) -> tuple[ResultCode, str]:
        """
        End subarray Scan operation.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        # EndScan for all subordinate devices:
        for group in [
            self._group_vcc,
            self._group_fsp_corr_subarray,
        ]:
            if group.get_size() > 0:
                results = group.command_inout("EndScan")
                self.logger.info("Results from EndScan:")
                for res in results:
                    self.logger.info(res.get_data())

        self.scan_id = 0
        self._component_scanning_callback(False)
        return (ResultCode.OK, "EndScan command completed OK")

    @check_communicating
    def abort(self: CbfSubarrayComponentManager) -> None:
        """
        Abort subarray configuration or operation.
        """
        # reset ready flag
        self._ready = False

        for group in [
            self._group_vcc,
            self._group_fsp_corr_subarray,  # TODO CIP-1850 Abort/ObsReset per FSP subarray
        ]:
            if group.get_size() > 0:
                results = group.command_inout("Abort")
                self.logger.info("Results from Abort:")
                for res in results:
                    self.logger.info(res.get_data())

    @check_communicating
    def obsreset(self: CbfSubarrayComponentManager) -> None:
        """
        Reset to IDLE from abort/fault.
        """
        # if subarray is in FAULT, we must first abort VCC and FSP operation
        # this will allow us to call ObsReset on them even if they are not in FAULT
        if self.obs_faulty:
            self.abort()
            # use callback to reset FAULT state
            self._component_obs_fault_callback(False)

        try:
            # send Vcc devices to IDLE
            if self._group_vcc.get_size() > 0:
                self._group_vcc.command_inout("ObsReset")

            # send any previously assigned FSPs to IDLE
            for group in [
                self._group_fsp_corr_subarray,
            ]:
                # TODO CIP-1850 Abort/ObsReset per FSP subarray
                if group.get_size() > 0:
                    results = group.command_inout("ObsReset")
                    self.logger.info("Results from ObsReset:")
                    for res in results:
                        self.logger.info(res.get_data())

        except tango.DevFailed:
            self._component_obs_fault_callback(True)

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        self._deconfigure()

    @check_communicating
    def restart(self: CbfSubarrayComponentManager) -> None:
        """
        Restart to EMPTY from abort/fault.
        """
        # leverage obsreset to send assigned resources to IDLE and deconfigure
        self.obsreset()

        # remove all assigned VCCs to return to EMPTY
        self.release_all_vcc()

    def update_component_resources(
        self: CbfSubarrayComponentManager, resourced: bool
    ) -> None:
        """
        Update the component resource status, calling callbacks as required.

        :param resourced: whether the component is resourced.
        """
        self.logger.debug(f"update_component_resources({resourced})")
        if resourced:
            # perform "component_resourced" if not previously resourced
            if not self._resourced:
                self._component_resourced_callback(True)
        elif self._resourced:
            self._component_resourced_callback(False)

        self._resourced = resourced

    def update_component_configuration(
        self: CbfSubarrayComponentManager, configured: bool
    ) -> None:
        """
        Update the component configuration status, calling callbacks as required.

        :param configured: whether the component is configured.
        """
        self.logger.debug(
            f"update_component_configuration({configured}); configured == {configured}, self._ready == {self._ready}"
        )
        # perform component_configured/unconfigured callback if in a VALID case
        # Cases:
        # configured == False and self._ready == False -> INVALID: cannot issue component_unconfigured from IDLE
        # configured == True and self._ready == False -> VALID: can issue component_configured from IDLE
        # configured == False and self._ready == True -> VALID: can issue component_unconfigured from READY
        # configured == True and self._ready == True -> INVALID: cannot issue component_configured from READY
        if configured and not self._ready:
            self._component_configured_callback(True)
            self._ready = True
        elif not configured and self._ready:
            self._component_configured_callback(False)
            self._ready = False

    def _calculate_fs_sample_rate(
        self: CbfSubarrayComponentManager, freq_band: str, dish: str
    ) -> dict:
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
        output_sample_rates = []
        for dish in self.dish_ids:
            output_sample_rates.append(
                self._calculate_fs_sample_rate(freq_band, dish)
            )

        return output_sample_rates

    def _calculate_dish_sample_rate(
        self: CbfSubarrayComponentManager, freq_band_info, freq_offset_k
    ):
        base_dish_sample_rate_MH = freq_band_info["base_dish_sample_rate_MHz"]
        sample_rate_const = freq_band_info["sample_rate_const"]

        return (base_dish_sample_rate_MH * mhz_to_hz) + (
            sample_rate_const * freq_offset_k * const.DELTA_F
        )
