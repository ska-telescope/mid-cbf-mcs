# -*- coding: utf-8 -*-
#
# This file is part of the TmTelstateTest project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" TmTelstateTest Tango device prototype

TmTelstateTest TANGO device class for the CBF prototype
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
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["TmTelstateTest", "main"]


class TmTelstateTest:
    """
    TmTelstateTest TANGO device class for the CBF prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(TmTelstateTest.class_variable) ENABLED START #


    # PROTECTED REGION END #    //  TmTelstateTest.class_variable

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
        # PROTECTED REGION ID(TmTelstateTest.init_device) ENABLED START #
        # PROTECTED REGION END #    //  TmTelstateTest.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(TmTelstateTest.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TmTelstateTest.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(TmTelstateTest.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TmTelstateTest.delete_device

    # ------------------
    # Attributes methods
    # ------------------



    # --------
    # Commands
    # --------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main

if __name__ == '__main__':
    main()
