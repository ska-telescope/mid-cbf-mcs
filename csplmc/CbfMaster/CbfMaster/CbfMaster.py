# -*- coding: utf-8 -*-
#
# This file is part of the CbfMaster project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CbfMaster Tango device prototype

CBFMaster TANGO device class for the CBFMaster prototype
"""

# PyTango imports
import PyTango
from PyTango import DebugIt
from PyTango.server import run
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command
from PyTango.server import device_property
from PyTango import AttrQuality, DispLevel, DevState
from PyTango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(CbfMaster.additionnal_import) ENABLED START #
# add the path to import global_enum package.
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from skabase.SKAMaster.SKAMaster import SKAMaster
from global_enum import HealthState, AdminMode
# PROTECTED REGION END #    //  CbfMaster.additionnal_import

__all__ = ["CbfMaster", "main"]


class CbfMaster(SKAMaster):
    """
    CBFMaster TANGO device class for the CBFMaster prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfMaster.class_variable) ENABLED START #

    def event_callback(self, event):
        # TODO: add admin mode
        if not event.err:
            try:
                device_name = event.device.dev_name()
                if event.attr_name == "State":
                    if "cbfSubarray" in device_name:
                        self._report_subarray_state[self._fqdn_subarray.index(device_name)] = event.attr_value.value
                    elif "vcc" in device_name:
                        self._report_vcc_state[self._fqdn_vcc.index(device_name)] = event.attr_value.value
                    elif "fsp" in device_name:
                        self._report_fsp_state[self._fqdn_fsp.index(device_name)] = event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received state change for unknown device " + str(event.attr_name)
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
                        return
                elif event.attr_name == "healthState":
                    if "cbfSubarray" in device_name:
                        self._report_subarray_health_state[self._fqdn_subarray.index(device_name)] = event.attr_value.value
                    elif "vcc" in device_name:
                        self._report_vcc_health_state[self._fqdn_vcc.index(device_name)] = event.attr_value.value
                    elif "fsp" in device_name:
                        self._report_fsp_health_state[self._fqdn_fsp.index(device_name)] = event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received health state change for unknown device " + str(event.attr_name)
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
                        return
                log_msg = "New value for " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)

                # update CBF global state
                self.__set_cbf_state()
            except Exception as except_occurred:
                self.dev_logging(str(except_occurred), PyTango.LogLevel.LOG_DEBUG)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

    def __set_cbf_state(self):
        self.__set_cbf_health_state()

        self.set_state(PyTango.DevState.DISABLE)

        # CBF transitions to ON if at least one receptor and subarray are operational
        vcc_working = False
        subarray_working = False

        for state in self._report_vcc_state:
            if state == PyTango.DevState.ON:
                vcc_working = True
                break

        if not vcc_working:
            return

        for state in self._report_subarray_state:
            if state == PyTango.DevState.ON:
                subarray_working = True
                break

        if not subarray_working:
            return

        self.set_state(PyTango.DevState.ON)

    def __set_cbf_health_state(self):
        # count the number of "OKs" in all subarrays/capabilities
        count_ok = 0
        for health_state in self._report_vcc_health_state + \
                self._report_fsp_health_state + \
                self._report_subarray_health_state:
            # set overall health state to unknown if at least one subarray/capability is unknown
            if health_state == HealthState.UNKNOWN.value:
                self._health_state = HealthState.UNKNOWN.value
                return
            elif health_state == HealthState.OK.value:
                count_ok += 1

        # change criteria later - this is an over-simplification
        # overall health state is OK if all subarrays/capabilities are OK
        if count_ok == self._count_vcc + self._count_fsp + self._count_subarray:
            self._health_state = HealthState.OK.value
        # overall health state is DEGRADED if not all, but at least one, subarray/capability is OK
        elif count_ok > 0:
            self._health_state = HealthState.DEGRADED.value
        # overall health state is FAILED if no subarray/capability is OK
        else:
            self._health_state = HealthState.FAILED.value

    # PROTECTED REGION END #    //  CbfMaster.class_variable

    # -----------------
    # Device Properties
    # -----------------









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
        doc="Percentage progress implemented for commands that  result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
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

    frequencyBandOffsetK = attribute(
        dtype=('int',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency band offset (k)",
        doc="Frequency band offset (k) of all 197 receptors as an array of ints.",
    )

    frequencyBandOffsetDeltaF = attribute(
        dtype=('int',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency band offset (delta f)",
        doc="Frequency band offset (delta f) of all 197 receptors as an array of ints.",
    )

    reportSubarrayState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
        label="FSP state",
        polling_period=3000,
        doc="Report the state of the FSP capabilities.",
    )

    reportSubarrayHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="FSP health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the FSP capabilities.",
    )

    reportSubarrayAdminMode = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKAMaster.init_device(self)
        # PROTECTED REGION ID(CbfMaster.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        # self._max_capabilities inherited from SKAMaster
        self._count_vcc = self._max_capabilities["VCC"]
        self._count_fsp = self._max_capabilities["FSP"]
        self._count_subarray = self._max_capabilities["Subarray"]

        # initialize attribute values
        self._command_progress = 0
        self._report_vcc_state = [PyTango.DevState.UNKNOWN for i in range(self._count_vcc)]
        self._report_vcc_health_state = [HealthState.UNKNOWN.value]*self._count_vcc
        self._report_vcc_admin_mode = [AdminMode.ONLINE.value]*self._count_vcc
        self._report_fsp_state = [PyTango.DevState.UNKNOWN for i in range(self._count_fsp)]
        self._report_fsp_health_state = [HealthState.UNKNOWN.value]*self._count_fsp
        self._report_fsp_admin_mode = [AdminMode.ONLINE.value]*self._count_fsp
        self._report_subarray_state = [PyTango.DevState.UNKNOWN for i in range(self._count_subarray)]
        self._report_subarray_health_state = [HealthState.UNKNOWN.value]*self._count_subarray
        self._report_subarray_admin_mode = [AdminMode.ONLINE.value]*self._count_subarray
        self._frequency_band_offset_k = [0]*self._count_vcc
        self._frequency_band_offset_delta_f = [0]*self._count_vcc

        # evaluate the CBF element global state
        self.__set_cbf_state()

        # initialize lists with subarray/capability FQDNs
        self._fqdn_vcc = ["mid_csp_cbf/vcc/" + str(i + 1).zfill(3) for i in range(self._count_vcc)]
        self._fqdn_fsp = ["mid_csp_cbf/fsp/" + str(i + 1).zfill(2) for i in range(self._count_fsp)]
        self._fqdn_subarray = ["mid_csp_cbf/cbfSubarray/" + str(i + 1).zfill(2) for i in range(self._count_subarray)]

        # groups to facilitate easy commands and attribute-reading/writing
        self._group_vcc = PyTango.Group("vcc")
        self._group_vcc.add("mid_csp_cbf/vcc/*")
        self._group_fsp = PyTango.Group("fsp")
        self._group_fsp.add("mid_csp_cbf/fsp/*")
        self._group_subarray = PyTango.Group("subarray")
        self._group_subarray.add("mid_csp_cbf/cbfSubarray/*")

        # initialize the dict with subarray/capability proxies
        self._proxies = {}

        # initialize the list with the subscribed event IDs
        self._event_id = []

        # Try connection with each subarray/capability
        for fqdn in self._fqdn_vcc + self._fqdn_fsp + self._fqdn_subarray:
            try:
                log_msg = "Trying connection to " + fqdn + " device"
                self.dev_logging(log_msg, int(PyTango.LogLevel.LOG_INFO))
                device_proxy = PyTango.DeviceProxy(fqdn)
                device_proxy.ping()

                self._proxies[fqdn] = device_proxy

                # set up attribute polling and change events on subarrays/capabilities
                for attribute in ["adminMode", "healthState", "State"]:
                    attribute_proxy = PyTango.AttributeProxy(fqdn + "/" + attribute)
                    attribute_proxy.poll(1000)  # polling period in milliseconds, may change later

                    attribute_info = attribute_proxy.get_config()
                    change_event_info = PyTango.ChangeEventInfo()
                    change_event_info.abs_change = "1"
                    attribute_info.events.ch_event = change_event_info
                    attribute_proxy.set_config(attribute_info)

                # Subscription of subarray/capability attributes: State and healthState
                event_id = device_proxy.subscribe_event("State", PyTango.EventType.CHANGE_EVENT,
                                                        self.event_callback, stateless=True)
                self._event_id.append(event_id)

                event_id = device_proxy.subscribe_event("healthState", PyTango.EventType.CHANGE_EVENT,
                                                        self.event_callback, stateless=True)
                self._event_id.append(event_id)
            except PyTango.DevFailed as df:
                for item in df.args:
                    log_msg = "Failure in connection to " + fqdn + " device: " + str(item.reason)
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

        # PROTECTED REGION END #    //  CbfMaster.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfMaster.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfMaster.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfMaster.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfMaster.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self):
        # PROTECTED REGION ID(CbfMaster.commandProgress_read) ENABLED START #
        return self._command_progress
        # PROTECTED REGION END #    //  CbfMaster.commandProgress_read

    def read_reportVCCState(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCState_read) ENABLED START #
        return self._report_vcc_state
        # PROTECTED REGION END #    //  CbfMaster.reportVCCState_read

    def read_reportVCCHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCHealthState_read) ENABLED START #
        return self._report_vcc_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportVCCHealthState_read

    def read_reportVCCAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCAdminMode_read) ENABLED START #
        return self._report_vcc_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportVCCAdminMode_read

    def read_reportFSPState(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPState_read) ENABLED START #
        return self._report_fsp_state
        # PROTECTED REGION END #    //  CbfMaster.reportFSPState_read

    def read_reportFSPHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPHealthState_read) ENABLED START #
        return self._report_fsp_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportFSPHealthState_read

    def read_reportFSPAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPAdminMode_read) ENABLED START #
        return self._report_fsp_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportFSPAdminMode_read

    def read_frequencyBandOffsetK(self):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetK_read) ENABLED START #
        return self._frequency_band_offset_k
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetK_read

    def write_frequencyBandOffsetK(self, value):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetK_write) ENABLED START #
        if len(value) == self._count_vcc:
            self._frequency_band_offset_k = value
        else:
            log_msg = "Skipped writing to frequencyBandOffsetK attribute (expected " + str(self._count_vcc) + \
                      " arguments, but received " + str(len(value)) + ". "
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetK_write

    def read_frequencyBandOffsetDeltaF(self):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetDeltaF_read) ENABLED START #
        return self._frequency_band_offset_delta_f
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetDeltaF_read

    def write_frequencyBandOffsetDeltaF(self, value):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetDeltaF_write) ENABLED START #
        if len(value) == self._count_vcc:
            self._frequency_band_offset_delta_f = value
        else:
            log_msg = "Skipped writing to frequencyBandOffsetDeltaF attribute (expected " + str(self._count_vcc) + \
                      " arguments, but received " + str(len(value)) + ". "
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetDeltaF_write

    def read_reportSubarrayState(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayState_read) ENABLED START #
        return self._report_subarray_state
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayState_read

    def read_reportSubarrayHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayHealthState_read) ENABLED START #
        return self._report_subarray_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayHealthState_read

    def read_reportSubarrayAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayAdminMode_read) ENABLED START #
        return self._report_subarray_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayAdminMode_read


    # --------
    # Commands
    # --------

    @command(
    dtype_in=('str',), 
    doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\nIf the array length is > 1, each array element specifies the FQDN of the\nCSP SubElement to switch ON.", 
    )
    @DebugIt()
    def On(self, argin):
        # PROTECTED REGION ID(CbfMaster.On) ENABLED START #
        # For now, simply send the "On" command to all constituent subarrays/capabilities
        """
        err_msg = []  # list of messages to log
        if len(argin) == 0:  # no input argument -> switch on all sub-elements
            device_list = self._fqdn_vcc + self._fqdn_fsp + self._fqdn_subarray
        else:
            device_list = argin

        # loop on capabilities/subarrays and issue the On command
        nerr = 0  # number of exception
        for device_name in device_list:
            try:
                # retrieve the proxy
                device_proxy = self._proxies[device_name]
                device_proxy.command_inout("On", [])
            except KeyError as error:
                err_msg.append("No proxy for device: " + str(error))
                nerr += 1
            except PyTango.DevFailed as df:
                err_msg.append("Command failure for device " + device_name + ": " + str(df.args[0].desc))
                nerr += 1
        # throw exception
        if nerr > 0:
            except_msg = ""
            for item in err_msg:
                except_msg += item + "\n"
                self.dev_logging(item, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", except_msg,
                                           "On command execution", PyTango.ErrSeverity.ERR)
        """
        # update global state
        self.__set_cbf_state()
        # PROTECTED REGION END #    //  CbfMaster.On

    @command(
    dtype_in=('str',), 
    doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\nIf the array length is > 1, each array element specifies the FQDN of the\nCSP SubElement to switch OFF.", 
    )
    @DebugIt()
    def Off(self, argin):
        # PROTECTED REGION ID(CbfMaster.Off) ENABLED START #
        # For now, simply send the "Off" command to all constituent subarrays/capabilities
        """
        err_msg = []  # list of messages to log
        if len(argin) == 0:  # no input argument -> switch on all sub-elements
            device_list = self._fqdn_vcc + self._fqdn_fsp + self._fqdn_subarray
        else:
            device_list = argin

        # loop on capabilities/subarrays and issue the On command
        nerr = 0  # number of exception
        for device_name in device_list:
            try:
                # retrieve the proxy
                device_proxy = self._proxies[device_name]
                device_proxy.command_inout("Off", [])
            except KeyError as error:
                err_msg.append("No proxy for device: " + str(error))
                nerr += 1
            except PyTango.DevFailed as df:
                err_msg.append("Command failure for device " + device_name + ": " + str(df.args[0].desc))
                nerr += 1
        # throw exception
        if nerr > 0:
            except_msg = ""
            for item in err_msg:
                except_msg += item + "\n"
                self.dev_logging(item, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", except_msg,
                                           "Off command execution", PyTango.ErrSeverity.ERR)
        """
        # update global state
        self.__set_cbf_state()
        # PROTECTED REGION END #    //  CbfMaster.Off

    @command(
    dtype_in=('str',), 
    doc_in="If the array length is 0, the command applies to the whole\nCSP Element.\nIf the array length is > 1, each array element specifies the FQDN of the\nCSP SubElement to put in STANDBY mode.", 
    )
    @DebugIt()
    def Standby(self, argin):
        # PROTECTED REGION ID(CbfMaster.Standby) ENABLED START #
        # For now, simply send the "Standby" command to all constituent subarrays/capabilities
        """
        err_msg = []  # list of messages to log
        if len(argin) == 0:  # no input argument -> switch on all sub-elements
            device_list = self._fqdn_vcc + self._fqdn_fsp + self._fqdn_subarray
        else:
            device_list = argin

        # loop on capabilities/subarrays and issue the On command
        nerr = 0  # number of exception
        for device_name in device_list:
            try:
                # retrieve the proxy
                device_proxy = self._proxies[device_name]
                device_proxy.command_inout("Standby", [])
            except KeyError as error:
                err_msg.append("No proxy for device: " + str(error))
                nerr += 1
            except PyTango.DevFailed as df:
                err_msg.append("Command failure for device " + device_name + ": " + str(df.args[0].desc))
                nerr += 1
        # throw exception
        if nerr > 0:
            except_msg = ""
            for item in err_msg:
                except_msg += item + "\n"
                self.dev_logging(item, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", except_msg,
                                           "Standby command execution", PyTango.ErrSeverity.ERR)
        """
        # update global state
        self.__set_cbf_state()
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
