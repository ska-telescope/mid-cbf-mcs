# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Fsp Tango device prototype

Fsp TANGO device class for the prototype
"""

# PyTango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
import enum
from SKACapability import SKACapability
# Additional import
# PROTECTED REGION ID(Fsp.additionnal_import) ENABLED START #
# PROTECTED REGION END #    //  Fsp.additionnal_import

__all__ = ["Fsp", "main"]


class Fsp(SKACapability):
    """
    Fsp TANGO device class for the prototype

    **Properties:**

    - Device Property
    """
    # PROTECTED REGION ID(Fsp.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  Fsp.class_variable

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
        """Initialises the attributes and properties of the Fsp."""
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Fsp.init_device) ENABLED START #
        # PROTECTED REGION END #    //  Fsp.init_device

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        # PROTECTED REGION ID(Fsp.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  Fsp.always_executed_hook

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        # PROTECTED REGION ID(Fsp.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  Fsp.delete_device
    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(
        dtype_out='ConstDevString',
        doc_out="Observation state",
    )
    @DebugIt()
    def ObsState(self):
        # PROTECTED REGION ID(Fsp.ObsState) ENABLED START #
        """
        Set the observation state

        :return:'ConstDevString'
        Observation state
        """
        return ""
        # PROTECTED REGION END #    //  Fsp.ObsState

    @command(
        dtype_out='DevString',
        doc_out="returns configID for all the fspCorrSubarray",
    )
    @DebugIt()
    def getConfigID(self):
        # PROTECTED REGION ID(Fsp.getConfigID) ENABLED START #
        """
        returns configID for all the fspCorrSubarray

        :return:None
        """
        pass
        # PROTECTED REGION END #    //  Fsp.getConfigID

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Fsp module."""
    # PROTECTED REGION ID(Fsp.main) ENABLED START #
    return run((Fsp,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Fsp.main


if __name__ == '__main__':
    main()
