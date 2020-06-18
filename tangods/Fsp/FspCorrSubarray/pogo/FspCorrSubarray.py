# -*- coding: utf-8 -*-
#
# This file is part of the FspCorrSubarray project
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
# PROTECTED REGION ID(FspCorrSubarray.additionnal_import) ENABLED START #
# PROTECTED REGION END #    //  FspCorrSubarray.additionnal_import

__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(SKACapability):
    """
    Fsp TANGO device class for the prototype

    **Properties:**

    - Device Property
    """
    # PROTECTED REGION ID(FspCorrSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspCorrSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    fspChannelOffset = attribute(
        dtype='DevLong',
        access=AttrWriteType.READ_WRITE,
        label="fspChannelOffset",
        doc="fsp Channel offset, integer, multiple of 14480",
    )

    outputLinkMap = attribute(
        dtype=(('DevULong64',),),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=2, max_dim_y=40,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the FspCorrSubarray."""
        SKACapability.init_device(self)
        # PROTECTED REGION ID(FspCorrSubarray.init_device) ENABLED START #
        self._fsp_channel_offset = 0
        self._output_link_map = ((0,),)
        # PROTECTED REGION END #    //  FspCorrSubarray.init_device

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        # PROTECTED REGION ID(FspCorrSubarray.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  FspCorrSubarray.always_executed_hook

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        # PROTECTED REGION ID(FspCorrSubarray.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  FspCorrSubarray.delete_device
    # ------------------
    # Attributes methods
    # ------------------

    def read_fspChannelOffset(self):
        # PROTECTED REGION ID(FspCorrSubarray.fspChannelOffset_read) ENABLED START #
        """Return the fspChannelOffset attribute."""
        return self._fsp_channel_offset
        # PROTECTED REGION END #    //  FspCorrSubarray.fspChannelOffset_read

    def write_fspChannelOffset(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.fspChannelOffset_write) ENABLED START #
        """Set the fspChannelOffset attribute."""
        pass
        # PROTECTED REGION END #    //  FspCorrSubarray.fspChannelOffset_write

    def read_outputLinkMap(self):
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_read) ENABLED START #
        """Return the outputLinkMap attribute."""
        return self._output_link_map
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_read

    def write_outputLinkMap(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_write) ENABLED START #
        """Set the outputLinkMap attribute."""
        pass
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_write

    # --------
    # Commands
    # --------

    @command(
        dtype_out='ConstDevString',
        doc_out="Observation state",
    )
    @DebugIt()
    def ObsState(self):
        # PROTECTED REGION ID(FspCorrSubarray.ObsState) ENABLED START #
        """
        Set the observation state

        :return:'ConstDevString'
        Observation state
        """
        return ""
        # PROTECTED REGION END #    //  FspCorrSubarray.ObsState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the FspCorrSubarray module."""
    # PROTECTED REGION ID(FspCorrSubarray.main) ENABLED START #
    return run((FspCorrSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspCorrSubarray.main


if __name__ == '__main__':
    main()
