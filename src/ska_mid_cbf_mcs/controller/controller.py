# -*- coding: utf-8 -*-
#
# This file is part of the CbfController project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# CbfController Tango device prototype
# CbfController TANGO device class for the CbfController prototype


# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(CbfController.additionnal_import) ENABLED START #
# add the path to import global_enum package.
import os
import sys
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))

from ska_tango_base import SKAMaster
from ska_tango_base.control_model import HealthState, AdminMode
from ska_tango_base.commands import ResultCode

# PROTECTED REGION END #    //  CbfController.additionnal_import

__all__ = ["CbfController", "main"]


class CbfController(SKAMaster):

    """
    CbfController TANGO device class.
    Primary point of contact for monitoring and control of Mid.CBF. Implements state and mode indicators, and a set of state transition commmands.
    """

    # PROTECTED REGION ID(CbfController.class_variable) ENABLED START #

    def __state_change_event_callback(self, event):

        if not event.err:
            try:
                device_name = event.device.dev_name()
                if "healthstate" in event.attr_name:
                    if "subarray" in device_name:
                        self._report_subarray_health_state[
                            self._fqdn_subarray.index(device_name)] = \
                            event.attr_value.value
                    elif "vcc" in device_name:
                        self._report_vcc_health_state[self._fqdn_vcc.index(device_name)] = \
                            event.attr_value.value
                    elif "fsp" in device_name:
                        self._report_fsp_health_state[self._fqdn_fsp.index(device_name)] = \
                            event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received health state change for unknown device " + \
                                  str(event.attr_name)
                        self.logger.warn(log_msg)
                        return
                elif "state" in event.attr_name:
                    if "subarray" in device_name:
                        self._report_subarray_state[self._fqdn_subarray.index(device_name)] = \
                            event.attr_value.value
                    elif "vcc" in device_name:
                        self._report_vcc_state[self._fqdn_vcc.index(device_name)] = \
                            event.attr_value.value
                    elif "fsp" in device_name:
                        self._report_fsp_state[self._fqdn_fsp.index(device_name)] = \
                            event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received state change for unknown device " + \
                                  str(event.attr_name)
                        self.logger.warn(log_msg)
                        return
                elif "adminmode" in event.attr_name:
                    if "subarray" in device_name:
                        self._report_subarray_admin_mode[self._fqdn_subarray.index(device_name)] = \
                            event.attr_value.value
                    elif "vcc" in device_name:
                        self._report_vcc_admin_mode[self._fqdn_vcc.index(device_name)] = \
                            event.attr_value.value
                    elif "fsp" in device_name:
                        self._report_fsp_admin_mode[self._fqdn_fsp.index(device_name)] = \
                            event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received admin mode change for unknown device " + \
                                  str(event.attr_name)
                        self.logger.warn(log_msg)
                        return

                log_msg = "New value for " + str(event.attr_name) + " is " + \
                          str(event.attr_value.value)
                self.logger.debug(log_msg)
            except Exception as except_occurred:
                self.logger.error(str(except_occurred))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def __membership_event_callback(self, event):
        if not event.err:
            try:
                device_name = event.device.dev_name()
                if "vcc" in device_name:
                    self._report_vcc_subarray_membership[self._fqdn_vcc.index(device_name)] = \
                        event.attr_value.value
                elif "fsp" in device_name:
                    if event.attr_value.value not in self._report_fsp_corr_subarray_membership[
                        self._fqdn_fsp.index(device_name)]:
                        logging.warning("{}".format(event.attr_value.value))
                        self._report_fsp_corr_subarray_membership[
                            self._fqdn_fsp.index(device_name)
                        ].append(event.attr_value.value)
                else:
                    # should NOT happen!
                    log_msg = "Received event for unknown device " + str(
                        event.attr_name)
                    self.logger.warn(log_msg)
                    return

                log_msg = "New value for " + str(event.attr_name) + " of device " + \
                          device_name + " is " + str(event.attr_value.value)
                self.logger.debug(log_msg)

            except Exception as except_occurred:
                self.logger.error(str(except_occurred))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    # def __config_ID_event_callback(self, event):
    #     if not event.err:
    #         try:
    #             self._subarray_config_ID[self._fqdn_subarray.index(event.device.dev_name())] = \
    #                 event.attr_value.value
    #         except Exception as except_occurred:
    #             self.logger.error(str(except_occurred))
    #     else:
    #         for item in event.errors:
    #             log_msg = item.reason + ": on attribute " + str(event.attr_name)
    #             self.logger.error(log_msg)

    def __get_num_capabilities(self):
        # self._max_capabilities inherited from SKAMaster
        # check first if property exists in DB
        """get number of capabilities for _init_Device. If property not found in db, then assign a default amount(197,27,16)"""
        if self._max_capabilities:
            try:
                self._count_vcc = self._max_capabilities["VCC"]
            except KeyError:  # not found in DB
                self._count_vcc = 197

            try:
                self._count_fsp = self._max_capabilities["FSP"]
            except KeyError:  # not found in DB
                self._count_fsp = 27

            try:
                self._count_subarray = self._max_capabilities["Subarray"]
            except KeyError:  # not found in DB
                self._count_subarray = 16
        else:
            self.logger.warn("MaxCapabilities device property not defined")

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

    reportFSPCorrSubarrayMembership = attribute(
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

    # def init_device(self):
    class InitCommand(SKAMaster.InitCommand):
        """initiate device and attributes"""
        def do(self):
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            device = self.target

            # SKAMaster.init_device(self)
            super().do()
            # device.set_state(tango.DevState.INIT)

            # defines device._count_vcc, device._count_fsp, and device._count_subarray
            device.__get_num_capabilities()

            device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            device._element_logging_level = tango.LogLevel.LOG_DEBUG
            device._central_logging_level = tango.LogLevel.LOG_DEBUG

            # initialize attribute values
            device._command_progress = 0
            device._report_vcc_state = [tango.DevState.UNKNOWN] * device._count_vcc
            device._report_vcc_health_state = [HealthState.UNKNOWN.value] * device._count_vcc
            device._report_vcc_admin_mode = [AdminMode.ONLINE.value] * device._count_vcc
            device._report_vcc_subarray_membership = [0] * device._count_vcc
            device._report_fsp_state = [tango.DevState.UNKNOWN] * device._count_fsp
            device._report_fsp_health_state = [HealthState.UNKNOWN.value] * device._count_fsp
            device._report_fsp_admin_mode = [AdminMode.ONLINE.value] * device._count_fsp
            device._report_fsp_corr_subarray_membership = [[] for i in range(device._count_fsp)]
            device._report_subarray_state = [tango.DevState.UNKNOWN] * device._count_subarray
            device._report_subarray_health_state = [HealthState.UNKNOWN.value] * device._count_subarray
            device._report_subarray_admin_mode = [AdminMode.ONLINE.value] * device._count_subarray
            device._frequency_offset_k = [0] * device._count_vcc
            device._frequency_offset_delta_f = [0] * device._count_vcc
            device._subarray_config_ID = [""] * device._count_subarray

            # initialize lists with subarray/capability FQDNs
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._fqdn_fsp = list(device.FSP)[:device._count_fsp]
            device._fqdn_subarray = list(device.CbfSubarray)[:device._count_subarray]

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
                vcc_proxy = tango.DeviceProxy(device._fqdn_vcc[i - 1])
                vcc_proxy.receptorID = receptorID
                del remaining[receptorIDIndex]

            # initialize the dict with subarray/capability proxies
            device._proxies = {}  # device_name:proxy

            # initialize the dict with the subscribed event IDs
            device._event_id = {}  # proxy:[eventID]

            # initialize groups
            device._group_vcc = tango.Group("VCC")
            for fqdn in device._fqdn_vcc:
                device._group_vcc.add(fqdn)
            device._group_fsp = tango.Group("FSP")
            for fqdn in device._fqdn_fsp:
                device._group_fsp.add(fqdn)
            device._group_subarray = tango.Group("CBF Subarray")
            for fqdn in device._fqdn_subarray:
                device._group_subarray.add(fqdn)

            # Try connection with each subarray/capability
            for fqdn in device._fqdn_vcc + device._fqdn_fsp + device._fqdn_subarray:
                try:
                    log_msg = "Trying connection to " + fqdn + " device"
                    device.logger.info(log_msg)
                    device_proxy = tango.DeviceProxy(fqdn)
                    device_proxy.ping()

                    device._proxies[fqdn] = device_proxy
                    events = []

                    # subscribe to change events on subarrays/capabilities
                    for attribute_val in ["adminMode", "healthState", "State"]:
                        events.append(
                            device_proxy.subscribe_event(
                                attribute_val, tango.EventType.CHANGE_EVENT,
                                device.__state_change_event_callback, stateless=True
                            )
                        )

                    # subscribe to VCC/FSP subarray membership change events
                    if "vcc" in fqdn or "fsp" in fqdn:
                        events.append(
                            device_proxy.subscribe_event(
                                "subarrayMembership", tango.EventType.CHANGE_EVENT,
                                device.__membership_event_callback, stateless=True
                            )
                        )

                    # subscribe to subarray config ID change events
                    # if "subarray" in fqdn:
                    #     events.append(
                    #         device_proxy.subscribe_event(
                    #             "configID", tango.EventType.CHANGE_EVENT,
                    #             device.__config_ID_event_callback, stateless=True
                    #         )
                    #     )

                    device._event_id[device_proxy] = events
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                        device.logger.error(log_msg)

            device.set_state(tango.DevState.STANDBY)

            message = "CbfController Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfController.always_executed_hook) ENABLED START #
        """hook to be executed before any command"""
        pass
        # PROTECTED REGION END #    //  CbfController.always_executed_hook

    def delete_device(self):
        """Unsubscribe to events, turn all the subarrays, VCCs and FSPs off""" 
        # PROTECTED REGION ID(CbfController.delete_device) ENABLED START #
        # unsubscribe to events
        for proxy in list(self._event_id.keys()):
            for event_id in self._event_id[proxy]:
                proxy.unsubscribe_event(event_id)

        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfController.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self):
        # PROTECTED REGION ID(CbfController.commandProgress_read) ENABLED START #
        """Return commandProgress attribute: percentage progress implemented for commands that result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)"""
        return self._command_progress
        # PROTECTED REGION END #    //  CbfController.commandProgress_read

    def read_receptorToVcc(self):
        # PROTECTED REGION ID(CbfController.receptorToVcc_read) ENABLED START #
        """Return 'receptorID:vccID'"""
        return self._receptor_to_vcc
        # PROTECTED REGION END #    //  CbfController.receptorToVcc_read

    def read_vccToReceptor(self):
        # PROTECTED REGION ID(CbfController.vccToReceptor_read) ENABLED START #
        """Return receptorToVcc attribute: 'vccID:receptorID'"""
        return self._vcc_to_receptor
        # PROTECTED REGION END #    //  CbfController.vccToReceptor_read

    def read_subarrayconfigID(self):
        # PROTECTED REGION ID(CbfController.subarrayconfigID_read) ENABLED START #
        """Return subarrayconfigID atrribute: ID of subarray config. USed for debug purposes. empty string if subarray is not configured for a scan"""
        return self._subarray_config_ID
        # PROTECTED REGION END #    //  CbfController.subarrayconfigID_read

    def read_reportVCCState(self):
        # PROTECTED REGION ID(CbfController.reportVCCState_read) ENABLED START #
        """Return reportVCCState attribute: the state of the VCC capabilities as an array of DevState"""
        return self._report_vcc_state
        # PROTECTED REGION END #    //  CbfController.reportVCCState_read

    def read_reportVCCHealthState(self):
        # PROTECTED REGION ID(CbfController.reportVCCHealthState_read) ENABLED START #
        """Return reportVCCHealthState attribute: health status of VCC capabilities as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]"""
        return self._report_vcc_health_state
        # PROTECTED REGION END #    //  CbfController.reportVCCHealthState_read

    def read_reportVCCAdminMode(self):
        # PROTECTED REGION ID(CbfController.reportVCCAdminMode_read) ENABLED START #
        """Return reportVCCAdminMode attribute: report the administration mode of the VCC capabilities as an array of unsigned short.\nFor ex.:\n[0,0,0,...1,2]"""
        return self._report_vcc_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportVCCAdminMode_read

    def read_reportVCCSubarrayMembership(self):
        """Return reportVCCSubarrayMembership attribute: report the subarray membership of VCCs (each can only belong to a single subarray), 0 if not assigned."""
        # PROTECTED REGION ID(CbfController.reportVCCSubarrayMembership_read) ENABLED START #
        return self._report_vcc_subarray_membership
        # PROTECTED REGION END #    //  CbfController.reportVCCSubarrayMembership_read

    def read_reportFSPState(self):
        # PROTECTED REGION ID(CbfController.reportFSPState_read) ENABLED START #
        """Return reportFSPState attribute: state of all the FSP capabilities in the form of array"""
        return self._report_fsp_state
        # PROTECTED REGION END #    //  CbfController.reportFSPState_read

    def read_reportFSPHealthState(self):
        # PROTECTED REGION ID(CbfController.reportFSPHealthState_read) ENABLED START #
        """Return reportFspHealthState attribute: Report the health status of the FSP capabilities"""
        return self._report_fsp_health_state
        # PROTECTED REGION END #    //  CbfController.reportFSPHealthState_read

    def read_reportFSPAdminMode(self):
        # PROTECTED REGION ID(CbfController.reportFSPAdminMode_read) ENABLED START #
        """Return reportFSPAdminMode attribute: Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]"""
        return self._report_fsp_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportFSPAdminMode_read

    def read_reportFSPCorrSubarrayMembership(self):
        # PROTECTED REGION ID(CbfController.reportFSPCorrSubarrayMembership_read) ENABLED START #
        """Return reportVCCSubarrayMembership attribute: Report the subarray membership of FSPs (each can only belong to at most 16 subarrays), 0 if not assigned."""
        return self._report_fsp_corr_subarray_membership
        # PROTECTED REGION END #    //  CbfController.reportFSPCorrSubarrayMembership_read

    def read_frequencyOffsetK(self):
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_read) ENABLED START #
        """Return frequencyOffsetK attribute: array of integers reporting receptors in subarray"""
        return self._frequency_offset_k
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_read

    def write_frequencyOffsetK(self, value):
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_write) ENABLED START #
        """Set frequencyOffsetK attribute"""
        if len(value) == self._count_vcc:
            self._frequency_offset_k = value
        else:
            log_msg = "Skipped writing to frequencyOffsetK attribute (expected {} arguments, " \
                      "but received {}.".format(self._count_vcc, len(value))
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_write

    def read_frequencyOffsetDeltaF(self):
        # PROTECTED REGION ID(CbfController.frequencyOffsetDeltaF_read) ENABLED START #
        """Return frequencyOffsetDeltaF attribute: Frequency offset (delta f) of all 197 receptors as an array of ints."""
        return self._frequency_offset_delta_f
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetDeltaF_read

    def write_frequencyOffsetDeltaF(self, value):
        # PROTECTED REGION ID(CbfController.frequencyOffsetDeltaF_write) ENABLED START #
        """Set the frequencyOffsetDeltaF attribute"""
        if len(value) == self._count_vcc:
            self._frequency_offset_delta_f = value
        else:
            log_msg = "Skipped writing to frequencyOffsetDeltaF attribute (expected {} arguments, " \
                      "but received {}.".format(self._count_vcc, len(value))
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetDeltaF_write

    def read_reportSubarrayState(self):
        # PROTECTED REGION ID(CbfController.reportSubarrayState_read) ENABLED START #
        """Return reportSubarrayState attribute: report the state of the Subarray with an array of DevState"""
        return self._report_subarray_state
        # PROTECTED REGION END #    //  CbfController.reportSubarrayState_read

    def read_reportSubarrayHealthState(self):
        # PROTECTED REGION ID(CbfController.reportSubarrayHealthState_read) ENABLED START #
        """Return reportSubarrayHealthState attribute: subarray healthstate in an array of unsigned short"""
        return self._report_subarray_health_state
        # PROTECTED REGION END #    //  CbfController.reportSubarrayHealthState_read

    def read_reportSubarrayAdminMode(self):
        # PROTECTED REGION ID(CbfController.reportSubarrayAdminMode_read) ENABLED START #
        """Return reportSubarrayAdminMode attribute: Report the administration mode of the Subarray as an array of unsigned short.\nfor ex:\n[0,0,2,..]"""
        return self._report_subarray_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportSubarrayAdminMode_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        """allowed if DevState is STANDBY"""
        if self.dev_state() == tango.DevState.STANDBY:
            return True
        return False

    @command()
    def On(self):
        """turn CbfController on, also turn on subarray, vcc, fsp"""
        # PROTECTED REGION ID(CbfController.On) ENABLED START #
        # 2020-07-14: don't turn Subarray on with ADR8 update
        self._group_subarray.command_inout("On")
        self._group_vcc.command_inout("On")
        self._group_fsp.command_inout("On")
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  CbfController.On

    def is_Off_allowed(self):
        """allowed if DevState is STANDBY"""
        if self.dev_state() == tango.DevState.STANDBY:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(CbfController.Off) ENABLED START #
        """turn off subarray, vcc, fsp, CbfController"""
        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfController.Off

    def is_Standby_allowed(self):
        """allowed if state is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def Standby(self):
        # PROTECTED REGION ID(CbfController.Standby) ENABLED START #
        """turn off subarray, vcc, fsp, turn CbfController to standby"""
        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")
        self.set_state(tango.DevState.STANDBY)
        # PROTECTED REGION END #    //  CbfController.Standby


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfController.main) ENABLED START #
    return run((CbfController,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfController.main


if __name__ == '__main__':
    main()
