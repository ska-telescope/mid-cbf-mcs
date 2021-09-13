# -*- coding: utf-8 -*-
#
# This file is part of the FspPssSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: Ryam Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

""" FspPssSubarray Tango device prototype

FspPssSubarray TANGO device class for the FspPssSubarray prototype
"""

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(FspPssSubarray.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base import CspSubElementObsDevice
from ska_tango_base.commands import ResultCode

# PROTECTED REGION END #    //  FspPssSubarray.additionnal_import

__all__ = ["FspPssSubarray", "main"]

class FspPssSubarray(CspSubElementObsDevice):
    """
    FspPssSubarray TANGO device class for the FspPssSubarray prototype
    """
    # PROTECTED REGION ID(FspPssSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPssSubarray.class_variable

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
        doc="FQDN of CBF Controller",
        default_value="mid_csp_cbf/controller/main"
    )

    # TODO: CbfSubarrayAddress prop not being used
    CbfSubarrayAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Subarray"
    )

    VCC = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )
    searchBeams = attribute(
        dtype=('str',),
        access=AttrWriteType.READ,
        max_dim_x=192,
        label="SearchBeams",
        doc="List of searchBeams assigned to fspsubarray",
    )
    searchWindowID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
        max_dim_x=2,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    searchBeamID = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ,
        max_dim_x=192,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    outputEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ,
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self):
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.state_model, self.logger)
        self.register_command_object(
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the Vcc's init_device() "command".
        """

        def do(self):
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            device = self.target

            # Make a private copy of the device properties:
            device._subarray_id = device.SubID
            device._fsp_id = device.FspID

            # initialize attribute values
            device._receptors = []
            device._search_beams = []
            device._search_window_id = 0
            device._search_beam_id = []
            device._output_enable = 0
            device._scan_id = 0
            device._config_id = ""

            # device proxy for easy reference to CBF Controller
            device._proxy_cbf_controller = tango.DeviceProxy(device.CbfControllerAddress)

            device._controller_max_capabilities = dict(
                pair.split(":") for pair in
                device._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
            )
            device._count_vcc = int(device._controller_max_capabilities["VCC"])
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._proxies_vcc = [*map(tango.DeviceProxy, device._fqdn_vcc)]

            message = "FspPssSubarry Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

        # PROTECTED REGION END #    //  FspPssSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspPssSubarray.always_executed_hook) ENABLED START #
        """hook before any commands"""
        pass
        # PROTECTED REGION END #    //  FspPssSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspPssSubarray.delete_device) ENABLED START #
        """Set Idle, remove all receptors, turn device OFF"""
        pass
        # PROTECTED REGION END #    //  FspPssSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self):
        # PROTECTED REGION ID(FspPssSubarray.receptors_read) ENABLED START #
        """return receptros attribute.(array of int)"""
        return self._receptors
        # PROTECTED REGION END #    //  FspPssSubarray.receptors_read

    def read_searchBeams(self):
        # PROTECTED REGION ID(FspPssSubarray.searchBeams_read) ENABLED START #
        """Return searchBeams attribute (JSON)"""
        return self._search_beams
        # PROTECTED REGION END #    //  FspPssSubarray.searchBeams_read

    def read_searchBeamID(self):
        # PROTECTED REGION ID(FspPssSubarray.read_searchBeamID ENABLED START #
        """REturn list of SearchBeam IDs(array of int). (From searchBeams JSON)"""
        return self._search_beam_id
        # PROTECTED REGION END #    //  FspPssSubarray.read_searchBeamID

    def read_searchWindowID(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchWindowID) ENABLED START #
        """Return searchWindowID attribtue(array of int)"""
        return self._search_window_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchWindowID

    def read_outputEnable(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_outputEnable) ENABLED START #
        """Enable/Disable transmission of the output products"""
        return self._output_enable
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_outputEnable

    # --------
    # Commands
    # --------

    def _add_receptors(self, receptorIDs):
        """add specified receptors to the FSP subarray. Input is array of int."""
        self.logger.debug("_AddReceptors")
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
        for receptorID in receptorIDs:
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
                        # TODO: this is not true if more receptors can be 
                        #       specified for the same search beam
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
        # PROTECTED REGION END #    //  FspPssSubarray.AddReceptors

    def _remove_receptors(self, argin):
        """Remove Receptors. Input is array of int"""
        self.logger.debug("_remove_receptors")
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)

    def _remove_all_receptors(self):
        self._remove_receptors(self._receptors[:])

    # --------
    # Commands
    # --------

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspPssSubarray's ConfigureScan() command.
        """

        """Input a serilized JSON object. """

        def do(self, argin):
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

            device = self.target

            argin = json.loads(argin)

            # Configure receptors.
            self.logger.debug("_receptors = {}".format(device._receptors))

            device._fsp_id = argin["fsp_id"]
            device._search_window_id = int(argin["search_window_id"])

            self.logger.debug("_search_window_id = {}".format(device._search_window_id))

            for searchBeam in argin["search_beam"]:

                if len(searchBeam["receptor_ids"]) != 1:
                    # TODO - to add support for multiple receptors
                    msg = "Currently only 1 receptor per searchBeam is supported"
                    self.logger.error(msg) 
                    return (ResultCode.FAILED, msg)

                device._add_receptors(map(int, searchBeam["receptor_ids"]))
                self.logger.debug("device._receptors = {}".format(device._receptors))
                device._search_beams.append(json.dumps(searchBeam))

                device._search_beam_id.append(int(searchBeam["search_beam_id"]))
            
            # TODO: _output_enable is not currently set

            # TODO - possibly move validation of params to  
            #        validate_input()
            # (result_code, msg) = self.validate_input(argin) # TODO

            result_code = ResultCode.OK # TODO  - temp - remove
            msg = "Configure command completed OK" # TODO temp, remove

            if result_code == ResultCode.OK:
                # store the configuration on command success
                device._last_scan_configuration = argin
                msg = "Configure command completed OK"

            return(result_code, msg)

        def validate_input(self, argin):
            """
            Validate the configuration parameters against allowed values, as needed.

            :param argin: The JSON formatted string with configuration for the device.
            :type argin: 'DevString'
            :return: A tuple containing a return code and a string message.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return (ResultCode.OK, "ConfigureScan arguments validation successfull") 

    @command(
    dtype_in='DevString',
    doc_in="JSON formatted string with the scan configuration.",
    dtype_out='DevVarLongStringArray',
    doc_out="A tuple containing a return code and a string message indicating status. "
            "The message is for information purpose only.",
    )

    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(Vcc.ConfigureScan) ENABLED START #
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.
        :type argin: 'DevString'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the FspPssSubarray's GoToIdle command.
        """

        def do(self):
            """
            Stateless hook for GoToIdle() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")

            device = self.target

            # initialize attribute values
            device._search_beams = []
            device._search_window_id = 0
            device._search_beam_id = []
            device._output_enable = 0
            device._scan_id = 0
            device._config_id = ""

            device._remove_all_receptors()

            if device.state_model.obs_state == ObsState.IDLE:
                return (ResultCode.OK, 
                "GoToIdle command completed OK. Device already IDLE")

            return (ResultCode.OK, "GoToIdle command completed OK")

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPssSubarray.main) ENABLED START #
    return run((FspPssSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPssSubarray.main


if __name__ == '__main__':
    main()
