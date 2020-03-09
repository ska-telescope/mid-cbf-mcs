# -*- coding: utf-8 -*-
#
# This file is part of the CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: Ryan Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2020 National Research Council of Canada
"""

"""
CbfSubarrayPssConfig Tango device prototype

CbfSubarrayPssConfig TANGO device class for the prototype
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
# PROTECTED REGION ID(CbfSubarrayPssConfig.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState, const
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  CbfSubarrayPssConfig.additionnal_import

__all__ = ["CbfSubarrayPssConfig", "main"]


class CbfSubarrayPssConfig(SKACapability):
    """
    SearchWindow TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarrayPssConfig.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarrayPssConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------

    FSP = device_property(
        dtype=('str',)
    )

    FspSubarray = device_property(
        dtype=('str',)
    )

    CbfMasterAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Master",
        default_value="mid_csp_cbf/sub_elt/master"
    )

    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        label="Fst PSS Configuration",
        doc="Fst PSS Configuration JSON",
        max_dim_x=197,
    )

    fspID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
    )

    searchWindowID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        max_dim_x=2,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    searchBeamID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        max_dim_x=1500,
        label="Search Beam ID",
        doc="Search Beam ID as specified by TM/LMC.",
    )

    outputEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ_WRITE,
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    averagingInterval = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Interval for averaging in time",
        doc="averaging interval aligned across all beams within the sub-array",
    )

    searchBeamAddress = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Search Beam Destination Addresses",
        doc="Destination addresses (MAC address, IP address, port) for Mid.CBF output products. ",
    )

    PssConfig = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Fst PSS Configuration",
        doc="Fst PSS Configuration JSON"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(CbfSubarrayPssConfig.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)

        # initialize attribute values
        self._pss_config = {}  # this is interpreted as a JSON object
        self._fsp_id = 0
        self._search_window_id = 0
        self._search_beam_id = 0
        self._receptors = []
        self._output_enable = 0
        self._averaging_interval = 0
        self._search_beam_address = ""

        # Getting Proxies for FSP and FSP Subarrays
        self._proxy_cbf_master = PyTango.DeviceProxy(self.CbfMasterAddress)
        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )
        self._proxies_fsp = [*map(PyTango.DeviceProxy, list(self.FSP)[:int(self._master_max_capabilities["FSP"])])]
        self._proxies_fsp_subarray = [*map(PyTango.DeviceProxy, list(self.FspSubarray))]

        self._obs_state = ObsState.IDLE.value
        self.set_state(PyTango.DevState.ON)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.delete_device

    def is_configure_scan_allowed(self):
        if self.dev_state() == PyTango.DevState.ON and \
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    def __raise_configure_scan_fatal_error(self, msg):
        self.logger.error(msg)
        PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                       PyTango.ErrSeverity.ERR)

    # ------------------
    # Attributes methods
    # ------------------
    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_receptors) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_receptors

    def write_receptors(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_receptors) ENABLED START #
        self._receptors = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_receptors

    def read_fspID(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_fspID) ENABLED START #
        return self._fsp_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_fspID

    def write_fspID(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_fspID) ENABLED START #
        self._fsp_id = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_fspID

    def read_searchWindowID(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchWindowID) ENABLED START #
        return self._search_window_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchWindowID

    def write_searchWindowID(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_searchWindowID) ENABLED START #
        self._search_window_id = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_searchWindowID

    def read_searchBeamID(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchBeamID) ENABLED START #
        return self._search_beam_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchBeamID

    def write_searchBeamID(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_searchBeamID) ENABLED START #
        self._search_beam_id = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_searchBeamID

    def read_outputEnable(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_outputEnable) ENABLED START #
        return self._output_enable
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_outputEnable

    def write_outputEnable(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_outputEnable) ENABLED START #
        self._output_enable = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_outputEnable

    def read_averagingInterval(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_averagingInterval) ENABLED START #
        return self._averaging_interval
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_averagingInterval

    def write_averagingInterval(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_averagingInterval) ENABLED START #
        self._averaging_interval = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_averagingInterval

    def read_searchBeamAddress(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchBeamAddress) ENABLED START #
        return self._search_beam_address
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchBeamAddress

    def write_searchBeamAddress(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_searchBeamAddress) ENABLED START #
        self._search_beam_address = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_searchBeamAddress

    def read_PssConfig(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_PssConfig) ENABLED START #
        return json.dumps(self._pss_config)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_PssConfig

    def write_PssConfig(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_PssConfig) ENABLED START #
        # if value is not valid JSON, the exception is caught by CbfSubarray.ConfigureScan()
        self._pss_config = json.loads(value)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_PssConfig

    # --------
    # Commands
    # --------
    @command(
        dtype_in='str',
        doc_in='JSON object to configure a fsp'
    )
    def ConfigureFSP(self, argin):
        # input configuration has already been checked in CbfSubarray device for FspID configuration type = PSS or 0
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            msg = "Device not in IDLE or READY obsState."
            self.logger.error(msg)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureFSP execution",
                                           PyTango.ErrSeverity.ERR)
        try:
            argin = json.loads(argin)
            self._pss_config = argin
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Configuration object is not a valid JSON object. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)
        self._obs_state = ObsState.CONFIGURING.value

        for fsp in argin:
            try:
                self._fsp_id = fsp["fspID"]
                self._search_window_id = int(fsp["searchWindowID"])
                self._search_beam_id = int(fsp["searchBeamID"])
                self._receptors = fsp["receptors"]
                self._output_enable = bool(fsp["outputEnable"])
                self._averaging_interval = int(fsp["averagingInterval"])
                self._search_beam_address = fsp["searchBeamDestinationAddress"]
            except PyTango.DevFailed:  # exception in ConfigureScan
                msg = "An exception occurred while configuring CbfSubarrayPssConfig attributes:\n{}\n" \
                  "Aborting configuration".format(sys.exc_info()[1].args[0].desc)
                self.__raise_configure_scan_fatal_error(msg)

        self._obs_state = ObsState.READY.value

    def is_EndScan_allowed(self):
        if self.dev_state() == PyTango.DevState.ON:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.EndScan) ENABLED START #
        if self._obs_state != ObsState.SCANNING.value:
            msg = "Device not in SCANNING obsState."
            self.logger.error(msg)
            PyTango.Except.throw_exception("Command failed", msg, "EndScan execution",
                                           PyTango.ErrSeverity.ERR)

        self._obs_state = ObsState.READY.value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.EndScan

    def is_Scan_allowed(self):
        if self.dev_state() == PyTango.DevState.ON:
            return True
        return False

    @command()
    def Scan(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.Scan) ENABLED START #
        if self._obs_state != ObsState.READY.value:
            msg = "Device not in READY obsState."
            self.logger.error(msg)
            PyTango.Except.throw_exception("Command failed", msg, "Scan execution",
                                           PyTango.ErrSeverity.ERR)
        # TODO: actually use argin
        # For MVP, ignore argin (activation time)
        self._obs_state = ObsState.SCANNING.value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.Scan

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.SetState

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarrayPssConfig.main) ENABLED START #
    return run((CbfSubarrayPssConfig,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarrayPssConfig.main

if __name__ == '__main__':
    main()
