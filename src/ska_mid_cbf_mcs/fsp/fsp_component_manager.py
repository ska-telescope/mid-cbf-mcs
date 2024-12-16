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

from threading import Event
from typing import Callable, Optional

import tango
from ska_control_model import AdminMode, PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


class FspComponentManager(CbfComponentManager):
    """
    A component manager for the Fsp device.
    """

    def __init__(
        self: FspComponentManager,
        *args: any,
        fsp_id: int,
        all_fsp_corr_subarray_fqdn: list[str],
        all_fsp_pst_subarray_fqdn: list[str],
        # TODO: for Mid.CBF, to be updated to a list of FQDNs (max length = 20),
        # one entry for each Talon board in the FSP_UNIT
        hps_fsp_controller_fqdn: str,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param fsp_id: the fsp id
        :param all_fsp_corr_subarray_fqdn: list of all fsp corr subarray fqdns
        :param all_fsp_pst_subarray_fqdn: list of all fsp pst subarray fqdns
        # TODO: for Mid.CBF, param hps_fsp_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_controller_fqdn: FQDN of the HPS FSP controller device
        """
        super().__init__(*args, **kwargs)

        self._fsp_id = fsp_id
        self._all_fsp_corr_subarray_fqdn = all_fsp_corr_subarray_fqdn
        self._all_fsp_pst_subarray_fqdn = all_fsp_pst_subarray_fqdn
        self._hps_fsp_controller_fqdn = hps_fsp_controller_fqdn

        # Proxies to all FSP function mode devices
        self._function_mode_proxies = {}

        self._proxy_hps_fsp_controller = None

        self.subarray_membership = []
        self.function_mode = FspModes.IDLE.value  # IDLE

    # -------------
    # Communication
    # -------------

    def _create_function_mode_proxies(
        self: FspComponentManager,
        fqdns: list[str],
        proxies: dict[str, context.DeviceProxy],
    ) -> None:
        """
        Helper function to create dict of proxies for differnt function modes.
        """
        for fqdn in fqdns:
            try:
                proxies[fqdn] = context.DeviceProxy(fqdn)
            except tango.DevFailed as df:
                self.logger.error(f"Failure in connecting to {fqdn}; {df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return

    def _start_communicating(
        self: FspComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self._create_function_mode_proxies(
            list(self._all_fsp_corr_subarray_fqdn)
            + list(self._all_fsp_pst_subarray_fqdn),
            self._function_mode_proxies,
        )

        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_controller = context.DeviceProxy(
                    device_name=self._hps_fsp_controller_fqdn
                )
                self._proxy_hps_fsp_controller.SetFunctionMode(
                    self.function_mode
                )
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failure in connection to HPS FSP controller; {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return

        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    # -------------
    # Fast Commands
    # -------------

    # None at this time

    # ---------------------
    # Long Running Commands
    # ---------------------

    # --- SetFunctionMode Command --- #

    def is_set_function_mode_allowed(self: FspComponentManager) -> bool:
        """
        Check if the SetFunctionMode command is allowed

        :return: True if the SetFunctionMode command is allowed, False otherwise
        """
        self.logger.debug("Checking if SetFunctionMode is allowed")
        if self.communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.warning(
                "SetFunctionMode command can only be issued when FSP is in AdminMode.OFFLINE/DevState.DISABLED"
            )
            return False
        if len(self.subarray_membership) != 0:
            self.logger.warning(
                f"SetFunctionMode command cannot be issued because FSP currently has subarray membership: {self.subarray_membership}."
            )
            return False
        return True

    def _validate_function_mode(
        self: FspComponentManager, function_mode: str
    ) -> bool:
        """
        Check if FSP function mode is valid.

        :param function_mode: function mode string to be evaluated
        :return: True if validation passes, otherwise False
        """
        # TODO: remove these conditions as new function modes are implemented
        if function_mode not in FspModes._member_names_ or function_mode in [
            "PSS-BF",
            "VLBI",
        ]:
            self.logger.error(
                f"{function_mode} not a valid FSP function mode."
            )
            return False
        return True

    def _set_function_mode(
        self: FspComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Switch the function mode of the FSP; can only be done if currently
        unassigned from any subarray membership.

        :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
        :param task_callback: Callback function to update task status
        :param task_abort_event: Event to signal task abort.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "InitSysParam", task_callback, task_abort_event
        ):
            return

        validate_success = self._validate_function_mode(argin)
        if not validate_success:
            task_callback(
                result=(
                    ResultCode.FAILED,
                    f"Failed to validate FSP function mode {argin}",
                ),
                status=TaskStatus.FAILED,
            )
            return

        function_mode = FspModes[argin].value
        self.function_mode = function_mode
        self.device_attr_change_callback("functionMode", self.function_mode)
        self.device_attr_archive_callback("functionMode", self.function_mode)
        self.logger.info(
            f"FSP set to function mode {FspModes(function_mode).name}"
        )

        task_callback(
            result=(
                ResultCode.OK,
                "SetFunctionMode completed OK",
            ),
            status=TaskStatus.COMPLETED,
        )
        return

    def set_function_mode(
        self: FspComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit SetFunctionMode command thread to task executor queue.

        :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
        :param task_callback: Callback function to update task status

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

    # --- AddSubarrayMembership command --- #

    def _validate_subarray_id(
        self: FspComponentManager, subarray_id: int
    ) -> bool:
        """
        Validate subarray ID to be added to current membership.

        :param subarray_id: an integer representing the subarray affiliation,
            value in [1, 16]

        :return: True if subarray ID is valid, otherwise False
        """
        if len(self.subarray_membership) == const.MAX_SUBARRAY:
            self.logger.error(
                f"Fsp already assigned to the maximum number of subarrays ({const.MAX_SUBARRAY})"
            )
            return False
        if subarray_id not in range(1, const.MAX_SUBARRAY + 1):
            self.logger.error(
                f"Subarray {subarray_id} invalid; must be in range [1, {const.MAX_SUBARRAY}]"
            )
            return False
        if subarray_id in self.subarray_membership:
            self.logger.error(f"FSP already belongs to subarray {subarray_id}")
            return False

        return True

    def _function_mode_subarray_online(
        self: FspComponentManager, subarray_id: int
    ) -> bool:
        """
        Set FSP function mode subarray device to AdminMode.ONLINE

        :param subarray_id: ID of subarray for which to set function mode proxy online
        :return: False if unsuccessful in setting online the FSP function mode subarray proxy,
            True otherwise
        """
        match self.function_mode:
            case FspModes.IDLE.value:
                self.logger.error(
                    f"FSP {self._fsp_id} function mode is IDLE; error adding subarray {subarray_id} function mode device to group proxy."
                )

            case FspModes.CORR.value:
                fqdn = self._all_fsp_corr_subarray_fqdn[subarray_id - 1]
                try:
                    proxy = self._function_mode_proxies[fqdn]
                    # set FSP devices simulationMode and adminMode attributes
                    proxy.simulationMode = self.simulation_mode
                    proxy.adminMode = AdminMode.ONLINE
                except KeyError as ke:
                    self.logger.error(
                        f"FSP {self._fsp_id} CORR subarray {subarray_id} FQDN not found in properties; {ke}"
                    )
                    return False
                except tango.DevFailed as df:
                    self.logger.error(f"Failed to turn on {fqdn}; {df}")
                    return False
                return True

            case FspModes.PSS_BF.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; PSS-BF not currently implemented"
                )

            case FspModes.PST_BF.value:
                fqdn = self._all_fsp_pst_subarray_fqdn[subarray_id - 1]
                try:
                    proxy = self._function_mode_proxies[fqdn]
                    # set FSP devices simulationMode and adminMode attributes
                    proxy.simulationMode = self.simulation_mode
                    proxy.adminMode = AdminMode.ONLINE
                except KeyError as ke:
                    self.logger.error(
                        f"FSP {self._fsp_id} PST-BF subarray {subarray_id} FQDN not found in properties; {ke}"
                    )
                    return False
                except tango.DevFailed as df:
                    self.logger.error(f"Failed to turn on {fqdn}; {df}")
                    return False
                return True

            case FspModes.VLBI.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; VLBI not currently implemented"
                )

        return False

    def is_add_subarray_membership_allowed(self: FspComponentManager) -> bool:
        """
        Check if the AddSubarrayMembership command is allowed

        :return: True if the AddSubarrayMembership command is allowed, False otherwise
        """
        self.logger.debug("Checking if AddSubarrayMembership is allowed")
        if not self.is_communicating:
            return False
        if self.function_mode == FspModes.IDLE.value:
            self.logger.warning(
                "AddSubarrayMembership command cannot be issued because FSP currently in function mode IDLE."
            )
            return False
        return True

    def _add_subarray_membership(
        self: FspComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Add a subarray to the subarrayMembership list.

        :param argin: an integer representing the subarray affiliation,
            value in [1, 16]
        :param task_callback: Callback function to update task status
        :param task_abort_event: Event to signal task abort.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "AddSubarrayMembership", task_callback, task_abort_event
        ):
            return

        validate_success = self._validate_subarray_id(argin)
        if not validate_success:
            task_callback(
                result=(
                    ResultCode.FAILED,
                    f"Unable to add subarray membership for subarray ID {argin}",
                ),
                status=TaskStatus.FAILED,
            )
            return

        on_success = self._function_mode_subarray_online(argin)
        if not on_success:
            task_callback(
                result=(
                    ResultCode.FAILED,
                    f"Unsuccessful in setting online function mode device for subarray {argin}",
                ),
                status=TaskStatus.FAILED,
            )
            return

        self.logger.info(f"Adding subarray {argin} to subarray membership.")

        self.subarray_membership.append(argin)
        self.device_attr_change_callback(
            "subarrayMembership", list(self.subarray_membership)
        )
        self.device_attr_archive_callback(
            "subarrayMembership", list(self.subarray_membership)
        )

        task_callback(
            result=(
                ResultCode.OK,
                "AddSubarrayMembership completed OK",
            ),
            status=TaskStatus.COMPLETED,
        )
        return

    def add_subarray_membership(
        self: FspComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit AddSubarrayMembership command thread to task executor queue.

        :param argin: an integer representing the subarray affiliation
        :param task_callback: Callback function to update task status

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._add_subarray_membership,
            args=[argin],
            is_cmd_allowed=self.is_add_subarray_membership_allowed,
            task_callback=task_callback,
        )

    # --- RemoveSubarrayMembership Command --- #

    def _function_mode_subarray_offline(
        self: FspComponentManager, subarray_id: int
    ) -> bool:
        """
        Set FSP function mode subarray device to AdminMode.OFFLINE

        :param subarray_id: ID of subarray for which to set function mode proxy offline
        :return: False if unsuccessful in setting offline the FSP function mode subarray proxy,
            True otherwise
        """
        match self.function_mode:
            case FspModes.IDLE.value:
                self.logger.error(
                    f"FSP {self._fsp_id} function mode is IDLE, no subarray membership to remove."
                )

            case FspModes.CORR.value:
                fqdn = self._all_fsp_corr_subarray_fqdn[subarray_id - 1]
                try:
                    proxy = self._function_mode_proxies[fqdn]
                    proxy.adminMode = AdminMode.OFFLINE
                except KeyError as ke:
                    self.logger.error(
                        f"FSP {self._fsp_id} CORR subarray {subarray_id} FQDN not found in properties; {ke}"
                    )
                    return False
                except tango.DevFailed as df:
                    self.logger.error(f"Failed to turn off {fqdn}; {df}")
                    return False
                return True

            case FspModes.PSS_BF.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; PSS-BF not currently implemented"
                )

            case FspModes.PST_BF.value:
                fqdn = self._all_fsp_pst_subarray_fqdn[subarray_id - 1]
                try:
                    proxy = self._function_mode_proxies[fqdn]
                    proxy.adminMode = AdminMode.OFFLINE
                except KeyError as ke:
                    self.logger.error(
                        f"FSP {self._fsp_id} PST-BF subarray {subarray_id} FQDN not found in properties; {ke}"
                    )
                    return False
                except tango.DevFailed as df:
                    self.logger.error(f"Failed to turn off {fqdn}; {df}")
                    return False
                return True

            case FspModes.VLBI.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; VLBI not currently implemented"
                )

        return False

    def is_remove_subarray_membership_allowed(
        self: FspComponentManager,
    ) -> bool:
        """
        Check if the RemoveSubarrayMembership command is allowed

        :return: True if the RemoveSubarrayMembership command is allowed, False otherwise
        """
        self.logger.debug("Checking if RemoveSubarrayMembership is allowed")
        if not self.is_communicating:
            return False
        if self.function_mode == FspModes.IDLE.value:
            self.logger.warning(
                "RemoveSubarrayMembership command cannot be issued because FSP currently in function mode IDLE."
            )
            return False
        return True

    def _remove_subarray_membership(
        self: FspComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing
        (no subarray is using this FSP), set function mode to empty.

        :param argin: an integer representing the subarray affiliation
        :param task_callback: Callback function to update task status
        :param task_abort_event: Event to signal task abort.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "RemoveSubarrayMembership", task_callback, task_abort_event
        ):
            return

        if argin not in self.subarray_membership:
            task_callback(
                result=(
                    ResultCode.FAILED,
                    f"FSP does not belong to subarray {argin}",
                ),
                status=TaskStatus.FAILED,
            )
            return

        self.logger.info(
            f"Removing subarray {argin} from subarray membership."
        )

        off_success = self._function_mode_subarray_offline(argin)
        if not off_success:
            task_callback(
                result=(
                    ResultCode.FAILED,
                    f"Unsuccessful in setting offline function mode device for subarray {argin}",
                ),
                status=TaskStatus.FAILED,
            )
            return

        self.subarray_membership.remove(argin)
        self.device_attr_change_callback(
            "subarrayMembership", list(self.subarray_membership)
        )
        self.device_attr_archive_callback(
            "subarrayMembership", list(self.subarray_membership)
        )

        task_callback(
            result=(
                ResultCode.OK,
                "RemoveSubarrayMembership completed OK",
            ),
            status=TaskStatus.COMPLETED,
        )
        return

    def remove_subarray_membership(
        self: FspComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveSubarrayMembership command thread to task executor queue.

        :param argin: an integer representing the subarray affiliation
        :param task_callback: Callback function to update task status

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._remove_subarray_membership,
            args=[argin],
            is_cmd_allowed=self.is_remove_subarray_membership_allowed,
            task_callback=task_callback,
        )
