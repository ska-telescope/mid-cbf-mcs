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

""" FspCorr Tango device prototype

FspCorr TANGO device class for the prototype
"""
import os  # noqa: E402
import sys  # noqa: E402

import tango  # noqa: E402
from ska_tango_base import SKACapability  # noqa: E402
from tango.server import command, run  # noqa: E402

# Additional import
# PROTECTED REGION ID(FspCorr.additionnal_import) ENABLED START #

# tango imports

# PROTECTED REGION END #    //  FspCorr.additionnal_import

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

__all__ = ["FspCorr", "main"]


class FspCorr(SKACapability):
    """
    FspCorr TANGO device class for the prototype
    """

    # PROTECTED REGION ID(FspCorr.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspCorr.class_variable

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
        # PROTECTED REGION ID(FspCorr.init_device) ENABLED START #
        """Set state to OFF."""
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspCorr.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspCorr.always_executed_hook) ENABLED START #
        """Hook before any commands"""
        # PROTECTED REGION END #    //  FspCorr.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspCorr.delete_device) ENABLED START #
        """hook before delete device"""
        # PROTECTED REGION END #    //  FspCorr.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(dtype_in="DevState", doc_in="New state")
    def SetState(self, argin):
        # PROTECTED REGION ID(FspCorr.SetState) ENABLED START #
        """Set state to argin(DevState)."""
        self.set_state(argin)
        # PROTECTED REGION END #    //  FspCorr.SetState


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspCorr.main) ENABLED START #
    return run((FspCorr,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspCorr.main


if __name__ == "__main__":
    main()
