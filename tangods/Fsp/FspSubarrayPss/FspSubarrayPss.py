# -*- coding: utf-8 -*-
#
# This file is part of the FspSubarrayPss project
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

""" FspSubarrayPss Tango device prototype

FspSubarrayPss TANGO device class for the FspSubarrayPss prototype
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
# PROTECTED REGION ID(FspSubarrayPss.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import const
from skabase.control_model import HealthState, AdminMode, ObsState
from skabase.SKASubarray.SKASubarray import SKASubarray

# PROTECTED REGION END #    //  FspSubarrayPss.additionnal_import

__all__ = ["FspSubarrayPss", "main"]

class SearchBeam:
  def __init__(self, search_beam_id, receptors, output_enable, averaging_interval, search_beam_address):
      self._search_beam_id = search_beam_id
      self._receptors = receptors
      self._output_enable = output_enable
      self._averaging_interval = averaging_interval
      self._search_beam_address = search_beam_address

class FspSubarrayPss(SKASubarray):
    """
    FspSubarrayPss TANGO device class for the FspSubarrayPss prototype
    """
    # PROTECTED REGION ID(FspSubarrayPss.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspSubarrayPss.class_variable

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
        dtype=('uint16',),
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
        dtype='uint16',
        access=AttrWriteType.READ,
        max_dim_x=1500,
        label="Search Beam ID",
        doc="Search Beam ID as specified by TM/LMC.",
    )

    outputEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ,
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    averagingInterval = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
        label="Interval for averaging in time",
        doc="averaging interval aligned across all beams within the sub-array",
    )

    searchBeamAddress = attribute(
        dtype='str',
        access=AttrWriteType.READ,
        label="Search Beam Destination Addresses",
        doc="Destination addresses (MAC address, IP address, port) for Mid.CBF output products. ",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(FspSubarrayPss.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # get relevant IDs
        self._subarray_id = self.SubID
        self._fsp_id = self.FspID
        self._search_beams = []

        # initialize attribute values
        self._search_window_id = 0
        self._search_beam_id = 0
        self._receptors = []
        self._output_enable = 0
        self._averaging_interval = 0
        self._search_beam_address = ""

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

        self._obs_state = ObsState.IDLE.value
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspSubarrayPss.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspSubarrayPss.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspSubarrayPss.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspSubarrayPss.delete_device) ENABLED START #
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspSubarrayPss.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self):
        # PROTECTED REGION ID(FspSubarrayPss.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  FspSubarrayPss.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(FspSubarrayPss.receptors_write) ENABLED START #
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  FspSubarrayPss.receptors_write

    def read_searchBeams(self):
        # PROTECTED REGION ID(FspSubarrayPss.searchBeams_read) ENABLED START #
        return self._search_beams
        # PROTECTED REGION END #    //  FspSubarrayPss.searchBeams_read

    def read_searchWindowID(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchWindowID) ENABLED START #
        return self._search_window_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchWindowID

    def read_searchBeamID(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchBeamID) ENABLED START #
        return self._search_beam_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchBeamID

    def read_outputEnable(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_outputEnable) ENABLED START #
        return self._output_enable
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_outputEnable

    def read_averagingInterval(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_averagingInterval) ENABLED START #
        return self._averaging_interval
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_averagingInterval

    def read_searchBeamAddress(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchBeamAddress) ENABLED START #
        return self._search_beam_address
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchBeamAddress

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        if self.dev_state() == tango.DevState.OFF and\
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(FspSubarrayPss.On) ENABLED START #
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  FspSubarrayPss.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(FspSubarrayPss.Off) ENABLED START #
        # This command can only be called when obsState=IDLE
        # self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspSubarrayPss.Off

    def is_AddReceptors_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [
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
        # PROTECTED REGION ID(FspSubarrayPss.AddReceptors) ENABLED START #
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
        # PROTECTED REGION END #    //  FspSubarrayPss.AddReceptors

    def is_RemoveReceptors_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [
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
        # PROTECTED REGION ID(FspSubarrayPss.RemoveReceptors) ENABLED START #
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  FspSubarrayPss.RemoveReceptors

    def is_RemoveAllReceptors_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(FspSubarrayPss.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspSubarrayPss.RemoveAllReceptors

    def is_ConfigureScan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(FspSubarrayPss.ConfigureScan) ENABLED START #
        # This function is called after the configuration has already been validated,
        # so the checks here have been removed to reduce overhead.

        # transition to obsState=CONFIGURING
        self._obs_state = ObsState.CONFIGURING.value
        self.push_change_event("obsState", self._obs_state)

        argin = json.loads(argin)

        # Configure receptors.
        self.RemoveAllReceptors()
        self.AddReceptors(map(int, argin["receptors"]))
        self._fsp_id = argin["fspID"]
        self._search_window_id = int(argin["searchWindowID"])
        self._search_beams = []

        for searchBeam in argin["searchBeam"]:
            single_beam = SearchBeam(int(searchBeam["searchBeamID"]), searchBeam["receptors"],
                                     bool(searchBeam["outputEnable"]), int(searchBeam["averagingInterval"]),
                                     searchBeam["searchBeamDestinationAddress"])

            self._search_beams.append(single_beam)

        # fspSubarrayPss moves to READY after configuration
        self._obs_state = ObsState.READY.value

        # PROTECTED REGION END #    //  FspSubarrayPss.ConfigureScan

    def is_EndScan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.SCANNING.value:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(FspSubarrayPss.EndScan) ENABLED START #
        self._obs_state = ObsState.READY.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspSubarrayPss.EndScan

    def is_Scan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.READY.value:
            return True
        return False

    @command()
    def Scan(self):
        # PROTECTED REGION ID(FspSubarrayPss.Scan) ENABLED START #
        self._obs_state = ObsState.SCANNING.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspSubarrayPss.Scan

    def is_GoToIdle_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command()
    def GoToIdle(self):
        # PROTECTED REGION ID(FspSubarrayPss.GoToIdle) ENABLED START #
        # transition to obsState=IDLE
        self._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  FspSubarrayPss.GoToIdle

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspSubarrayPss.main) ENABLED START #
    return run((FspSubarrayPss,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspSubarrayPss.main


if __name__ == '__main__':
    main()
