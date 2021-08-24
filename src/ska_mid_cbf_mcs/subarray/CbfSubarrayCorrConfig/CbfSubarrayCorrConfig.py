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

from ska_tango_base.control_model import ObsState, AdminMode, HealthState
from ska_tango_base import SKACapability
# PROTECTED REGION END #    //  CbfSubarrayCorrConfig.additionnal_import

__all__ = ["CbfSubarrayCorrConfig", "main"]


class CbfSubarrayCorrConfig(SKACapability):

    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarrayCorrConfig.class_variable) ENABLED START #

    # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------

    FspCorrSubarray = device_property(
        dtype=('str',)
    )

    CbfControllerAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Controller",
        default_value="mid_csp_cbf/sub_elt/controller"
    )

    # ----------
    # Attributes
    # ----------

    fspID = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=27,
    )

    corrConfig = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Fst Corr Configuration",
        doc="Fst Corr Configuration JSON"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """inherit device from SKA Capability; initialize attributes"""
        SKACapability.init_device(self)
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # initialize attribute values
        self._fsp_id = []
        self._corr_config = {}  # this is interpreted as a JSON object

        # Getting Proxies for FSP and FSP Subarrays

        # TODO - controller proxy and CbfControllerAddress not needed - to remove
        self._proxy_cbf_controller = tango.DeviceProxy(self.CbfControllerAddress)

        self._proxies_fsp_corr_subarray = [*map(tango.DeviceProxy, list(self.FspCorrSubarray))]

        self._update_obs_state(ObsState.IDLE)
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        pass
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.delete_device) ENABLED START #
        """hook to delete device"""
        pass
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.delete_device

    def is_configure_scan_allowed(self):
        """allowed when cbfSubarrayCorrConfig is On, and ObsState is idle or ready"""
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.IDLE, ObsState.READY]:
            return True
        return False

    def __raise_configure_scan_fatal_error(self, msg):
        self.logger.error(msg)
        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                       tango.ErrSeverity.ERR)

    # ------------------
    # Attributes methods
    # ------------------

    def read_fspID(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_fspID) ENABLED START #
        """Return fspID attribute: array of int"""
        return self._fsp_id
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_fspID

    def write_fspID(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_fspID) ENABLED START #
        """Set fspID attribute: array of int"""
        self._fsp_id = value
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.write_fspID

    def read_corrConfig(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.read_PssConfig) ENABLED START #
        """Return corrConfig attribute: JSON"""
        return json.dumps(self._corr_config)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.read_PssConfig

    def write_corrConfig(self, value):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.write_PssConfig) ENABLED START #
        # if value is not valid JSON, the exception is caught by CbfSubarray.ConfigureScan()
        """Set corrConfig attribute: JSON"""
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
        """ 
        Send config(argin) to FSPCorrSubarray to ConfigureScan.
        Set corrConfig attribute; Set CbfSubarrayCorrConfig to configuring; Set fspID attribute
        """
        # input configuration has already been checked in CbfSubarray device for FspID configuration type = PSS or 0
        if self._obs_state not in [ObsState.IDLE, ObsState.READY]:
            msg = "Device not in IDLE or READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureFSP execution",
                                           tango.ErrSeverity.ERR)
        try:
            # set corr_config to the most recent fsp configuration JSON
            argin = json.loads(argin)
            self._corr_config = argin
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Configuration object is not a valid JSON object. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        self._update_obs_state(ObsState.CONFIGURING)
        self._fsp_id = []
        count = 0
        for fsp in argin:
            try:
                self._fsp_id.append(int(fsp["fspID"]))
                ###################### Send config to fspCorrSubarray for Fsp configuration ####################
                proxy_fsp_corr_subarray = self._proxies_fsp_corr_subarray[self._fsp_id[count] - 1]
                proxy_fsp_corr_subarray.ConfigureScan(json.dumps(fsp))
                count = count + 1
            except tango.DevFailed:  # exception in ConfigureScan
                msg = "An exception occurred while configuring CbfSubarrayCorrConfig attributes:\n{}\n" \
                  "Aborting configuration".format(sys.exc_info()[1].args[0].desc)
                self.__raise_configure_scan_fatal_error(msg)

        self._update_obs_state(ObsState.READY)

    def is_EndScan_allowed(self):
        """allowed if CbfSubarrayCorrConfig is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.EndScan) ENABLED START #
        """Set ObsState of CbfsubarrayCorrConfig to READY if it is cuurently SCANNING"""
        if self._obs_state != ObsState.SCANNING:
            msg = "Device not in SCANNING obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "EndScan execution",
                                           tango.ErrSeverity.ERR)

        self._update_obs_state(ObsState.READY)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.EndScan

    def is_Scan_allowed(self):
        """allowed if CbfSubarrayCorrConfig is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def Scan(self, argin):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.Scan) ENABLED START #
        """Set ObsState of CbfsubarrayCorrConfig to SCANNING if it is cuurently READY"""
        if self._obs_state != ObsState.READY:
            msg = "Device not in READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "Scan execution",
                                           tango.ErrSeverity.ERR)
        # TODO: actually use argin
        # For MVP, ignore argin (activation time)
        self._update_obs_state(ObsState.SCANNING)
        # PROTECTED REGION END #    //  CbfSubarrayCorrConfig.Scan

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(CbfSubarrayCorrConfig.SetState) ENABLED START #
        """set state(tango.DevState)"""
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
