# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
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

# Fsp Tango device prototype
# Fsp TANGO device class for the prototype

# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(Fsp.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from ska.base.control_model import ObsState
from ska.base import SKACapability
# PROTECTED REGION END #    //  Fsp.additionnal_import

__all__ = ["Fsp", "main"]


class Fsp(SKACapability):
    """
    Fsp TANGO device class for the prototype
    """
    # PROTECTED REGION ID(Fsp.class_variable) ENABLED START #

    def __get_capability_proxies(self):
        # for now, assume that given addresses are valid
        if self.CorrelationAddress:
            self._proxy_correlation = tango.DeviceProxy(self.CorrelationAddress)
        if self.PSSAddress:
            self._proxy_pss = tango.DeviceProxy(self.PSSAddress)
        if self.PSTAddress:
            self._proxy_pst = tango.DeviceProxy(self.PSTAddress)
        if self.VLBIAddress:
            self._proxy_vlbi = tango.DeviceProxy(self.VLBIAddress)
        if self.FspCorrSubarray:
            self._proxy_fsp_corr_subarray = [*map(
                tango.DeviceProxy,
                list(self.FspCorrSubarray)
            )]

    # PROTECTED REGION END #    //  Fsp.class_variable

    # -----------------
    # Device Properties
    # -----------------

    FspID = device_property(
        dtype='uint16'
    )

    CorrelationAddress = device_property(
        dtype='str'
    )

    PSSAddress = device_property(
        dtype='str'
    )

    PSTAddress = device_property(
        dtype='str'
    )

    VLBIAddress = device_property(
        dtype='str'
    )

    FspCorrSubarray = device_property(
        dtype=('str',)
    )
    FspPssSubarray = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    functionMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Function mode",
        doc="Function mode; an int in the range [0, 4]",
        enum_labels=["IDLE", "CORRELATION", "PSS", "PST", "VLBI", ],
    )

    subarrayMembership = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        access=AttrWriteType.READ,
        label="Subarray membership",
        doc="Subarray membership"
    )

    scanID = attribute(
        dtype='DevLong64',
        label="scanID",
        doc="scan ID, set when transition to SCANNING is performed",
    )

    configID = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Config ID",
        doc="set when transition to READY is performed",
    )

    # jonesMatrix = attribute(
    #     dtype=(double,),
    #     max_dim_x=16,
    #     access=AttrWriteType.READ,
    #     label='Jones Matrix',
    #     doc='Jones Matrix, given per frequency slice'
    # )
   
    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Fsp.init_device) ENABLED START #
        """Inherit from SKA Capability; Initialize attributes. Set state to OFF."""
        self.set_state(tango.DevState.INIT)

        # defines self._proxy_correlation, self._proxy_pss, self._proxy_pst, self._proxy_vlbi,
        # and self._proxy_fsp_corr_subarray
        self.__get_capability_proxies()

        # the modes are already disabled on initialization,
        # self._proxy_correlation.SetState(tango.DevState.DISABLE)
        # self._proxy_pss.SetState(tango.DevState.DISABLE)
        # self._proxy_pst.SetState(tango.DevState.DISABLE)
        # self._proxy_vlbi.SetState(tango.DevState.DISABLE)

        self._fsp_id = self.FspID

        # initialize attribute values
        self._function_mode = 0  # IDLE
        self._subarray_membership = []
        self._scan_id = 0
        self._config_id = ""
        #self._jones_matrix = [0.0 for i in range(16)]

        # initialize FSP subarray group
        self._group_fsp_corr_subarray = tango.Group("FSP Subarray Corr")
        for fqdn in list(self.FspCorrSubarray):
            self._group_fsp_corr_subarray.add(fqdn)

        self._group_fsp_pss_subarray = tango.Group("FSP Subarray Pss")
        for fqdn in list(self.FspPssSubarray):
            self._group_fsp_pss_subarray.add(fqdn)

        # 
        self._fsp_corr_proxies =[]
        for fqdn in list(self.FspCorrSubarray):
            self._fsp_corr_proxies.append(tango.DeviceProxy(fqdn))

       # self.state_model._obs_state = ObsState.IDLE.value
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(Fsp.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        pass
        # PROTECTED REGION END #    //  Fsp.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(Fsp.delete_device) ENABLED START #
        """Hook to delete device. Turn corr, pss, pst, vlbi, corr and pss subarray OFF. Remove membership; """
        self._proxy_correlation.SetState(tango.DevState.OFF)
        self._proxy_pss.SetState(tango.DevState.OFF)
        self._proxy_pst.SetState(tango.DevState.OFF)
        self._proxy_vlbi.SetState(tango.DevState.OFF)
        self._group_fsp_corr_subarray.command_inout("Off")
        self._group_fsp_pss_subarray.command_inout("Off")

        # remove all subarray membership
        for subarray_ID in self._subarray_membership[:]:
            self.RemoveSubarrayMembership(subarray_ID)

        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_functionMode(self):
        # PROTECTED REGION ID(Fsp.functionMode_read) ENABLED START #
        """Return functionMode attribute (DevEnum representing mode)."""
        return self._function_mode
        # PROTECTED REGION END #    //  Fsp.functionMode_read

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Fsp.subarrayMembership_read) ENABLED START #
        """Return subarrayMembership attribute (an array of affiliations of the FSP)."""
        return self._subarray_membership
        # PROTECTED REGION END #    //  Fsp.subarrayMembership_read

    def read_scanID(self):
        # PROTECTED REGION ID(FspCorrSubarray.scanID_read) ENABLED START #
        """Return the scanID attribute."""
        return self._scan_id
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_read

    def read_configID(self):
        # PROTECTED REGION ID(Fsp.configID_read) ENABLED START #
        """Return the configID attribute."""
        return self._config_id
        # PROTECTED REGION END #    //  Fsp.configID_read


    def write_configID(self, value):
        # PROTECTED REGION ID(Fsp.configID_write) ENABLED START #
        """Set the configID attribute."""
        self._config_id=value
        # PROTECTED REGION END #    //  Fsp.configID_write

    # def read_jonesMatrix(self):
    #     # PROTECTED REGION ID(Fsp.jonesMatrix_read) ENABLED START #
    #     """Return jonesMatrix attribute(max=16 array): Jones Matrix, given per frequency slice"""
    #     return self._jones_matrix
    #     # PROTECTED REGION END #    //  Fsp.jonesMatrix_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        """allowed if FSP state is OFF, ObsState is IDLE."""
        if self.dev_state() == tango.DevState.OFF:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(Fsp.On) ENABLED START #
        """Set corr, pss, pst, vlbi to 'DISABLE'. Set corr and pss subarray to 'On'. Set FSP device to 'On'."""
        self._proxy_correlation.SetState(tango.DevState.DISABLE)
        self._proxy_pss.SetState(tango.DevState.DISABLE)
        self._proxy_pst.SetState(tango.DevState.DISABLE)
        self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        self._group_fsp_corr_subarray.command_inout("On")
        self._group_fsp_pss_subarray.command_inout("On")

        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  Fsp.On

    def is_Off_allowed(self):
        """allowed if FSP state is ON, ObsState is IDLE"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(Fsp.Off) ENABLED START #
        """Send OFF signal to all the subordinates in the FSP'. Turn Off FSP device. Remove all Subarray membership. """
        self._proxy_correlation.SetState(tango.DevState.OFF)
        self._proxy_pss.SetState(tango.DevState.OFF)
        self._proxy_pst.SetState(tango.DevState.OFF)
        self._proxy_vlbi.SetState(tango.DevState.OFF)
        self._group_fsp_corr_subarray.command_inout("Off")
        self._group_fsp_pss_subarray.command_inout("Off")

        # remove all subarray membership
        for subarray_ID in self._subarray_membership[:]:
            self.RemoveSubarrayMembership(subarray_ID)

        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.Off

    def is_SetFunctionMode_allowed(self):
        """allowed if FSP state is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='Function mode'
    )
    def SetFunctionMode(self, argin):
        # PROTECTED REGION ID(Fsp.SetFunctionMode) ENABLED START #
        """argin should be one of ('IDLE','CORR','PSS-BF','PST-BF','VLBI'). 
        If IDLE set the pss, pst, corr, Vlbi to 'DISABLE'.
        OTherwise, turn one of them ON according to argin, and all others DISABLE.
        """
        if argin == "IDLE":
            self._function_mode = 0
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "CORR":
            self._function_mode = 1
            self._proxy_correlation.SetState(tango.DevState.ON)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "PSS-BF":
            self._function_mode = 2
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.ON)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "PST-BF":
            self._function_mode = 3
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.ON)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "VLBI":
            self._function_mode = 4
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.ON)

        # shouldn't happen
        self.logger.warn("functionMode not valid. Ignoring.")
        # PROTECTED REGION END #    //  Fsp.SetFunctionMode

    def is_AddSubarrayMembership_allowed(self):
        """allowed if the FSP state is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def AddSubarrayMembership(self, argin):
        # PROTECTED REGION ID(Fsp.AddSubarrayMembership) ENABLED START #
        """Input should be an integer representing the subarray affiliation. Add a subarray to the subarrayMembership list"""
        if argin not in self._subarray_membership:
            self._subarray_membership.append(argin)
        else:
            log_msg = "FSP already belongs to subarray {}.".format(argin)
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  Fsp.AddSubarrayMembership

    def is_RemoveSubarrayMembership_allowed(self):
        """allowed if FSP state is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def RemoveSubarrayMembership(self, argin):
        # PROTECTED REGION ID(Fsp.RemoveSubarrayMembership) ENABLED START #
        """Input should be an integer representing the subarray number. 
        If subarrayMembership is empty after removing (no subarray is using this FSP), set function mode to empty"""
        if argin in self._subarray_membership:
            self._subarray_membership.remove(argin)
            # change function mode to IDLE if no subarrays are using it.
            if not self._subarray_membership:
                self._function_mode = 0
        else:
            log_msg = "FSP does not belong to subarray {}.".format(argin)
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  Fsp.RemoveSubarrayMembership

    @command(
        dtype_out='DevString',
        doc_out="returns configID for all the fspCorrSubarray",
    )
    def getConfigID(self):
        # PROTECTED REGION ID(Fsp.getConfigID) ENABLED START #
        """
        returns configID for all the fspCorrSubarray
        """
        result ={}
        for proxy in self._fsp_corr_proxies:
            result[str(proxy)]=proxy.configID
        return str(result)
        # PROTECTED REGION END #    //  Fsp.getConfigID

    # def is_SetObservingState_allowed(self):
    #     """allowed if FSP is ON and ObsState is IDLE,CONFIGURING,READY, not SCANNING"""
    #     if self.dev_state() == tango.DevState.ON and \
    #             self.state_model._obs_state in [
    #         ObsState.IDLE.value,
    #         ObsState.CONFIGURING.value,
    #         ObsState.READY.value
    #     ]:
    #         return True
    #     return False

    # @command(
    #     dtype_in='uint16',
    #     doc_in="New obsState (CONFIGURING OR READY)"
    # )
    # def SetObservingState(self, argin):
    #     # PROTECTED REGION ID(Fsp.SetObservingState) ENABLED START #
    #     """Since obsState is read-only, CBF Subarray needs a way to change the obsState of an FSP, BUT ONLY TO CONFIGURING OR READY, during a scan configuration."""
    #     if argin in [ObsState.CONFIGURING.value, ObsState.READY.value]:
    #         self.state_model._obs_state = argin
    #     else:
    #         # shouldn't happen
    #         self.logger.warn("obsState must be CONFIGURING or READY. Ignoring.")
    #     # PROTECTED REGION END #    // Fsp.SetObservingState

    # def is_EndScan_allowed(self):
    #     """allowed when FSP is ON and ObsState is SCANNING"""
    #     if self.dev_state() == tango.DevState.ON and \
    #             self.state_model._obs_state == ObsState.SCANNING.value:
    #         return True
    #     return False

    # @command()
    # def EndScan(self):
    #     # PROTECTED REGION ID(Fsp.EndScan) ENABLED START #
    #     """End the scan: Set the obsState to READY. Set ScanID to 0"""
    #     self.state_model._obs_state = ObsState.READY.value
    #     self._scan_id = 0
    #     # nothing else is supposed to happen
    #     # PROTECTED REGION END #    //  Fsp.EndScan

    # def is_Scan_allowed(self):
    #     """scan is allowed when FSP is on, ObsState is READY"""
    #     if self.dev_state() == tango.DevState.ON and \
    #             self.state_model._obs_state == ObsState.READY.value:
    #         return True
    #     return False

    # @command(
    #     dtype_in='uint16',
    #     doc_in="Scan ID"
    # )
    # def Scan(self, argin):
    #     # PROTECTED REGION ID(Fsp.Scan) ENABLED START #
    #     """set FSP ObsState to SCANNING"""
    #     self.state_model._obs_state = ObsState.SCANNING.value
    #     # Set scanID
    #     try:
    #         self._scan_id=int(argin)
    #     except:
    #         msg="The input scanID is not integer."
    #         self.logger.error(msg)
    #         tango.Except.throw_exception("Command failed", msg, "FspCorrSubarray Scan execution",
    #                                      tango.ErrSeverity.ERR)
    #     # nothing else is supposed to happen
    #     # PROTECTED REGION END #    //  Fsp.Scan

    # def is_GoToIdle_allowed(self):
    #     """allowed if FSP is ON and obsState is IDLE or READY"""
    #     if self.dev_state() == tango.DevState.ON and \
    #             self.state_model._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
    #         return True
    #     return False

    # @command()
    # def GoToIdle(self):
    #     # PROTECTED REGION ID(Fsp.GoToIdle) ENABLED START #
    #     """Set OBsState IDLE for this FSP"""
    #     # transition to obsState=IDLE
    #     self.state_model._obs_state = ObsState.IDLE.value
    #     # PROTECTED REGION END #    //  Fsp.GoToIdle

    # def _void_callback(self, event):
    #     # This callback is only meant to be used to test if a subscription is valid
    #     if not event.err:
    #         pass
    #     else:
    #         for item in event.errors:
    #             log_msg = item.reason + ": on attribute " + str(event.attr_name)
    #             self.logger.error(log_msg)

    # def _jones_matrix_event_callback(self, event):
    #     if not event.err:
    #         if self.state_model._obs_state not in [ObsState.READY.value, ObsState.SCANNING.value]:
    #             log_msg = "Ignoring Jones matrix (obsState not correct)."
    #             self.logger.warn(log_msg)
    #             return
    #         try:
    #             log_msg = "Received Jones Matrix update."
    #             self.logger.warn(log_msg)

    #             value = str(event.attr_value.value)
    #             if value == self._last_received_jones_matrix:
    #                 log_msg = "Ignoring Jones matrix (identical to previous)."
    #                 self.logger.warn(log_msg)
    #                 return

    #             self._last_received_jones_matrix = value
    #             jones_matrix_all = json.loads(value)

    #             for jones_matrix in jones_matrix_all["jonesMatrix"]:
    #                 t = Thread(
    #                     target=self._update_jones_matrix,
    #                     args=(int(jones_matrix["epoch"]), json.dumps(jones_matrix["jonesDetails"]))
    #                 )
    #                 t.start()
    #         except Exception as e:
    #             self.logger.error(str(e))
    #     else:
    #         for item in event.errors:
    #             log_msg = item.reason + ": on attribute " + str(event.attr_name)
    #             self.logger.error(log_msg)

    # def _validate_jones_matrix(self, argin):
    #     #try to deserialize input string to a JSON object
    #     try:
    #         argin = json.loads(argin)
    #     except json.JSONDecodeError:
    #         msg = "Jones Matrix object is not a valid JSON object; aborting update."
    #         self._raise_jones_matrix_fatal_error(msg)    
    
    # def _raise_jones_matrix_fatal_error(self, msg):
    #     self.logger.error(msg)
    #     tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
    #                                  tango.ErrSeverity.ERR)

    # def is_UpdateJonesMatrix_allowed(self):
    #         """allowed when Devstate is ON and ObsState is READY OR SCANNINNG"""
    #         if self.dev_state() == tango.DevState.ON and \
    #                 self.state_model._obs_state in [ObsState.READY.value, ObsState.SCANNING.value]:
    #             return True
    #         return False

    # @command(
    #     dtype_in='str',
    #     doc_in="Jones Matrix, given per frequency slice"
    # )
    # def UpdateJonesMatrix(self, argin):
    #     # PROTECTED REGION ID(Fsp.UpdateJonesMatrix) ENABLED START #
    #     """update FSP's Jones matrix (serialized JSON object)"""
    #     argin = json.loads(argin)

    #     for frequency_slice in argin:
    #         if 1 <= frequency_slice["fsid"] <= 26:
    #                 if len(frequency_slice["matrix"]) == 16 or len(frequency_slice["matrix"]) == 4:  # Jones matrix will be 4x4 or 2x2 depending on mode of operation
    #                     self._jones_matrix = frequency_slice["matrix"]
    #                 else:
    #                     log_msg = "'matrix' not valid for frequency slice {}".format(frequency_slice["fsid"])
    #                     self.logger.error(log_msg)
    #         else:
    #             log_msg = "'fsid' {} not valid for frequency slice {}".format(fsid["fsid"], self._fsp_id)
    #             self.logger.error(log_msg)
    #     # PROTECTED REGION END #    // Fsp.UpdateJonesMatrix

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Fsp.main) ENABLED START #
    return run((Fsp,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Fsp.main

if __name__ == '__main__':
    main()
