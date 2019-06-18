# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Vcc Tango device prototype

Vcc TANGO device class for the prototype
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
# PROTECTED REGION ID(Vcc.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  Vcc.additionnal_import

__all__ = ["Vcc", "main"]


class Vcc(SKACapability):
    """
    Vcc TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(Vcc.class_variable) ENABLED START #

    def __get_capability_proxies(self):
        # for now, assume that given addresses are valid
        if self.Band1And2Address:
            self._proxy_band_12 = PyTango.DeviceProxy(self.Band1And2Address)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "vcc_band12"
            self._proxy_band_12 = PyTango.DeviceProxy("/".join(names))

        if self.Band3Address:
            self._proxy_band_3 = PyTango.DeviceProxy(self.Band3Address)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "vcc_band3"
            self._proxy_band_3 = PyTango.DeviceProxy("/".join(names))

        if self.Band4Address:
            self._proxy_band_4 = PyTango.DeviceProxy(self.Band4Address)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "vcc_band4"
            self._proxy_band_4 = PyTango.DeviceProxy("/".join(names))

        if self.Band5Address:
            self._proxy_band_5 = PyTango.DeviceProxy(self.Band5Address)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "vcc_band5"
            self._proxy_band_5 = PyTango.DeviceProxy("/".join(names))

        if self.TDCAddress1:
            self._proxy_tdc_1 = PyTango.DeviceProxy(self.TDCAddress1)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "vcc_tdc1"
            self._proxy_tdc_1 = PyTango.DeviceProxy("/".join(names))

        if self.TDCAddress2:
            self._proxy_tdc_2 = PyTango.DeviceProxy(self.TDCAddress2)
        else:
            # use this default value
            names = self.get_name().split("/")
            names[1] = "vcc_tdc2"
            self._proxy_tdc_2 = PyTango.DeviceProxy("/".join(names))

    # PROTECTED REGION END #    //  Vcc.class_variable

    # -----------------
    # Device Properties
    # -----------------

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

    TDCAddress1 = device_property(
        dtype='str'
    )

    TDCAddress2 = device_property(
        dtype='str'
    )


    # ----------
    # Attributes
    # ----------

















    receptorID = attribute(
        dtype='uint16',
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


    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(Vcc.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value

        # defines self._proxy_band_12, self._proxy_band_3, self._proxy_band_4, self._proxy_band_5,
        # self._proxy_tdc_1, and self._proxy_tdc_2
        self.__get_capability_proxies()

        # the bands are already disabled on initialization
        # self._proxy_band_12.SetState(PyTango.DevState.DISABLE)
        # self._proxy_band_3.SetState(PyTango.DevState.DISABLE)
        # self._proxy_band_4.SetState(PyTango.DevState.DISABLE)
        # self._proxy_band_5.SetState(PyTango.DevState.DISABLE)
        # self._proxy_tdc_1.SetState(PyTango.DevState.DISABLE)
        # self._proxy_tdc_2.SetState(PyTango.DevSTate.DISABLE)

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

        self.set_state(PyTango.DevState.OFF)
        # PROTECTED REGION END #    //  Vcc.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(Vcc.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Vcc.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptorID(self):
        # PROTECTED REGION ID(Vcc.receptorID_read) ENABLED START #
        return self._receptor_ID
        # PROTECTED REGION END #    //  Vcc.receptorID_read

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Vcc.subarrayMembership_read) ENABLED START #
        return self._subarray_membership
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_read

    def write_subarrayMembership(self, value):
        # PROTECTED REGION ID(Vcc.subarrayMembership_write) ENABLED START #
        self._subarray_membership = value
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


    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(Vcc.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  Vcc.SetState

    @command(
        dtype_in='uint16',
        doc_in='New health state'
    )
    def SetHealthState(self, argin):
        # PROTECTED REGION ID(Vcc.SetHealthState) ENABLED START #
        self._health_state = argin
        # PROTECTED REGION END #    //  Vcc.SetHealthState

    @command(
        dtype_in='str',
        doc_in='New frequency band'
    )
    def SetFrequencyBand(self, argin):
        # PROTECTED REGION ID(Vcc.SetFrequencyBand) ENABLED START #
        if argin in ["1", "2"]:
            self._frequency_band = ["1", "2"].index(argin)
            self._proxy_band_12.SetState(PyTango.DevState.ON)
            self._proxy_band_3.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_4.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_5.SetState(PyTango.DevState.DISABLE)
        elif argin == "3":
            self._frequency_band = 2
            self._proxy_band_12.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_3.SetState(PyTango.DevState.ON)
            self._proxy_band_4.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_5.SetState(PyTango.DevState.DISABLE)
        elif argin == "4":
            self._frequency_band = 3
            self._proxy_band_12.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_3.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_4.SetState(PyTango.DevState.ON)
            self._proxy_band_5.SetState(PyTango.DevState.DISABLE)
        elif argin in ["5a", "5b"]:
            self._frequency_band = ["5a", "5b"].index(argin) + 4
            self._proxy_band_12.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_3.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_4.SetState(PyTango.DevState.DISABLE)
            self._proxy_band_5.SetState(PyTango.DevState.ON)

        # shouldn't happen
        self.dev_logging("frequencyBand not in valid range. Ignoring.",
                         PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    // Vcc.SetFrequencyBand

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ConfigureSearchWindow(self, argin):
        # PROTECTED REGION ID(Vcc.ConfigureSearchWindow) ENABLED START #

        # transition state to CONFIGURING
        self._obs_state = ObsState.CONFIGURING.value

        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            # this is a fatal error
            msg = "Search window configuration object is not a valid JSON object. Aborting "
            "configuration."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                           PyTango.ErrSeverity.ERR)

        errs = []

        # variable to use as TDC proxy
        proxy_tdc = 0

        # Validate searchWindowID.
        # If not given, ignore the entire search window and append an error.
        # If malformed, ignore the entire search window and append an error.
        if "searchWindowID" in argin:
            if int(argin["searchWindowID"]) == 1:
                proxy_tdc = self._proxy_tdc_1
            elif int(argin["searchWindowID"]) == 2:
                proxy_tdc = self._proxy_tdc_2
            else:  # searchWindowID not in valid range
                msg = "\n".join(errs)
                msg += "'searchWindowID' must be one of [1, 2] (received {}). "
                "Ignoring search window".format(str(argin["searchWindowID"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureSearchWindow execution",
                                               PyTango.ErrSeverity.ERR)
        else:  # searchWindowID not given
            msg = "\n".join(errs)
            msg += "Search window specified, but 'searchWindowID' not given. "
            "Ignoring search window."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate searchWindowTuning.
        # If not given, ignore the entire search window and append an error.
        # If malformed, ignore the entire search window and append an error.
        if "searchWindowTuning" in argin:
            # TODO: validate input
            proxy_tdc.searchWindowTuning = argin["searchWindowTuning"]
        else:  # searchWindowTuning not given
            msg = "\n".join(errs)
            msg += "Search window specified, but 'searchWindowTuning' not given. "
            "Ignoring search window."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate tdcEnable.
        # If not given, ignore the entire search window and append an error.
        # If not given, ignore the entire search window and append an error.
        if "tdcEnable" in argin:
            if argin["tdcEnable"] in [True, False]:
                proxy_tdc.tdcEnable = argin["tdcEnable"]
                if argin["tdcEnable"]:
                    # transition to ON if TDC is enabled
                    proxy_tdc.SetState(PyTango.DevState.ON)
            else:
                msg = "\n".join(errs)
                msg += "Search window specified, but 'tdcEnable' not given. "
                "Ignoring search window."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureSearchWindow execution",
                                               PyTango.ErrSeverity.ERR)
        else:  # enableTDC not given
            msg = "\n".join(errs)
            msg += "Search window specified, but 'tdcEnable' not given. "
            "Ignoring search window."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate tdcNumBits.
        # If not given when required, ignore the entire search window and append an error.
        # If malformed when required, ignore the entire search window and append an error.
        if proxy_tdc.tdcEnable:
            if "tdcNumBits" in argin:
                if int(argin["tdcNumBits"]) in [2, 4, 8]:
                    proxy_tdc.tdcNumBits = int(argin["tdcNumBits"])
                else:
                    msg = "\n".join(errs)
                    msg += "'tdcNumBits' must be one of [2, 4, 8] (received {}). "
                    "Ignoring search window.".format(str(argin["tdcNumBits"]))
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureSearchWindow execution",
                                                   PyTango.ErrSeverity.ERR)
            else:  # numberBits not given
                msg = "\n".join(errs)
                msg += "Search window specified, but 'tdcNumBits' not given. "
                "Ignoring search window."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureSearchWindow execution",
                                               PyTango.ErrSeverity.ERR)

        # Validate tdcPeriodBeforeEpoch.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "tdcPeriodBeforeEpoch" in argin:
            if int(argin["tdcPeriodBeforeEpoch"]) > 0:
                proxy_tdc.tdcPeriodBeforeEpoch = int(argin["tdcPeriodBeforeEpoch"])
            else:
                proxy_tdc.tdcPeriodBeforeEpoch = 2
                log_msg = "'tdcPeriodBeforeEpoch' must be a positive integer (received {}). "
                "Defaulting to 2.".format(str(argin["tdcPeriodBeforeEpoch"]))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)
        else:  # periodBeforeEpoch not given
            proxy_tdc.tdcPeriodBeforeEpoch = 2
            log_msg = "Search window specified, but 'tdcPeriodBeforeEpoch' not given. "
            "Defaulting to 2."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate tdcPeriodAfterEpoch.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "tdcPeriodAfterEpoch" in argin:
            if int(argin["tdcPeriodAfterEpoch"]) > 0:
                proxy_tdc.tdcPeriodAfterEpoch = int(argin["tdcPeriodAfterEpoch"])
            else:
                proxy_tdc.tdcPeriodAfterEpoch = 22
                log_msg = "'tdcPeriodAfterEpoch' must be a positive integer (received {}). "
                "Defaulting to 22.".format(str(argin["tdcPeriodAfterEpoch"]))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)
        else:  # periodAfterEpoch not given
            proxy_tdc.tdcPeriodAfterEpoch = 22
            log_msg = "Search window specified, but 'tdcPeriodAfterEpoch' not given. "
            "Defaulting to 22."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate destinationAddress.
        # If not given when required, ignore the entire search window and append an error.
        # If malformed when required, ignore the entire search window and append and error.
        if proxy_tdc.tdcEnable:
            if "destinationAddress" in argin:
                # TODO: validate input
                proxy_tdc.tdcDestinationAddress = argin["destinationAddress"]
            else:  # destinationAddress not given
                # due to implementation details, this should never happen
                msg = "\n".join(errs)
                msg += "Search window specified, but 'destinationAddress' not given. "
                "Ignoring search window."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureSearchWindow execution",
                                               PyTango.ErrSeverity.ERR)

        # raise an error if something went wrong
        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                           PyTango.ErrSeverity.ERR)

        # transition state to IDLE when done
        self._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  Vcc.ConfigureSearchWindow

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main

if __name__ == '__main__':
    main()
