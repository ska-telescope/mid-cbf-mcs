# -*- coding: utf-8 -*-
#
# This file is part of the CbfMaster project
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

# CbfMaster Tango device prototype
# CBFMaster TANGO device class for the CBFMaster prototype


# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(CbfMaster.additionnal_import) ENABLED START #
# add the path to import global_enum package.
import os
import sys
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from skabase.SKAMaster.SKAMaster import SKAMaster
from skabase.control_model import HealthState, AdminMode

# PROTECTED REGION END #    //  CbfMaster.additionnal_import

__all__ = ["CbfMaster", "main"]


class CbfMaster(SKAMaster):

    """
    CBFMaster TANGO device class.

    Primary point of contact for monitoring and control of Mid.CBF. Implements state and mode indicators, and a set of state transition commmands.
    """




    # PROTECTED REGION ID(CbfMaster.class_variable) ENABLED START #

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

    # PROTECTED REGION END #    //  CbfMaster.class_variable

    
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
        polling_period=3000,
        abs_change=1,
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

    def init_device(self):
        """initiate device and attributes"""
        SKAMaster.init_device(self)
        # PROTECTED REGION ID(CbfMaster.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # defines self._count_vcc, self._count_fsp, and self._count_subarray
        self.__get_num_capabilities()

        self._storage_logging_level = tango.LogLevel.LOG_DEBUG
        self._element_logging_level = tango.LogLevel.LOG_DEBUG
        self._central_logging_level = tango.LogLevel.LOG_DEBUG

        # initialize attribute values
        self._command_progress = 0
        self._report_vcc_state = [tango.DevState.UNKNOWN] * self._count_vcc
        self._report_vcc_health_state = [HealthState.UNKNOWN.value] * self._count_vcc
        self._report_vcc_admin_mode = [AdminMode.ONLINE.value] * self._count_vcc
        self._report_vcc_subarray_membership = [0] * self._count_vcc
        self._report_fsp_state = [tango.DevState.UNKNOWN] * self._count_fsp
        self._report_fsp_health_state = [HealthState.UNKNOWN.value] * self._count_fsp
        self._report_fsp_admin_mode = [AdminMode.ONLINE.value] * self._count_fsp
        self._report_fsp_corr_subarray_membership = [[] for i in range(self._count_fsp)]
        self._report_subarray_state = [tango.DevState.UNKNOWN] * self._count_subarray
        self._report_subarray_health_state = [HealthState.UNKNOWN.value] * self._count_subarray
        self._report_subarray_admin_mode = [AdminMode.ONLINE.value] * self._count_subarray
        self._frequency_offset_k = [0] * self._count_vcc
        self._frequency_offset_delta_f = [0] * self._count_vcc
        self._subarray_config_ID = [0] * self._count_subarray

        # initialize lists with subarray/capability FQDNs
        self._fqdn_vcc = list(self.VCC)[:self._count_vcc]
        self._fqdn_fsp = list(self.FSP)[:self._count_fsp]
        self._fqdn_subarray = list(self.CbfSubarray)[:self._count_subarray]

        # initialize dicts with maps receptorID <=> vccID (randomly for now, for testing purposes)
        # maps receptor IDs to VCC IDs, in the form "receptorID:vccID"
        self._receptor_to_vcc = []
        # maps VCC IDs to receptor IDs, in the form "vccID:receptorID"
        self._vcc_to_receptor = []

        remaining = list(range(1, self._count_vcc + 1))
        for i in range(1, self._count_vcc + 1):
            receptorIDIndex = randint(0, len(remaining) - 1)
            receptorID = remaining[receptorIDIndex]
            self._receptor_to_vcc.append("{}:{}".format(receptorID, i))
            self._vcc_to_receptor.append("{}:{}".format(i, receptorID))
            vcc_proxy = tango.DeviceProxy(self._fqdn_vcc[i - 1])
            vcc_proxy.receptorID = receptorID
            del remaining[receptorIDIndex]

        # initialize the dict with subarray/capability proxies
        self._proxies = {}  # device_name:proxy

        # initialize the dict with the subscribed event IDs
        self._event_id = {}  # proxy:[eventID]

        # initialize groups
        self._group_vcc = tango.Group("VCC")
        for fqdn in self._fqdn_vcc:
            self._group_vcc.add(fqdn)
        self._group_fsp = tango.Group("FSP")
        for fqdn in self._fqdn_fsp:
            self._group_fsp.add(fqdn)
        self._group_subarray = tango.Group("CBF Subarray")
        for fqdn in self._fqdn_subarray:
            self._group_subarray.add(fqdn)

        # Try connection with each subarray/capability
        for fqdn in self._fqdn_vcc + self._fqdn_fsp + self._fqdn_subarray:
            try:
                log_msg = "Trying connection to " + fqdn + " device"
                self.logger.info(log_msg)
                device_proxy = tango.DeviceProxy(fqdn)
                device_proxy.ping()

                self._proxies[fqdn] = device_proxy
                events = []

                # subscribe to change events on subarrays/capabilities
                for attribute_val in ["adminMode", "healthState", "State"]:
                    events.append(
                        device_proxy.subscribe_event(
                            attribute_val, tango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback, stateless=True
                        )
                    )

                # subscribe to VCC/FSP subarray membership change events
                if "vcc" in fqdn or "fsp" in fqdn:
                    events.append(
                        device_proxy.subscribe_event(
                            "subarrayMembership", tango.EventType.CHANGE_EVENT,
                            self.__membership_event_callback, stateless=True
                        )
                    )

                # subscribe to subarray config ID change events
                # if "subarray" in fqdn:
                #     events.append(
                #         device_proxy.subscribe_event(
                #             "configID", tango.EventType.CHANGE_EVENT,
                #             self.__config_ID_event_callback, stateless=True
                #         )
                #     )

                self._event_id[device_proxy] = events
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                    self.logger.error(log_msg)

        self.set_state(tango.DevState.STANDBY)
        # PROTECTED REGION END #    //  CbfMaster.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfMaster.always_executed_hook) ENABLED START #
        """hook to be executed before any command"""
        pass
        # PROTECTED REGION END #    //  CbfMaster.always_executed_hook

    def delete_device(self):
        """Unsubscribe to sevens, turn all the subarrays, VCCs and FSPs off""" 
        # PROTECTED REGION ID(CbfMaster.delete_device) ENABLED START #
        # unsubscribe to events
        for proxy in list(self._event_id.keys()):
            for event_id in self._event_id[proxy]:
                proxy.unsubscribe_event(event_id)

        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfMaster.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self):
        # PROTECTED REGION ID(CbfMaster.commandProgress_read) ENABLED START #
        """Return commandProgress attribute: percentage progress implemented for commands that result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)"""
        return self._command_progress
        # PROTECTED REGION END #    //  CbfMaster.commandProgress_read

    def read_receptorToVcc(self):
        # PROTECTED REGION ID(CbfMaster.receptorToVcc_read) ENABLED START #
        """Return 'receptorID:vccID'"""
        return self._receptor_to_vcc
        # PROTECTED REGION END #    //  CbfMaster.receptorToVcc_read

    def read_vccToReceptor(self):
        # PROTECTED REGION ID(CbfMaster.vccToReceptor_read) ENABLED START #
        """Return receptorToVcc attribute: 'vccID:receptorID'"""
        return self._vcc_to_receptor
        # PROTECTED REGION END #    //  CbfMaster.vccToReceptor_read

    def read_subarrayconfigID(self):
        # PROTECTED REGION ID(CbfMaster.subarrayconfigID_read) ENABLED START #
        """Return subarrayconfigID atrribute: ID of subarray config. USed for debug purposes. empty string if subarray is not configured for a scan"""
        return self._subarray_config_ID
        # PROTECTED REGION END #    //  CbfMaster.subarrayconfigID_read

    def read_reportVCCState(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCState_read) ENABLED START #
        """Return reportVCCState attribute: the state of the VCC capabilities as an array of DevState"""
        return self._report_vcc_state
        # PROTECTED REGION END #    //  CbfMaster.reportVCCState_read

    def read_reportVCCHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCHealthState_read) ENABLED START #
        """Return reportVCCHealthState attribute: health status of VCC capabilities as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]"""
        return self._report_vcc_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportVCCHealthState_read

    def read_reportVCCAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCAdminMode_read) ENABLED START #
        """Return reportVCCAdminMode attribute: report the administration mode of the VCC capabilities as an array of unsigned short.\nFor ex.:\n[0,0,0,...1,2]"""
        return self._report_vcc_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportVCCAdminMode_read

    def read_reportVCCSubarrayMembership(self):
        """Return reportVCCSubarrayMembership attribute: report the subarray membership of VCCs (each can only belong to a single subarray), 0 if not assigned."""
        # PROTECTED REGION ID(CbfMaster.reportVCCSubarrayMembership_read) ENABLED START #
        return self._report_vcc_subarray_membership
        # PROTECTED REGION END #    //  CbfMaster.reportVCCSubarrayMembership_read

    def read_reportFSPState(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPState_read) ENABLED START #
        """Return reportFSPState attribute: state of all the FSP capabilities in the form of array"""
        return self._report_fsp_state
        # PROTECTED REGION END #    //  CbfMaster.reportFSPState_read

    def read_reportFSPHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPHealthState_read) ENABLED START #
        """Return reportFspHealthState attribute: Report the health status of the FSP capabilities"""
        return self._report_fsp_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportFSPHealthState_read

    def read_reportFSPAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPAdminMode_read) ENABLED START #
        """Return reportFSPAdminMode attribute: Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]"""
        return self._report_fsp_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportFSPAdminMode_read

    def read_reportFSPCorrSubarrayMembership(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPCorrSubarrayMembership_read) ENABLED START #
        """Return reportVCCSubarrayMembership attribute: Report the subarray membership of FSPs (each can only belong to at most 16 subarrays), 0 if not assigned."""
        return self._report_fsp_corr_subarray_membership
        # PROTECTED REGION END #    //  CbfMaster.reportFSPCorrSubarrayMembership_read

    def read_frequencyOffsetK(self):
        # PROTECTED REGION ID(CbfMaster.frequencyOffsetK_read) ENABLED START #
        """Return frequencyOffsetK attribute: array of integers reporting receptors in subarray"""
        return self._frequency_offset_k
        # PROTECTED REGION END #    //  CbfMaster.frequencyOffsetK_read

    def write_frequencyOffsetK(self, value):
        # PROTECTED REGION ID(CbfMaster.frequencyOffsetK_write) ENABLED START #
        """Set frequencyOffsetK attribute"""
        if len(value) == self._count_vcc:
            self._frequency_offset_k = value
        else:
            log_msg = "Skipped writing to frequencyOffsetK attribute (expected {} arguments, " \
                      "but received {}.".format(self._count_vcc, len(value))
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  CbfMaster.frequencyOffsetK_write

    def read_frequencyOffsetDeltaF(self):
        # PROTECTED REGION ID(CbfMaster.frequencyOffsetDeltaF_read) ENABLED START #
        """Return frequencyOffsetDeltaF attribute: Frequency offset (delta f) of all 197 receptors as an array of ints."""
        return self._frequency_offset_delta_f
        # PROTECTED REGION END #    //  CbfMaster.frequencyOffsetDeltaF_read

    def write_frequencyOffsetDeltaF(self, value):
        # PROTECTED REGION ID(CbfMaster.frequencyOffsetDeltaF_write) ENABLED START #
        """Set the frequencyOffsetDeltaF attribute"""
        if len(value) == self._count_vcc:
            self._frequency_offset_delta_f = value
        else:
            log_msg = "Skipped writing to frequencyOffsetDeltaF attribute (expected {} arguments, " \
                      "but received {}.".format(self._count_vcc, len(value))
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  CbfMaster.frequencyOffsetDeltaF_write

    def read_reportSubarrayState(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayState_read) ENABLED START #
        """Return reportSubarrayState attribute: report the state of the Subarray with an array of DevState"""
        return self._report_subarray_state
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayState_read

    def read_reportSubarrayHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayHealthState_read) ENABLED START #
        """Return reportSubarrayHealthState attribute: subarray healthstate in an array of unsigned short"""
        return self._report_subarray_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayHealthState_read

    def read_reportSubarrayAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayAdminMode_read) ENABLED START #
        """Return reportSubarrayAdminMode attribute: Report the administration mode of the Subarray as an array of unsigned short.\nfor ex:\n[0,0,2,..]"""
        return self._report_subarray_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayAdminMode_read

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
        """turn CbfMaster on, also turn on subarray, vcc, fsp"""
        # PROTECTED REGION ID(CbfMaster.On) ENABLED START #
        self._group_subarray.command_inout("On")
        self._group_vcc.command_inout("On")
        self._group_fsp.command_inout("On")
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  CbfMaster.On

    def is_Off_allowed(self):
        """allowed if DevState is STANDBY"""
        if self.dev_state() == tango.DevState.STANDBY:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(CbfMaster.Off) ENABLED START #
        """turn off subarray, vcc, fsp, cbfmaster"""
        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfMaster.Off

    def is_Standby_allowed(self):
        """allowed if state is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def Standby(self):
        # PROTECTED REGION ID(CbfMaster.Standby) ENABLED START #
        """turn off subarray, vcc, fsp, turn cbfmaster to standby"""
        self._group_subarray.command_inout("Off")
        self._group_vcc.command_inout("Off")
        self._group_fsp.command_inout("Off")
        self.set_state(tango.DevState.STANDBY)
        # PROTECTED REGION END #    //  CbfMaster.Standby


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfMaster.main) ENABLED START #
    return run((CbfMaster,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfMaster.main


if __name__ == '__main__':
    main()
