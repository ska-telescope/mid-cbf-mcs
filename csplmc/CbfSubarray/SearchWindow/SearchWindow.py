# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" SearchWindow Tango device prototype

SearchWindow TANGO device class for the prototype
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
# PROTECTED REGION ID(SearchWindow.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  SearchWindow.additionnal_import

__all__ = ["SearchWindow", "main"]


class SearchWindow(SKACapability):
    """
    SearchWindow TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(SearchWindow.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  SearchWindow.class_variable

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
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination addresses for transient data"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(SearchWindow.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        # initialize attribute values
        self._search_window_tuning = 0
        self._enable_TDC = False
        self._number_bits = 0
        self._period_before_epoch = 0
        self._period_after_epoch = 0
        self._destination_address = {}  # this is interpreted as a JSON object

        self.set_state(PyTango.DevState.DISABLE)
        # PROTECTED REGION END #    //  SearchWindow.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(SearchWindow.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SearchWindow.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(SearchWindow.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SearchWindow.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_searchWindowTuning(self):
        # PROTECTED REGION ID(SearchWindow.searchWindowTuning_read) ENABLED START #
        return self._search_window_tuning
        # PROTECTED REGION END #    //  SearchWindow.searchWindowTuning_read

    def write_searchWindowTuning(self, value):
        # PROTECTED REGION ID(SearchWindow.searchWindowTuning_write) ENABLED START #
        self._search_window_tuning = value
        # PROTECTED REGION END #    //  SearchWindow.searchWindowTuning_write

    def read_tdcEnable(self):
        # PROTECTED REGION ID(SearchWindow.tdcEnable_read) ENABLED START #
        return self._enable_TDC
        # PROTECTED REGION END #    //  SearchWindow.tdcEnable_read

    def write_tdcEnable(self, value):
        # PROTECTED REGION ID(SearchWindow.tdcEnable_write) ENABLED START #
        self._enable_TDC = value
        # PROTECTED REGION END #    //  SearchWindow.tdcEnable_write

    def read_tdcNumBits(self):
        # PROTECTED REGION ID(SearchWindow.tdcNumBits_read) ENABLED START #
        return self._number_bits
        # PROTECTED REGION END #    //  SearchWindow.tdcNumBits_read

    def write_tdcNumBits(self, value):
        # PROTECTED REGION ID(SearchWindow.tdcNumBits_write) ENABLED START #
        self._number_bits = value
        # PROTECTED REGION END #    //  SearchWindow.tdcNumBits_write

    def read_tdcPeriodBeforeEpoch(self):
        # PROTECTED REGION ID(SearchWindow.tdcPeriodBeforeEpoch_read) ENABLED START #
        return self._period_before_epoch
        # PROTECTED REGION END #    //  SearchWindow.tdcPeriodBeforeEpoch_read

    def write_tdcPeriodBeforeEpoch(self, value):
        # PROTECTED REGION ID(SearchWindow.tdcPeriodBeforeEpoch_write) ENABLED START #
        self._period_before_epoch = value
        # PROTECTED REGION END #    //  SearchWindow.tdcPeriodBeforeEpoch_write

    def read_tdcPeriodAfterEpoch(self):
        # PROTECTED REGION ID(SearchWindow.tdcPeriodAfterEpoch_read) ENABLED START #
        return self._period_after_epoch
        # PROTECTED REGION END #    //  SearchWindow.tdcPeriodAfterEpoch_read

    def write_tdcPeriodAfterEpoch(self, value):
        # PROTECTED REGION ID(SearchWindow.tdcPeriodAfterEpoch_write) ENABLED START #
        self._period_after_epoch = value
        # PROTECTED REGION END #    //  SearchWindow.tdcPeriodAfterEpoch_write

    def read_tdcDestinationAddress(self):
        # PROTECTED REGION ID(SearchWindow.tdcDestinationAddress_read) ENABLED START #
        return json.dumps(self._destination_address)
        # PROTECTED REGION END #    //  SearchWindow.tdcDestinationAddress_read

    def write_tdcDestinationAddress(self, value):
        # PROTECTED REGION ID(SearchWindow.tdcDestinationAddress_write) ENABLED START #
        # if value is not valid JSON, the exception is caught by CbfSubarray.ConfigureScan()
        self._destination_address = json.loads(value)
        # PROTECTED REGION END #    //  SearchWindow.tdcDestinationAddress_write

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(SearchWindow.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  SearchWindow.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(SearchWindow.main) ENABLED START #
    return run((SearchWindow,), args=args, **kwargs)
    # PROTECTED REGION END #    //  SearchWindow.main

if __name__ == '__main__':
    main()
