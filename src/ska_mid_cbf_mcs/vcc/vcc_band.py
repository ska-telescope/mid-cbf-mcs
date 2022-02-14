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

# """ VccBand Tango device prototype

# VccBand TANGO device class for the prototype
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
# PROTECTED REGION ID(VccBand.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))

from ska_tango_base.control_model import HealthState, AdminMode, PowerMode
from ska_tango_base.base.base_device import SKABaseDevice 
from ska_tango_base.commands import ResultCode

# PROTECTED REGION END #    //  VccBand.additionnal_import

__all__ = ["VccBand", "main"]


class VccBand(SKABaseDevice):
    """
    VccBand TANGO device class for the prototype
    """
    # PROTECTED REGION ID(VccBand.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  VccBand.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    # TODO: implement component manager

    def init_command_objects(self):
        """Register command objects (handlers) for this device's commands."""
        super().init_command_objects()

    class InitCommand(SKABaseDevice.InitCommand):
        
        def do(self):
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
            :rtype: (ResultCode, str)
            """
            self.target.component_manager.component_power_mode_changed(PowerMode.OFF)
            return super().do()

    class OnCommand(SKABaseDevice.OnCommand):
        
        def do(self):
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
            :rtype: (ResultCode, str)
            """
            self.target.component_power_mode_changed(PowerMode.ON)
            return (ResultCode.OK, "On completed OK")
    
    class OffCommand(SKABaseDevice.OffCommand):
        
        def do(self):
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
            :rtype: (ResultCode, str)
            """
            self.target.component_power_mode_changed(PowerMode.OFF)
            return (ResultCode.OK, "Off completed OK")

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccBand.always_executed_hook) ENABLED START #
        """hook to be executed before commands"""
        pass
        # PROTECTED REGION END #    //  VccBand.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccBand.delete_device) ENABLED START #
        """hook to delete device"""
        pass
        # PROTECTED REGION END #    //  VccBand.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    # None

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(VccBand.main) ENABLED START #
    return run((VccBand,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccBand.main

if __name__ == '__main__':
    main()
