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

import copy
import json
import logging
from typing import Callable, List, Optional, Tuple

import tango
from ska_tango_base.base.component_manager import check_communicating
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.fsp.hps_fsp_controller_simulator import (
    HpsFspControllerSimulator,
)
from ska_mid_cbf_mcs.fsp.hps_fsp_corr_controller_simulator import (
    HpsFspCorrControllerSimulator,
)
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy


class FspComponentManager(CbfComponentManager):
    """A component manager for the Fsp device."""

    def __init__(
        self: FspComponentManager,
        logger: logging.Logger,
        fsp_id: int,
        fsp_corr_subarray_fqdns_all: List[str],
        hps_fsp_controller_fqdn: str,  # TODO: for Mid.CBF, to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        hps_fsp_corr_controller_fqdn: str,  # TODO: for Mid.CBF, to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
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
        :param push_change_event: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        :param simulation_mode: simulation mode identifies if the real FSP HPS
            applications or the simulator should be connected
        """
        self._connected = False

        self._fsp_id = fsp_id

        self._fsp_corr_subarray_fqdns_all = fsp_corr_subarray_fqdns_all

        self._hps_fsp_controller_fqdn = hps_fsp_controller_fqdn
        self._hps_fsp_corr_controller_fqdn = hps_fsp_corr_controller_fqdn

        self._group_fsp_corr_subarray = None
        self._proxy_hps_fsp_controller = None
        self._proxy_hps_fsp_corr_controller = None

        self._subarray_membership = []
        self.function_mode = FspModes.IDLE.value  # IDLE
        self._jones_matrix = ""
        self._delay_model = ""
        self._timing_beam_weights = ""

        self._simulation_mode = simulation_mode

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    @property
    def subarray_membership(self: FspComponentManager) -> List[int]:
        """
        Subarray Membership

        :return: an array of affiliations of the FSP.
        :rtype: List[int]
        """
        return self._subarray_membership

    @property
    def delay_model(self: FspComponentManager) -> str:
        """
        Delay Model

        :return: the delay model
        :rtype: str
        """
        return self._delay_model

    @property
    def simulation_mode(self: FspComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(
        self: FspComponentManager, value: SimulationMode
    ) -> None:
        """
        Set the simulation mode of the component manager.

        :param value: value to set simulation mode to
        """
        self._simulation_mode = value

    def start_communicating(
        self: FspComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._get_function_mode_group_proxies()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: FspComponentManager) -> None:
        """Stop communication with the component"""

        super().stop_communicating()

        self._connected = False

    def _get_proxy(
        self: FspComponentManager, fqdn_or_name: str, is_group: bool
    ) -> CbfDeviceProxy | CbfGroupProxy | None:
        """
        Attempt to get a device proxy of the specified device.

        :param fqdn_or_name: FQDN of the device to connect to
            or the name of the group proxy to connect to
        :param is_group: True if the proxy to connect to is a group proxy
        :return: CbfDeviceProxy or CbfGroupProxy or None if no connection was made
        """
        try:
            self.logger.info(f"Attempting connection to {fqdn_or_name} ")
            if is_group:
                device_proxy = CbfGroupProxy(
                    name=fqdn_or_name, logger=self.logger
                )
            else:
                device_proxy = CbfDeviceProxy(
                    fqdn=fqdn_or_name, logger=self.logger, connect=False
                )
                device_proxy.connect(
                    max_time=0
                )  # Make one attempt at connecting
            return device_proxy
        except tango.DevFailed as df:
            for item in df.args:
                self.logger.error(
                    f"Failed connection to {fqdn_or_name} : {item.reason}"
                )
            self.update_component_fault(True)
            return None

    def _get_capability_proxies(
        self: FspComponentManager,
    ) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

        if not self._simulation_mode:
            self.logger.info("Trying to connected to REAL HPS devices")
            if self._proxy_hps_fsp_controller is None:
                self._proxy_hps_fsp_controller = self._get_proxy(
                    self._hps_fsp_controller_fqdn, is_group=False
                )

            if self._proxy_hps_fsp_corr_controller is None:
                self._proxy_hps_fsp_corr_controller = self._get_proxy(
                    self._hps_fsp_corr_controller_fqdn, is_group=False
                )
        else:
            self.logger.info("Trying to connected to Simulated HPS devices")
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
    def remove_subarray_membership(
        self: FspComponentManager, subarray_id: int
    ) -> Tuple[ResultCode, str]:
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
        result_code = ResultCode.OK
        message = "Fsp RemoveSubarrayMembership command completed OK"
        if subarray_id in self._subarray_membership:
            self._subarray_membership.remove(subarray_id)
            self._push_change_event(
                "subarrayMembership", self._subarray_membership
            )
            # change function mode to IDLE if no subarrays are using it.
            if len(self._subarray_membership) == 0:
                # TODO AA0.5+: PSS, PST, VLBI
                match self.function_mode:
                    case FspModes.CORR.value:
                        self._group_fsp_corr_subarray.command_inout("GoToIdle")
                    case FspModes.PSS_BF.value:
                        self.logger.error(
                            "Error in GoToIdle; PSS-BF not implemented in AA0.5"
                        )
                    case FspModes.PST_BF.value:
                        self.logger.error(
                            "Error in GoToIdle; PST-BF not implemented in AA0.5"
                        )
                    case FspModes.VLBI.value:
                        self.logger.error(
                            "Error in GoToIdle; VLBI not implemented in AA0.5"
                        )
                self._remove_subarray_from_group_proxy(subarray_id)
                self.set_function_mode("IDLE")
        else:
            result_code = ResultCode.FAILED
            message = f"Fsp RemoveSubarrayMembership command failed; FSP does not belong to subarray {subarray_id}."

        return (result_code, message)

    @check_communicating
    def add_subarray_membership(
        self: FspComponentManager, subarray_id: int
    ) -> Tuple[ResultCode, str]:
        """
        Add a subarray to the subarrayMembership list.

        :param subarray_id: an integer representing the subarray affiliation
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        result_code = ResultCode.OK
        message = "Fsp AddSubarrayMembership command completed OK"
        if len(self._subarray_membership) == const.MAX_SUBARRAY:
            message = (
                "Fsp already assigned to the maximum number subarrays "
                f"({const.MAX_SUBARRAY})"
            )
            result_code = ResultCode.FAILED
        elif subarray_id not in self._subarray_membership:
            self._add_subarray_to_group_proxy(subarray_id)
            self._subarray_membership.append(subarray_id)
            self._push_change_event(
                "subarrayMembership", self._subarray_membership
            )
        else:
            result_code = ResultCode.FAILED
            message = f"Fsp AddSubarrayMembership command failed; FSP already belongs to subarray {subarray_id}."

        return (result_code, message)

    def _issue_command_all_subarray_group_proxies(
        self: FspComponentManager, command: str
    ):
        """Issue command to all function mode subarray devices, independent of subarray membership."""
        # TODO AA0.5+: PSS, PST, VLBI
        group_fsp_corr_subarray = self._get_proxy(
            "FSP Subarray Corr", is_group=True
        )
        for fqdn in self._fsp_corr_subarray_fqdns_all:
            group_fsp_corr_subarray.add(fqdn)

        group_fsp_corr_subarray.command_inout(command)

    @check_communicating
    def on(
        self: FspComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the fsp and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:
            self.logger.info(f"Value of _connected: {self._connected}")

            self._get_capability_proxies()

            # TODO: in the future, DsFspController to implement on(), off()
            # commands. Then invoke here the DsFspController on() command.
            self._issue_command_all_subarray_group_proxies("On")

            message = "Fsp On command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp On command failed: \
                    proxies not connected"
            self.logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def off(
        self: FspComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn off the fsp and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:
            # TODO: in the future, DsFspController to implement on(), off()
            # commands. Then invoke here the DsFspController off() command.
            self._issue_command_all_subarray_group_proxies("Off")

            for subarray_ID in self._subarray_membership:
                self.remove_subarray_membership(subarray_ID)

            message = "Fsp Off command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp Off command failed: \
                    proxies not connected"
            self.logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def standby(
        self: FspComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Put the fsp into low power standby mode

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        message = "Fsp Standby command completed OK"
        return (ResultCode.OK, message)

    @check_communicating
    def set_function_mode(
        self: FspComponentManager, function_mode: str
    ) -> Tuple[ResultCode, str]:
        """
        Switch the function mode of the FSP; can only be done if currently
        unassigned from any subarray membership.

        :param function_mode: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:
            if len(self._subarray_membership) > 0:
                self.logger.error(
                    f"FSP {self._fsp_id} currently belongs to \
                                   subarray(s) {self._subarray_membership}, \
                                   cannot change function mode at this time."
                )
                return (
                    ResultCode.FAILED,
                    "Fsp SetFunctionMode command FAILED",
                )
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
                    return (ResultCode.FAILED, "PSS-BF not implemented")
                case "PST-BF":
                    self.logger.error(
                        "Error in SetFunctionMode; PST-BF not implemented in AA0.5"
                    )
                    return (ResultCode.FAILED, "PST-BF not implemented")
                case "VLBI":
                    self.logger.error(
                        "Error in SetFunctionMode; VLBI not implemented in AA0.5"
                    )
                    return (ResultCode.FAILED, "VLBI not implemented")
                case _:
                    message = f"{function_mode} not a valid FSP function mode."
                    return (ResultCode.FAILED, message)

            try:
                self._proxy_hps_fsp_controller.SetFunctionMode(
                    self.function_mode
                )
            except tango.DevFailed as df:
                return (
                    ResultCode.FAILED,
                    f"Failed to issue SetFunctionMode command to HPS FSP controller; {df.args[0].desc}",
                )

            self._push_change_event("functionMode", self.function_mode)
            self.logger.info(
                f"FSP set to function mode {FspModes(self.function_mode).name}"
            )

            return (ResultCode.OK, "Fsp SetFunctionMode command completed OK")

        else:
            log_msg = "Fsp SetFunctionMode command failed: \
                    proxies not connected"
            self.logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def update_delay_model(
        self: FspComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Update the FSP's delay model (serialized JSON object)

        :param argin: the delay model data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering update_delay_model")

        if self._connected:
            # update if current function mode is either PSS-BF, PST-BF or CORR
            if self.function_mode in [
                FspModes.PSS_BF.value,
                FspModes.PST_BF.value,
                FspModes.CORR.value,
            ]:
                # the whole delay model must be stored
                self._delay_model = copy.deepcopy(argin)
                delay_model = json.loads(argin)
                # TODO handle delay models in function modes other than CORR
                self._proxy_hps_fsp_corr_controller.UpdateDelayModels(
                    json.dumps(delay_model)
                )

            else:
                log_msg = (
                    "Fsp UpdateDelayModel command failed: "
                    f"model not used in function mode {self.function_mode}"
                )
                self.logger.warning(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "Fsp UpdateDelayModel command completed OK"
            return (ResultCode.OK, message)
        else:
            log_msg = "Fsp UpdateDelayModel command failed: \
                    proxies not connected"
            self.logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

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
