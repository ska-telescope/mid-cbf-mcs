# -*- coding: utf-8 -*-
#
# This file is part of the CbfConfigurationPSS project
#
#
#
# Distributed under the terms of the none license.
# See LICENSE.txt for more info.

""" CbfConfigurationPSS

A generic base device for Observations for SKA.
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
from skabase.SKASubarray.SKASubarray import SKASubarray
# Additional import
# PROTECTED REGION ID(CbfConfigurationPSS.additionnal_import) ENABLED START #
# PROTECTED REGION END #    //  CbfConfigurationPSS.additionnal_import

__all__ = ["CbfConfigurationPSS", "main"]


class CbfConfigurationPSS(SKASubarray):
    """
    A generic base device for Observations for SKA.
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfConfigurationPSS.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfConfigurationPSS.class_variable

    # -----------------
    # Device Properties
    # -----------------





    # ----------
    # Attributes
    # ----------

    obsState = attribute(
        dtype='DevEnum',
        doc="Observing State",
        enum_labels=["IDLE", "CONFIGURING", "READY", "SCANNING", "PAUSED", "ABORTED", "FAULT", ],
    )

    obsMode = attribute(
        dtype='DevEnum',
        doc="Observing Mode",
        enum_labels=["IDLE", "IMAGING", "PULSAR-SEARCH", "PULSAR-TIMING", "DYNAMIC-SPECTRUM", "TRANSIENT-SEARCH", "VLBI", "CALIBRATION", ],
    )

    configurationProgress = attribute(
        dtype='uint16',
        unit="%",
        max_value=100,
        min_value=0,
        doc="Percentage configuration progress",
    )

    configurationDelayExpected = attribute(
        dtype='uint16',
        unit="seconds",
        doc="Configuration delay expected in seconds",
    )










    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKABaseDevice.init_device(self)
        # PROTECTED REGION ID(CbfConfigurationPSS.init_device) ENABLED START #
        # PROTECTED REGION END #    //  CbfConfigurationPSS.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfConfigurationPSS.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfConfigurationPSS.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfConfigurationPSS.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfConfigurationPSS.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_obsState(self):
        # PROTECTED REGION ID(CbfConfigurationPSS.obsState_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CbfConfigurationPSS.obsState_read

    def read_obsMode(self):
        # PROTECTED REGION ID(CbfConfigurationPSS.obsMode_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CbfConfigurationPSS.obsMode_read

    def read_configurationProgress(self):
        # PROTECTED REGION ID(CbfConfigurationPSS.configurationProgress_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CbfConfigurationPSS.configurationProgress_read

    def read_configurationDelayExpected(self):
        # PROTECTED REGION ID(CbfConfigurationPSS.configurationDelayExpected_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  CbfConfigurationPSS.configurationDelayExpected_read


    # --------
    # Commands
    # --------

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfConfigurationPSS.main) ENABLED START #
    return run((CbfConfigurationPSS,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfConfigurationPSS.main

if __name__ == '__main__':
    main()
