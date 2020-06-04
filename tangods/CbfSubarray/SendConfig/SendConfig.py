# -*- coding: utf-8 -*-
#
# This file is part of the CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: Ryan Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2020 National Research Council of Canada
# """

"""
SendConfig TANGO device class for the prototype
"""

# PyTango imports
import PyTango
from PyTango import DebugIt
from PyTango import DeviceProxy
from PyTango.server import run
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command
from PyTango.server import device_property
from PyTango import AttrQuality, DispLevel, DevState
from PyTango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(SendConfig.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  SendConfig.additionnal_import

__all__ = ["SendConfig", "main"]


class SendConfig(SKACapability):
    """
    SendConfig TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(SendConfig.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  SendConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------
    SubarrayAddress = device_property(
        dtype='str'
    )
    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(SendConfig.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self.subarray_proxy = DeviceProxy(self.SubarrayAddress),
        # initialize attribute values

        self.set_state(PyTango.DevState.ON)
        # PROTECTED REGION END #    //  SendConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(SendConfig.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SendConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(SendConfig.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SendConfig.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command()
    def SendConfig(self):
        f = open(file_path + "/config.json")
        subarray_proxy = DeviceProxy(self.SubarrayAddress)
        subarray_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        # PROTECTED REGION ID(SendConfig.SetState) ENABLED START #
        # PROTECTED REGION END #    // SendConfig.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(SendConfig.main) ENABLED START #
    return run((SendConfig,), args=args, **kwargs)
    # PROTECTED REGION END #    //  SendConfig.main

if __name__ == '__main__':
    main()
