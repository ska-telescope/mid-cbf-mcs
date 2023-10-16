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
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.component.util import check_communicating
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
        fsp_pss_subarray_fqdns_all: List[str],
        fsp_pst_subarray_fqdns_all: List[str],
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
        :param fsp_pss_subarray_fqdns_all: list of all
            fsp pss subarray fqdns
        :param fsp_pst_subarray_fqdns_all: list of all
            fsp pst subarray fqdns
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
        self._fsp_pss_subarray_fqdns_all = fsp_pss_subarray_fqdns_all
        self._fsp_pst_subarray_fqdns_all = fsp_pst_subarray_fqdns_all

        self._hps_fsp_controller_fqdn = hps_fsp_controller_fqdn
        self._hps_fsp_corr_controller_fqdn = hps_fsp_corr_controller_fqdn

        self._group_fsp_corr_subarray = None
        self._group_fsp_pss_subarray = None
        self._group_fsp_pst_subarray = None
        self._proxy_hps_fsp_controller = None
        self._proxy_hps_fsp_corr_controller = None
        self._proxy_fsp_corr_subarray = None
        self._proxy_fsp_pss_subarray = None
        self._proxy_fsp_pst_subarray = None

        self._subarray_membership = []
        self._function_mode = FspModes.IDLE.value  # IDLE
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
    def function_mode(self: FspComponentManager) -> tango.DevEnum:
        """
        Function Mode

        :return: the Fsp function mode
        :rtype: tango.DevEnum
        """
        return self._function_mode

    @property
    def jones_matrix(self: FspComponentManager) -> str:
        """
        Jones Matrix

        :return: the jones matrix
        :rtype: str
        """
        return self._jones_matrix

    @property
    def delay_model(self: FspComponentManager) -> str:
        """
        Delay Model

        :return: the delay model
        :rtype: str
        """
        return self._delay_model

    @property
    def timing_beam_weights(self: FspComponentManager) -> str:
        """
        Timing Beam Weights

        :return: the timing beam weights
        :rtype: str
        """
        return self._timing_beam_weights

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

    def start_communicating(self: FspComponentManager,) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._get_group_proxies()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: FspComponentManager) -> None:
        """Stop communication with the component"""

        super().stop_communicating()

        self._connected = False

    def _get_device_proxy(
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
            self._logger.info(f"Attempting connection to {fqdn_or_name} ")
            if is_group:
                device_proxy = CbfGroupProxy(
                    name=fqdn_or_name, logger=self._logger
                )
            else:
                device_proxy = CbfDeviceProxy(
                    fqdn=fqdn_or_name, logger=self._logger, connect=False
                )
                device_proxy.connect(
                    max_time=0
                )  # Make one attempt at connecting
            return device_proxy
        except tango.DevFailed as df:
            for item in df.args:
                self._logger.error(
                    f"Failed connection to {fqdn_or_name} : {item.reason}"
                )
            self.update_component_fault(True)
            return None

    def _get_capability_proxies(self: FspComponentManager,) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

        if not self._simulation_mode:
            self._logger.info("Trying to connected to REAL HPS devices")
            if self._proxy_hps_fsp_controller is None:
                self._proxy_hps_fsp_controller = self._get_device_proxy(
                    self._hps_fsp_controller_fqdn, is_group=False
                )

            if self._proxy_hps_fsp_corr_controller is None:
                self._proxy_hps_fsp_corr_controller = self._get_device_proxy(
                    self._hps_fsp_corr_controller_fqdn, is_group=False
                )
        else:
            self._logger.info("Trying to connected to Simulated HPS devices")
            self._proxy_hps_fsp_corr_controller = HpsFspCorrControllerSimulator(
                self._hps_fsp_corr_controller_fqdn
            )
            self._proxy_hps_fsp_controller = HpsFspControllerSimulator(
                self._hps_fsp_controller_fqdn,
                self._proxy_hps_fsp_corr_controller,
            )

        if self._proxy_fsp_corr_subarray is None:
            self._proxy_fsp_corr_subarray = [
                self._get_device_proxy(fqdn, is_group=False)
                for fqdn in self._fsp_corr_subarray_fqdns_all
            ]

        if self._proxy_fsp_pss_subarray is None:
            self._proxy_fsp_pss_subarray = [
                self._get_device_proxy(fqdn, is_group=False)
                for fqdn in self._fsp_pss_subarray_fqdns_all
            ]

        if self._proxy_fsp_pst_subarray is None:
            self._proxy_fsp_pst_subarray = [
                self._get_device_proxy(fqdn, is_group=False)
                for fqdn in self._fsp_pst_subarray_fqdns_all
            ]

    def _get_group_proxies(self: FspComponentManager,) -> None:
        """Establish connections with the group proxies"""
        if self._group_fsp_corr_subarray is None:
            self._group_fsp_corr_subarray = self._get_device_proxy(
                "FSP Subarray Corr", is_group=True
            )
            for fqdn in list(self._fsp_corr_subarray_fqdns_all):
                self._group_fsp_corr_subarray.add(fqdn)
        if self._group_fsp_pss_subarray is None:
            self._group_fsp_pss_subarray = self._get_device_proxy(
                "FSP Subarray Pss", is_group=True
            )
            for fqdn in list(self._fsp_pss_subarray_fqdns_all):
                self._group_fsp_pss_subarray.add(fqdn)
        if self._group_fsp_pst_subarray is None:
            self._group_fsp_pst_subarray = self._get_device_proxy(
                "FSP Subarray Pst", is_group=True
            )
            for fqdn in list(self._fsp_pst_subarray_fqdns_all):
                self._group_fsp_pst_subarray.add(fqdn)

    @check_communicating
    def remove_subarray_membership(
        self: FspComponentManager, argin: int
    ) -> Tuple[ResultCode, str]:
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing
        (no subarray is using this FSP), set function mode to empty.

        :param argin: an integer representing the subarray affiliation
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        result_code = ResultCode.OK
        message = "Fsp RemoveSubarrayMembership command completed OK"
        if argin in self._subarray_membership:
            self._subarray_membership.remove(argin)
            self._push_change_event(
                "subarrayMembership", self._subarray_membership
            )
            # change function mode to IDLE if no subarrays are using it.
            if len(self._subarray_membership) == 0:
                # TODO implement VLBI
                if self._function_mode == FspModes.CORR.value:
                    self._group_fsp_corr_subarray.command_inout("GoToIdle")
                if self._function_mode == FspModes.PSS_BF.value:
                    self._group_fsp_pss_subarray.command_inout("GoToIdle")
                if self._function_mode == FspModes.PST_BF.value:
                    self._group_fsp_pst_subarray.command_inout("GoToIdle")
                self._function_mode = FspModes.IDLE.value
                self._push_change_event("functionMode", self._function_mode)
        else:
            result_code = ResultCode.FAILED
            message = f"Fsp RemoveSubarrayMembership command failed; FSP does not belong to subarray {argin}."

        return (result_code, message)

    @check_communicating
    def add_subarray_membership(
        self: FspComponentManager, argin: int
    ) -> Tuple[ResultCode, str]:
        """
        Add a subarray to the subarrayMembership list.

        :param argin: an integer representing the subarray affiliation
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
        elif argin not in self._subarray_membership:
            self._subarray_membership.append(argin)
            self._push_change_event(
                "subarrayMembership", self._subarray_membership
            )
        else:
            result_code = ResultCode.FAILED
            message = f"Fsp AddSubarrayMembership command failed; FSP already belongs to subarray {argin}."

        return (result_code, message)

    @check_communicating
    def on(self: FspComponentManager,) -> Tuple[ResultCode, str]:
        """
        Turn on the fsp and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:
            self._logger.info(f"Value of _connected: {self._connected}")

            self._get_capability_proxies()

            # TODO: in the future, DsFspController to implement on(), off()
            # commands. Then invoke here the DsFspController on() command.

            self._group_fsp_corr_subarray.command_inout("On")
            self._group_fsp_pss_subarray.command_inout("On")
            self._group_fsp_pst_subarray.command_inout("On")

            message = "Fsp On command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp On command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def off(self: FspComponentManager,) -> Tuple[ResultCode, str]:
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

            self._group_fsp_corr_subarray.command_inout("Off")
            self._group_fsp_pss_subarray.command_inout("Off")
            self._group_fsp_pst_subarray.command_inout("Off")

            for subarray_ID in self._subarray_membership[:]:
                self.remove_subarray_membership(subarray_ID)

            message = "Fsp Off command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp Off command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def standby(self: FspComponentManager,) -> Tuple[ResultCode, str]:
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
        self: FspComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Put the fsp into low power standby mode

        :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:
            function_mode = FspModes.IDLE.value
            if argin == "IDLE":
                pass
            elif argin == "CORR":
                function_mode = FspModes.CORR.value
            elif argin == "PSS-BF":
                function_mode = FspModes.PSS_BF.value
            elif argin == "PST-BF":
                function_mode = FspModes.PST_BF.value
            elif argin == "VLBI":
                function_mode = FspModes.VLBI.value
            else:
                # shouldn't happen
                self._logger.warning("functionMode not valid. Ignoring.")
                message = "Fsp SetFunctionMode command failed: \
                    functionMode not valid"
                return (ResultCode.FAILED, message)

            try:
                self._proxy_hps_fsp_controller.SetFunctionMode(function_mode)
            except Exception as e:
                self._logger.error(str(e))

            self._function_mode = function_mode
            self._push_change_event("functionMode", self._function_mode)
            self._logger.info(f"FSP set to function mode {argin}")

            message = "Fsp SetFunctionMode command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp SetFunctionMode command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def update_jones_matrix(
        self: FspComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Update the FSP's jones matrix (serialized JSON object)

        :param argin: the jones matrix data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug("Entering update_jones_matrix")

        if self._connected:
            # update if current function mode is either PSS-BF, PST-BF or VLBI
            if self._function_mode in [
                FspModes.PSS_BF.value,
                FspModes.PST_BF.value,
                FspModes.VLBI.value,
            ]:
                # the whole jones matrix object must be stored
                self._jones_matrix = copy.deepcopy(argin)
                jones_matrix = json.loads(argin)
                # only send integer receptorID to HPS
                for matrix in jones_matrix["jones_matrix"]:
                    matrix["receptor"] = matrix["receptor"][1]
                # TODO HPS jones matrix handling currently unimplemented

            else:
                log_msg = (
                    "Fsp UpdateJonesMatrix command failed: "
                    f"matrix not used in function mode {self._function_mode}"
                )
                self._logger.warning(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "Fsp UpdateJonesMatrix command completed OK"
            return (ResultCode.OK, message)
        else:
            log_msg = "Fsp UpdateJonesMatrix command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
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
        self._logger.debug("Entering update_delay_model")

        if self._connected:
            # update if current function mode is either PSS-BF, PST-BF or CORR
            if self._function_mode in [
                FspModes.PSS_BF.value,
                FspModes.PST_BF.value,
                FspModes.CORR.value,
            ]:
                # the whole delay model must be stored
                self._delay_model = copy.deepcopy(argin)
                delay_model = json.loads(argin)
                # only send integer receptorID to HPS
                for delay_detail in delay_model["delay_details"]:
                    delay_detail["receptor"] = delay_detail["receptor"][1]
                # TODO handle delay models in function modes other than CORR
                self._proxy_hps_fsp_corr_controller.UpdateDelayModels(
                    json.dumps(delay_model)
                )

            else:
                log_msg = (
                    "Fsp UpdateDelayModel command failed: "
                    f"model not used in function mode {self._function_mode}"
                )
                self._logger.warning(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "Fsp UpdateDelayModel command completed OK"
            return (ResultCode.OK, message)
        else:
            log_msg = "Fsp UpdateDelayModel command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def update_timing_beam_weights(
        self: FspComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Update the FSP's timing beam weights (serialized JSON object)

        :param argin: the timing beam weight data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug("Entering update_timing_beam_weights")

        if self._connected:
            # update if current function mode is PST-BF
            if self._function_mode == FspModes.PST_BF.value:
                # the whole timing beam weights object must be stored
                self._timing_beam_weights = copy.deepcopy(argin)
                timing_beam_weights = json.loads(argin)
                # only send integer receptorID to HPS
                for weights in timing_beam_weights["timing_beam_weights"]:
                    weights["receptor"] = weights["receptor"][1]
                # TODO PST controller currently unimplemented
                # self._proxy_hps_fsp_pst_controller.UpdateTimingBeamWeights(
                #     json.dumps(timing_beam_weights)
                # )

            else:
                log_msg = (
                    "Fsp UpdateTimingBeamWeights command failed: "
                    f"weights not used in function mode {self._function_mode}"
                )
                self._logger.warning(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "Fsp UpdateTimingBeamWeights command completed OK"
            return (ResultCode.OK, message)
        else:
            log_msg = "Fsp UpdateTimingBeamWeights command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    @check_communicating
    def get_fsp_corr_config_id(self: FspComponentManager,) -> str:
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
            self._logger.error(log_msg)
            return ""
