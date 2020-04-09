# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
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

# Fsp Tango device prototype
# Fsp TANGO device class for the prototype

# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(Fsp.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  Fsp.additionnal_import

__all__ = ["Fsp", "main"]


class Fsp(SKACapability):
    """
    Fsp TANGO device class for the prototype
    """
    # PROTECTED REGION ID(Fsp.class_variable) ENABLED START #

    def __get_capability_proxies(self):
        # for now, assume that given addresses are valid
        if self.CorrelationAddress:
            self._proxy_correlation = tango.DeviceProxy(self.CorrelationAddress)
        if self.PSSAddress:
            self._proxy_pss = tango.DeviceProxy(self.PSSAddress)
        if self.PSTAddress:
            self._proxy_pst = tango.DeviceProxy(self.PSTAddress)
        if self.VLBIAddress:
            self._proxy_vlbi = tango.DeviceProxy(self.VLBIAddress)
        if self.FspSubarrayCorr:
            self._proxy_fsp_subarray_corr = [*map(
                tango.DeviceProxy,
                list(self.FspSubarrayCorr)
            )]

    # PROTECTED REGION END #    //  Fsp.class_variable

    # -----------------
    # Device Properties
    # -----------------

    FspID = device_property(
        dtype='uint16'
    )

    CorrelationAddress = device_property(
        dtype='str'
    )

    PSSAddress = device_property(
        dtype='str'
    )

    PSTAddress = device_property(
        dtype='str'
    )

    VLBIAddress = device_property(
        dtype='str'
    )

    FspSubarrayCorr = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    functionMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Function mode",
        doc="Function mode; an int in the range [0, 4]",
        enum_labels=["IDLE", "CORRELATION", "PSS", "PST", "VLBI", ],
    )

    subarrayMembership = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        access=AttrWriteType.READ,
        label="Subarray membership",
        doc="Subarray membership"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Fsp.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # defines self._proxy_correlation, self._proxy_pss, self._proxy_pst, self._proxy_vlbi,
        # and self._proxy_fsp_subarray_corr
        self.__get_capability_proxies()

        # the modes are already disabled on initialization,
        # self._proxy_correlation.SetState(tango.DevState.DISABLE)
        # self._proxy_pss.SetState(tango.DevState.DISABLE)
        # self._proxy_pst.SetState(tango.DevState.DISABLE)
        # self._proxy_vlbi.SetState(tango.DevState.DISABLE)

        self._fsp_id = self.FspID

        # initialize attribute values
        self._function_mode = 0  # IDLE
        self._subarray_membership = []

        # initialize FSP subarray group
        self._group_fsp_subarray_corr = tango.Group("FSP Subarray")
        for fqdn in list(self.FspSubarrayCorr):
            self._group_fsp_subarray_corr.add(fqdn)

        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(Fsp.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Fsp.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(Fsp.delete_device) ENABLED START #
        self._proxy_correlation.SetState(tango.DevState.OFF)
        self._proxy_pss.SetState(tango.DevState.OFF)
        self._proxy_pst.SetState(tango.DevState.OFF)
        self._proxy_vlbi.SetState(tango.DevState.OFF)
        self._group_fsp_subarray_corr.command_inout("Off")

        # remove all subarray membership
        for subarray_ID in self._subarray_membership[:]:
            self.RemoveSubarrayMembership(subarray_ID)

        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_functionMode(self):
        # PROTECTED REGION ID(Fsp.functionMode_read) ENABLED START #
        return self._function_mode
        # PROTECTED REGION END #    //  Fsp.functionMode_read

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Fsp.subarrayMembership_read) ENABLED START #
        return self._subarray_membership
        # PROTECTED REGION END #    //  Fsp.subarrayMembership_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        if self.dev_state() == tango.DevState.OFF:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(Fsp.On) ENABLED START #
        self._proxy_correlation.SetState(tango.DevState.DISABLE)
        self._proxy_pss.SetState(tango.DevState.DISABLE)
        self._proxy_pst.SetState(tango.DevState.DISABLE)
        self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        self._group_fsp_subarray_corr.command_inout("On")

        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  Fsp.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(Fsp.Off) ENABLED START #
        self._proxy_correlation.SetState(tango.DevState.OFF)
        self._proxy_pss.SetState(tango.DevState.OFF)
        self._proxy_pst.SetState(tango.DevState.OFF)
        self._proxy_vlbi.SetState(tango.DevState.OFF)
        self._group_fsp_subarray_corr.command_inout("Off")

        # remove all subarray membership
        for subarray_ID in self._subarray_membership[:]:
            self.RemoveSubarrayMembership(subarray_ID)

        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Fsp.Off

    def is_SetFunctionMode_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='Function mode'
    )
    def SetFunctionMode(self, argin):
        # PROTECTED REGION ID(Fsp.SetFunctionMode) ENABLED START #
        if argin == "IDLE":
            self._function_mode = 0
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "CORR":
            self._function_mode = 1
            self._proxy_correlation.SetState(tango.DevState.ON)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "PSS-BF":
            self._function_mode = 2
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.ON)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "PST-BF":
            self._function_mode = 3
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.ON)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
        if argin == "VLBI":
            self._function_mode = 4
            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.ON)

        # shouldn't happen
        self.logger.warn("functionMode not valid. Ignoring.")
        # PROTECTED REGION END #    //  Fsp.SetFunctionMode

    def is_AddSubarrayMembership_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def AddSubarrayMembership(self, argin):
        # PROTECTED REGION ID(Fsp.AddSubarrayMembership) ENABLED START #
        if argin not in self._subarray_membership:
            self._subarray_membership.append(argin)
        else:
            log_msg = "FSP already belongs to subarray {}.".format(argin)
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  Fsp.AddSubarrayMembership

    def is_RemoveSubarrayMembership_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def RemoveSubarrayMembership(self, argin):
        # PROTECTED REGION ID(Fsp.RemoveSubarrayMembership) ENABLED START #
        if argin in self._subarray_membership:
            self._subarray_membership.remove(argin)
            # change function mode to IDLE if no subarrays are using it.
            if not self._subarray_membership:
                self._function_mode = 0
        else:
            log_msg = "FSP does not belong to subarray {}.".format(argin)
            self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  Fsp.RemoveSubarrayMembership

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Fsp.main) ENABLED START #
    return run((Fsp,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Fsp.main

if __name__ == '__main__':
    main()
