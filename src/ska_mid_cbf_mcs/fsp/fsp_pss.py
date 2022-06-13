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

# """ FspPss Tango device prototype

# FspPss TANGO device class for the prototype
# """

# Additional import
# PROTECTED REGION ID(FspPss.additionnal_import) ENABLED START #
import os
import sys

# tango imports
import tango
from tango import (
    AttrQuality,
    AttrWriteType,
    DebugIt,
    DevState,
    DispLevel,
    PipeWriteType,
)
from tango.server import Device, attribute, command, device_property, run

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from ska_tango_base import SKACapability
from ska_tango_base.control_model import AdminMode, HealthState

# PROTECTED REGION END #    //  FspPss.additionnal_import

__all__ = ["FspPss", "main"]


class FspPss(SKACapability):
    """
    FspPss TANGO device class for the prototype
    """

    # PROTECTED REGION ID(FspPss.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPss.class_variable

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
        # PROTECTED REGION ID(FspPss.init_device) ENABLED START #
        """Set state to OFF"""
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspPss.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspPss.always_executed_hook) ENABLED START #
        """hook before commands"""
        pass
        # PROTECTED REGION END #    //  FspPss.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspPss.delete_device) ENABLED START #
        """hook to delelte device"""
        pass
        # PROTECTED REGION END #    //  FspPss.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(dtype_in="DevState", doc_in="New state")
    def SetState(self, argin):
        # PROTECTED REGION ID(FspPss.SetState) ENABLED START #
        """Input is DevState."""
        self.set_state(argin)
        # PROTECTED REGION END #    //  FspPss.SetState


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPss.main) ENABLED START #
    return run((FspPss,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPss.main


if __name__ == "__main__":
    main()
