# -*- coding: utf-8 -*-
#
# This file is part of the CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: Ryan Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2020 National Research Council of Canada
"""

# CbfSubarrayCorrConfig Tango device prototype
# CbfSubarrayCorrConfig TANGO device class for the prototype

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device, DeviceMeta
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(CbfSubarrayCorrConfig.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState, const
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  CbfSubarrayCorrConfig.additionnal_import

__all__ = ["CbfSubarrayCorrConfig", "main"]


class CbfSubarrayCorrConfig(SKACapability):

    # SearchWindow TANGO device class for the prototype

    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarrayCorrConfig.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------

    FSP = device_property(
        dtype=('str',)
    )

    FspSubarray = device_property(
        dtype=('str',)
    )

    CbfMasterAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Master",
        default_value="mid_csp_cbf/sub_elt/master"
    )

    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
    )

    frequencySliceID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
    )

    corrBandwidth = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
    )

    zoomWindowTuning = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
    )

    integrationTime = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,

    )

    channelAveragingMap = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
    )

    CorrConfig = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Fst Corr Configuration",
        doc="Fst Corr Configuration JSON"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # initialize attribute values
        self._fsp_id = 0
        self._corr_config = {}  # this is interpreted as a JSON object
        self._frequency_slice_id = 0
        self._corr_bandwidth = 0
        self._zoom_window_tuning = 0
        self._receptors = []
        self._integration_time = 0
        self._channel_averaging_map = {}

        # Getting Proxies for FSP and FSP Subarrays
        self._proxy_cbf_master = tango.DeviceProxy(self.CbfMasterAddress)
        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )
        self._proxies_fsp = [*map(tango.DeviceProxy, list(self.FSP)[:int(self._master_max_capabilities["FSP"])])]
        self._proxies_fsp_subarray = [*map(tango.DeviceProxy, list(self.FspSubarray))]

        self._obs_state = ObsState.IDLE.value
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.delete_device

    def is_configure_scan_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    def __raise_configure_scan_fatal_error(self, msg):
        self.logger.error(msg)
        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                       tango.ErrSeverity.ERR)

    # ------------------
    # Attributes methods
    # ------------------
    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_receptors) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_receptors

    def write_receptors(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_receptors) ENABLED START #
        self._receptors = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_receptors

    def read_frequencySliceID(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_fspID) ENABLED START #
        return self._frequency_slice_id
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_fspID

    def write_frequencySliceID(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_fspID) ENABLED START #
        self._frequency_slice_id = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_fspID

    def read_corrBandwidth(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_searchWindowID) ENABLED START #
        return self._corr_bandwidth
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_searchWindowID

    def write_corrBandwidth(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_searchWindowID) ENABLED START #
        self._corr_bandwidth = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_searchWindowID

    def read_zoomWindowTuning(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_searchBeamID) ENABLED START #
        return self._zoom_window_tuning
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_searchBeamID

    def write_zoomWindowTuning(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_searchBeamID) ENABLED START #
        self._zoom_window_tuning = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_searchBeamID

    def read_integrationTime(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_outputEnable) ENABLED START #
        return self._integration_time
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_outputEnable

    def write_integrationTime(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_outputEnable) ENABLED START #
        self._integration_time = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_outputEnable

    def read_averagingInterval(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_averagingInterval) ENABLED START #
        return self._averaging_interval
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_averagingInterval

    def write_averagingInterval(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_averagingInterval) ENABLED START #
        self._averaging_interval = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_averagingInterval

    def read_channelAveragingMap(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_searchBeamAddress) ENABLED START #
        return self._channel_averaging_map
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_searchBeamAddress

    def write_channelAveragingMap(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_searchBeamAddress) ENABLED START #
        self._channel_averaging_map = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_searchBeamAddress

    def read_CorrConfig(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_PssConfig) ENABLED START #
        return json.dumps(self._corr_config)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_PssConfig

    def write_CorrConfig(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_PssConfig) ENABLED START #
        # if value is not valid JSON, the exception is caught by CbfSubarray.ConfigureScan()
        self._corr_config = json.loads(value)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_PssConfig

    # --------
    # Commands
    # --------
    @command(
        dtype_in='str',
        doc_in='JSON object to configure a fsp'
    )
    def ConfigureFSP(self, argin):
        # input configuration has already been checked in CbfSubarray device for FspID configuration type = PSS or 0
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            msg = "Device not in IDLE or READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureFSP execution",
                                           tango.ErrSeverity.ERR)
        try:
            argin = json.loads(argin)
            self._corr_config = argin
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Configuration object is not a valid JSON object. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)
        self._obs_state = ObsState.CONFIGURING.value

        for fsp in argin:
            try:
                self._fsp_id = int(fsp["fspID"])

                if "receptors" in fsp:
                    self._receptors = fsp["receptors"]

                self._frequency_slice_id = int(fsp["frequencySliceID"])
                self._corr_bandwidth = int(fsp["corrBandwidth"])

                if "zoomWindowTuning" in fsp:
                    self._zoom_window_tuning = int(fsp["zoomWindowTuning"])

                self._integration_time = int(fsp["integrationTime"])

                if "channelAveragingMap" in fsp:
                    self._channel_averaging_map = fsp["channelAveragingMap"]

                # Send config to FspSubarray for Fsp configuration
                proxy_fsp_subarray = self._proxies_fsp_subarray[self._fsp_id - 1]
                proxy_fsp_subarray.ConfigureScan(json.dumps(fsp))
            except tango.DevFailed:  # exception in ConfigureScan
                msg = "An exception occurred while configuring CbfSubarrayCorrConfig attributes:\n{}\n" \
                  "Aborting configuration".format(sys.exc_info()[1].args[0].desc)
                self.__raise_configure_scan_fatal_error(msg)

        self._obs_state = ObsState.READY.value

    def is_EndScan_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.EndScan) ENABLED START #
        if self._obs_state != ObsState.SCANNING.value:
            msg = "Device not in SCANNING obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "EndScan execution",
                                           tango.ErrSeverity.ERR)

        self._obs_state = ObsState.READY.value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.EndScan

    def is_Scan_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def Scan(self, argin):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.Scan) ENABLED START #
        if self._obs_state != ObsState.READY.value:
            msg = "Device not in READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "Scan execution",
                                           tango.ErrSeverity.ERR)
        # TODO: actually use argin
        # For MVP, ignore argin (activation time)
        self._obs_state = ObsState.SCANNING.value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.Scan

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.SetState

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarrayCorrConfig.main) ENABLED START #
    return run((CbfSubarrayCorrConfig,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.main

if __name__ == '__main__':
    main()
