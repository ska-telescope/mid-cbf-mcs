# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" VccTransientDataCapture Tango device prototype

VccTransientDataCapture TANGO device class for the prototype
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
# PROTECTED REGION ID(VccTransientDataCapture.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  VccTransientDataCapture.additionnal_import

__all__ = ["VccTransientDataCapture", "main"]


class VccTransientDataCapture(SKACapability):
    """
    VccTransientDataCapture TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(VccTransientDataCapture.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  VccTransientDataCapture.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    searchWindowTuning = attribute(
        dtype='uint64',
        access=AttrWriteType.READ_WRITE,
        label="Search window tuning",
        doc="Search window tuning"
    )

    enableTDC = attribute(
        dtype='bool',
        access=AttrWriteType.READ_WRITE,
        label="Enable transient data capture",
        doc="Enable transient data capture"
    )

    numberBits = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Number of bits",
        doc="Number of bits"
    )

    periodBeforeEpoch = attribute(
        dtype='uint',
        access=AttrWriteType.READ_WRITE,
        label="Period before the epoch",
        doc="Period before the epoch for which data is saved"
    )

    periodAfterEpoch = attribute(
        dtype='uint',
        access=AttrWriteType.READ_WRITE,
        label="Period after the epoch",
        doc="Period after the epoch for which data is saved"
    )

    destinationAddress = attribute(
        dtype=('str',),
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination address (MAC address, IP address, port) for transient data"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(VccTransientDataCapture.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        # initialize attribute values
        self._search_window_tuning = 0
        self._enable_TDC = False
        self._number_bits = 0
        self._period_before_epoch = 0
        self._period_after_epoch = 0
        self._destination_address = ("", "", "")

        self.set_state(PyTango.DevState.DISABLE)
        # PROTECTED REGION END #    //  VccTransientDataCapture.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccTransientDataCapture.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  VccTransientDataCapture.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccTransientDataCapture.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  VccTransientDataCapture.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_searchWindowTuning(self):
        # PROTECTED REGION ID(VccTransientDataCapture.searchWindowTuning_read) ENABLED START #
        return self._search_window_tuning
        # PROTECTED REGION END #    //  VccTransientDataCapture.searchWindowTuning_read

    def write_searchWindowTuning(self, value):
        # PROTECTED REGION ID(VccTransientDataCapture.searchWindowTuning_write) ENABLED START #
        self._search_window_tuning = value
        # PROTECTED REGION END #    //  VccTransientData.searchWindowTuning_write

    def read_enableTDC(self):
        # PROTECTED REGION ID(VccTransientDataCapture.enableTDC_read) ENABLED START #
        return self._enable_TDC
        # PROTECTED REGION END #    //  VccTransientDataCapture.enableTDC_read

    def write_enableTDC(self, value):
        # PROTECTED REGION ID(VccTransientDataCapture.enableTDC_write) ENABLED START #
        self._enable_TDC = value
        # PROTECTED REGION END #    //  VccTransientData.enableTDC_write

    def read_numberBits(self):
        # PROTECTED REGION ID(VccTransientDataCapture.numberBits_read) ENABLED START #
        return self._number_bits
        # PROTECTED REGION END #    //  VccTransientDataCapture.numberBits_read

    def write_numberBits(self, value):
        # PROTECTED REGION ID(VccTransientDataCapture.numberBits_write) ENABLED START #
        self._number_bits = value
        # PROTECTED REGION END #    //  VccTransientData.numberBits_write

    def read_periodBeforeEpoch(self):
        # PROTECTED REGION ID(VccTransientDataCapture.periodBeforeEpoch_read) ENABLED START #
        return self._period_before_epoch
        # PROTECTED REGION END #    //  VccTransientDataCapture.periodBeforeEpoch_read

    def write_periodBeforeEpoch(self, value):
        # PROTECTED REGION ID(VccTransientDataCapture.periodBeforeEpoch_write) ENABLED START #
        self._period_before_epoch = value
        # PROTECTED REGION END #    //  VccTransientData.periodBeforeEpoch_write

    def read_periodAfterEpoch(self):
        # PROTECTED REGION ID(VccTransientDataCapture.periodAfterEpoch_read) ENABLED START #
        return self._period_after_epoch
        # PROTECTED REGION END #    //  VccTransientDataCapture.periodAfterEpoch_read

    def write_periodAfterEpoch(self, value):
        # PROTECTED REGION ID(VccTransientDataCapture.periodAfterEpoch_write) ENABLED START #
        self._period_after_epoch = value
        # PROTECTED REGION END #    //  VccTransientData.periodAfterEpoch_write

    def read_destinationAddress(self):
        # PROTECTED REGION ID(VccTransientDataCapture.destinationAddress_read) ENABLED START #
        return self._destination_address
        # PROTECTED REGION END #    //  VccTransientDataCapture.destinationAddress_read

    def write_destinationAddress(self, value):
        # PROTECTED REGION ID(VccTransientDataCapture.destinationAddress_write) ENABLED START #
        self._destination_address = value
        # PROTECTED REGION END #    //  VccTransientData.destinationAddress_write

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(VccTransientDataCapture.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  VccTransientDataCapture.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(VccTransientDataCapture.main) ENABLED START #
    return run((VccTransientDataCapture,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccTransientDataCapture.main

if __name__ == '__main__':
    main()
