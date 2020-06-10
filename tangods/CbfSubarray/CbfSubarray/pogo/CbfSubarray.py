# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CbfSubarray Tango device prototype

CBFSubarray TANGO device class for the CBFSubarray prototype
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
from SKASubarray import SKASubarray
# Additional import
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #
# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


FrequencyBand = enum.IntEnum(
    value="FrequencyBand",
    names=[
        ("1", 0),
        ("2", 1),
        ("3", 2),
        ("4", 3),
        ("5a", 4),
        ("5b", 5),
    ]
)
"""Python enumerated type for FrequencyBand attribute."""


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype

    **Properties:**

    - Device Property
    """
    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    frequencyBand = attribute(
        dtype=FrequencyBand,
        access=AttrWriteType.READ_WRITE,
        label="Frequency band",
        memorized=True,
        doc="One of {1, 2, 3, 4, 5a, 5b}",
    )

    configID = attribute(
        dtype='DevULong64',
        access=AttrWriteType.READ_WRITE,
        label="config ID",
        memorized=True,
        doc="config ID",
    )

    receptors = attribute(
        dtype=('DevLong',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        display_level=DispLevel.EXPERT,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the CbfSubarray."""
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
        self._frequency_band = FrequencyBand.1
        self._config_ID = 0
        self._receptors = (0,)
        # PROTECTED REGION END #    //  CbfSubarray.init_device

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  CbfSubarray.delete_device
    # ------------------
    # Attributes methods
    # ------------------

    def read_frequencyBand(self):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_read) ENABLED START #
        """Return the frequencyBand attribute."""
        return self._frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def write_frequencyBand(self, value):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_write) ENABLED START #
        """Set the frequencyBand attribute."""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_write

    def read_configID(self):
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """Return the configID attribute."""
        return self._config_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def write_configID(self, value):
        # PROTECTED REGION ID(CbfSubarray.configID_write) ENABLED START #
        """Set the configID attribute."""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.configID_write

    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        """Return the receptors attribute."""
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(CbfSubarray.receptors_write) ENABLED START #
        """Set the receptors attribute."""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.receptors_write

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevString',
        doc_in="Scan configuration",
        dtype_out='DevString',
        doc_out="Status",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        """

        :param argin: 'DevString'
        Scan configuration

        :return:'DevString'
        Status
        """
        return ""
        # PROTECTED REGION END #    //  CbfSubarray.ConfigureScan

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the CbfSubarray module."""
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == '__main__':
    main()
