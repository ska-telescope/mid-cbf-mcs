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

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import const
from ska.base.control_model import HealthState, AdminMode, ObsState
from ska.base import SKASubarray

# PROTECTED REGION END #    //  FspPssSubarray.additionnal_import

__all__ = ["FspPssSubarray", "main"]

class FspPssSubarray(SKASubarray):
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

    CbfMasterAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Master",
        default_value="mid_csp_cbf/master/main"
    )

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
        access=AttrWriteType.READ_WRITE,
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

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(FspPssSubarray.init_device) ENABLED START #
        """Initialize attribtues. Get proxy as reference to other elements."""
        self.set_state(tango.DevState.INIT)

        # get relevant IDs
        self._subarray_id = self.SubID
        self._fsp_id = self.FspID
        self._search_beams = []

        # initialize attribute values
        self._search_window_id = 0
        self._search_beam_id = []
        self._receptors = []
        self._output_enable = 0

        # device proxy for easy reference to CBF Master
        self._proxy_cbf_master = tango.DeviceProxy(self.CbfMasterAddress)

        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )
        self._count_vcc = int(self._master_max_capabilities["VCC"])
        self._fqdn_vcc = list(self.VCC)[:self._count_vcc]
        self._proxies_vcc = [*map(tango.DeviceProxy, self._fqdn_vcc)]

        # device proxy for easy reference to CBF Subarray
        self._proxy_cbf_subarray = tango.DeviceProxy(self.CbfSubarrayAddress)

        self.state_model._obs_state = ObsState.IDLE.value
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspPssSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspPssSubarray.always_executed_hook) ENABLED START #
        """hook before any commands"""
        pass
        # PROTECTED REGION END #    //  FspPssSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspPssSubarray.delete_device) ENABLED START #
        """Set Idle, remove all receptors, turn device OFF"""
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspPssSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self):
        # PROTECTED REGION ID(FspPssSubarray.receptors_read) ENABLED START #
        """return receptros attribute.(array of int)"""
        return self._receptors
        # PROTECTED REGION END #    //  FspPssSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(FspPssSubarray.receptors_write) ENABLED START #
        """Set/replcace receptros attribute.(array of int)"""
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  FspPssSubarray.receptors_write

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

    def is_On_allowed(self):
        if self.dev_state() == tango.DevState.OFF and\
                self.state_model._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(FspPssSubarray.On) ENABLED START #
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  FspPssSubarray.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(FspPssSubarray.Off) ENABLED START #
        # This command can only be called when obsState=IDLE
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspPssSubarray.Off

    def is_AddReceptors_allowed(self):
        """allowed if FSPPssSubarry is ON, ObsState is not SCANNING"""
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(FspPssSubarray.AddReceptors) ENABLED START #
        """add specified receptors to the FSP subarray. Input is array of int."""
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_master.receptorToVcc)
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
        # PROTECTED REGION END #    //  FspPssSubarray.AddReceptors

    def is_RemoveReceptors_allowed(self):
        """allowed if FSPPssSubarry is ON, ObsState is not SCANNING"""
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(FspPssSubarray.RemoveReceptors) ENABLED START #
        """Remove Receptors. Input is array of int"""
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  FspPssSubarray.RemoveReceptors

    def is_RemoveAllReceptors_allowed(self):
        """allowed if FSPPssSubarry is ON, ObsState is not SCANNING"""
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command()
    def RemoveAllReceptors(self):
        """Remove all Receptors of this subarray"""
        # PROTECTED REGION ID(FspPssSubarray.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspPssSubarray.RemoveAllReceptors

    def is_ConfigureScan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(FspPssSubarray.ConfigureScan) ENABLED START #
        # This function is called after the configuration has already been validated,
        # so the checks here have been removed to reduce overhead.
        """Input a JSON. Configure scan for fsp. Called by CbfSubarrayPssConfig(proxy_fsp_pss_subarray.ConfigureScan(json.dumps(fsp)))"""
        # transition to obsState=CONFIGURING
        self.state_model._obs_state = ObsState.CONFIGURING.value
        self.push_change_event("obsState", self.state_model._obs_state)

        argin = json.loads(argin)

        # Configure receptors.
        self.RemoveAllReceptors()
        self.AddReceptors(map(int, argin["receptors"]))
        self._fsp_id = argin["fspID"]
        self._search_window_id = int(argin["searchWindowID"])
        self._search_beams = []
        self._search_beam_id = []
        self._receptors = []

        for searchBeam in argin["searchBeam"]:
            self._search_beams.append(json.dumps(searchBeam))
            self._receptors.extend(searchBeam["receptors"])
            self._search_beam_id.append(int(searchBeam["searchBeamID"]))

        # fspPssSubarray moves to READY after configuration
        self.state_model._obs_state = ObsState.READY.value

        # PROTECTED REGION END #    //  FspPssSubarray.ConfigureScan

    def is_EndScan_allowed(self):
        """allowed if ON nd ObsState is SCANNING"""
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state == ObsState.SCANNING.value:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(FspPssSubarray.EndScan) ENABLED START #
        """Set ObsState to READY"""
        self.state_model._obs_state = ObsState.READY.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspPssSubarray.EndScan

    def is_Scan_allowed(self):
        """allowed if ON and ObsState READY"""
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state == ObsState.READY.value:
            return True
        return False

    @command()
    def Scan(self):
        # PROTECTED REGION ID(FspPssSubarray.Scan) ENABLED START #
        """Set ObsState to SCANNING"""
        self.state_model._obs_state = ObsState.SCANNING.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspPssSubarray.Scan

    def is_GoToIdle_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self.state_model._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command()
    def GoToIdle(self):
        """ObsState to IDLE"""
        # PROTECTED REGION ID(FspPssSubarray.GoToIdle) ENABLED START #
        # transition to obsState=IDLE
        self.state_model._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  FspPssSubarray.GoToIdle

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPssSubarray.main) ENABLED START #
    return run((FspPssSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPssSubarray.main


if __name__ == '__main__':
    main()
