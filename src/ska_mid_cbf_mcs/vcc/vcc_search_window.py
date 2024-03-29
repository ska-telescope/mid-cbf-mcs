# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# """ VccSearchWindow Tango device prototype

# VccSearchWindow TANGO device class for the prototype
# """

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

from ska_tango_base.control_model import HealthState, AdminMode
from ska_tango_base import SKACapability
from ska_tango_base.commands import ResultCode

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

    class InitCommand(SKACapability.InitCommand):
        def do(self):
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            self.logger.debug("Entering InitCommand()")

            super().do()

            device = self.target

            # initialize attribute values
            device._search_window_tuning = 0
            device._enable_TDC = False
            device._number_bits = 0
            device._period_before_epoch = 0
            device._period_after_epoch = 0
            device._destination_address = ["", "", ""]
            #self.logger.warn("State() = {}".format(device.get_state()))
            message = "VccSearchWindow Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self):
        # PROTECTED REGION ID(VccSearchWindow.always_executed_hook) ENABLED START #
        """hook to be executed before any TANGO command is executed"""
        pass
        # PROTECTED REGION END #    //  VccSearchWindow.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(VccSearchWindow.delete_device) ENABLED START #
        """hook to delete resoures allocated in init_device"""
        pass
        # PROTECTED REGION END #    //  VccSearchWindow.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_searchWindowTuning(self):
        # PROTECTED REGION ID(VccSearchWindow.searchWindowTuning_read) ENABLED START #
        """Return searchWindowTuning attribute"""
        return self._search_window_tuning
        # PROTECTED REGION END #    //  VccSearchWindow.searchWindowTuning_read

    def write_searchWindowTuning(self, value):
        # PROTECTED REGION ID(VccSearchWindow.searchWindowTuning_write) ENABLED START #
        """Set searchWindowTuning attribute(int)"""
        self._search_window_tuning = value
        # PROTECTED REGION END #    //  VccSearchWindow.searchWindowTuning_write

    def read_tdcEnable(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcEnable_read) ENABLED START #
        """Return the tdcEnable attribute: Enable transient data capture"""
        return self._enable_TDC
        # PROTECTED REGION END #    //  VccSearchWindow.tdcEnable_read

    def write_tdcEnable(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcEnable_write) ENABLED START #
        """Set the tdcEnable attribute: Enable transient data capture"""
        self._enable_TDC = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcEnable_write

    def read_tdcNumBits(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcNumBits_read) ENABLED START #
        """Return the tdcEnable attribute: transient data capture bits"""
        return self._number_bits
        # PROTECTED REGION END #    //  VccSearchWindow.tdcNumBits_read

    def write_tdcNumBits(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcNumBits_write) ENABLED START #
        """set the tdcNumBits attribute: transient data capture bits"""
        self._number_bits = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcNumBits_write

    def read_tdcPeriodBeforeEpoch(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodBeforeEpoch_read) ENABLED START #
        """Return the tdcPeriodBeforeEpoch attribute: Period before the epoch for which data is saved"""
        return self._period_before_epoch
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodBeforeEpoch_read

    def write_tdcPeriodBeforeEpoch(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodBeforeEpoch_write) ENABLED START #
        """Set the tdcPeriodBeforeEpoch attribute: Period before the epoch for which data is saved"""
        self._period_before_epoch = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodBeforeEpoch_write

    def read_tdcPeriodAfterEpoch(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodAfterEpoch_read) ENABLED START #
        """Return the tdcPeriodAfterEpoch attribute: Period after the epoch for which data is saved"""
        return self._period_after_epoch
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodAfterEpoch_read

    def write_tdcPeriodAfterEpoch(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcPeriodAfterEpoch_write) ENABLED START #
        """Set the tdcPeriodAfterEpoch attribute: Period after the epoch for which data is saved"""
        self._period_after_epoch = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcPeriodAfterEpoch_write

    def read_tdcDestinationAddress(self):
        # PROTECTED REGION ID(VccSearchWindow.tdcDestinationAddress_read) ENABLED START #
        """Return the tdcDestinationAddress attribute:Destination addresses for transient data(str/json)"""
        return self._destination_address
        # PROTECTED REGION END #    //  VccSearchWindow.tdcDestinationAddress_read

    def write_tdcDestinationAddress(self, value):
        # PROTECTED REGION ID(VccSearchWindow.tdcDestinationAddress_write) ENABLED START #
        """Set the tdcDestinationAddress attribute:Destination addresses for transient data(str/json)"""
        self._destination_address = value
        # PROTECTED REGION END #    //  VccSearchWindow.tdcDestinationAddress_write

    # --------
    # Commands
    # --------

    # None

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(VccSearchWindow.main) ENABLED START #
    return run((VccSearchWindow,), args=args, **kwargs)
    # PROTECTED REGION END #    //  VccSearchWindow.main

if __name__ == '__main__':
    main()
