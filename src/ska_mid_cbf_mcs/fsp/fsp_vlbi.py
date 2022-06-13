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

# """ FspVlbi Tango device prototype

# FspVlbi TANGO device class for the prototype
# """

# Additional import
# PROTECTED REGION ID(FspVlbi.additionnal_import) ENABLED START #
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

# PROTECTED REGION END #    //  FspVlbi.additionnal_import

__all__ = ["FspVlbi", "main"]


class FspVlbi(SKACapability):
    """
    FspVlbi TANGO device class for the prototype
    """

    # PROTECTED REGION ID(FspVlbi.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspVlbi.class_variable

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
        # PROTECTED REGION ID(FspVlbi.init_device) ENABLED START #
        """Set state to OFF"""
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspVlbi.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspVlbi.always_executed_hook) ENABLED START #
        """hook before commands"""
        pass
        # PROTECTED REGION END #    //  FspVlbi.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspVlbi.delete_device) ENABLED START #
        """hook to delelte device"""
        pass
        # PROTECTED REGION END #    //  FspVlbi.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(dtype_in="DevState", doc_in="New state")
    def SetState(self, argin):
        # PROTECTED REGION ID(FspVlbi.SetState) ENABLED START #
        """Input is DevState."""
        self.set_state(argin)
        # PROTECTED REGION END #    //  FspVlbi.SetState


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspVlbi.main) ENABLED START #
    return run((FspVlbi,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspVlbi.main


if __name__ == "__main__":
    main()
