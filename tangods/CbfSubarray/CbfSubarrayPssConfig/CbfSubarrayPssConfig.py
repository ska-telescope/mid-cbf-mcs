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

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  CbfSubarrayPssConfig.additionnal_import

__all__ = ["CbfSubarrayPssConfig", "main"]


class CbfSubarrayPssConfig(SKACapability):
    """
    CbfSubarrayPssConfig TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarrayPssConfig.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarrayPssConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    pssEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ_WRITE,
        label="Enable transient data capture",
        doc="Enable transient data capture"
    )

    fspID = attribute(
        dtype='uint16'
    )

    searchWindowID = attribute(
        dtype='uint16',
        max_dim_x=2,
        min_dim_x=1,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    searchBeamID = attribute(
        dtype='uint16',
        max_dim_x=1500,
        min_dim_x=1,
        label="Search Beam ID",
        doc="Search Beam ID as specified by TM/LMC.",
    )

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    outputEnable = attribute(
        dtype='bool',
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    averagingInterval = attribute(
        dtype='uint16',
        label="Interval for averaging in time",
        doc="averaging interval aligned across all beams within the sub-array",
    )
    searchBeamAddress = attribute(
        dtype='str',
        label="Search Beam Destination Addresses",
        doc="Destination addresses (MAC address, IP address, port) for Mid.CBF output products. ",
    )

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

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(CbfSubarrayPssConfig.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)

        # initialize attribute values
        self._enable_Pss = False
        self._fsp_id = 0
        self._search_window_id = 0
        self._search_beam_id = 0
        self._receptors = []
        self._output_enable = 0
        self._averaging_interval = 0
        self._search_beam_address = 0


        #Getting Proxies for FSP and FSP Subarray
        self._proxy_cbf_master = PyTango.DeviceProxy(self.CbfMasterAddress)
        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )
        self._proxies_fsp = [*map(PyTango.DeviceProxy, list(self.FSP)[:int(self._master_max_capabilities["FSP"])])]
        self._proxies_fsp_subarray = [*map(PyTango.DeviceProxy,  list(self.FspSubarray))]

        self.set_state(PyTango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.delete_device

    def is_ConfigureScan_allowed(self):
        if self.dev_state() == PyTango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False


    def ValidatePssConfiguration(self, argin):
        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "PSS configuration object is not a valid JSON object."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "CbfSubarrayPssConfig execution",
                                           PyTango.ErrSeverity.ERR)
        if "searchWindowID" in argin:
            if int(argin["searchWindowID"]) in [1, 2]:
                #Set searchWindowID attribute
                self._search_window_id = int(argin["searchWindowID"])
                pass
            else:  # searchWindowID not in valid range
                msg = "'searchWindowID' must be one of [1, 2] (received {}).".format(
                    str(argin["searchWindowID"])
                )
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureSearchWindow execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'searchWindowID' not given."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                           PyTango.ErrSeverity.ERR)

        if "searchBeamID" in argin:
            if int(argin["searchBeamID"]) >=1 and int(argin["searchBeamID"]) <=1500:
                #Set searchBeamID attribute
                self._search_beam_id = int(argin["searchBeamID"])
                pass
            else:  # searchWindowID not in valid range
                msg = "'searchBeamID' must be within range 1-1500 (received {}).".format(
                    str(argin["searchBeamID"])
                )
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ValidatePssConfiguration execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            msg = "Search beam ID specified, but 'searchBeamID' not given."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ValidatePssConfiguration execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate receptors.
        # This is always given, due to implementation details.
        if "receptors" in argin:
            try:
                self.RemoveAllReceptors()
                self.AddReceptors(map(int, argin["receptors"]))
                self.RemoveAllReceptors()
            except PyTango.DevFailed as df:  # error in AddReceptors()
                self.RemoveAllReceptors()
                msg = sys.exc_info()[1].args[0].desc + "\n'receptors' was malformed."
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
            pass
            self._receptors = map(int, argin["receptors"])
        else:
            msg = "receptors specified, but 'receptors' not given."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ValidatePssConfiguration execution",
                                           PyTango.ErrSeverity.ERR)

        self._output_enable = 0
        self._averaging_interval = 0
        self._search_beam_address = 0



    # ------------------
    # Attributes methods
    # ------------------

    def read_PssEnable(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_PssEnable) ENABLED START #
        return self._enable_Pss
        # PROTECTED REGION END #    // CbfSubarrayPssConfig.read_PssEnable

    def write_PssEnable(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_PssEnable) ENABLED START #
        self._enable_Pss = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_PssEnable

    def read_PssConfig(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_PssConfig) ENABLED START #
        return json.dumps(self._pss_Config)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_PssConfig

    def write_PssConfig(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_PssConfig) ENABLED START #
        # if value is not valid JSON, the exception is caught by CbfSubarray.ConfigureScan()
        self._pss_Config = json.loads(value)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_PssConfig

    # --------
    # Commands
    # --------

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.RemoveAllReceptors

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.AddReceptors) ENABLED START #
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
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, int(PyTango.LogLevel.LOG_ERROR))
            PyTango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                           PyTango.ErrSeverity.ERR)
        # PROTECTED REGION END #    // CbfSubarrayPssConfig.AddReceptors

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.SetState

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a fsp'
    )
    def ConfigureFSP(self, argin):
        # input configuration has already been checked in CbfSubarray device for FspID configuration type = PSS or 0
        self.ValidatePssConfiguration(argin)



# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarrayPssConfig.main) ENABLED START #
    return run((CbfSubarrayPssConfig,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarrayPssConfig.main

if __name__ == '__main__':
    main()
