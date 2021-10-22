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
CbfController
Sub-element controller device for Mid.CBf
"""

from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple
from random import randint

# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(CbfController.additionnal_import) ENABLED START #
# add the path to import global_enum package.

# SKA imports
from ska_tango_base import SKAMaster, SKABaseDevice
from ska_tango_base.control_model import HealthState, AdminMode
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy

# PROTECTED REGION END #    //  CbfController.additionnal_import

__all__ = ["CbfController", "main"]


class CbfController(SKAMaster):

    """
    CbfController TANGO device class.
    Primary point of contact for monitoring and control of Mid.CBF. Implements state and mode indicators, and a set of state transition commmands.
    """

    # PROTECTED REGION ID(CbfController.class_variable) ENABLED START #


    # PROTECTED REGION END #    //  CbfController.class_variable

    
    # -----------------
    # Device Properties
    # -----------------

    CbfSubarray = device_property(
       
        dtype=('str',)
    )

    VCC = device_property(
        
        dtype=('str',)
    )

    FSP = device_property(
        
        dtype=('str',)
    )

    TalonLRU = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    commandProgress = attribute(
        dtype='uint16',
        label="Command progress percentage",
        max_value=100,
        min_value=0,
        polling_period=3000,
        abs_change=5,
        rel_change=2,
        doc="Percentage progress implemented for commands that result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
    )

    receptorToVcc = attribute(
        dtype=('str',),
        max_dim_x=197,
        label="Receptor-VCC map",
        polling_period=3000,
        doc="Maps receptors IDs to VCC IDs, in the form \"receptorID:vccID\"",
    )

    vccToReceptor = attribute(
        dtype=('str',),
        max_dim_x=197,
        label="VCC-receptor map",
        polling_period=3000,
        doc="Maps VCC IDs to receptor IDs, in the form \"vccID:receptorID\"",
    )

    subarrayconfigID = attribute(
        dtype=('str',),
        max_dim_x=16,
        label="Subarray config IDs",
        polling_period=3000,
        doc="ID of subarray configuration. empty string if subarray is not configured for a scan."
    )

    reportVCCState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
        label="VCC state",
        polling_period=3000,
        doc="Report the state of the VCC capabilities as an array of DevState",
    )

    reportVCCHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of VCC capabilities as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    reportVCCAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the VCC capabilities as an array of unsigned short.\nFor ex.:\n[0,0,0,...1,2]",
    )

    reportVCCSubarrayMembership = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC subarray membership",
        # no polling period so it reads the true value and not the one in cache
        doc="Report the subarray membership of VCCs (each can only belong to a single subarray), 0 if not assigned."
    )

    reportFSPState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
        label="FSP state",
        polling_period=3000,
        doc="Report the state of the FSP capabilities.",
    )

    reportFSPHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the FSP capabilities.",
    )

    reportFSPAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    reportFSPSubarrayMembership = attribute(
        dtype=(('uint16',),),
        max_dim_x=16,
        max_dim_y=27,
        label="FSP subarray membership",
        polling_period=3000,
        abs_change=1,
        doc="Report the subarray membership of FSPs (each can only belong to at most 16 subarrays), 0 if not assigned."
    )

    frequencyOffsetK = attribute(
        dtype=('int',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency offset (k)",
        doc="Frequency offset (k) of all 197 receptors as an array of ints.",
    )

    frequencyOffsetDeltaF = attribute(
        dtype=('int',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency offset (delta f)",
        doc="Frequency offset (delta f) of all 197 receptors as an array of ints.",
    )

    reportSubarrayState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
        label="Subarray state",
        polling_period=3000,
        doc="Report the state of the Subarray",
    )

    reportSubarrayHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="Subarray health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the Subarray.",
    )

    reportSubarrayAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the Subarray as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: CbfController) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.state_model, self.logger)

        self.register_command_object(
            "On", self.OnCommand(*device_args)
        )

        self.register_command_object(
            "Off", self.OffCommand(*device_args)
        )

        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

    class InitCommand(SKAMaster.InitCommand):

        def __get_num_capabilities(
            self: CbfController.InitCommand, 
        ) -> None:
            # self._max_capabilities inherited from SKAMaster
            # check first if property exists in DB
            """Get number of capabilities for _init_Device. 
            If property not found in db, then assign a default amount(197,27,16)"""
            
            device = self.target
            
            if device._max_capabilities:
                try:
                    device._count_vcc = device._max_capabilities["VCC"]
                except KeyError:  # not found in DB
                    device._count_vcc = 197

                try:
                    device._count_fsp = device._max_capabilities["FSP"]
                except KeyError:  # not found in DB
                    device._count_fsp = 27

                try:
                    device._count_subarray = device._max_capabilities["Subarray"]
                except KeyError:  # not found in DB
                    device._count_subarray = 16
            else:
                self.logger.warn("MaxCapabilities device property not defined")

        def do(
            self: CbfController.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            super().do()

            device = self.target

            # defines self._count_vcc, self._count_fsp, and self._count_subarray
            self.__get_num_capabilities()

            device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            device._element_logging_level = tango.LogLevel.LOG_DEBUG
            device._central_logging_level = tango.LogLevel.LOG_DEBUG

            # initialize attribute values
            device._command_progress = 0

            device._report_vcc_state = [tango.DevState.UNKNOWN] * device._count_vcc
            device._report_vcc_health_state = [HealthState.UNKNOWN.value] * device._count_vcc
            device._report_vcc_admin_mode = [AdminMode.ONLINE.value] * device._count_vcc
            device._report_vcc_subarray_membership = [0] * device._count_vcc
            device._frequency_offset_k = [0] * device._count_vcc
            device._frequency_offset_delta_f = [0] * device._count_vcc

            device._report_fsp_state = [tango.DevState.UNKNOWN] * device._count_fsp
            device._report_fsp_health_state = [HealthState.UNKNOWN.value] * device._count_fsp
            device._report_fsp_admin_mode = [AdminMode.ONLINE.value] * device._count_fsp
            device._report_fsp_subarray_membership = [[] for i in range(device._count_fsp)]

            device._report_subarray_state = [tango.DevState.UNKNOWN] * device._count_subarray
            device._report_subarray_health_state = [HealthState.UNKNOWN.value] * device._count_subarray
            device._report_subarray_admin_mode = [AdminMode.ONLINE.value] * device._count_subarray
            device._subarray_config_ID = [""] * device._count_subarray

            device._report_talon_lru_state = [tango.DevState.UNKNOWN] * len(device.TalonLRU)
            device._report_talon_lru_health_state = [HealthState.UNKNOWN.value] * len(device.TalonLRU)
            device._report_talon_lru_admin_mode = [AdminMode.ONLINE.value] * len(device.TalonLRU)

            # initialize lists with subarray/capability FQDNs
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._fqdn_fsp = list(device.FSP)[:device._count_fsp]
            device._fqdn_subarray = list(device.CbfSubarray)[:device._count_subarray]
            device._fqdn_talon_lru = list(device.TalonLRU)

            # initialize dicts with maps receptorID <=> vccID (randomly for now, for testing purposes)
            # maps receptor IDs to VCC IDs, in the form "receptorID:vccID"
            device._receptor_to_vcc = []
            # maps VCC IDs to receptor IDs, in the form "vccID:receptorID"
            device._vcc_to_receptor = []

            remaining = list(range(1, device._count_vcc + 1))
            for i in range(1, device._count_vcc + 1):
                receptorIDIndex = randint(0, len(remaining) - 1)
                receptorID = remaining[receptorIDIndex]
                device._receptor_to_vcc.append("{}:{}".format(receptorID, i))
                device._vcc_to_receptor.append("{}:{}".format(i, receptorID))
                vcc_proxy = CbfDeviceProxy(
                    fqdn=device._fqdn_vcc[i - 1], 
                    logger=device.logger
                )
                vcc_proxy.receptorID = receptorID
                del remaining[receptorIDIndex]

            # initialize the dict with subarray/capability proxies
            device._proxies = {}  # device_name:proxy

            # initialize the dict with the subscribed event IDs
            device._event_id = {}  # proxy:[eventID]

            # initialize groups
            device._group_vcc = None
            device._group_fsp = None
            device._group_subarray = None

            message = "CbfController Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self: CbfController) -> None:
        # PROTECTED REGION ID(CbfController.always_executed_hook) ENABLED START #
        """hook to be executed before any command"""
        if self._group_vcc is None:
            self._group_vcc = CbfGroupProxy("VCC", logger=self.logger)
            self._group_vcc.add(self._fqdn_vcc)
        if self._group_fsp is None:
            self._group_fsp = CbfGroupProxy("FSP", logger=self.logger)
            self._group_fsp.add(self._fqdn_fsp)
        if self._group_subarray is None:
            self._group_subarray = CbfGroupProxy("CBF Subarray", logger=self.logger)
            self._group_subarray.add(self._fqdn_subarray)
        
        for fqdn in self._fqdn_vcc + self._fqdn_fsp + self._fqdn_talon_lru + self._fqdn_subarray :
            if fqdn not in self._proxies:
                try:
                    log_msg = "Trying connection to " + fqdn + " device"
                    self.logger.info(log_msg)
                    device_proxy = CbfDeviceProxy(
                        fqdn=fqdn, 
                        logger=self.logger
                    )
                    device_proxy.ping()

                    self._proxies[fqdn] = device_proxy
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                        self.logger.error(log_msg)
        # PROTECTED REGION END #    //  CbfController.always_executed_hook

    def delete_device(self: CbfController) -> None:
        """Unsubscribe to events, turn all the subarrays, VCCs and FSPs off""" 
        # PROTECTED REGION ID(CbfController.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfController.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self: CbfController) -> int:
        # PROTECTED REGION ID(CbfController.commandProgress_read) ENABLED START #
        """Return commandProgress attribute: percentage progress implemented for 
        commands that result in state/mode transitions for a large number of 
        components and/or are executed in stages (e.g power up, power down)"""
        return self._command_progress
        # PROTECTED REGION END #    //  CbfController.commandProgress_read

    def read_receptorToVcc(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.receptorToVcc_read) ENABLED START #
        """Return 'receptorID:vccID'"""
        return self._receptor_to_vcc
        # PROTECTED REGION END #    //  CbfController.receptorToVcc_read

    def read_vccToReceptor(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.vccToReceptor_read) ENABLED START #
        """Return receptorToVcc attribute: 'vccID:receptorID'"""
        return self._vcc_to_receptor
        # PROTECTED REGION END #    //  CbfController.vccToReceptor_read

    def read_subarrayconfigID(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.subarrayconfigID_read) ENABLED START #
        """Return subarrayconfigID atrribute: ID of subarray config. 
        Used for debug purposes. empty string if subarray is not configured for a scan"""
        return self._subarray_config_ID
        # PROTECTED REGION END #    //  CbfController.subarrayconfigID_read

    def read_reportVCCState(self: CbfController) -> List[tango.DevState]:
        # PROTECTED REGION ID(CbfController.reportVCCState_read) ENABLED START #
        """Return reportVCCState attribute: the state of the VCC capabilities as an array of DevState"""
        return self._report_vcc_state
        # PROTECTED REGION END #    //  CbfController.reportVCCState_read

    def read_reportVCCHealthState(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportVCCHealthState_read) ENABLED START #
        """Return reportVCCHealthState attribute: health status of VCC capabilities 
        as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]"""
        return self._report_vcc_health_state
        # PROTECTED REGION END #    //  CbfController.reportVCCHealthState_read

    def read_reportVCCAdminMode(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportVCCAdminMode_read) ENABLED START #
        """Return reportVCCAdminMode attribute: report the administration mode 
        of the VCC capabilities as an array of unsigned short.\nFor ex.:\n[0,0,0,...1,2]"""
        return self._report_vcc_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportVCCAdminMode_read

    def read_reportVCCSubarrayMembership(self: CbfController) -> List[int]:
        """Return reportVCCSubarrayMembership attribute: report the subarray membership of VCCs 
        (each can only belong to a single subarray), 0 if not assigned."""
        # PROTECTED REGION ID(CbfController.reportVCCSubarrayMembership_read) ENABLED START #
        return self._report_vcc_subarray_membership
        # PROTECTED REGION END #    //  CbfController.reportVCCSubarrayMembership_read

    def read_reportFSPState(self: CbfController) -> List[tango.DevState]:
        # PROTECTED REGION ID(CbfController.reportFSPState_read) ENABLED START #
        """Return reportFSPState attribute: state of all the FSP capabilities in the form of array"""
        return self._report_fsp_state
        # PROTECTED REGION END #    //  CbfController.reportFSPState_read

    def read_reportFSPHealthState(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportFSPHealthState_read) ENABLED START #
        """Return reportFspHealthState attribute: Report the health status of the FSP capabilities"""
        return self._report_fsp_health_state
        # PROTECTED REGION END #    //  CbfController.reportFSPHealthState_read

    def read_reportFSPAdminMode(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportFSPAdminMode_read) ENABLED START #
        """Return reportFSPAdminMode attribute: Report the administration mode 
        of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]"""
        return self._report_fsp_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportFSPAdminMode_read

    def read_reportFSPSubarrayMembership(self: CbfController) -> List[List[int]]:
        # PROTECTED REGION ID(CbfController.reportFSPSubarrayMembership_read) ENABLED START #
        """Return reportVCCSubarrayMembership attribute: Report the subarray membership 
        of FSPs (each can only belong to at most 16 subarrays), 0 if not assigned."""
        return self._report_fsp_subarray_membership
        # PROTECTED REGION END #    //  CbfController.reportFSPSubarrayMembership_read

    def read_frequencyOffsetK(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_read) ENABLED START #
        """Return frequencyOffsetK attribute: array of integers reporting receptors in subarray"""
        return self._frequency_offset_k
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_read

    def write_frequencyOffsetK(self: CbfController, value: List[int]) -> None:
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_write) ENABLED START #
        """Set frequencyOffsetK attribute"""
        if len(value) == self._count_vcc:
            self._frequency_offset_k = value
        else:
            log_msg = "Skipped writing to frequencyOffsetK attribute (expected {} arguments, " \
                      "but received {}.".format(self._count_vcc, len(value))
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_write

    def read_frequencyOffsetDeltaF(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.frequencyOffsetDeltaF_read) ENABLED START #
        """Return frequencyOffsetDeltaF attribute: Frequency offset (delta f) 
        of all 197 receptors as an array of ints."""
        return self._frequency_offset_delta_f
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetDeltaF_read

    def write_frequencyOffsetDeltaF(self: CbfController, value: List[int]) -> None:
        # PROTECTED REGION ID(CbfController.frequencyOffsetDeltaF_write) ENABLED START #
        """Set the frequencyOffsetDeltaF attribute"""
        if len(value) == self._count_vcc:
            self._frequency_offset_delta_f = value
        else:
            log_msg = "Skipped writing to frequencyOffsetDeltaF attribute (expected {} arguments, " \
                      "but received {}.".format(self._count_vcc, len(value))
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetDeltaF_write

    def read_reportSubarrayState(self: CbfController) -> List[tango.DevState]:
        # PROTECTED REGION ID(CbfController.reportSubarrayState_read) ENABLED START #
        """Return reportSubarrayState attribute: report the state of the Subarray with an array of DevState"""
        return self._report_subarray_state
        # PROTECTED REGION END #    //  CbfController.reportSubarrayState_read

    def read_reportSubarrayHealthState(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportSubarrayHealthState_read) ENABLED START #
        """Return reportSubarrayHealthState attribute: subarray healthstate in an array of unsigned short"""
        return self._report_subarray_health_state
        # PROTECTED REGION END #    //  CbfController.reportSubarrayHealthState_read

    def read_reportSubarrayAdminMode(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportSubarrayAdminMode_read) ENABLED START #
        """Return reportSubarrayAdminMode attribute: Report the administration mode 
        of the Subarray as an array of unsigned short.\nfor ex:\n[0,0,2,..]"""
        return self._report_subarray_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportSubarrayAdminMode_read

    # --------
    # Commands
    # --------

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the CbfController's On() command.
        """
    

        def __state_change_event_callback(
            self: CbfController.OnCommand, 
            fqdn,
            name,
            value,
            quality
        ) -> None:

            device = self.target

            if value is not None:
                try:
                    if "healthstate" in name:
                        if "subarray" in fqdn:
                            device._report_subarray_health_state[
                                device._fqdn_subarray.index(fqdn)
                            ] = value
                        elif "vcc" in fqdn:
                            device._report_vcc_health_state[
                                device._fqdn_vcc.index(fqdn)
                            ] = value
                        elif "fsp" in fqdn:
                            device._report_fsp_health_state[
                                device._fqdn_fsp.index(fqdn)
                            ] = value
                        elif "talon_lru" in fqdn:
                            device._report_talon_lru_health_state[
                                device._fqdn_talon_lru.index(fqdn)
                                ] = value
                        else:
                            # should NOT happen!
                            log_msg = "Received health state change for unknown device " + \
                                    str(name)
                            device.logger.warn(log_msg)
                            return
                    elif "state" in name:
                        if "subarray" in fqdn:
                            device._report_subarray_state[
                                device._fqdn_subarray.index(fqdn)
                            ] = value
                        elif "vcc" in fqdn:
                            device._report_vcc_state[
                                device._fqdn_vcc.index(fqdn)
                            ] = value
                        elif "fsp" in fqdn:
                            device._report_fsp_state[
                                device._fqdn_fsp.index(fqdn)
                            ] = value
                        elif "talon_lru" in fqdn:
                            device._report_talon_lru_state[
                                device._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            # should NOT happen!
                            log_msg = "Received state change for unknown device " + \
                                    str(name)
                            device.logger.warn(log_msg)
                            return
                    elif "adminmode" in name:
                        if "subarray" in fqdn:
                            device._report_subarray_admin_mode[
                                device._fqdn_subarray.index(fqdn)
                            ] = value
                        elif "vcc" in fqdn:
                            device._report_vcc_admin_mode[
                                device._fqdn_vcc.index(fqdn)
                            ] = value
                        elif "fsp" in fqdn:
                            device._report_fsp_admin_mode[
                                device._fqdn_fsp.index(fqdn)
                            ] = value
                        elif "talon_lru" in fqdn:
                            device._report_talon_lru_admin_mode[
                                device._fqdn_talon_lru.index(fqdn)
                            ] = value
                        else:
                            # should NOT happen!
                            log_msg = "Received admin mode change for unknown device " + \
                                    str(name)
                            self.logger.warn(log_msg)
                            return

                    log_msg = "New value for " + str(name) + " of device " + \
                        fqdn + ": " + str(value)
                    device.logger.info(log_msg)
                except Exception as except_occurred:
                    self.logger.error(str(except_occurred))
            else:
                self.logger.warn(
                    "None value for attribute " + str(name) + 
                    " of device " + fqdn
                )

        def __membership_event_callback(
            self: CbfController.OnCommand, 
            fqdn,
            name,
            value,
            quality
        ) -> None:

            device = self.target

            if value is not None:
                try:
                    if "vcc" in fqdn:
                        device._report_vcc_subarray_membership[
                            device._fqdn_vcc.index(fqdn)
                        ] = value
                    elif "fsp" in fqdn:
                        if value not in device._report_fsp_subarray_membership[
                            device._fqdn_fsp.index(fqdn)]:
                            device.logger.warning("{}".format(value))
                            device._report_fsp_subarray_membership[
                                device._fqdn_fsp.index(fqdn)
                            ].append(value)
                    else:
                        # should NOT happen!
                        log_msg = "Received event for unknown device " + str(name)
                        self.logger.warn(log_msg)
                        return

                    log_msg = "New value for " + str(name) + " of device " + \
                            fqdn + ": " + str(value)
                    self.logger.info(log_msg)

                except Exception as except_occurred:
                    self.logger.error(str(except_occurred))
            else:
                self.logger.warn(
                    "None value for attribute " + str(name) + 
                    " of device " + fqdn
                )

        
        def __config_ID_event_callback(
            self: CbfController.OnCommand, 
            fqdn,
            name,
            value,
            quality
        ) -> None:

            device = self.target

            if value is not None:
                try:
                    device._subarray_config_ID[
                        device._fqdn_subarray.index(fqdn)
                    ] = value
                    log_msg = "New value for " + str(name) + " of device " + \
                            fqdn + ": " + str(value)
                    self.logger.info(log_msg)
                except Exception as except_occurred:
                    self.logger.error(str(except_occurred))
            else:
                self.logger.warn(
                    "None value for attribute " + str(name) + 
                    " of device " + fqdn
                )

        def do(            
            self: CbfController.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message)=super().do()

            device = self.target

            # Try connection with each subarray/capability
            for fqdn, proxy in device._proxies.items():
                attribute_test = AdminMode(proxy.read_attribute("adminMode").value).name
                device.logger.warn(f"{attribute_test}")
                attribute_test = AdminMode(proxy.adminMode).name
                device.logger.warn(f"{attribute_test}")
                try:
                    events = []

                    # subscribe to change events on subarrays/capabilities
                    for attribute_val in ["adminMode", "healthState", "State"]:
                        events.append(
                            proxy.add_change_event_callback(
                                attribute_name=attribute_val,
                                callback=self.__state_change_event_callback,
                                stateless=True
                            )
                        )

                    # subscribe to VCC/FSP subarray membership change events
                    if "vcc" in fqdn or "fsp" in fqdn:
                        events.append(
                            proxy.add_change_event_callback(
                                attribute_name="subarrayMembership",
                                callback=self.__membership_event_callback,
                                stateless=True
                            )
                        )

                    #TODO: re-enable and fix if this is needed?
                    # subscribe to subarray config ID change events
                    if "subarray" in fqdn:
                        events.append(
                            proxy.add_change_event_callback(
                                attribute_name="configID",
                                callback=self.__config_ID_event_callback,
                                stateless=True
                            )
                        )

                    device._event_id[proxy] = events
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                        device.logger.error(log_msg)

            for talon_lru_fqdn in device._fqdn_talon_lru:
                device._proxies[talon_lru_fqdn].command_inout("On")

            device._group_subarray.command_inout("On")
            device._group_vcc.command_inout("On")
            device._group_fsp.command_inout("On")

            return (result_code,message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the CbfController's Off() command.
        """
        def do(
            self: CbfController.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message)=super().do()

            device = self.target

            for talon_lru_fqdn in device._fqdn_talon_lru:
                device._proxies[talon_lru_fqdn].Off()

            device._group_subarray.command_inout("Off")
            device._group_vcc.command_inout("Off")
            device._group_fsp.command_inout("Off")

            for proxy in list(device._event_id.keys()):
                for event_id in device._event_id[proxy]:
                    device.logger.info(
                        "Unsubscribing from event " + str(event_id) +
                        ", device: " + str(proxy._fqdn)
                    )
                    proxy.unsubscribe_event(event_id)

            return (result_code,message)


    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the CbfController's Standby() command.
        """
        def do(            
            self: CbfController.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.
            Turn off subarray, vcc, fsp, turn CbfController to standby

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message)=super().do()

            device = self.target

            device._group_subarray.command_inout("Off")
            device._group_vcc.command_inout("Off")
            device._group_fsp.command_inout("Off")

            return (result_code,message)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfController.main) ENABLED START #
    return run((CbfController,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfController.main


if __name__ == '__main__':
    main()