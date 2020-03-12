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

# Vcc Tango device prototype
# Vcc TANGO device class for the prototype

# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(Vcc.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import const
from skabase.control_model import ObsState
from skabase.SKACapability.SKACapability import SKACapability

# PROTECTED REGION END #    //  Vcc.additionnal_import

__all__ = ["Vcc", "main"]


class Vcc(SKACapability):
    """
    Vcc TANGO device class for the prototype
    """

    # PROTECTED REGION ID(Vcc.class_variable) ENABLED START #

    def __get_capability_proxies(self):
        # for now, assume that given addresses are valid
        if self.Band1And2Address:
            self._proxy_band_12 = tango.DeviceProxy(self.Band1And2Address)
        if self.Band3Address:
            self._proxy_band_3 = tango.DeviceProxy(self.Band3Address)
        if self.Band4Address:
            self._proxy_band_4 = tango.DeviceProxy(self.Band4Address)
        if self.Band5Address:
            self._proxy_band_5 = tango.DeviceProxy(self.Band5Address)
        if self.SW1Address:
            self._proxy_sw_1 = tango.DeviceProxy(self.SW1Address)
        if self.SW2Address:
            self._proxy_sw_2 = tango.DeviceProxy(self.SW2Address)

    # PROTECTED REGION END #    //  Vcc.class_variable

    # -----------------
    # Device Properties
    # -----------------

    VccID = device_property(
        dtype='uint16'
    )

    Band1And2Address = device_property(
        dtype='str'
    )

    Band3Address = device_property(
        dtype='str'
    )

    Band4Address = device_property(
        dtype='str'
    )

    Band5Address = device_property(
        dtype='str'
    )

    SW1Address = device_property(
        dtype='str'
    )

    SW2Address = device_property(
        dtype='str'
    )

    # ----------
    # Attributes
    # ----------

    receptorID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Receptor ID",
        doc="Receptor ID",
    )

    subarrayMembership = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Subarray membership",
        doc="Subarray membership",
    )

    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    band5Tuning = attribute(
        dtype=('float',),
        max_dim_x=2,
        access=AttrWriteType.READ_WRITE,
        label="Stream tuning (GHz)",
        doc="Stream tuning (GHz)"
    )

    frequencyBandOffsetStream1 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band offset (stream 1) (Hz)",
        doc="Frequency band offset (stream 1) (Hz)"
    )

    frequencyBandOffsetStream2 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band offset (stream 2) (Hz)",
        doc="Frequency band offset (stream 2) (Hz)"
    )

    dopplerPhaseCorrection = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction coefficients",
        doc="Doppler phase correction coefficients"
    )

    rfiFlaggingMask = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="RFI Flagging Mask",
        doc="RFI Flagging Mask"
    )

    scfoBand1 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 1)",
        doc="Sample clock frequency offset for band 1",
    )

    scfoBand2 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 2)",
        doc="Sample clock frequency offset for band 2",
    )

    scfoBand3 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 3)",
        doc="Sample clock frequency offset for band 3",
    )

    scfoBand4 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 4)",
        doc="Sample clock frequency offset for band 4",
    )

    scfoBand5a = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 5a)",
        doc="Sample clock frequency offset for band 5a",
    )

    scfoBand5b = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 5b)",
        doc="Sample clock frequency offset for band 5b",
    )

    delayModel = attribute(
        dtype=(('double',),),
        max_dim_x=6,
        max_dim_y=26,
        access=AttrWriteType.READ,
        label="Delay model coefficients",
        doc="Delay model coefficients, given per frequency slice"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Vcc.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # defines self._proxy_band_12, self._proxy_band_3, self._proxy_band_4, self._proxy_band_5,
        # self._proxy_sw_1, and self._proxy_sw_2
        self.__get_capability_proxies()

        self._vcc_id = self.VccID

        # the bands are already disabled on initialization
        # self._proxy_band_12.SetState(tango.DevState.DISABLE)
        # self._proxy_band_3.SetState(tango.DevState.DISABLE)
        # self._proxy_band_4.SetState(tango.DevState.DISABLE)
        # self._proxy_band_5.SetState(tango.DevState.DISABLE)
        # self._proxy_tdc_1.SetState(tango.DevState.DISABLE)
        # self._proxy_tdc_2.SetState(tango.DevSTate.DISABLE)

        # initialize attribute values
        self._receptor_ID = 0
        self._frequency_band = 0
        self._subarray_membership = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._doppler_phase_correction = (0, 0, 0, 0)
        self._rfi_flagging_mask = ""
        self._scfo_band_1 = 0
        self._scfo_band_2 = 0
        self._scfo_band_3 = 0
        self._scfo_band_4 = 0
        self._scfo_band_5a = 0
        self._scfo_band_5b = 0
        self._delay_model = [[0] * 6 for i in range(26)]

        self._obs_state = ObsState.IDLE.value
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Vcc.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(Vcc.delete_device) ENABLED START #
        self._proxy_band_12.SetState(tango.DevState.OFF)
        self._proxy_band_3.SetState(tango.DevState.OFF)
        self._proxy_band_4.SetState(tango.DevState.OFF)
        self._proxy_band_5.SetState(tango.DevState.OFF)
        self._proxy_sw_1.SetState(tango.DevState.OFF)
        self._proxy_sw_2.SetState(tango.DevState.OFF)

        self.GoToIdle()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Vcc.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptorID(self):
        # PROTECTED REGION ID(Vcc.receptorID_read) ENABLED START #
        return self._receptor_ID
        # PROTECTED REGION END #    //  Vcc.receptorID_read

    def write_receptorID(self, value):
        # PROTECTED REGION ID(Vcc.receptorID_write) ENABLED START #
        self._receptor_ID = value
        # PROTECTED REGION END #    //  Vcc.receptorID_write

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Vcc.subarrayMembership_read) ENABLED START #
        return self._subarray_membership
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_read

    def write_subarrayMembership(self, value):
        # PROTECTED REGION ID(Vcc.subarrayMembership_write) ENABLED START #
        self._subarray_membership = value
        if not value:
            self._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_write

    def read_frequencyBand(self):
        # PROTECTED REGION ID(Vcc.frequencyBand_read) ENABLED START #
        return self._frequency_band
        # PROTECTED REGION END #    //  Vcc.frequencyBand_read

    def read_band5Tuning(self):
        # PROTECTED REGION ID(Vcc.band5Tuning_read) ENABLED START #
        return self._stream_tuning
        # PROTECTED REGION END #    //  Vcc.band5Tuning_read

    def write_band5Tuning(self, value):
        # PROTECTED REGION ID(Vcc.band5Tuning_write) ENABLED START #
        self._stream_tuning = value
        # PROTECTED REGION END #    //  Vcc.band5Tuning_write

    def read_frequencyBandOffsetStream1(self):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream1_read) ENABLED START #
        return self._frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream1_read

    def write_frequencyBandOffsetStream1(self, value):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream1_write) ENABLED START #
        self._frequency_band_offset_stream_1 = value
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream1_write

    def read_frequencyBandOffsetStream2(self):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream2_read) ENABLED START #
        return self._frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream2_read

    def write_frequencyBandOffsetStream2(self, value):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream2_write) ENABLED START #
        self._frequency_band_offset_stream_2 = value
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream2_write

    def read_dopplerPhaseCorrection(self):
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_read) ENABLED START #
        return self._doppler_phase_correction
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_read

    def write_dopplerPhaseCorrection(self, value):
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_write) ENABLED START #
        self._doppler_phase_correction = value
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_write

    def read_rfiFlaggingMask(self):
        # PROTECTED REGION ID(Vcc.rfiFlaggingMask_read) ENABLED START #
        return self._rfi_flagging_mask
        # PROTECTED REGION END #    //  Vcc.rfiFlaggingMask_read

    def write_rfiFlaggingMask(self, value):
        # PROTECTED REGION ID(Vcc.rfiFlaggingMask_write) ENABLED START #
        self._rfi_flagging_mask = value
        # PROTECTED REGION END #    //  Vcc.rfiFlaggingMask_write

    def read_scfoBand1(self):
        # PROTECTED REGION ID(Vcc.scfoBand1_read) ENABLED START #
        return self._scfo_band_1
        # PROTECTED REGION END #    //  Vcc.scfoBand1_read

    def write_scfoBand1(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand1_write) ENABLED START #
        self._scfo_band_1 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand1_write

    def read_scfoBand2(self):
        # PROTECTED REGION ID(Vcc.scfoBand2_read) ENABLED START #
        return self._scfo_band_2
        # PROTECTED REGION END #    //  Vcc.scfoBand2_read

    def write_scfoBand2(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand2_write) ENABLED START #
        self._scfo_band_2 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand2_write

    def read_scfoBand3(self):
        # PROTECTED REGION ID(Vcc.scfoBand3_read) ENABLED START #
        return self._scfo_band_3
        # PROTECTED REGION END #    //  Vcc.scfoBand3_read

    def write_scfoBand3(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand3_write) ENABLED START #
        self._scfo_band_3 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand3_write

    def read_scfoBand4(self):
        # PROTECTED REGION ID(Vcc.scfoBand4_read) ENABLED START #
        return self._scfo_band_4
        # PROTECTED REGION END #    //  Vcc.scfoBand4_read

    def write_scfoBand4(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand4_write) ENABLED START #
        self._scfo_band_4 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand4_write

    def read_scfoBand5a(self):
        # PROTECTED REGION ID(Vcc.scfoBand5a_read) ENABLED START #
        return self._scfo_band_5a
        # PROTECTED REGION END #    //  Vcc.scfoBand5a_read

    def write_scfoBand5a(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand5a_write) ENABLED START #
        self._scfo_band_5a = value
        # PROTECTED REGION END #    //  Vcc.scfoBand5a_write

    def read_scfoBand5b(self):
        # PROTECTED REGION ID(Vcc.scfoBand5b_read) ENABLED START #
        return self._scfo_band_5b
        # PROTECTED REGION END #    //  Vcc.scfoBand5b_read

    def write_scfoBand5b(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand5b_write) ENABLED START #
        self._scfo_band_5b = value
        # PROTECTED REGION END #    //  Vcc.scfoBand5b_write

    def read_delayModel(self):
        # PROTECTED REGION ID(Vcc.delayModel_read) ENABLED START #
        return self._delay_model
        # PROTECTED REGION END #    //  Vcc.delayModel_read

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        if self.dev_state() == tango.DevState.OFF and \
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(Vcc.On) ENABLED START #
        self._proxy_band_12.SetState(tango.DevState.DISABLE)
        self._proxy_band_3.SetState(tango.DevState.DISABLE)
        self._proxy_band_4.SetState(tango.DevState.DISABLE)
        self._proxy_band_5.SetState(tango.DevState.DISABLE)
        self._proxy_sw_1.SetState(tango.DevState.DISABLE)
        self._proxy_sw_2.SetState(tango.DevState.DISABLE)

        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  Vcc.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(Vcc.Off) ENABLED START #
        self._proxy_band_12.SetState(tango.DevState.OFF)
        self._proxy_band_3.SetState(tango.DevState.OFF)
        self._proxy_band_4.SetState(tango.DevState.OFF)
        self._proxy_band_5.SetState(tango.DevState.OFF)
        self._proxy_sw_1.SetState(tango.DevState.OFF)
        self._proxy_sw_2.SetState(tango.DevState.OFF)

        # This command can only be called when obsState=IDLE
        # self.GoToIdle()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  Vcc.Off

    def is_SetFrequencyBand_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state == ObsState.CONFIGURING.value:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='New frequency band'
    )
    def SetFrequencyBand(self, argin):
        # PROTECTED REGION ID(Vcc.SetFrequencyBand) ENABLED START #
        if argin in ["1", "2"]:
            self._frequency_band = ["1", "2"].index(argin)
            self._proxy_band_12.SetState(tango.DevState.ON)
            self._proxy_band_3.SetState(tango.DevState.DISABLE)
            self._proxy_band_4.SetState(tango.DevState.DISABLE)
            self._proxy_band_5.SetState(tango.DevState.DISABLE)
        elif argin == "3":
            self._frequency_band = 2
            self._proxy_band_12.SetState(tango.DevState.DISABLE)
            self._proxy_band_3.SetState(tango.DevState.ON)
            self._proxy_band_4.SetState(tango.DevState.DISABLE)
            self._proxy_band_5.SetState(tango.DevState.DISABLE)
        elif argin == "4":
            self._frequency_band = 3
            self._proxy_band_12.SetState(tango.DevState.DISABLE)
            self._proxy_band_3.SetState(tango.DevState.DISABLE)
            self._proxy_band_4.SetState(tango.DevState.ON)
            self._proxy_band_5.SetState(tango.DevState.DISABLE)
        elif argin in ["5a", "5b"]:
            self._frequency_band = ["5a", "5b"].index(argin) + 4
            self._proxy_band_12.SetState(tango.DevState.DISABLE)
            self._proxy_band_3.SetState(tango.DevState.DISABLE)
            self._proxy_band_4.SetState(tango.DevState.DISABLE)
            self._proxy_band_5.SetState(tango.DevState.ON)

        # shouldn't happen
        self.logger.warn("frequencyBand not in valid range. Ignoring.")
        # PROTECTED REGION END #    // Vcc.SetFrequencyBand

    def is_SetObservingState_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [
            ObsState.IDLE.value,
            ObsState.CONFIGURING.value,
            ObsState.READY.value
        ]:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in="New obsState (CONFIGURING OR READY)"
    )
    def SetObservingState(self, argin):
        # PROTECTED REGION ID(Vcc.SetObservingState) ENABLED START #
        # Since obsState is read-only, CBF Subarray needs a way to change the obsState
        # of a VCC, BUT ONLY TO CONFIGURING OR READY, during a scan configuration.
        if argin in [ObsState.CONFIGURING.value, ObsState.READY.value]:
            self._obs_state = argin
        else:
            # shouldn't happen
            self.logger.warn("obsState must be CONFIGURING or READY. Ignoring.")
        # PROTECTED REGION END #    // Vcc.SetFrequencyBand

    def is_UpdateDelayModel_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.READY.value, ObsState.SCANNING.value]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Delay model, given per frequency slice"
    )
    def UpdateDelayModel(self, argin):
        # PROTECTED REGION ID(Vcc.UpdateDelayModel) ENABLED START #
        argin = json.loads(argin)

        for receptor in argin:
            if receptor["receptor"] == self._receptor_ID:
                for frequency_slice in receptor["receptorDelayDetails"]:
                    if 1 <= frequency_slice["fsid"] <= 26:
                        if len(frequency_slice["delayCoeff"]) == 6:
                            self._delay_model[frequency_slice["fsid"] - 1] = \
                                frequency_slice["delayCoeff"]
                        else:
                            log_msg = "'delayCoeff' not valid for frequency slice {} of " \
                                      "receptor {}".format(frequency_slice["fsid"], self._receptor_ID)
                            self.logger.error(log_msg)
                    else:
                        log_msg = "'fsid' {} not valid for receptor {}".format(
                            frequency_slice["fsid"], self._receptor_ID
                        )
                        self.logger.error(log_msg)
        # PROTECTED REGION END #    // Vcc.UpdateDelayModel

    def is_ValidateSearchWindow_allowed(self):
        # This command has no side effects, so just allow it anytime
        return True

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ValidateSearchWindow(self, argin):
        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Search window configuration object is not a valid JSON object."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate searchWindowID.
        if "searchWindowID" in argin:
            if int(argin["searchWindowID"]) in [1, 2]:
                pass
            else:  # searchWindowID not in valid range
                msg = "'searchWindowID' must be one of [1, 2] (received {}).".format(
                    str(argin["searchWindowID"])
                )
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'searchWindowID' not given."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate searchWindowTuning.
        if "searchWindowTuning" in argin:
            if argin["frequencyBand"] in list(range(4)):  # frequency band is not band 5
                frequency_band_range = [
                    const.FREQUENCY_BAND_1_RANGE,
                    const.FREQUENCY_BAND_2_RANGE,
                    const.FREQUENCY_BAND_3_RANGE,
                    const.FREQUENCY_BAND_4_RANGE
                ][argin["frequencyBand"]]

                if frequency_band_range[0] * 10 ** 9 + argin["frequencyBandOffsetStream1"] <= \
                        int(argin["searchWindowTuning"]) <= \
                        frequency_band_range[1] * 10 ** 9 + argin["frequencyBandOffsetStream1"]:
                    pass
                else:
                    msg = "'searchWindowTuning' must be within observed band."
                    self.logger.error(msg)
                    tango.Except.throw_exception("Command failed", msg,
                                                 "ConfigureSearchWindow execution",
                                                 tango.ErrSeverity.ERR)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                frequency_band_range_1 = (
                    argin["band5Tuning"][0] * 10 ** 9 + argin["frequencyBandOffsetStream1"] - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    argin["band5Tuning"][0] * 10 ** 9 + argin["frequencyBandOffsetStream1"] + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                frequency_band_range_2 = (
                    argin["band5Tuning"][1] * 10 ** 9 + argin["frequencyBandOffsetStream2"] - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    argin["band5Tuning"][1] * 10 ** 9 + argin["frequencyBandOffsetStream2"] + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                if (frequency_band_range_1[0] <= \
                    int(argin["searchWindowTuning"]) <= \
                    frequency_band_range_1[1]) or \
                        (frequency_band_range_2[0] <= \
                         int(argin["searchWindowTuning"]) <= \
                         frequency_band_range_2[1]):
                    pass
                else:
                    msg = "'searchWindowTuning' must be within observed band."
                    self.logger.error(msg)
                    tango.Except.throw_exception("Command failed", msg,
                                                 "ConfigureSearchWindow execution",
                                                 tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'searchWindowTuning' not given."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate tdcEnable.
        if "tdcEnable" in argin:
            if argin["tdcEnable"] in [True, False]:
                pass
            else:
                msg = "Search window specified, but 'tdcEnable' not given."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'tdcEnable' not given."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate tdcNumBits.
        if argin["tdcEnable"]:
            if "tdcNumBits" in argin:
                if int(argin["tdcNumBits"]) in [2, 4, 8]:
                    pass
                else:
                    msg = "'tdcNumBits' must be one of [2, 4, 8] (received {}).".format(
                        str(argin["tdcNumBits"])
                    )
                    self.logger.error(msg)
                    tango.Except.throw_exception("Command failed", msg,
                                                 "ConfigureSearchWindow execution",
                                                 tango.ErrSeverity.ERR)
            else:
                msg = "Search window specified with TDC enabled, but 'tdcNumBits' not given."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)

        # Validate tdcPeriodBeforeEpoch.
        if "tdcPeriodBeforeEpoch" in argin:
            if int(argin["tdcPeriodBeforeEpoch"]) > 0:
                pass
            else:
                msg = "'tdcPeriodBeforeEpoch' must be a positive integer (received {}).".format(
                    str(argin["tdcPeriodBeforeEpoch"])
                )
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            pass

        # Validate tdcPeriodAfterEpoch.
        if "tdcPeriodAfterEpoch" in argin:
            if int(argin["tdcPeriodAfterEpoch"]) > 0:
                pass
            else:
                msg = "'tdcPeriodAfterEpoch' must be a positive integer (received {}).".format(
                    str(argin["tdcPeriodAfterEpoch"])
                )
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            pass

        # Validate tdcDestinationAddress.
        if argin["tdcEnable"]:
            try:
                for receptor in argin["tdcDestinationAddress"]:
                    # if int(receptor["receptorID"]) == self._receptor_ID:
                    # TODO: validate input
                    break
                else:  # receptorID not found
                    raise KeyError  # just handle all the errors in one place
            except KeyError:
                # tdcDestinationAddress not given or receptorID not in tdcDestinationAddress
                msg = "Search window specified with TDC enabled, but 'tdcDestinationAddress' " \
                      "not given or missing receptors."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)

    def is_ConfigureSearchWindow_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state == ObsState.CONFIGURING.value:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ConfigureSearchWindow(self, argin):
        # PROTECTED REGION ID(Vcc.ConfigureSearchWindow) ENABLED START #
        # This function is called after the configuration has already been validated,
        # so the checks here have been removed to reduce overhead.

        argin = json.loads(argin)

        # variable to use as SW proxy
        proxy_sw = 0

        # Configure searchWindowID.
        if int(argin["searchWindowID"]) == 1:
            proxy_sw = self._proxy_sw_1
        elif int(argin["searchWindowID"]) == 2:
            proxy_sw = self._proxy_sw_2

        # Configure searchWindowTuning.
        if self._frequency_band in list(range(4)):  # frequency band is not band 5
            proxy_sw.searchWindowTuning = argin["searchWindowTuning"]

            frequency_band_range = [
                const.FREQUENCY_BAND_1_RANGE,
                const.FREQUENCY_BAND_2_RANGE,
                const.FREQUENCY_BAND_3_RANGE,
                const.FREQUENCY_BAND_4_RANGE
            ][self._frequency_band]

            if frequency_band_range[0] * 10 ** 9 + self._frequency_band_offset_stream_1 + \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                    int(argin["searchWindowTuning"]) <= \
                    frequency_band_range[1] * 10 ** 9 + self._frequency_band_offset_stream_1 - \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2:
                # this is the acceptable range
                pass
            else:
                # log a warning message
                log_msg = "'searchWindowTuning' partially out of observed band. " \
                          "Proceeding."
                self.logger.warn(log_msg)
        else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
            proxy_sw.searchWindowTuning = argin["searchWindowTuning"]

            frequency_band_range_1 = (
                self._stream_tuning[0] * 10 ** 9 + self._frequency_band_offset_stream_1 - \
                const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                self._stream_tuning[0] * 10 ** 9 + self._frequency_band_offset_stream_1 + \
                const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
            )

            frequency_band_range_2 = (
                self._stream_tuning[1] * 10 ** 9 + self._frequency_band_offset_stream_2 - \
                const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                self._stream_tuning[1] * 10 ** 9 + self._frequency_band_offset_stream_2 + \
                const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
            )

            if (frequency_band_range_1[0] + \
                const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                int(argin["searchWindowTuning"]) <= \
                frequency_band_range_1[1] - \
                const.SEARCH_WINDOW_BW * 10 ** 6 / 2) or \
                    (frequency_band_range_2[0] + \
                     const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                     int(argin["searchWindowTuning"]) <= \
                     frequency_band_range_2[1] - \
                     const.SEARCH_WINDOW_BW * 10 ** 6 / 2):
                # this is the acceptable range
                pass
            else:
                # log a warning message
                log_msg = "'searchWindowTuning' partially out of observed band. " \
                          "Proceeding."
                self.logger.warn(log_msg)

        # Configure tdcEnable.
        proxy_sw.tdcEnable = argin["tdcEnable"]
        if argin["tdcEnable"]:
            # transition to ON if TDC is enabled
            proxy_sw.SetState(tango.DevState.ON)
        else:
            proxy_sw.SetState(tango.DevState.DISABLE)

        # Configure tdcNumBits.
        if argin["tdcEnable"]:
            proxy_sw.tdcNumBits = int(argin["tdcNumBits"])

        # Configure tdcPeriodBeforeEpoch.
        if "tdcPeriodBeforeEpoch" in argin:
            proxy_sw.tdcPeriodBeforeEpoch = int(argin["tdcPeriodBeforeEpoch"])
        else:
            proxy_sw.tdcPeriodBeforeEpoch = 2
            log_msg = "Search window specified, but 'tdcPeriodBeforeEpoch' not given. " \
                      "Defaulting to 2."
            self.logger.warn(log_msg)

        # Configure tdcPeriodAfterEpoch.
        if "tdcPeriodAfterEpoch" in argin:
            proxy_sw.tdcPeriodAfterEpoch = int(argin["tdcPeriodAfterEpoch"])
        else:
            proxy_sw.tdcPeriodAfterEpoch = 22
            log_msg = "Search window specified, but 'tdcPeriodAfterEpoch' not given. " \
                      "Defaulting to 22."
            self.logger.warn(log_msg)

        # Configure tdcDestinationAddress.
        if argin["tdcEnable"]:
            for receptor in argin["tdcDestinationAddress"]:
                if int(receptor["receptorID"]) == self._receptor_ID:
                    # TODO: validate input
                    proxy_sw.tdcDestinationAddress = \
                        receptor["tdcDestinationAddress"]
                    break

        # PROTECTED REGION END #    //  Vcc.ConfigureSearchWindow

    def is_EndScan_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state == ObsState.SCANNING.value:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(Vcc.EndScan) ENABLED START #
        self._obs_state = ObsState.READY.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  Vcc.EndScan

    def is_Scan_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state == ObsState.READY.value:
            return True
        return False

    @command()
    def Scan(self):
        # PROTECTED REGION ID(Vcc.Scan) ENABLED START #
        self._obs_state = ObsState.SCANNING.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  Vcc.Scan

    def is_GoToIdle_allowed(self):
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command()
    def GoToIdle(self):
        # PROTECTED REGION ID(Vcc.GoToIdle) ENABLED START #
        # transition to obsState=IDLE
        self._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  Vcc.GoToIdle


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main


if __name__ == '__main__':
    main()
