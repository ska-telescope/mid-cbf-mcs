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
from threading import Event
from typing import Any, Callable, Optional

import tango
from ska_control_model import PowerState, TaskStatus
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.base.component_manager import check_communicating
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.fsp.hps_fsp_controller_simulator import (
    HpsFspControllerSimulator,
)
from ska_mid_cbf_mcs.fsp.hps_fsp_corr_controller_simulator import (
    HpsFspCorrControllerSimulator,
)
from ska_mid_cbf_mcs.testing import context


class FspComponentManager(CbfComponentManager):
    """A component manager for the Fsp device."""

    def __init__(
        self: FspComponentManager,
        *args: Any,
        fsp_id: int,
        fsp_corr_subarray_fqdns_all: list[str],
        hps_fsp_controller_fqdn: str,  # TODO: for Mid.CBF, to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        hps_fsp_corr_controller_fqdn: str,  # TODO: for Mid.CBF, to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param fsp_id: the fsp id
        :param fsp_corr_subarray_fqdns_all: list of all
            fsp corr subarray fqdns
        # TODO: for Mid.CBF, param hps_fsp_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_controller_fqdn: FQDN of the HPS FSP controller device
        # TODO: for Mid.CBF, param hps_fsp_corr_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_corr_controller_fqdn: FQDN of the HPS FSP Correlator controller device
        """
        super().__init__(*args, **kwargs)

        self._fsp_id = fsp_id

        self._fsp_corr_subarray_fqdns_all = fsp_corr_subarray_fqdns_all

        self._hps_fsp_controller_fqdn = hps_fsp_controller_fqdn
        self._hps_fsp_corr_controller_fqdn = hps_fsp_corr_controller_fqdn

        self._group_fsp_corr_subarray = None
        self._proxy_hps_fsp_controller = None
        self._proxy_hps_fsp_corr_controller = None

        self.subarray_membership = []
        self.function_mode = FspModes.IDLE.value  # IDLE

        self.delay_model = ""

    def start_communicating(
        self: FspComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""
        if self._communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Already communicating.")
            return

        self._get_function_mode_group_proxies()

        super().start_communicating()
        self._update_component_state(power=PowerState.OFF)

    def _get_proxy(
        self: FspComponentManager, name: str, is_group: bool
    ) -> context.DeviceProxy | context.Group | None:
        """
        Attempt to get a device proxy of the specified device.

        :param name: FQDN of the device name or the name of the group proxy
        :param is_group: True if the proxy to connect to is a group proxy
        :return: context.DeviceProxy, context.Group or None if no connection
            was made
        """
        try:
            if is_group:
                self.logger.info(f"Creating group proxy connection {name}")
                proxy = context.Group(name=name)
            else:
                self.logger.info(f"Creating device proxy connection to {name}")
                proxy = context.DeviceProxy(device_name=name)
            return proxy
        except tango.DevFailed as df:
            for item in df.args:
                self.logger.error(
                    f"Failed connection to {name} : {item.reason}"
                )
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return None

    def _get_capability_proxies(
        self: FspComponentManager,
    ) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

        if not self.simulation_mode:
            self.logger.info("Trying to connect to real HPS devices")
            if self._proxy_hps_fsp_controller is None:
                self._proxy_hps_fsp_controller = self._get_proxy(
                    self._hps_fsp_controller_fqdn, is_group=False
                )

            if self._proxy_hps_fsp_corr_controller is None:
                self._proxy_hps_fsp_corr_controller = self._get_proxy(
                    self._hps_fsp_corr_controller_fqdn, is_group=False
                )
        else:
            self.logger.info("Trying to connect to Simulated HPS devices")
            self._proxy_hps_fsp_corr_controller = (
                HpsFspCorrControllerSimulator(
                    self._hps_fsp_corr_controller_fqdn
                )
            )
            self._proxy_hps_fsp_controller = HpsFspControllerSimulator(
                self._hps_fsp_controller_fqdn,
                self._proxy_hps_fsp_corr_controller,
            )

    def _get_function_mode_group_proxies(
        self: FspComponentManager,
    ) -> None:
        """Establish connections with the group proxies"""
        if self._group_fsp_corr_subarray is None:
            self._group_fsp_corr_subarray = self._get_proxy(
                "FSP Subarray Corr", is_group=True
            )
        # TODO AA0.5+: PSS, PST, VLBI

    def is_set_function_mode_allowed(self: FspComponentManager) -> bool:
        self.logger.debug("Checking if FSP SetFunctionMode is allowed.")
        if self._component_state["power"] != PowerState.ON:
            self.logger.warning(
                f"FSP SetFunctionMode not allowed in current state:\
                    {self._component_state['power']}"
            )
            return False
        if len(self.subarray_membership) > 0:
            self.logger.warning(
                f"FSP {self._fsp_id} currently belongs to \
                    subarray(s) {self.subarray_membership}, \
                    cannot change function mode at this time."
            )
            return False
        return True

    @check_communicating
    def _set_function_mode(
        self: FspComponentManager,
        function_mode: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Switch the function mode of the HPS FSP controller

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "SetFunctionMode", task_callback, task_abort_event
        ):
            return

        match function_mode:
            case "IDLE":
                self.function_mode = FspModes.IDLE.value
            case "CORR":
                self.function_mode = FspModes.CORR.value
            # CIP-1924 temporarily removed PSS/PST as they are not currently implemented
            case "PSS-BF":
                self.logger.error(
                    "Error in SetFunctionMode; PSS-BF not implemented in AA0.5"
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "PSS-BF not implemented",
                    ),
                )
                return
            case "PST-BF":
                self.logger.error(
                    "Error in SetFunctionMode; PST-BF not implemented in AA0.5"
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "PST-BF not implemented",
                    ),
                )
                return
            case "VLBI":
                self.logger.error(
                    "Error in SetFunctionMode; VLBI not implemented in AA0.5"
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "VLBI not implemented",
                    ),
                )
                return
            case _:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        f"{function_mode} not a valid FSP function mode.",
                    ),
                )
                return

        self.logger.info(
            f"FSP set to function mode {FspModes(self.function_mode).name}"
        )
        self._device_attr_change_callback("functionMode", self.function_mode)
        self._device_attr_archive_callback("functionMode", self.function_mode)

        try:
            self._proxy_hps_fsp_controller.SetFunctionMode(self.function_mode)
        except tango.DevFailed as df:
            self.logger.error(f"{df.args[0].desc}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue SetFunctionMode command to HPS FSP controller",
                ),
            )
            return

        task_callback(
            result=(ResultCode.OK, "SetFunctionMode completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def set_function_mode(
        self: FspComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Switch the function mode of the FSP; can only be done if currently
        unassigned from any subarray membership.

        :param function_mode: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._set_function_mode,
            args=[argin],
            is_cmd_allowed=self.is_set_function_mode_allowed,
            task_callback=task_callback,
        )

    def _remove_subarray_from_group_proxy(
        self: FspComponentManager, subarray_id: int
    ) -> None:
        """Remove FSP function mode subarray device from group proxy for specified subarray."""
        match self.function_mode:
            case FspModes.IDLE.value:
                self.logger.error(
                    f"FSP {self._fsp_id} function mode is IDLE; error removing subarray {subarray_id} function mode device from group proxy."
                )
            case FspModes.CORR.value:
                for fqdn in self._fsp_corr_subarray_fqdns_all:
                    # remove CORR subarray device with FQDN index matching subarray_id
                    if subarray_id == int(fqdn[-2:]):
                        self._group_fsp_corr_subarray.remove(fqdn)
                        break
                else:
                    self.logger.error(
                        f"FSP {self._fsp_id} CORR subarray {subarray_id} FQDN not found in properties."
                    )
            case FspModes.PSS_BF.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; PSS-BF not implemented in AA0.5"
                )
            case FspModes.PST_BF.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; PST-BF not implemented in AA0.5"
                )
            case FspModes.VLBI.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; VLBI not implemented in AA0.5"
                )

    @check_communicating
    def remove_subarray_membership(
        self: FspComponentManager, subarray_id: int
    ) -> DevVarLongStringArrayType:
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing
        (no subarray is using this FSP), set function mode to empty.

        :param subarray_id: an integer representing the subarray affiliation

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        result_code, message = (
            ResultCode.OK,
            "RemoveSubarrayMembership completed OK",
        )
        if subarray_id in self.subarray_membership:
            self.logger.info(
                f"Removing subarray {subarray_id} from subarray membership."
            )

            self._remove_subarray_from_group_proxy(subarray_id)

            self.subarray_membership.remove(subarray_id)
            self._device_attr_change_callback(
                "subarrayMembership", self.subarray_membership
            )
            self._device_attr_archive_callback(
                "subarrayMembership", self.subarray_membership
            )
        else:
            result_code, message = (
                ResultCode.FAILED,
                f"FSP does not belong to subarray {subarray_id}",
            )

        return (result_code, message)

    # TODO: subarray handle FSP GoToIdle and resetting function mode to IDLE

    def _add_subarray_to_group_proxy(
        self: FspComponentManager, subarray_id: int
    ) -> None:
        """Add FSP function mode subarray device to group proxy for specified subarray."""
        match self.function_mode:
            case FspModes.IDLE.value:
                self.logger.error(
                    f"FSP {self._fsp_id} function mode is IDLE; error adding subarray {subarray_id} function mode device to group proxy."
                )
            case FspModes.CORR.value:
                for fqdn in self._fsp_corr_subarray_fqdns_all:
                    # add CORR subarray device with FQDN index matching subarray_id
                    if subarray_id == int(fqdn[-2:]):
                        self._group_fsp_corr_subarray.add(fqdn)
                        break
                else:
                    self.logger.error(
                        f"FSP {self._fsp_id} CORR subarray {subarray_id} FQDN not found in properties."
                    )
            case FspModes.PSS_BF.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; PSS-BF not implemented in AA0.5"
                )
            case FspModes.PST_BF.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; PST-BF not implemented in AA0.5"
                )
            case FspModes.VLBI.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; VLBI not implemented in AA0.5"
                )

    @check_communicating
    def add_subarray_membership(
        self: FspComponentManager, subarray_id: int
    ) -> DevVarLongStringArrayType:
        """
        Add a subarray to the subarrayMembership list.

        :param subarray_id: an integer representing the subarray affiliation,
            value in [1, 16]

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        result_code, message = (
            ResultCode.OK,
            "AddSubarrayMembership completed OK",
        )
        if len(self.subarray_membership) == const.MAX_SUBARRAY:
            result_code, message = (
                ResultCode.FAILED,
                f"Fsp already assigned to the maximum number of subarrays ({const.MAX_SUBARRAY})",
            )
        elif subarray_id - 1 not in range(const.MAX_SUBARRAY):
            result_code, message = (
                ResultCode.FAILED,
                f"Subarray {subarray_id} invalid; must be in range [1, {const.MAX_SUBARRAY}]",
            )
        elif subarray_id not in self.subarray_membership:
            self.logger.info(
                f"Adding subarray {subarray_id} to subarray membership"
            )

            self._add_subarray_to_group_proxy(subarray_id)

            self.subarray_membership.append(subarray_id)
            self._device_attr_change_callback(
                "subarrayMembership", self.subarray_membership
            )
            self._device_attr_archive_callback(
                "subarrayMembership", self.subarray_membership
            )
        else:
            result_code, message = (
                ResultCode.FAILED,
                f"FSP already belongs to subarray {subarray_id}",
            )

        return (result_code, message)

    def _issue_command_all_subarray_group_proxies(
        self: FspComponentManager, command_name: str
    ):
        """
        Issue command to all function mode subarray devices, independent of
        subarray membership.
        """
        # TODO AA0.5+: PSS, PST, VLBI
        group_fsp_corr_subarray = self._get_proxy(
            "FSP Subarray Corr", is_group=True
        )
        for fqdn in self._fsp_corr_subarray_fqdns_all:
            group_fsp_corr_subarray.add(fqdn)

        group_fsp_corr_subarray.command_inout(command_name)

    def is_on_allowed(self: FspComponentManager) -> bool:
        self.logger.debug("Checking if FSP On is allowed.")
        if self._component_state["power"] not in [
            PowerState.OFF,
            PowerState.UNKNOWN,
        ]:
            self.logger.warning(
                f"On not allowed; PowerState is {self._component_state['power']}"
            )
            return False
        return True

    @check_communicating
    def _on(
        self: FspComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Turn on the FSP and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        self._get_capability_proxies()

        # TODO: in the future, DsFspController to implement on(), off()
        # commands. Then invoke here the DsFspController on() command.
        self._issue_command_all_subarray_group_proxies("On")

        # Update state callback
        self._update_component_state(power=PowerState.ON)

        task_callback(
            result=(ResultCode.OK, "On completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def on(
        self: FspComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Turn on the FSP and its subordinate devices

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._on,
            is_cmd_allowed=self.is_on_allowed,
            task_callback=task_callback,
        )

    def is_off_allowed(self: FspComponentManager) -> bool:
        self.logger.debug("Checking if FSP Off is allowed.")
        if self._component_state["power"] not in [
            PowerState.ON,
            PowerState.UNKNOWN,
        ]:
            self.logger.warning(
                f"Off not allowed; PowerState is {self._component_state['power']}"
            )
            return False
        return True

    @check_communicating
    def _off(
        self: FspComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Turn off the FSP and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        # TODO: in the future, DsFspController to implement on(), off()
        # commands. Then invoke here the DsFspController off() command.
        self._issue_command_all_subarray_group_proxies("Off")

        for subarray_ID in self.subarray_membership:
            self.remove_subarray_membership(subarray_ID)

        # Update state callback
        self._update_component_state(power=PowerState.OFF)

        task_callback(
            result=(ResultCode.OK, "Off completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def off(
        self: FspComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Turn off the FSP and its subordinate devices

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )

    @check_communicating
    def update_delay_model(
        self: FspComponentManager, argin: str
    ) -> DevVarLongStringArrayType:
        """
        Update the FSP's delay model (serialized JSON object)

        :param argin: the delay model data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering update_delay_model")
        result_code, message = ResultCode.OK, "UpdateDelayModels completed OK"
        # update if current function mode is either PSS-BF, PST-BF or CORR
        if self.function_mode in [
            FspModes.PSS_BF.value,
            FspModes.PST_BF.value,
            FspModes.CORR.value,
        ]:
            # the whole delay model must be stored
            self.delay_model = argin
            delay_model = json.loads(argin)

            # TODO handle delay models in function modes other than CORR
            try:
                self._proxy_hps_fsp_corr_controller.UpdateDelayModels(
                    json.dumps(delay_model)
                )
            except tango.DevFailed as df:
                self.logger.error(f"{df.args[0].desc}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                result_code, message = (
                    ResultCode.FAILED,
                    "Failed to issue UpdateDelayModels command to HPS FSP Corr controller",
                )

        else:
            result_code, message = (
                ResultCode.FAILED,
                f"Delay models not used in function mode {self.function_mode}",
            )

        return (result_code, message)

    @check_communicating
    def get_fsp_corr_config_id(
        self: FspComponentManager,
    ) -> str:
        """
        Get the configID for all the fspCorrSubarray

        :return: the configID
        :rtype: str
        """

        if self._connected:
            result = {}
            for proxy in self._proxy_fsp_corr_subarray:
                result[str(proxy)] = proxy.configID
            return str(result)

        else:
            log_msg = "Fsp getConfigID command failed: \
                    proxies not connected"
            self.logger.error(log_msg)
            return ""
