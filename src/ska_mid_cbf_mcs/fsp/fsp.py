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

from ska_tango_base import SKACapability
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
        if self.FspPssSubarray:
            self._proxy_fsp_pss_subarray = [*map(
                tango.DeviceProxy,
                list(self.FspPssSubarray)
            )]
        if self.FspPstSubarray:
            self._proxy_fsp_pst_subarray = [*map(
                tango.DeviceProxy,
                list(self.FspPstSubarray)
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

    FspPstSubarray = device_property(
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

    jonesMatrix = attribute(
        dtype=(('double',),),
        max_dim_x=4,
        max_dim_y=16,
        access=AttrWriteType.READ,
        label='Jones Matrix',
        doc='Jones Matrix, given per frequency slice'
    )

    delayModel = attribute(
        dtype = (('double',),),
        max_dim_x=6,
        max_dim_y=16,
        access=AttrWriteType.READ,
        label='Delay Model',
        doc='Differential off-boresight beam delay model'
    )

    timingBeamWeights = attribute(
        dtype = (('double',),),
        max_dim_x=6,
        max_dim_y=16,
        access=AttrWriteType.READ,
        label='Timing Beam Weights',
        doc='Amplitude weights used in the tied-array beamforming'
    )
   
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

        self._fsp_id = self.FspID

        # initialize attribute values
        self._function_mode = 0  # IDLE
        self._subarray_membership = []
        self._scan_id = 0
        self._config_id = ""
        self._jones_matrix = [[0.0] * 4 for _ in range(4)]
        self._delay_model = [[0.0] * 6 for _ in range(4)]
        self._timing_beam_weights = [[0.0] * 6 for _ in range(4)]

        # initialize FSP subarray group
        self._group_fsp_corr_subarray = tango.Group("FSP Subarray Corr")
        for fqdn in list(self.FspCorrSubarray):
            self._group_fsp_corr_subarray.add(fqdn)

        self._group_fsp_pss_subarray = tango.Group("FSP Subarray Pss")
        for fqdn in list(self.FspPssSubarray):
            self._group_fsp_pss_subarray.add(fqdn)

        self._group_fsp_pst_subarray = tango.Group("FSP Subarray Pst")
        for fqdn in list(self.FspPstSubarray):
            self._group_fsp_pst_subarray.add(fqdn)

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
        self._group_fsp_pst_subarray.command_inout("Off")

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

    def read_jonesMatrix(self):
        # PROTECTED REGION ID(Fsp.jonesMatrix_read) ENABLED START #
        """Return the jonesMatrix attribute."""
        return self._jones_matrix
        # PROTECTED REGION END #    //  Fsp.jonesMatrix_read

    def read_delayModel(self):
        # PROTECTED REGION ID(Fsp.delayModel_read) ENABLED START #
        """Return the delayModel attribute."""
        return self._delay_model
        # PROTECTED REGION END #    //  Fsp.delayModel_read
    
    def read_timingBeamWeights(self):
        # PROTECTED REGION ID(Fsp.timingBeamWeights_read) ENABLED START #
        """Return the timingBeamWeights attribute."""
        return self._timing_beam_weights
        # PROTECTED REGION END #    //  Fsp.timingBeamWeights_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        """allowed if FSP state is OFF"""
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
        self._group_fsp_pst_subarray.command_inout("On")

        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  Fsp.On

    def is_Off_allowed(self):
        """allowed if FSP state is ON"""
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
        self._group_fsp_pst_subarray.command_inout("Off")

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
        elif argin == "CORR":
            self._function_mode = 1
            self._proxy_correlation.SetState(tango.DevState.ON)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        elif argin == "PSS-BF":
            self._function_mode = 2
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.ON)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        elif argin == "PST-BF":
            self._function_mode = 3
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.ON)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        elif argin == "VLBI":
            self._function_mode = 4
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.ON)
        else:
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
        for proxy in self._proxy_fsp_corr_subarray:
            result[str(proxy)]=proxy.configID
        return str(result)
        # PROTECTED REGION END #    //  Fsp.getConfigID

    def is_UpdateJonesMatrix_allowed(self):
        """allowed when Devstate is ON and ObsState is READY OR SCANNINNG"""
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Jones Matrix, given per frequency slice"
    )
    def UpdateJonesMatrix(self, argin):
        # PROTECTED REGION ID(Fsp.UpdateJonesMatrix) ENABLED START #
        self.logger.debug("Fsp.UpdateJonesMatrix")
        """update FSP's Jones matrix (serialized JSON object)"""
        if self._function_mode in [2, 3]:
            argin = json.loads(argin)

            for i in self._subarray_membership:
                if self._function_mode == 2:
                    proxy = self._proxy_fsp_pss_subarray[i - 1]
                else:
                    proxy = self._proxy_fsp_pst_subarray[i - 1]
                for receptor in argin:
                    rec_id = int(receptor["receptor"])
                    if rec_id in proxy.receptors:
                        for frequency_slice in receptor["receptorMatrix"]:
                            fs_id = frequency_slice["fsid"]
                            matrix = frequency_slice["matrix"]
                            if fs_id == self._fsp_id:
                                if len(matrix) == 4:
                                    self._jones_matrix[rec_id - 1] = matrix.copy()
                                else:
                                    log_msg = "'matrix' not valid length for frequency slice {} of " \
                                            "receptor {}".format(fs_id, rec_id)
                                    self.logger.error(log_msg)
                            else:
                                log_msg = "'fsid' {} not valid for receptor {}".format(
                                    fs_id, rec_id
                                )
                                self.logger.error(log_msg)
        else:
            log_msg = "matrix not usable in function mode {}".format(self._function_mode)
            self.logger.error(log_msg)
        # PROTECTED REGION END #    // Fsp.UpdateJonesMatrix

    def is_UpdateDelayModel_allowed(self):
        """allowed when Devstate is ON and ObsState is READY OR SCANNINNG"""
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Delay Model, per receptor per polarization per timing beam"
    )
    def UpdateDelayModel(self, argin):
        # PROTECTED REGION ID(Fsp.UpdateDelayModel) ENABLED START #
        self.logger.debug("Fsp.UpdateDelayModel")
        """update FSP's delay model (serialized JSON object)"""

        # update if current function mode is either PSS-BF or PST-BF
        if self._function_mode in [2, 3]:
            argin = json.loads(argin)
            for i in self._subarray_membership:
                if self._function_mode == 2:
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
                                    log_msg = "'model' not valid length for frequency slice {} of " \
                                            "receptor {}".format(fs_id, rec_id)
                                    self.logger.error(log_msg)
                            else:
                                log_msg = "'fsid' {} not valid for receptor {}".format(
                                    fs_id, rec_id
                                )
                                self.logger.error(log_msg)
        else:
            log_msg = "model not usable in function mode {}".format(self._function_mode)
            self.logger.error(log_msg)
        # PROTECTED REGION END #    // Fsp.UpdateDelayModel

    def is_UpdateTimingBeamWeights_allowed(self):
        """allowed when Devstate is ON and ObsState is READY OR SCANNINNG"""
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Timing Beam Weights, per beam per receptor per group of 8 channels"
    )
    def UpdateBeamWeights(self, argin):
        # PROTECTED REGION ID(Fsp.UpdateTimingBeamWeights) ENABLED START #
        self.logger.debug("Fsp.UpdateBeamWeights")
        """update FSP's timing beam weights (serialized JSON object)"""

        # update if current function mode is PST-BF
        if self._function_mode == 3:
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
                                    log_msg = "'weights' not valid length for frequency slice {} of " \
                                            "receptor {}".format(fs_id, rec_id)
                                    self.logger.error(log_msg)
                            else:
                                log_msg = "'fsid' {} not valid for receptor {}".format(
                                    fs_id, rec_id
                                )
                                self.logger.error(log_msg)
        else:
            log_msg = "weights not usable in function mode {}".format(self._function_mode)
            self.logger.error(log_msg)
        # PROTECTED REGION END #    // Fsp.UpdateTimingBeamWeights

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Fsp.main) ENABLED START #
    return run((Fsp,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Fsp.main

if __name__ == '__main__':
    main()
