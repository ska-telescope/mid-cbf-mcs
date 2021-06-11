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
# VccBand5 TANGO device class for the prototype
# """

import os
import sys
import json

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType

# SKA import

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from ska_tango_base.control_model import HealthState, AdminMode
from ska_tango_base import SKACapability
from ska_tango_base.commands import ResultCode

__all__ = ["VccBand5", "main"]


class VccBand5(SKACapability):
    """
    VccBand5 TANGO device class for the prototype
    """
    # PROTECTED REGION ID(VccBand5.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  VccBand5.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    class InitCommand(SKACapability.InitCommand):

        def do(self):
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            super().do()

            device = self.target

            #self.logger.warn("State() = {}".format(device.get_state()))
            message = "VccBand5 Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccBand5.always_executed_hook) ENABLED START #
        """hook to be executed before commands"""
        pass
        # PROTECTED REGION END #    //  VccBand5.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccBand5.delete_device) ENABLED START #
        """hook to delete device"""
        pass
        # PROTECTED REGION END #    //  VccBand5.delete_device

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
    # PROTECTED REGION ID(VccBand5.main) ENABLED START #
    return run((VccBand5,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccBand5.main

if __name__ == '__main__':
    main()
