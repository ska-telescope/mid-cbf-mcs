# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Fsp Tango device prototype

Fsp TANGO device class for the prototype
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
# PROTECTED REGION ID(Fsp.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  Fsp.additionnal_import

__all__ = ["Fsp", "main"]


class Fsp(SKACapability):
    """
    Fsp TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(Fsp.class_variable) ENABLED START #

    def __get_capability_proxies(self):
        # for now, assume that given addresses are valid
        if self.CorrelationAddress:
            self._proxy_correlation = PyTango.DeviceProxy(self.CorrelationAddress)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "fsp_corr"
            self._proxy_correlation = PyTango.DeviceProxy("/".join(names))

        if self.PSSAddress:
            self._proxy_pss = PyTango.DeviceProxy(self.PSSAddress)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "fsp_pss"
            self._proxy_pss = PyTango.DeviceProxy("/".join(names))

        if self.PSTAddress:
            self._proxy_pst = PyTango.DeviceProxy(self.PSTAddress)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "fsp_pst"
            self._proxy_pst = PyTango.DeviceProxy("/".join(names))

        if self.VLBIAddress:
            self._proxy_vlbi = PyTango.DeviceProxy(self.VLBIAddress)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "fsp_vlbi"
            self._proxy_vlbi = PyTango.DeviceProxy("/".join(names))

    # PROTECTED REGION END #    //  Fsp.class_variable

    # -----------------
    # Device Properties
    # -----------------

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

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Fsp.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        # defines self._proxy_correlation, self._proxy_pss, self._proxy_pst, and self._proxy_vlbi
        self.__get_capability_proxies()

        # the modes are already disabled on initialization,
        # self._proxy_correlation.SetState(PyTango.DevState.DISABLE)
        # self._proxy_pss.SetState(PyTango.DevState.DISABLE)
        # self._proxy_pst.SetState(PyTango.DevState.DISABLE)
        # self._proxy_vlbi.SetState(PyTango.DevState.DISABLE)

        # initialize attribute values
        self._function_mode = 0  # IDLE
        self._subarray_membership = []

        self._obs_state = ObsState.IDLE.value
        self.set_state(PyTango.DevState.STANDBY)
        # PROTECTED REGION END #    //  Fsp.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(Fsp.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Fsp.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(Fsp.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Fsp.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_functionMode(self):
        # PROTECTED REGION ID(Fsp.functionMode_read) ENABLED START #
        return self._function_mode
        # PROTECTED REGION END #    //  Fsp.functionMode_read

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Fsp.subarrayMembership_read) ENABLED START #
        return self._subarray_membership
        # PROTECTED REGION END #    //  Fsp.subarrayMembership_read

    # --------
    # Commands
    # --------

    @command()
    def On(self):
        # PROTECTED REGION ID(Fsp.On) ENABLED START #
        self.set_state(PyTango.DevState.ON)
        # PROTECTED REGION END #    //  Fsp.On

    @command()
    def Off(self):
        # PROTECTED REGION ID(Fsp.Off) ENABLED START #
        self.set_state(PyTango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.Off

    @command()
    def Standby(self):
        # PROTECTED REGION ID(Fsp.Standby) ENABLED START #
        self.set_state(PyTango.DevState.STANDBY)
        # PROTECTED REGION END #    //  Fsp.Standby

    @command(
        dtype_in='str',
        doc_in='Function mode'
    )
    def SetFunctionMode(self, argin):
        # PROTECTED REGION ID(Fsp.SetFunctionMode) ENABLED START #
        if argin == "IDLE":
            self._function_mode = 0
            self._proxy_correlation.SetState(PyTango.DevState.DISABLE)
            self._proxy_pss.SetState(PyTango.DevState.DISABLE)
            self._proxy_pst.SetState(PyTango.DevState.DISABLE)
            self._proxy_vlbi.SetState(PyTango.DevState.DISABLE)
        if argin == "CORR":
            self._function_mode = 1
            self._proxy_correlation.SetState(PyTango.DevState.ON)
            self._proxy_pss.SetState(PyTango.DevState.DISABLE)
            self._proxy_pst.SetState(PyTango.DevState.DISABLE)
            self._proxy_vlbi.SetState(PyTango.DevState.DISABLE)
        if argin == "PSS-BF":
            self._function_mode = 2
            self._proxy_correlation.SetState(PyTango.DevState.DISABLE)
            self._proxy_pss.SetState(PyTango.DevState.ON)
            self._proxy_pst.SetState(PyTango.DevState.DISABLE)
            self._proxy_vlbi.SetState(PyTango.DevState.DISABLE)
        if argin == "PST-BF":
            self._function_mode = 3
            self._proxy_correlation.SetState(PyTango.DevState.DISABLE)
            self._proxy_pss.SetState(PyTango.DevState.DISABLE)
            self._proxy_pst.SetState(PyTango.DevState.ON)
            self._proxy_vlbi.SetState(PyTango.DevState.DISABLE)
        if argin == "VLBI":
            self._function_mode = 4
            self._proxy_correlation.SetState(PyTango.DevState.DISABLE)
            self._proxy_pss.SetState(PyTango.DevState.DISABLE)
            self._proxy_pst.SetState(PyTango.DevState.DISABLE)
            self._proxy_vlbi.SetState(PyTango.DevState.ON)

        # shouldn't happen
        self.dev_logging("functionMode not valid. Ignoring.", PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  Fsp.SetFunctionMode

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def AddSubarrayMembership(self, argin):
        # PROTECTED REGION ID(Fsp.AddSubarrayMembership) ENABLED START #
        if argin not in self._subarray_membership:
            self._subarray_membership.append(argin)
        else:
            log_msg = "FSP already belongs to subarray {}.".format(argin)
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  Fsp.AddSubarrayMembership

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def RemoveSubarrayMembership(self, argin):
        # PROTECTED REGION ID(Fsp.RemoveSubarrayMembership) ENABLED START #
        if argin in self._subarray_membership:
            self._subarray_membership.remove(argin)
            # change function mode to IDLE if no subarrays are using it.
            if not self._subarray_membership:
                self._function_mode = 0
        else:
            log_msg = "FSP does not belong to subarray {}.".format(argin)
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  Fsp.RemoveSubarrayMembership

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Fsp.main) ENABLED START #
    return run((Fsp,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Fsp.main

if __name__ == '__main__':
    main()
