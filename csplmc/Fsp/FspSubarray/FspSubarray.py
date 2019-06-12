# -*- coding: utf-8 -*-
#
# This file is part of the FspSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" FspSubarray Tango device prototype

FspSubarray TANGO device class for the FspSubarray prototype
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
# PROTECTED REGION ID(FspSubarray.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState
from skabase.SKASubarray.SKASubarray import SKASubarray
# PROTECTED REGION END #    //  FspSubarray.additionnal_import

__all__ = ["FspSubarray", "main"]


class FspSubarray(SKASubarray):
    """
    FspSubarray TANGO device class for the FspSubarray prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(FspSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------


    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    frequencySliceID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Frequency slice ID",
        doc="Frequency slice ID"
    )

    bandwidth = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Bandwidth to be correlated",
        doc="Bandwidth to be correlated is <Full Bandwidth>/2^bandwidth"
    )

    zoomWindowTuning = attribute(
        dtype='uint',
        access=AttrWriteType.READ_WRITE,
        label="Zoom window tuning (kHz)",
        doc="Zoom window tuning (kHz)"
    )

    integrationTime = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Integration time (ms)",
        doc="Integration time (ms)"
    )

    channelAveragingMap = attribute(
        dtype='uint16',
        max_dim_x=2,
        max_dim_y=20,
        access=AttrWriteType.READ_WRITE,
        label="Channel averaging map",
        doc="Channel averaging map"
    )

    destinationAddress = attribute(
        dtype=('str',),
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination addresses (MAC address, IP address, port) for visibilities"
    )

    delayModel = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Delay model coefficients",
        doc="Delay model coefficients, given as a JSON object"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(FspSubarray.init_device) ENABLED START #
        # initialize attribute values
        self._receptors = []
        self._frequency_band = 0
        self._frequency_slice_ID = 0
        self._bandwidth = 0
        self._zoom_window_tuning = 0
        self._integration_time = 0
        self._channel_averaging_map = [[0, 0] for i in range(20)]
        self._destination_address = ("", "", "")
        self._delay_model = ""
        # PROTECTED REGION END #    //  FspSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspSubarray.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self):
        # PROTECTED REGION ID(FspSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  FspSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(FspSubarray.receptors_write) ENABLED START #
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  FspSubarray.receptors_write

    def read_frequencyBand(self):
        # PROTECTED REGION ID(FspSubarray.frequencyBand_read) ENABLED START #
        return self._frequency_band
        # PROTECTED REGION END #    //  FspSubarray.frequencyBand_read

    def write_frequencyBand(self, value):
        # PROTECTED REGION ID(FspSubarray.frequencyBand_write) ENABLED START #
        self._frequency_band = value
        # PROTECTED REGION END #    //  FspSubarray.frequencyBand_write

    def read_frequencySliceID(self):
        # PROTECTED REGION ID(FspSubarray.frequencySliceID_read) ENABLED START #
        return self._frequency_slice_ID
        # PROTECTED REGION END #    //  FspSubarray.frequencySliceID_read

    def write_frequencySliceID(self, value):
        # PROTECTED REGION ID(FspSubarray.frequencySliceID_write) ENABLED START #
        self._frequency_slice_ID = value
        # PROTECTED REGION END #    //  FspSubarray.frequencySliceID_write

    def read_bandwidth(self):
        # PROTECTED REGION ID(FspSubarray.bandwidth_read) ENABLED START #
        return self._bandwidth
        # PROTECTED REGION END #    //  FspSubarray.bandwidth_read

    def write_bandwidth(self, value):
        # PROTECTED REGION ID(FspSubarray.bandwidth_write) ENABLED START #
        self._bandwidth = value
        # PROTECTED REGION END #    //  FspSubarray.bandwidth_write

    def read_zoomWindowTuning(self):
        # PROTECTED REGION ID(FspSubarray.zoomWindowTuning_read) ENABLED START #
        return self._zoom_window_tuning
        # PROTECTED REGION END #    //  FspSubarray.zoomWindowTuning_read

    def write_zoomWindowTuning(self, value):
        # PROTECTED REGION ID(FspSubarray.zoomWindowTuning_write) ENABLED START #
        self._zoom_window_tuning = value
        # PROTECTED REGION END #    //  FspSubarray.zoomWindowTuning_write

    def read_integrationTime(self):
        # PROTECTED REGION ID(FspSubarray.integrationTime_read) ENABLED START #
        return self._integration_time
        # PROTECTED REGION END #    //  FspSubarray.integrationTime_read

    def write_integrationTime(self, value):
        # PROTECTED REGION ID(FspSubarray.integrationTime_write) ENABLED START #
        self._integration_time = value
        # PROTECTED REGION END #    //  FspSubarray.integrationTime_write

    def read_channelAveragingMap(self):
        # PROTECTED REGION ID(FspSubarray.channelAveragingMap_read) ENABLED START #
        return self._channel_averaging_map
        # PROTECTED REGION END #    //  FspSubarray.channelAveragingMap_read

    def write_channelAveragingMap(self, value):
        # PROTECTED REGION ID(FspSubarray.channelAveragingMap_write) ENABLED START #
        self._channel_averaging_map = value
        # PROTECTED REGION END #    //  FspSubarray.channelAveragingMap_write

    def read_destinationAddress(self):
        # PROTECTED REGION ID(FspSubarray.destinationAddress_read) ENABLED START #
        return self._destination_address
        # PROTECTED REGION END #    //  FspSubarray.destinationAddress_read

    def write_destinationAddress(self, value):
        # PROTECTED REGION ID(FspSubarray.destinationAddress_write) ENABLED START #
        self._destination_address = value
        # PROTECTED REGION END #    //  FspSubarray.destinationAddress_write

    def read_delayModel(self):
        # PROTECTED REGION ID(FspSubarray.delayModel_read) ENABLED START #
        return self._delay_model
        # PROTECTED REGION END #    //  FspSubarray.delayModel_read

    def write_delayModel(self, value):
        # PROTECTED REGION ID(FspSubarray.delayModel_write) ENABLED START #
        self._delay_model = value
        # PROTECTED REGION END #    //  FspSubarray.delayModel_write


    # --------
    # Commands
    # --------

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    @DebugIt()
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(FspSubarray.AddReceptors) ENABLED START #
        for receptorID in argin:
            self._receptors.append(receptorID)
        # PROTECTED REGION END #    //  FspSubarray.AddReceptors

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(FspSubarray.RemoveReceptors) ENABLED START #
        for receptorID in argin:
            self._receptors.remove(receptorID)
        # PROTECTED REGION END #    //  FspSubarray.RemoveReceptors

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(FspSubarray.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspSubarray.RemoveAllReceptors

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspSubarray.main) ENABLED START #
    return run((FspSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspSubarray.main

if __name__ == '__main__':
    main()
