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

__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(SKACapability):
    """
    Fsp TANGO device class for the prototype

    **Properties:**

    - Device Property
    """

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

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the FspCorrSubarray."""
        SKACapability.init_device(self)

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        pass

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        pass
    # ------------------
    # Attributes methods
    # ------------------

    def read_fspChannelOffset(self):
        return 0

    def write_fspChannelOffset(self, value):
        pass

    # --------
    # Commands
    # --------

    @command(
        dtype_out='ConstDevString',
        doc_out="Observation state",
    )
    @DebugIt()
    def ObsState(self):
        return ""

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the FspCorrSubarray module."""
    return run((FspCorrSubarray,), args=args, **kwargs)


if __name__ == '__main__':
    main()
