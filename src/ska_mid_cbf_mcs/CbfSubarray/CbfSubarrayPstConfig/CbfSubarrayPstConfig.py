# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarrayPstConfig project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CBF

"""

# PyTango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device, DeviceMeta
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(CbfSubarrayPstConfig.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState, const
from ska_tango_base import SKACapability
# PROTECTED REGION END #    //  CbfSubarrayPstConfig.additionnal_import

__all__ = ["CbfSubarrayPstConfig", "main"]


class CbfSubarrayPstConfig(SKACapability):
    """
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarrayPstConfig.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfSubarrayPstConfig.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CbfControllerAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Controller",
        default_value="mid_csp_cbf/sub_elt/controller"
    )

    FspPstSubarray = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    pstConfig = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
    )

    fspID = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=27,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        self.set_change_event("obsState", True, True)
        self.set_archive_event("obsState", True, True)
        self.set_change_event("adminMode", True, True)
        self.set_archive_event("adminMode", True, True)
        # PROTECTED REGION ID(CbfSubarrayPstConfig.init_device) ENABLED START #

        # initialize attribute values
        self._pst_config = {} # interpreted as a JSON object
        self._fsp_id = []

        # get proxies for controlller and FSP Subarray devices
        self._proxy_cbf_controller = tango.DeviceProxy(self.CbfControllerAddress)
        self._proxy_fsp_pst_subarray = [*map(tango.DeviceProxy, list(self.FspPstSubarray))]

        # enter EMPTY state

        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_pstConfig(self):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.pstConfig_read) ENABLED START #
        """Return pstConfig attribute: JSON"""
        return json.dumps(self._pst_config)
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.pstConfig_read

    def write_pstConfig(self, value):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.pstConfig_write) ENABLED START #
        """Set pstConfig attribute: JSON"""
        self._pst_config = json.loads(value)
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.pstConfig_write

    def read_fspID(self):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.fspID_read) ENABLED START #
        """Return fspID attribute: array of int"""
        return self._fsp_id
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.fspID_read

    def write_fspID(self, value):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.fspID_write) ENABLED START #
        """Set fspID attribute: array of int"""
        self._fsp_id = value
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.fspID_write


    # --------
    # Commands
    # --------

    @command(
    dtype_in='str', 
    )
    def ConfigureFSP(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.ConfigureFSP) ENABLED START #
        """Set pstConfig attribute; Set CbfSubarrayPstConfig to configuring; Set fspID attribute; Send config to fspPstSubarray for Fsp configuration"""
        # input configuration has already been checked in CbfSubarray device for FspID configuration type = PST or 0
        if self._obs_state not in [ObsState.IDLE, ObsState.READY]:
            msg = "Device not in IDLE or READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureFSP execution",
                                           tango.ErrSeverity.ERR)
        try:
            # set pst_config to the most recent fsp configuration JSON
            argin = json.loads(argin)
            self._pst_config = argin
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Configuration object is not a valid JSON object. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        self._update_obs_state(ObsState.CONFIGURING)
        self._fsp_id = []
        count = 0
        for fsp in argin:
            try:
                self._fsp_id.append(int(fsp["fspID"]))
                # Send config to fspPstSubarray for Fsp configuration
                proxy= self._proxy_fsp_pst_subarray[self._fsp_id[count] - 1]
                proxy.ConfigureScan(json.dumps(fsp))
                count = count + 1
            except tango.DevFailed:  # exception in ConfigureScan
                msg = "An exception occurred while configuring CbfSubarrayPstConfig attributes:\n{}\n" \
                  "Aborting configuration".format(sys.exc_info()[1].args[0].desc)
                self.__raise_configure_scan_fatal_error(msg)

        self._update_obs_state(ObsState.READY)
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.ConfigureFSP

    @command(
    )
    def EndScan(self):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.EndScan) ENABLED START #
        """Set ObsState of CbfsubarrayPsttConfig to READY if it is cuurently SCANNING"""
        if self._obs_state != ObsState.SCANNING:
            msg = "Device not in SCANNING obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "EndScan execution",
                                           tango.ErrSeverity.ERR)

        self._update_obs_state(ObsState.READY)
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.EndScan

    @command(
    dtype_in='str', 
    )
    def Scan(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.Scan) ENABLED START #
        """Set ObsState of CbfsubarrayPstConfig to SCANNING if it is cuurently READY"""
        if self._update_obs_state != ObsState.READY:
            msg = "Device not in READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "Scan execution",
                                           tango.ErrSeverity.ERR)
        # TODO: actually use argin
        # For MVP, ignore argin (activation time)
        self._update_obs_state(ObsState.SCANNING)
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.Scan

    @command(
    dtype_in='DevState', 
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(CbfSubarrayPstConfig.SetState) ENABLED START #
        """set state(tango.DevState)"""
        self.set_state(argin)
        # PROTECTED REGION END #    //  CbfSubarrayPstConfig.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarrayPstConfig.main) ENABLED START #
    return run((CbfSubarrayPstConfig,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarrayPstConfig.main

if __name__ == '__main__':
    main()
