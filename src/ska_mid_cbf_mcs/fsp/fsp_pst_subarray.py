# -*- coding: utf-8 -*-
#
# This file is part of the FspPstSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Mid.CBF MCS

"""
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple

# PyTango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(FspPstSubarray.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))

from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base import SKASubarray, CspSubElementObsDevice, SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
# PROTECTED REGION END #    //  FspPstSubarray.additionnal_import

__all__ = ["FspPstSubarray", "main"]


class FspPstSubarray(CspSubElementObsDevice):
    """
    FspPstSubarray TANGO device class for the FspPstSubarray prototype
    """
    # PROTECTED REGION ID(FspPstSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPstSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16'
    )

    FspID = device_property(
        dtype='uint16'
    )

    CbfControllerAddress = device_property(
        dtype='str', 
        default_value="mid_csp_cbf/controller/main"
    )

    CbfSubarrayAddress = device_property(
        dtype='str'
    )

    VCC = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    outputEnable = attribute(
        dtype='bool',
        label="Enable Output",
        doc="Enable/disable transmission of output products."
    )

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to the subarray."
    )

    timingBeams = attribute(
        dtype=('str',),
        max_dim_x=16,
        label="TimingBeams",
        doc="List of timing beams assigned to FSP PST Subarray."
    )

    timingBeamID = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        label="TimingBeamID",
        doc="Identifiers of timing beams assigned to FSP PST Subarray"
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: FspPstSubarray) -> None:
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
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )

        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

        self.register_command_object(
            "EndScan", self.EndScanCommand(*device_args)
        )

        self.register_command_object(
            "Scan", self.ScanCommand(*device_args)
        )
    
    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the FspPstSubarray's init_device() "command".
        """

        def do(
            self: FspPstSubarray.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            device = self.target

            #get relevant IDs
            device._subarray_id = device.SubID
            device._fsp_id = device.FspID

            # initialize attribute values
            device._timing_beams = []
            device._timing_beam_id = []
            device._receptors = []
            device._output_enable = 0

            # device proxy for connection to CbfController
            device._proxy_cbf_controller = CbfDeviceProxy(
                fqdn=device.CbfControllerAddress,
                logger=device.logger
            )
            device._controller_max_capabilities = dict(
                pair.split(":") for pair in 
                device._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
            )

            # Connect to all VCC devices turned on by CbfController:
            device._count_vcc = int(device._controller_max_capabilities["VCC"])
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._proxies_vcc = [
                CbfDeviceProxy(
                    logger=device.logger, 
                    fqdn=address) for address in device._fqdn_vcc
            ]

            # device proxy for easy reference to CBF Subarray
            # TODO: Is device._proxy_cbf_subarray used anywhere?
            device._proxy_cbf_subarray = CbfDeviceProxy(
                fqdn=device.CbfSubarrayAddress,
                logger=device.logger
            )

            message = "FspPstSubarray Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self: FspPstSubarray) -> None:
        # PROTECTED REGION ID(FspPstSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspPstSubarray.always_executed_hook

    def delete_device(self: FspPstSubarray) -> None:
        # PROTECTED REGION ID(FspPstSubarray.delete_device) ENABLED START #
        """Set Idle, remove all receptors, turn device OFF"""
        pass
        # PROTECTED REGION END #    //  FspPstSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_outputEnable(self: FspPstSubarray) -> bool:
        # PROTECTED REGION ID(FspPstSubarray.outputEnable_read) ENABLED START #
        return self._output_enable
        # PROTECTED REGION END #    //  FspPstSubarray.outputEnable_read

    def read_receptors(self: FspPstSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPstSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  FspPstSubarray.receptors_read

    def write_receptors(self: FspPstSubarray, value: receptors) -> None:
        # PROTECTED REGION ID(FspPstSubarray.receptors_write) ENABLED START #
        """Set/replace receptors attribute.(array of int)"""
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  FspPstSubarray.receptors_write

    def read_timingBeams(self: FspPstSubarray) -> List[str]:
        # PROTECTED REGION ID(FspPstSubarray.timingBeams_read) ENABLED START #
        """Return timingBeams attribute (JSON)"""
        return self._timing_beams
        # PROTECTED REGION END #    //  FspPstSubarray.timingBeams_read

    def read_timingBeamID(self: FspPstSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPstSubarray.timingBeamID_read) ENABLED START #
        """Return list of Timing Beam IDs(array of int). (From timingBeams JSON)"""
        return self._timing_beam_id
        # PROTECTED REGION END #    //  FspPstSubarray.timingBeamID_read


    # --------
    # Commands
    # --------

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the FspPstSubarray's On() command.
        """
        def do(            
            self: FspPstSubarray.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message)=super().do()

            return (result_code,message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the FspPstSubarray's Off() command.
        """
        def do(            
            self: FspPstSubarray.OffCommand,
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

            device.RemoveAllReceptors()

            return (result_code,message)

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def AddReceptors(
        self: FspPstSubarray, 
        argin: List[int]
        ) -> None:
        # PROTECTED REGION ID(FspPstSubarray.AddReceptors) ENABLED START #
        """add specified receptors to the FSP subarray. Input is array of int."""
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                subarrayID = self._proxies_vcc[vccID - 1].subarrayMembership

                # only add receptor if it belongs to the CBF subarray
                if subarrayID != self._subarray_id:
                    errs.append("Receptor {} does not belong to subarray {}.".format(
                        str(receptorID), str(self._subarray_id)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)
                    else:
                        log_msg = "Receptor {} already assigned to current FSP subarray.".format(
                            str(receptorID))
                        self.logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                           tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  FspPstSubarray.AddReceptors

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(
        self: FspPstSubarray, 
        argin: List[int]
        ) -> None:
        # PROTECTED REGION ID(FspPstSubarray.RemoveReceptors) ENABLED START #
        """Remove Receptors. Input is array of int"""
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  FspPstSubarray.RemoveReceptors
    
    @command()
    def RemoveAllReceptors(self: FspPstSubarray) -> None:
        # PROTECTED REGION ID(FspPstSubarray.RemoveAllReceptors) ENABLED START #
        """Remove all Receptors of this subarray"""
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspPstSubarray.RemoveAllReceptors

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspPstSubarray's ConfigureScan() command.
        """

        """Input a serilized JSON object. """

        def do(
            self: FspPstSubarray, 
            argin: str
            ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string
            :type argin: str

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            self.logger.debug("Entering ConfigureScanCommand()")

            device = self.target

            # validate the input args

            # NOTE: This function is called after the
            # configuration has already  been validated, 
            # so the checks here have been removed to
            #  reduce overhead TODO:  to change where the
            # validation is done

            argin = json.loads(argin)

            # Configure receptors.
            # TODO: Why are we overwriting the device property fsp ID
            #       with the argument in the ConfigureScan json file
            if device._fsp_id != argin["fsp_id"]:
                device.logger.warning(
                    "The Fsp ID from ConfigureScan {} does not equal the Fsp ID from the device properties {}"
                    .format(device._fsp_id, argin["fsp_id"]))

            device._fsp_id = argin["fsp_id"]
            device._timing_beams = []
            device._timing_beam_id = []
            device._receptors = []

            for timingBeam in argin["timing_beam"]:
                device.AddReceptors(map(int, timingBeam["receptor_ids"]))
                device._timing_beams.append(json.dumps(timingBeam))
                device._timing_beam_id.append(int(timingBeam["timing_beam_id"]))  

            result_code = ResultCode.OK # TODO  - temp - remove
            msg = "Configure command completed OK" # TODO temp, remove

            if result_code == ResultCode.OK:
                msg = "Configure command completed OK"

            return(result_code, msg)

    class EndScanCommand(CspSubElementObsDevice.EndScanCommand):
        """
        A class for the FspPstSubarray's EndScan() command.
        """
        def do(            
            self: FspPstSubarray.EndScanCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for EndScan() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message)=super().do()

            return (result_code,message)

    class ScanCommand(CspSubElementObsDevice.ScanCommand):
        """
        A class for the FspPstSubarray's Scan() command.
        """
        def do(            
            self: FspPstSubarray.ScanCommand,
            argin: int
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :param argin: ScanID
            :type argin: int
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message)=super().do(argin)

            return (result_code, message)

    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the FspPstSubarray's GoToIdle command.
        """

        def do(
            self: FspPstSubarray.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for GoToIdle() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")

            (result_code,message)=super().do()

            device = self.target

            device._timing_beams = []
            device._timing_beam_id = []
            device._output_enable = 0
            device.RemoveAllReceptors()

            return (result_code,message)

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPstSubarray.main) ENABLED START #
    return run((FspPstSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPstSubarray.main

if __name__ == '__main__':
    main()