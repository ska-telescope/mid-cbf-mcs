# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Vcc Tango device prototype

Vcc TANGO device class for the prototype
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
# PROTECTED REGION ID(Vcc.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  Vcc.additionnal_import

__all__ = ["Vcc", "main"]


class Vcc(SKACapability):
    """
    Vcc TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(Vcc.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  Vcc.class_variable

    # -----------------
    # Device Properties
    # -----------------









    # ----------
    # Attributes
    # ----------

















    receptorID = attribute(
        dtype='int',
        label="Receptor ID",
        doc="Receptor ID",
    )

    subarrayMembership = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="Subarray membership",
        doc="Subarray membership",
    )


    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Vcc.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        self._receptor_ID = 0
        self._subarray_membership = 0

        self.set_state(PyTango.DevState.OFF)
        # PROTECTED REGION END #    //  Vcc.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(Vcc.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Vcc.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptorID(self):
        # PROTECTED REGION ID(Vcc.receptorID_read) ENABLED START #
        return self._receptor_ID
        # PROTECTED REGION END #    //  Vcc.receptorID_read

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Vcc.subarrayMembership_read) ENABLED START #
        return self._subarray_membership
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_read

    def write_subarrayMembership(self, value):
        # PROTECTED REGION ID(Vcc.subarrayMembership_write) ENABLED START #
        self._subarray_membership = value
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_write


    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(Vcc.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  Vcc.SetState

    @command(
        dtype_in='uint16',
        doc_in='New health state'
    )
    def SetHealthState(self, argin):
        # PROTECTED REGION ID(Vcc.SetHealthState) ENABLED START #
        self._health_state = argin
        # PROTECTED REGION END #    //  Vcc.SetHealthState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main

if __name__ == '__main__':
    main()
