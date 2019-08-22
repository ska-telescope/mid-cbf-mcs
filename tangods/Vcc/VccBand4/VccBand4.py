# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

""" VccBand4 Tango device prototype

VccBand4 TANGO device class for the prototype
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
# PROTECTED REGION ID(VccBand4.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  VccBand4.additionnal_import

__all__ = ["VccBand4", "main"]


class VccBand4(SKACapability):
    """
    VccBand4 TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(VccBand4.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  VccBand4.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(VccBand4.init_device) ENABLED START #
        self.set_state(PyTango.DevState.OFF)
        # PROTECTED REGION END #    //  VccBand4.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccBand4.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  VccBand4.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccBand4.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  VccBand4.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(VccBand4.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  VccBand4.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(VccBand4.main) ENABLED START #
    return run((VccBand4,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccBand4.main

if __name__ == '__main__':
    main()
