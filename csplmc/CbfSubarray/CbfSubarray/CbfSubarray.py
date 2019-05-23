# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CbfSubarray Tango device prototype

CBFSubarray TANGO device class for the CBFSubarray prototype
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
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKASubarray.SKASubarray import SKASubarray
# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------








    # ----------
    # Attributes
    # ----------
















    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band",
        memorized=True,
        doc="One of {1, 2, 3, 4, 5a, 5b}",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    scanID = attribute(
        dtype='uint64',
        access=AttrWriteType.READ_WRITE,
        label="Scan ID",
        memorized=True,
        doc="Scan ID",
    )



    receptors = attribute(
        dtype=('int',),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
        self._health_state = HealthState.UNKNOWN.value

        self._frequency_band = 0
        self._scan_ID = 0
        self._receptors = []

        self._proxy_cbf_master = PyTango.DeviceProxy("mid_csp_cbf/master/main")

        # this is done by the SKASubarray base class
        # self.set_state(PyTango.DevState.DISABLE)
        # PROTECTED REGION END #    //  CbfSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_frequencyBand(self):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_read) ENABLED START #
        return self._frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def write_frequencyBand(self, value):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_write) ENABLED START #
        self._frequency_band = value
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_write

    def read_scanID(self):
        # PROTECTED REGION ID(CbfSubarray.scanID_read) ENABLED START #
        return self._scan_ID
        # PROTECTED REGION END #    //  CbfSubarray.scanID_read

    def write_scanID(self, value):
        # PROTECTED REGION ID(CbfSubarray.scanID_write) ENABLED START #
        self._scan_ID = value
        # PROTECTED REGION END #    //  CbfSubarray.scanID_write

    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read


    # --------
    # Commands
    # --------

    @command(
    dtype_in='str', 
    doc_in="Scan configuration", 
    dtype_out='str', 
    doc_out="Status", 
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        # argin will be a JSON object, with schema TBD
        return ""
        # PROTECTED REGION END #    //  CbfSubarray.ConfigureScan

    @command(
        dtype_in=('int',),
        doc_in="List of receptor IDs",
    )
    @DebugIt()
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.AddReceptors) ENABLED START #
        errs = []  # list of error messages
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = PyTango.DeviceProxy("mid_csp_cbf/vcc/" + str(vccID).zfill(3))
                subarrayID = vccProxy.subarrayMembership

                # only add receptor if it does not already belong to a different subarray
                if subarrayID not in [0, int(self.get_name()[-2:])]:
                    errs.append("Receptor {} already in use by subarray {}.".format(str(receptorID), str(subarrayID)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)

                        # change subarray membership of vcc
                        # last two chars of fqdn is subarrayID
                        vccProxy.subarrayMembership = int(self.get_name()[-2:])
                    else:
                        log_msg = "Receptor {} already assigned to subarray. Skipping.".format(str(receptorID))
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, int(PyTango.LogLevel.LOG_ERROR))
            PyTango.Except.throw_exception("Command failed", msg, "AddReceptors execution", PyTango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CbfSubarray.AddReceptors

    @command(
        dtype_in=('int',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.RemoveReceptors) ENABLED START #
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            if receptorID in self._receptors:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = PyTango.DeviceProxy("mid_csp_cbf/vcc/" + str(vccID).zfill(3))

                self._receptors.remove(receptorID)

                # reset subarray membership of vcc
                vccProxy.subarrayMembership = 0
            else:
                log_msg = "Receptor {} not assigned to subarray. Skipping.".format(str(receptorID))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  CbfSubarray.RemoveReceptors

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main

if __name__ == '__main__':
    main()
