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

# """ FspPst Tango device prototype

# FspPst TANGO device class for the prototype
# """

# Additional import
# PROTECTED REGION ID(FspPst.additionnal_import) ENABLED START #
from ska_tango_base import SKACapability
import os
import sys

# tango imports
import tango
from tango.server import command, run

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)


# PROTECTED REGION END #    //  FspPst.additionnal_import

__all__ = ["FspPst", "main"]


class FspPst(SKACapability):
    """
    FspPst TANGO device class for the prototype
    """

    # PROTECTED REGION ID(FspPst.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPst.class_variable

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
        # PROTECTED REGION ID(FspPst.init_device) ENABLED START #
        """Set state to OFF"""
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspPst.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspPst.always_executed_hook) ENABLED START #
        """hook before commands"""
        # PROTECTED REGION END #    //  FspPst.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspPst.delete_device) ENABLED START #
        """hook to delelte device"""
        # PROTECTED REGION END #    //  FspPst.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(dtype_in="DevState", doc_in="New state")
    def SetState(self, argin):
        # PROTECTED REGION ID(FspPst.SetState) ENABLED START #
        """Input is DevState."""
        self.set_state(argin)
        # PROTECTED REGION END #    //  FspPst.SetState


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPst.main) ENABLED START #
    return run((FspPst,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPst.main


if __name__ == "__main__":
    main()
