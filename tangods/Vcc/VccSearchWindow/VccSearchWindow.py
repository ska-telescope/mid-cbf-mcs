# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

""" VccSearchWindow Tango device prototype

VccSearchWindow TANGO device class for the prototype
"""

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(VccSearchWindow.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from skabase.control_model import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  VccSearchWindow.additionnal_import

__all__ = ["VccSearchWindow", "main"]


class VccSearchWindow(SKACapability):
    """
    VccSearchWindow TANGO device class for the prototype
    """
    # PROTECTED REGION ID(VccSearchWindow.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  VccSearchWindow.class_variable

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

    tdcEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ_WRITE,
        label="Enable transient data capture",
        doc="Enable transient data capture"
    )

    tdcNumBits = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Number of bits",
        doc="Number of bits"
    )

    tdcPeriodBeforeEpoch = attribute(
        dtype='uint',
        access=AttrWriteType.READ_WRITE,
        label="Period before the epoch",
        doc="Period before the epoch for which data is saved"
    )

    tdcPeriodAfterEpoch = attribute(
        dtype='uint',
        access=AttrWriteType.READ_WRITE,
        label="Period after the epoch",
        doc="Period after the epoch for which data is saved"
    )

    tdcDestinationAddress = attribute(
        dtype=('str',),
        max_dim_x=3,
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination addresses (MAC address, IP address, port) for transient data"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(VccSearchWindow.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # initialize attribute values
        self._search_window_tuning = 0
        self._enable_TDC = False
        self._number_bits = 0
        self._period_before_epoch = 0
        self._period_after_epoch = 0
        self._destination_address = ["", "", ""]

        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  VccSearchWindow.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccSearchWindow.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  VccSearchWindow.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccSearchWindow.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  VccSearchWindow.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_searchWindowTuning(self):
        # PROTECTED REGION ID(VccSearchWindow.searchWindowTuning_read) ENABLED START #
        return self._search_window_tuning
        # PROTECTED REGION END #    //  VccSearchWindow.searchWindowTuning_read

    def write_searchWindowTuning(self, value):
        # PROTECTED REGION ID(VccSearchWindow.searchWindowTuning_write) ENABLED START #
        self._search_window_tuning = value
        # PROTECTED REGION END #    //  VccSearchWindow.searchWindowTuning_write

    def read_tdcEnable(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcEnable_read) ENABLED START #
        return self._enable_TDC
        # PROTECTED REGION END #    //  VccSearchWindow.tdcEnable_read

    def write_tdcEnable(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcEnable_write) ENABLED START #
        self._enable_TDC = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcEnable_write

    def read_tdcNumBits(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcNumBits_read) ENABLED START #
        return self._number_bits
        # PROTECTED REGION END #    //  VccSearchWindow.tdcNumBits_read

    def write_tdcNumBits(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcNumBits_write) ENABLED START #
        self._number_bits = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcNumBits_write

    def read_tdcPeriodBeforeEpoch(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodBeforeEpoch_read) ENABLED START #
        return self._period_before_epoch
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodBeforeEpoch_read

    def write_tdcPeriodBeforeEpoch(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodBeforeEpoch_write) ENABLED START #
        self._period_before_epoch = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodBeforeEpoch_write

    def read_tdcPeriodAfterEpoch(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodAfterEpoch_read) ENABLED START #
        return self._period_after_epoch
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodAfterEpoch_read

    def write_tdcPeriodAfterEpoch(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodAfterEpoch_write) ENABLED START #
        self._period_after_epoch = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodAfterEpoch_write

    def read_tdcDestinationAddress(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcDestinationAddress_read) ENABLED START #
        return self._destination_address
        # PROTECTED REGION END #    //  VccSearchWindow.tdcDestinationAddress_read

    def write_tdcDestinationAddress(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcDestinationAddress_write) ENABLED START #
        self._destination_address = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcDestinationAddress_write

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(VccSearchWindow.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  VccSearchWindow.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(VccSearchWindow.main) ENABLED START #
    return run((VccSearchWindow,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccSearchWindow.main

if __name__ == '__main__':
    main()
