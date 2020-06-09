# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# """ 
# VccBand3 TANGO device class for the prototype
# """

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
# PROTECTED REGION ID(VccBand3.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from skabase.control_model import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  VccBand3.additionnal_import

__all__ = ["VccBand3", "main"]


class VccBand3(SKACapability):
    """
    VccBand3 TANGO device class for the prototype
    """
    # PROTECTED REGION ID(VccBand3.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  VccBand3.class_variable

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
        # PROTECTED REGION ID(VccBand3.init_device) ENABLED START #
        """initialize device and set DevState to OFF"""
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  VccBand3.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccBand3.always_executed_hook) ENABLED START #
        """hook to be executed before commands"""
        pass
        # PROTECTED REGION END #    //  VccBand3.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccBand3.delete_device) ENABLED START #
        """hook to delete device"""
        pass
        # PROTECTED REGION END #    //  VccBand3.delete_device

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
        # PROTECTED REGION ID(VccBand3.SetState) ENABLED START #
        """Set the state of this Device; called by VCC"""
        self.set_state(argin)
        # PROTECTED REGION END #    //  VccBand3.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(VccBand3.main) ENABLED START #
    return run((VccBand3,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccBand3.main

if __name__ == '__main__':
    main()
