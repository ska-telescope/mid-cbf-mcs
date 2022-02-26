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
from typing import Callable, Optional, Tuple, List

import logging
import tango
from enum import Enum
import json

from ska_mid_cbf_mcs.component.component_manager import (
    CommunicationStatus,
    CbfComponentManager,
)
from ska_tango_base.control_model import PowerMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.commons.global_enum import FspModes

MAX_SUBARRAY_MEMBERSHIPS = 16

class FspComponentManager(CbfComponentManager):
    """A component manager for the Fsp device."""

    def __init__(
        self: FspComponentManager,
        logger: logging.Logger,
        fsp_id: int,
        fsp_corr_subarray_fqdns_all: List[str],
        fsp_pss_subarray_fqdns_all: List[str],
        fsp_pst_subarray_fqdns_all: List[str],
        fsp_corr_subarray_address: str,
        fsp_pss_subarray_address: str,
        fsp_pst_subarray_address: str,
        vlbi_address: str,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
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
        :param fsp_corr_subarray_address: the address of the fsp corr subarray
        :param fsp_pss_subarray_address: the address of the fsp pss subarray
        :param fsp_pst_subarray_address: the address of the fsp pst subarray
        :param vlbi_address: the address of the vlbi
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
        
        self._connected = False

        self._fsp_id = fsp_id

        self._fsp_corr_subarray_fqdns_all = fsp_corr_subarray_fqdns_all
        self._fsp_pss_subarray_fqdns_all = fsp_pss_subarray_fqdns_all
        self._fsp_pst_subarray_fqdns_all = fsp_pst_subarray_fqdns_all
        self._fsp_corr_subarray_address = fsp_corr_subarray_address
        self._fsp_pss_subarray_address = fsp_pss_subarray_address
        self._fsp_pst_subarray_address = fsp_pst_subarray_address
        self._vlbi_address = vlbi_address

        self._group_fsp_corr_subarray = None
        self._group_fsp_pss_subarray = None
        self._group_fsp_pst_subarray = None
        self._proxy_correlation = None
        self._proxy_pss = None
        self._proxy_pst = None
        self._proxy_vlbi = None
        self._proxy_fsp_corr_subarray = None
        self._proxy_fsp_pss_subarray = None
        self._proxy_fsp_pst_subarray = None

        self._subarray_membership = []
        self._function_mode = FspModes.IDLE.value  # IDLE
        self._jones_matrix = [[0.0] * 16 for _ in range(4)]
        self._delay_model = [[0.0] * 6 for _ in range(4)]
        self._timing_beam_weights = [[0.0] * 6 for _ in range(4)]

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
    def jones_matrix(self: FspComponentManager) -> List[List[float]]:
        """
        Jones Matrix

        :return: the jones matrix
        :rtype: List[List[float]]
        """
        return self._jones_matrix
    
    @property
    def delay_model(self: FspComponentManager) -> List[List[float]]:
        """
        Delay Model

        :return: the delay model
        :rtype: List[List[float]]
        """
        return self._delay_model
    
    @property
    def timing_beam_weights(self: FspComponentManager) -> List[List[float]]:
        """
        Timing Beam Weights

        :return: the timing beam weights
        :rtype: List[List[float]]
        """
        return self._timing_beam_weights
    
    def start_communicating(
        self: FspComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._get_capability_proxies()
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
        self: FspComponentManager,
        fqdn_or_name: str,
        is_group: bool
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
                device_proxy = CbfGroupProxy(name=fqdn_or_name, logger=self._logger)
            else:
                device_proxy = CbfDeviceProxy(fqdn=fqdn_or_name, logger=self._logger, connect=False)
                device_proxy.connect(max_time=0) # Make one attempt at connecting
            return device_proxy
        except tango.DevFailed as df:
            for item in df.args:
                self._logger.error(f"Failed connection to {fqdn_or_name} : {item.reason}")
            self.update_component_fault(True)
            return None
    
    
    
    def _get_capability_proxies(
            self: FspComponentManager, 
    ) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

   
        if self._proxy_correlation is None:
            if self._fsp_corr_subarray_address:
                self._proxy_correlation = \
                    self._get_device_proxy(
                        self._fsp_corr_subarray_address, 
                        is_group=False)
                
            if self._proxy_pss is None:
                if self._fsp_pss_subarray_address:
                    self._proxy_pss = \
                        self._get_device_proxy(
                            self._fsp_pss_subarray_address, 
                            is_group=False)
                
            if self._proxy_pst is None:
                if self._fsp_pst_subarray_address:
                    self._proxy_pst = \
                        self._get_device_proxy(
                            self._fsp_pst_subarray_address, 
                            is_group=False)
                
            if self._proxy_vlbi is None:
                if self._vlbi_address:
                    self._proxy_vlbi = \
                        self._get_device_proxy(
                            self._vlbi_address, 
                            is_group=False)

            if self._proxy_fsp_corr_subarray is None:
                if self._fsp_corr_subarray_fqdns_all:
                    self._proxy_fsp_corr_subarray = \
                        [self._get_device_proxy(fqdn, is_group=False) \
                        for fqdn in self._fsp_corr_subarray_fqdns_all]

            if self._proxy_fsp_pss_subarray is None:
                if self._fsp_pss_subarray_fqdns_all:
                    self._proxy_fsp_pss_subarray = \
                        [self._get_device_proxy(fqdn, is_group=False) \
                        for fqdn in self._fsp_pss_subarray_fqdns_all]

            if self._proxy_fsp_pst_subarray is None:
                if self._fsp_pst_subarray_fqdns_all:
                    self._proxy_fsp_pst_subarray = \
                        [self._get_device_proxy(fqdn, is_group=False) \
                        for fqdn in self._fsp_pst_subarray_fqdns_all]
        
       
    def _get_group_proxies(
        self: FspComponentManager, 
    ) -> None:
        """Establish connections with the group proxies"""
        if self._group_fsp_corr_subarray is None:
            self._group_fsp_corr_subarray = \
                self._get_device_proxy("FSP Subarray Corr", is_group=True)
            for fqdn in list(self._fsp_corr_subarray_fqdns_all):
                self._group_fsp_corr_subarray.add(fqdn)
        if self._group_fsp_pss_subarray is None:
            self._group_fsp_pss_subarray = \
                self._get_device_proxy("FSP Subarray Pss", is_group=True)
            for fqdn in list(self._fsp_pss_subarray_fqdns_all):
                self._group_fsp_pss_subarray.add(fqdn)
        if self._group_fsp_pst_subarray is None:
            self._group_fsp_pst_subarray = \
                self._get_device_proxy("FSP Subarray Pst", is_group=True)
            for fqdn in list(self._fsp_pst_subarray_fqdns_all):
                self._group_fsp_pst_subarray.add(fqdn)
    
    def remove_subarray_membership(
        self: FspComponentManager,
        argin: int,
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
        if argin in self._subarray_membership:
            self._subarray_membership.remove(argin)
            # change function mode to IDLE if no subarrays are using it.
            if not self._subarray_membership:
                self._function_mode = FspModes.IDLE.value
        else:
            log_msg = "FSP does not belong to subarray {}.".format(argin)
            self._logger.warning(log_msg)
        
        message = "Fsp RemoveSubarrayMembership command completed OK"
        return (ResultCode.OK, message)
    
    def add_subarray_membership(
        self: FspComponentManager,
        argin: int,
        ) -> Tuple[ResultCode, str]:
        """
        Add a subarray to the subarrayMembership list.

        :param argin: an integer representing the subarray affiliation
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        if len(self._subarray_membership) == MAX_SUBARRAY_MEMBERSHIPS:
            log_msg = "Fsp already assigned to the \
                maximum number subarrays ({})".format(MAX_SUBARRAY_MEMBERSHIPS)
            self._logger.warning(log_msg)
            message = "Fsp AddSubarrayMembership command completed OK"
            return (ResultCode.OK, message)

        if argin not in self._subarray_membership:
            self._subarray_membership.append(argin)
        else:
            log_msg = "Fsp already belongs to subarray {}.".format(argin)
            self._logger.warning(log_msg)
        
        message = "Fsp AddSubarrayMembership command completed OK"
        return (ResultCode.OK, message)
    
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
            #TODO: VLBI device needs a component manager and power commands
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
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

            self._proxy_correlation.SetState(tango.DevState.OFF)
            self._proxy_pss.SetState(tango.DevState.OFF)
            self._proxy_pst.SetState(tango.DevState.OFF)
            self._proxy_vlbi.SetState(tango.DevState.OFF)
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
    
    def set_function_mode(      
        self: FspComponentManager,
        argin: str,
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

            if argin == "IDLE":
                self._function_mode = FspModes.IDLE.value
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "CORR":
                self._function_mode = FspModes.CORR.value
                self._proxy_correlation.SetState(tango.DevState.ON)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "PSS-BF":
                self._function_mode = FspModes.PSS_BF.value
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.ON)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "PST-BF":
                self._function_mode = FspModes.PST_BF.value
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.ON)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "VLBI":
                self._function_mode = FspModes.VLBI.value
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.ON)
            else:
                # shouldn't happen
                self._logger.warning("functionMode not valid. Ignoring.")
                message = "Fsp SetFunctionMode command failed: \
                    functionMode not valid"
                return (ResultCode.FAILED, message)

            message = "Fsp SetFunctionMode command completed OK"
            return (ResultCode.OK, message)
        
        else:
            log_msg = "Fsp SetFunctionMode command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    def update_jones_matrix(      
        self: FspComponentManager,
        argin: str,
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
            if self._function_mode in [
                FspModes.PSS_BF.value,
                FspModes.PST_BF.value,
                FspModes.VLBI.value
            ]:
                argin = json.loads(argin)

                for i in self._subarray_membership:
                    if self._function_mode == FspModes.PSS_BF.value:
                        proxy = self._proxy_fsp_pss_subarray[i - 1]
                        fs_length = 16
                    elif self._function_mode == FspModes.PST_BF.value:
                        proxy = self._proxy_fsp_pst_subarray[i - 1]
                        fs_length = 4
                    else:
                        fs_length = 4
                        # TODO: support for function mode VLBI
                        log_msg = "Fsp UpdateJonesMatrix command failed: \
                                function mode {} currently not supported".format(self._function_mode)
                        self._logger.error(log_msg)
                        return (ResultCode.FAILED, log_msg)

                    for receptor in argin:
                        rec_id = int(receptor["receptor"])
                        if rec_id in proxy.receptors:
                            for frequency_slice in receptor["receptorMatrix"]:
                                fs_id = frequency_slice["fsid"]
                                matrix = frequency_slice["matrix"]
                                if fs_id == self._fsp_id:
                                    if len(matrix) == fs_length:
                                        self._jones_matrix[rec_id - 1] = matrix.copy()
                                    else:
                                        log_msg = "Fsp UpdateJonesMatrix command error: \
                                        'matrix' not valid length for frequency slice {} of " \
                                                "receptor {}".format(fs_id, rec_id)
                                        self._logger.error(log_msg)
                                else:
                                    log_msg = "Fsp UpdateJonesMatrix command error: \
                                        'fsid' {} not valid for receptor {}".format(
                                        fs_id, rec_id
                                    )
                                    self._logger.error(log_msg)
            else:
                log_msg = "Fsp UpdateJonesMatrix command failed: \
                    matrix not used in function mode {}".format(self._function_mode)
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)

            message = "Fsp UpdateJonesMatrix command completed OK"
            return (ResultCode.OK, message)
        
        else:
            log_msg = "Fsp UpdateJonesMatrix command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)
    
    def update_delay_model(      
        self: FspComponentManager,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """
        Update the FSP's delay model (serialized JSON object)

        :param argin: the delay model data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:
            # update if current function mode is either PSS-BF or PST-BF
            if self._function_mode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                argin = json.loads(argin)
                for i in self._subarray_membership:
                    if self._function_mode == FspModes.PSS_BF.value:
                        proxy = self._proxy_fsp_pss_subarray[i - 1]
                    else:
                        proxy = self._proxy_fsp_pst_subarray[i - 1]
                    for receptor in argin:
                        rec_id = int(receptor["receptor"])
                        if rec_id in proxy.receptors:
                            for frequency_slice in receptor["receptorDelayDetails"]:
                                fs_id = frequency_slice["fsid"]
                                model = frequency_slice["delayCoeff"]
                                if fs_id == self._fsp_id:
                                    if len(model) == 6:
                                        self._delay_model[rec_id - 1] = model.copy()
                                    else:
                                        log_msg = "Fsp UpdateDelayModel command failed: \
                                            'model' not valid length for frequency slice {} of " \
                                                "receptor {}".format(fs_id, rec_id)
                                        self._logger.error(log_msg)
                                        return (ResultCode.FAILED, log_msg)
                                else:
                                    log_msg = "Fsp UpdateDelayModel command failed: \
                                        'fsid' {} not valid for receptor {}".format(
                                        fs_id, rec_id
                                    )
                                    self._logger.error(log_msg)
                                    return (ResultCode.FAILED, log_msg)

            else:
                log_msg = "Fsp UpdateDelayModel command failed: \
                    model not used in function mode {}".format(self._function_mode)
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)
            
            message = "Fsp UpdateDelayModel command completed OK"
            return (ResultCode.OK, message)
        
        else:
            log_msg = "Fsp UpdateDelayModel command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)
    
    def update_timing_beam_weights(      
        self: FspComponentManager,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """
        Update the FSP's timing beam weights (serialized JSON object)

        :param argin: the timing beam weight data:param argin: the timing beam weight data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:

            # update if current function mode is PST-BF
            if self._function_mode == FspModes.PST_BF.value:
                argin = json.loads(argin)
                for i in self._subarray_membership:
                    proxy = self._proxy_fsp_pst_subarray[i - 1]
                    for receptor in argin:
                        rec_id = int(receptor["receptor"])
                        if rec_id in proxy.receptors:
                            for frequency_slice in receptor["receptorWeightsDetails"]:
                                fs_id = frequency_slice["fsid"]
                                weights = frequency_slice["weights"]
                                if fs_id == self._fsp_id:
                                    if len(weights) == 6:
                                        self._timing_beam_weights[rec_id - 1] = weights.copy()
                                    else:
                                        log_msg = "Fsp UpdateDelayModel command failed: \
                                                'weights' not valid length for frequency slice {} of \
                                                receptor {}".format(fs_id, rec_id)
                                        self._logger.error(log_msg)
                                        return (ResultCode.FAILED, log_msg)
                                    
                                else:
                                    log_msg = "Fsp UpdateDelayModel command failed: \
                                            'fsid' {} not valid for receptor {}".format(
                                                fs_id, rec_id
                                            )
                                    self._logger.error(log_msg)
                                    return (ResultCode.FAILED, log_msg)
                                    
            else:
                log_msg = "Fsp UpdateDelayModel command failed: \
                    weights not used in function mode {}".format(self._function_mode)
                self._logger.error(log_msg)
                return (ResultCode.FAILED, log_msg)
                
            message = "Fsp UpdateDelayModel command completed OK"
            return (ResultCode.OK, message)
        
        else:
            log_msg = "Fsp UpdateDelayModel command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)
    
    def get_fsp_corr_config_id(      
        self: FspComponentManager,
    ) -> str:
        """
        Get the configID for all the fspCorrSubarray

        :return: the configID
        :rtype: str
        """

        if self._connected:
            result ={}
            for proxy in self._proxy_fsp_corr_subarray:
                result[str(proxy)]=proxy.configID
            return str(result)
        
        else:
            log_msg = "Fsp getConfigID command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return ""