# -*- coding: utf-8 -*-
#
# This file is part of the CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: Ryan Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2020 National Research Council of Canada
"""

"""
CbfSubarrayPssConfig Tango device prototype

CbfSubarrayPssConfig TANGO device class for the prototype
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
# PROTECTED REGION ID(CbfSubarrayPssConfig.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  CbfSubarrayPssConfig.additionnal_import

__all__ = ["CbfSubarrayPssConfig", "main"]


class CbfSubarrayPssConfig(SKACapability):
    """
    SearchWindow TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarrayPssConfig.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarrayPssConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    PssEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ_WRITE,
        label="Enable transient data capture",
        doc="Enable transient data capture"
    )

    PssConfig = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Fst PSS Configuration",
        doc="Fst PSS Configuration JSON"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(CbfSubarrayPssConfig.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)

        # initialize attribute values
        self._enable_Pss = False
        self._pss_Config = {}  # this is interpreted as a JSON object

        self.set_state(PyTango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_PssEnable(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_PssEnable) ENABLED START #
        return self._enable_Pss
        # PROTECTED REGION END #    // CbfSubarrayPssConfig.read_PssEnable

    def write_PssEnable(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_PssEnable) ENABLED START #
        self._enable_Pss = value
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_PssEnable

    def read_PssConfig(self):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_PssConfig) ENABLED START #
        return json.dumps(self._pss_Config)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_PssConfig

    def write_PssConfig(self, value):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.write_PssConfig) ENABLED START #
        # if value is not valid JSON, the exception is caught by CbfSubarray.ConfigureScan()
        self._pss_Config = json.loads(value)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.write_PssConfig

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPssConfig.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarrayPssConfig.main) ENABLED START #
    return run((CbfSubarrayPssConfig,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarrayPssConfig.main

if __name__ == '__main__':
    main()
