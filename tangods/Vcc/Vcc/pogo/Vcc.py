# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Vcc Tango device prototype

Vcc TANGO device class for the prototype
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
# PROTECTED REGION ID(Vcc.additionnal_import) ENABLED START #
# PROTECTED REGION END #    //  Vcc.additionnal_import

__all__ = ["Vcc", "main"]


class Vcc(SKACapability):
    """
    Vcc TANGO device class for the prototype

    **Properties:**

    - Device Property
    """
    # PROTECTED REGION ID(Vcc.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  Vcc.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    receptorID = attribute(
        dtype='DevLong',
        label="Receptor ID",
        doc="Receptor ID",
    )

    subarrayMembership = attribute(
        dtype='DevLong',
        label="Subarray membership",
        doc="Subarray membership",
    )

    scanID = attribute(
        dtype='DevULong',
        access=AttrWriteType.READ_WRITE,
        label="scanID",
        doc="scan ID",
    )

    configID = attribute(
        dtype='DevString',
        access=AttrWriteType.READ_WRITE,
        label="config ID",
        doc="config ID",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the Vcc."""
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Vcc.init_device) ENABLED START #
        self._receptor_id = 0
        self._subarray_membership = 0
        # PROTECTED REGION END #    //  Vcc.init_device

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        # PROTECTED REGION ID(Vcc.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  Vcc.delete_device
    # ------------------
    # Attributes methods
    # ------------------

    def read_receptorID(self):
        # PROTECTED REGION ID(Vcc.receptorID_read) ENABLED START #
        """Return the receptorID attribute."""
        return self._receptor_id
        # PROTECTED REGION END #    //  Vcc.receptorID_read

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Vcc.subarrayMembership_read) ENABLED START #
        """Return the subarrayMembership attribute."""
        return self._subarray_membership
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_read

    def read_scanID(self):
        # PROTECTED REGION ID(Vcc.scanID_read) ENABLED START #
        """Return the scanID attribute."""
        return self._scan_id
        # PROTECTED REGION END #    //  Vcc.scanID_read

    def write_scanID(self, value):
        # PROTECTED REGION ID(Vcc.scanID_write) ENABLED START #
        """Set the scanID attribute."""
        self._scan_id=value
        # PROTECTED REGION END #    //  Vcc.scanID_write

    def read_configID(self):
        # PROTECTED REGION ID(Vcc.configID_read) ENABLED START #
        """Return the configID attribute."""
        return self._config_id
        # PROTECTED REGION END #    //  Vcc.configID_read

    def write_configID(self, value):
        # PROTECTED REGION ID(Vcc.configID_write) ENABLED START #
        """Set the configID attribute."""
        self._config_id = value
        # PROTECTED REGION END #    //  Vcc.configID_write

    # --------
    # Commands
    # --------

    @command(
        dtype_out='ConstDevString',
        doc_out="Observation state",
    )
    @DebugIt()
    def ObsState(self):
        # PROTECTED REGION ID(Vcc.ObsState) ENABLED START #
        """
        Set the observation state

        :return:'ConstDevString'
        Observation state
        """
        return ""
        # PROTECTED REGION END #    //  Vcc.ObsState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Vcc module."""
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main


if __name__ == '__main__':
    main()
