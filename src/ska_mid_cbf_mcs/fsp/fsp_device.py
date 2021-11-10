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
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple

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

from ska_tango_base import SKACapability, SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
# PROTECTED REGION END #    //  Fsp.additionnal_import

__all__ = ["Fsp", "main"]


class Fsp(SKACapability):
    """
    Fsp TANGO device class for the prototype
    """
    # PROTECTED REGION ID(Fsp.class_variable) ENABLED START #

    def __get_capability_proxies(
            self: Fsp, 
    ) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

        if self._proxy_correlation is None:
            if self.CorrelationAddress:
                self._proxy_correlation = CbfDeviceProxy(
                    fqdn=self.CorrelationAddress,
                    logger=self.logger
                )
            
        if self._proxy_pss is None:
            if self.PSSAddress:
                self._proxy_pss = CbfDeviceProxy(
                    fqdn=self.PSSAddress,
                    logger=self.logger
                )
            
        if self._proxy_pst is None:
            if self.PSTAddress:
                self._proxy_pst = CbfDeviceProxy(
                    fqdn=self.PSTAddress,
                    logger=self.logger
                )
            
        if self._proxy_vlbi is None:
            if self.VLBIAddress:
                self._proxy_vlbi = CbfDeviceProxy(
                    fqdn=self.VLBIAddress,
                    logger=self.logger
                )

        if self._proxy_fsp_corr_subarray is None:
            if self.FspCorrSubarray:
                self._proxy_fsp_corr_subarray = \
                    [CbfDeviceProxy(fqdn=fqdn, logger=self.logger) \
                    for fqdn in self.FspCorrSubarray]

        if self._proxy_fsp_pss_subarray is None:
            if self.FspPssSubarray:
                self._proxy_fsp_pss_subarray = \
                    [CbfDeviceProxy(fqdn=fqdn, logger=self.logger) \
                    for fqdn in self.FspPssSubarray]

        if self._proxy_fsp_pst_subarray is None:
            if self.FspPstSubarray:
                self._proxy_fsp_pst_subarray = \
                    [CbfDeviceProxy(fqdn=fqdn, logger=self.logger) \
                    for fqdn in self.FspPstSubarray]
    
    def __get_group_proxies(
        self: Fsp, 
    ) -> None:
        """Establish connections with the group proxies"""
        if self._group_fsp_corr_subarray is None:
            self._group_fsp_corr_subarray = CbfGroupProxy("FSP Subarray Corr", logger=self.logger)
            for fqdn in list(self.FspCorrSubarray):
                self._group_fsp_corr_subarray.add(fqdn)
        if self._group_fsp_pss_subarray is None:
            self._group_fsp_pss_subarray = CbfGroupProxy("FSP Subarray Pss", logger=self.logger)
            for fqdn in list(self.FspPssSubarray):
                self._group_fsp_pss_subarray.add(fqdn)
        if self._group_fsp_pst_subarray is None:
            self._group_fsp_pst_subarray = CbfGroupProxy("FSP Subarray Pst", logger=self.logger)
            for fqdn in list(self.FspPstSubarray):
                self._group_fsp_pst_subarray.add(fqdn)

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

    def init_command_objects(self: Fsp) -> None:
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

    def always_executed_hook(self: Fsp) -> None:
        # PROTECTED REGION ID(Fsp.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        self.__get_capability_proxies()
        self.__get_group_proxies()

        # PROTECTED REGION END #    //  Fsp.always_executed_hook

    def delete_device(self: Fsp) -> None:
        # PROTECTED REGION ID(Fsp.delete_device) ENABLED START #
        """Hook to delete device."""
        pass
        # PROTECTED REGION END #    //  Fsp.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_functionMode(self: Fsp) -> tango.DevEnum:
        # PROTECTED REGION ID(Fsp.functionMode_read) ENABLED START #
        """
            Read the functionMode attribute.

            :return: a DevEnum representing the mode.
            :rtype: tango.DevEnum
        """
        return self._function_mode
        # PROTECTED REGION END #    //  Fsp.functionMode_read

    def read_subarrayMembership(self: Fsp) -> List[int]:
        # PROTECTED REGION ID(Fsp.subarrayMembership_read) ENABLED START #
        """
            Read the subarrayMembership attribute.

            :return: an array of affiliations of the FSP.
            :rtype: List[int]
        """
        return self._subarray_membership
        # PROTECTED REGION END #    //  Fsp.subarrayMembership_read

    def read_scanID(self: Fsp) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.scanID_read) ENABLED START #
        """
            Read the scanID attribute.

            :return: the scanID.
            :rtype: int
        """
        return self._scan_id
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_read

    def read_configID(self: Fsp) -> str:
        # PROTECTED REGION ID(Fsp.configID_read) ENABLED START #
        """
            Read the configID attribute.

            :return: the configID.
            :rtype: str
        """
        return self._config_id
        # PROTECTED REGION END #    //  Fsp.configID_read

    def write_configID(self: Fsp, value: str) -> None:
        # PROTECTED REGION ID(Fsp.configID_write) ENABLED START #
        """
            Write the configID attribute.

            :param value: the configID value.
        """
        self._config_id=value
        # PROTECTED REGION END #    //  Fsp.configID_write

    def read_jonesMatrix(self: Fsp) -> List[List[float]]:
        # PROTECTED REGION ID(Fsp.jonesMatrix_read) ENABLED START #
        """
            Read the jonesMatrix attribute.

            :return: the jonesMatrix.
            :rtype: List[List[float]]
        """
        return self._jones_matrix
        # PROTECTED REGION END #    //  Fsp.jonesMatrix_read

    def read_delayModel(self: Fsp) -> List[List[float]]:
        # PROTECTED REGION ID(Fsp.delayModel_read) ENABLED START #
        """
            Read the delayModel attribute.

            :return: the delayModel.
            :rtype: List[List[float]]
        """
        return self._delay_model
        # PROTECTED REGION END #    //  Fsp.delayModel_read
    
    def read_timingBeamWeights(self: Fsp) -> List[List[float]]:
        # PROTECTED REGION ID(Fsp.timingBeamWeights_read) ENABLED START #
        """
            Read the timingBeamWeights attribute.

            :return: the timingBeamWeights.
            :rtype: List[List[float]]
        """
        return self._timing_beam_weights
        # PROTECTED REGION END #    //  Fsp.timingBeamWeights_read

    # --------
    # Commands
    # --------

    class InitCommand(SKACapability.InitCommand):
        """
        A class for the Fsp's init_device() "command".
        """

        def do(
            self: Fsp.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message)=super().do()

            device = self.target

            # initialize FSP proxies
            device._group_fsp_corr_subarray = None
            device._group_fsp_pss_subarray = None
            device._group_fsp_pst_subarray = None
            device._proxy_correlation = None
            device._proxy_pss = None
            device._proxy_pst = None
            device._proxy_vlbi = None
            device._proxy_fsp_corr_subarray = None
            device._proxy_fsp_pss_subarray = None
            device._proxy_fsp_pst_subarray = None

            device._fsp_id = device.FspID

            # initialize attribute values
            device._function_mode = 0  # IDLE
            device._subarray_membership = []
            device._scan_id = 0
            device._config_id = ""
            device._jones_matrix = [[0.0] * 4 for _ in range(4)]
            device._delay_model = [[0.0] * 6 for _ in range(4)]
            device._timing_beam_weights = [[0.0] * 6 for _ in range(4)]

            return (result_code,message)

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the Fsp's On() command.
        """
        def do(
            self: Fsp.OnCommand,
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

            device._proxy_correlation.SetState(tango.DevState.DISABLE)
            device._proxy_pss.SetState(tango.DevState.DISABLE)
            device._proxy_pst.SetState(tango.DevState.DISABLE)
            device._proxy_vlbi.SetState(tango.DevState.DISABLE)
            device._group_fsp_corr_subarray.command_inout("On")
            device._group_fsp_pss_subarray.command_inout("On")
            device._group_fsp_pst_subarray.command_inout("On")

            return (result_code,message)
    
    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the Fsp's Off() command.
        """
        def do(
            self: Fsp.OffCommand,
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

            device._proxy_correlation.SetState(tango.DevState.OFF)
            device._proxy_pss.SetState(tango.DevState.OFF)
            device._proxy_pst.SetState(tango.DevState.OFF)
            device._proxy_vlbi.SetState(tango.DevState.OFF)
            device._group_fsp_corr_subarray.command_inout("Off")
            device._group_fsp_pss_subarray.command_inout("Off")
            device._group_fsp_pst_subarray.command_inout("Off")

            # remove all subarray membership
            for subarray_ID in device._subarray_membership[:]:
                device.RemoveSubarrayMembership(subarray_ID)

            return (result_code,message)

    def is_SetFunctionMode_allowed(
        self: Fsp
        ) -> bool:
        """
            Determine if SetFunctionMode is allowed 
            (allowed if FSP state is ON).

            :return: if SetFunctionMode is allowed
            :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='Function mode'
    )
    def SetFunctionMode(
        self: Fsp,
        argin: str,
        ) -> None:
        # PROTECTED REGION ID(Fsp.SetFunctionMode) ENABLED START #
        """
            Set the Fsp Function Mode, either IDLE, CORR, PSS-BF, PST-BF, or VLBI
            If IDLE set the pss, pst, corr and vlbi devicess to DISABLE. OTherwise, 
            turn one of them ON according to argin, and all others DISABLE.

            :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
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

    def is_AddSubarrayMembership_allowed(self: Fsp) -> bool:
        """
            Determine if AddSubarrayMembership is allowed
            (allowed if FSP state is ON).

            :return: if AddSubarrayMembership is allowed
            :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def AddSubarrayMembership(
        self: Fsp,
        argin: int,
        ) -> None:
        # PROTECTED REGION ID(Fsp.AddSubarrayMembership) ENABLED START #
        """
            Add a subarray to the subarrayMembership list.

            :param argin: an integer representing the subarray affiliation
        """
        if argin not in self._subarray_membership:
            self._subarray_membership.append(argin)
        else:
            log_msg = "FSP already belongs to subarray {}.".format(argin)
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  Fsp.AddSubarrayMembership

    def is_RemoveSubarrayMembership_allowed(self: Fsp) -> bool:
        """
            Determine if RemoveSubarrayMembership is allowed 
            (allowed if FSP state is ON).

            :return: if RemoveSubarrayMembership is allowed
            :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def RemoveSubarrayMembership(
        self: Fsp,
        argin: int,
        ) -> None:
        # PROTECTED REGION ID(Fsp.RemoveSubarrayMembership) ENABLED START #
        """
            Remove subarray from the subarrayMembership list.
            If subarrayMembership is empty after removing 
            (no subarray is using this FSP), set function mode to empty.

            :param argin: an integer representing the subarray affiliation
        """
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
    def getConfigID(self: Fsp) -> str:
        # PROTECTED REGION ID(Fsp.getConfigID) ENABLED START #
        """
            Get the configID for all the fspCorrSubarray

            :return: the configID
            :rtype: str
        """
        result ={}
        for proxy in self._proxy_fsp_corr_subarray:
            result[str(proxy)]=proxy.configID
        return str(result)
        # PROTECTED REGION END #    //  Fsp.getConfigID

    def is_UpdateJonesMatrix_allowed(self: Fsp) -> bool:
        """
            Determine if UpdateJonesMatrix is allowed 
            (allowed if FSP state is ON and ObsState is 
            READY OR SCANNINNG).

            :return: if UpdateJonesMatrix is allowed
            :rtype: bool
        """
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Jones Matrix, given per frequency slice"
    )
    def UpdateJonesMatrix(
        self: Fsp, 
        argin: str,
        ) -> None:
        # PROTECTED REGION ID(Fsp.UpdateJonesMatrix) ENABLED START #
        """
            Update the FSP's jones matrix (serialized JSON object)

            :param argin: the jones matrix data
        """
        self.logger.debug("Fsp.UpdateJonesMatrix")
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

    def is_UpdateDelayModel_allowed(self: Fsp) -> bool:
        """
            Determine if UpdateDelayModelis allowed 
            (allowed if FSP state is ON and ObsState is 
            READY OR SCANNINNG).

            :return: if UpdateDelayModel is allowed
            :rtype: bool
        """
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Delay Model, per receptor per polarization per timing beam"
    )
    def UpdateDelayModel(
        self: Fsp, 
        argin: str,
        ) -> None:
        # PROTECTED REGION ID(Fsp.UpdateDelayModel) ENABLED START #
        """
            Update the FSP's delay model (serialized JSON object)

            :param argin: the delay model data
        """
        self.logger.debug("Fsp.UpdateDelayModel")

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

    def is_UpdateTimingBeamWeights_allowed(self: Fsp) -> bool:
        """
            Determine if UpdateTimingBeamWeights is allowed 
            (allowed if FSP state is ON and ObsState is 
            READY OR SCANNINNG).

            :return: if UpdateTimingBeamWeights is allowed
            :rtype: bool
        """
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Timing Beam Weights, per beam per receptor per group of 8 channels"
    )
    def UpdateBeamWeights(
        self: Fsp, 
        argin: str,
        ) -> None:
        # PROTECTED REGION ID(Fsp.UpdateTimingBeamWeights) ENABLED START #
        """
            Update the FSP's timing beam weights (serialized JSON object)

            :param argin: the timing beam weight data
        """
        self.logger.debug("Fsp.UpdateBeamWeights")

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