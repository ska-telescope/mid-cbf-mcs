# -*- coding: utf-8 -*-
#
# This file is part of the CbfMaster project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CbfMaster Tango device prototype

CBFMaster TANGO device class for the CBFMaster prototype
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
from SKAMaster import SKAMaster
# Additional import
# PROTECTED REGION ID(CbfMaster.additionnal_import) ENABLED START #
# PROTECTED REGION END #    //  CbfMaster.additionnal_import

__all__ = ["CbfMaster", "main"]


class CbfMaster(SKAMaster):
    """
    CBFMaster TANGO device class for the CBFMaster prototype

    **Properties:**

    - Device Property
    """
    # PROTECTED REGION ID(CbfMaster.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  CbfMaster.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    commandProgress = attribute(
        dtype='DevUShort',
        label="Command progress percentage",
        polling_period=3000,
        rel_change=2,
        abs_change=5,
        max_value=100,
        min_value=0,
        doc="Percentage progress implemented for commands that  result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
    )

    reportVCCState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
        label="VCC state",
        polling_period=3000,
        doc="Report the state of the VCC capabilities as an array of DevState",
    )

    reportVCCHealthState = attribute(
        dtype=('DevUShort',),
        max_dim_x=197,
        label="VCC health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of VCC capabilities as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    reportVCCAdminMode = attribute(
        dtype=('DevUShort',),
        max_dim_x=197,
        label="VCC admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the VCC capabilities as an array of unsigned short.\nFor ex.:\n[0,0,0,...1,2]",
    )

    reportFSPState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
        label="FSP state",
        polling_period=3000,
        doc="Report the state of the FSP capabilities.",
    )

    reportFSPHealthState = attribute(
        dtype=('DevUShort',),
        max_dim_x=27,
        label="FSP health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the FSP capabilities.",
    )

    reportFSPAdminMode = attribute(
        dtype=('DevUShort',),
        max_dim_x=27,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    frequencyBandOffsetK = attribute(
        dtype=('DevLong',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency band offset (k)",
        doc="Frequency band offset (k) of all 197 receptors as an array of ints.",
    )

    frequencyBandOffsetDeltaF = attribute(
        dtype=('DevLong',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency band offset (delta f)",
        doc="Frequency band offset (delta f) of all 197 receptors as an array of ints.",
    )

    reportSubarrayState = attribute(
        dtype=('DevState',),
        max_dim_x=16,
        label="FSP state",
        polling_period=3000,
        doc="Report the state of the FSP capabilities.",
    )

    reportSubarrayHealthState = attribute(
        dtype=('DevUShort',),
        max_dim_x=16,
        label="FSP health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the FSP capabilities.",
    )

    reportSubarrayAdminMode = attribute(
        dtype=('DevUShort',),
        max_dim_x=16,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the CbfMaster."""
        SKAMaster.init_device(self)
        # PROTECTED REGION ID(CbfMaster.init_device) ENABLED START #
        self._command_progress = 0
        self._report_vcc_state = (PyTango.DevState.UNKNOWN,)
        self._report_vcc_health_state = (0,)
        self._report_vcc_admin_mode = (0,)
        self._report_fsp_state = (PyTango.DevState.UNKNOWN,)
        self._report_fsp_health_state = (0,)
        self._report_fsp_admin_mode = (0,)
        self._frequency_band_offset_k = (0,)
        self._frequency_band_offset_delta_f = (0,)
        self._report_subarray_state = (PyTango.DevState.UNKNOWN,)
        self._report_subarray_health_state = (0,)
        self._report_subarray_admin_mode = (0,)
        # PROTECTED REGION END #    //  CbfMaster.init_device

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        # PROTECTED REGION ID(CbfMaster.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  CbfMaster.always_executed_hook

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        # PROTECTED REGION ID(CbfMaster.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  CbfMaster.delete_device
    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self):
        # PROTECTED REGION ID(CbfMaster.commandProgress_read) ENABLED START #
        """Return the commandProgress attribute."""
        return self._command_progress
        # PROTECTED REGION END #    //  CbfMaster.commandProgress_read

    def read_reportVCCState(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCState_read) ENABLED START #
        """Return the reportVCCState attribute."""
        return self._report_vcc_state
        # PROTECTED REGION END #    //  CbfMaster.reportVCCState_read

    def read_reportVCCHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCHealthState_read) ENABLED START #
        """Return the reportVCCHealthState attribute."""
        return self._report_vcc_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportVCCHealthState_read

    def read_reportVCCAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportVCCAdminMode_read) ENABLED START #
        """Return the reportVCCAdminMode attribute."""
        return self._report_vcc_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportVCCAdminMode_read

    def read_reportFSPState(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPState_read) ENABLED START #
        """Return the reportFSPState attribute."""
        return self._report_fsp_state
        # PROTECTED REGION END #    //  CbfMaster.reportFSPState_read

    def read_reportFSPHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPHealthState_read) ENABLED START #
        """Return the reportFSPHealthState attribute."""
        return self._report_fsp_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportFSPHealthState_read

    def read_reportFSPAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportFSPAdminMode_read) ENABLED START #
        """Return the reportFSPAdminMode attribute."""
        return self._report_fsp_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportFSPAdminMode_read

    def read_frequencyBandOffsetK(self):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetK_read) ENABLED START #
        """Return the frequencyBandOffsetK attribute."""
        return self._frequency_band_offset_k
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetK_read

    def write_frequencyBandOffsetK(self, value):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetK_write) ENABLED START #
        """Set the frequencyBandOffsetK attribute."""
        pass
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetK_write

    def read_frequencyBandOffsetDeltaF(self):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetDeltaF_read) ENABLED START #
        """Return the frequencyBandOffsetDeltaF attribute."""
        return self._frequency_band_offset_delta_f
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetDeltaF_read

    def write_frequencyBandOffsetDeltaF(self, value):
        # PROTECTED REGION ID(CbfMaster.frequencyBandOffsetDeltaF_write) ENABLED START #
        """Set the frequencyBandOffsetDeltaF attribute."""
        pass
        # PROTECTED REGION END #    //  CbfMaster.frequencyBandOffsetDeltaF_write

    def read_reportSubarrayState(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayState_read) ENABLED START #
        """Return the reportSubarrayState attribute."""
        return self._report_subarray_state
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayState_read

    def read_reportSubarrayHealthState(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayHealthState_read) ENABLED START #
        """Return the reportSubarrayHealthState attribute."""
        return self._report_subarray_health_state
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayHealthState_read

    def read_reportSubarrayAdminMode(self):
        # PROTECTED REGION ID(CbfMaster.reportSubarrayAdminMode_read) ENABLED START #
        """Return the reportSubarrayAdminMode attribute."""
        return self._report_subarray_admin_mode
        # PROTECTED REGION END #    //  CbfMaster.reportSubarrayAdminMode_read

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevVarStringArray',
        doc_in="If the array length is 0, the command applies to the whole"
               "CSP Element."
               "If the array length is > 1, each array element specifies the FQDN of the"
               "CSP SubElement to switch ON.",
    )
    @DebugIt()
    def On(self, argin):
        # PROTECTED REGION ID(CbfMaster.On) ENABLED START #
        """
        Transit CSP or one or more CSP SubElements fromSTANDBY to ON

        :param argin: 'DevVarStringArray'
            If the array length is 0, the command applies to the whole
            CSP Element.
            If the array length is > 1, each array element specifies the FQDN of the
            CSP SubElement to switch ON.

        :return:None
        """
        pass
        # PROTECTED REGION END #    //  CbfMaster.On

    @command(
        dtype_in='DevVarStringArray',
        doc_in="If the array length is 0, the command applies to the whole"
               "CSP Element."
               "If the array length is > 1, each array element specifies the FQDN of the"
               "CSP SubElement to switch OFF.",
    )
    @DebugIt()
    def Off(self, argin):
        # PROTECTED REGION ID(CbfMaster.Off) ENABLED START #
        """
        Transit CSP or one or more CSP SubElements from ON to OFF.

        :param argin: 'DevVarStringArray'
            If the array length is 0, the command applies to the whole
            CSP Element.
            If the array length is > 1, each array element specifies the FQDN of the
            CSP SubElement to switch OFF.

        :return:None
        """
        pass
        # PROTECTED REGION END #    //  CbfMaster.Off

    @command(
        dtype_in='DevVarStringArray',
        doc_in="If the array length is 0, the command applies to the whole"
               "CSP Element."
               "If the array length is > 1, each array element specifies the FQDN of the"
               "CSP SubElement to put in STANDBY mode.",
    )
    @DebugIt()
    def Standby(self, argin):
        # PROTECTED REGION ID(CbfMaster.Standby) ENABLED START #
        """
            Transit CSP or one or more CSP SubElements from ON/OFF to 
            STANDBY.

        :param argin: 'DevVarStringArray'
            If the array length is 0, the command applies to the whole
            CSP Element.
            If the array length is > 1, each array element specifies the FQDN of the
            CSP SubElement to put in STANDBY mode.

        :return:None
        """
        pass
        # PROTECTED REGION END #    //  CbfMaster.Standby

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the CbfMaster module."""
    # PROTECTED REGION ID(CbfMaster.main) ENABLED START #
    return run((CbfMaster,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfMaster.main


if __name__ == '__main__':
    main()
