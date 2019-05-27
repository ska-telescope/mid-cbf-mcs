# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" CbfSubarray Tango device prototype

CBFSubarray TANGO device class for the CBFSubarray prototype
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
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKASubarray.SKASubarray import SKASubarray
# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
        dtype_out='str',
        doc_out="Status",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        """
        The input JSON object has the following schema:
        {
            "scanID": int,
            "receptors": [int, int, int, ...],
            "frequencyBand": int,
            "frequencyOffset": [int, int, int, ...],  (per receptor)
            "streamTuning: [float, float],
            "frequencyBandOffset": [int, int],
            "dopplerPhaseCorrection": [float, float, float, float],
            "rfiFlaggingMask": [
                {
                    "receptorID": int,
                    "frequencySliceID": int,
                    ...
                },
                ... (x <number of receptors>*<number of frequency slices>)
            ],
            "searchWindow": [
                {
                    "searchWindowID": int,
                    "searchWindowTuning": int,
                    "enableTDC": bool,
                    "numberBits": int,
                    "destinationAddress": [str, str, str]
                },
                {
                    ...
                }
            ],
            "fsp": [
                {
                    "fspID": int,
                    "functionMode": int,
                    "receptors": [int, int, int, ...],
                    "frequencySliceID": int,
                    "bandwidth": int,
                    "zoomWindowTuning": int,
                    "integrationTime": int,
                    "channelAveragingMap": [
                        [int, int],
                        [int, int],
                        [int, int],
                        ... (x20)
                    ],
                    "destinationAddress": [str, str, str],
                    "delayTrackingCalibration": [float, float, float, ... (x6)]
                },
                ... (x <number of frequency slices> (more for different processing modes))
            ]
        }
        """
        errs = []

        # Validate scanID.
        # If not given, use memorized scanID if valid.
        # If malformed, abort the scan configuration.
        if "scanID" in argin:
            try:
                val = int(argin["scanID"])
                if val > 0:  # scanID must be positive
                    self._scan_ID = val
                else:  # scanID not positive
                    msg = "\n".join(errs)
                    msg += "'scanID' must be positive (received {}). Aborting configuration.".format(str(val))
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureScan execution", PyTango.ErrSeverity.ERR)
            except ValueError:  # scanID not an int (or something that can be converted to an int)
                msg = "\n".join(errs)
                msg += "'scanID' must be an integer (received {}). Aborting configuration.".format(str(argin["scanID"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # scanID not given
            memorized_ID = self.read_attribute("scanID").value
            # memorized scanID must be non-zero
            if memorized_ID == 0:
                msg = "\n".join(errs)
                msg += "'scanID' must be given (memorized scanID is zero). Aborting configuration."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
            else:
                self._scan_ID = memorized_ID
                log_msg = "'scanID' not given. Using memorized scanID of {}".format(str(self._scan_ID))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate receptors.
        # If not given, use previously assigned receptors.
        # If malformed, use previously assigned receptors, but append an error.
        if "receptors" in argin:
            try:
                self.command_inout("AddReceptors", argin["receptors"])
            except DevFailed as df:  # receptors is malformed
                self.dev_logging(df.args[0].desc, PyTango.LogLevel.LOG_ERROR)
                errs.append(df.args[0].desc)
        # check if at least one receptor is assigned
        if not self._receptors:
            msg = "\n".join(errs)
            msg += "At least one receptor must be assigned to the subarray. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

        # Validate frequencyBand.
        # If not given, use memorized frequencyBand.
        # If malformed, abort the scan configuration.
        if "frequencyBand" in argin:
            if argin["frequencyBand"] in list(range(6)):  # frequencyBand must be in range [0, 5]
                self._frequency_band = argin["frequencyBand"]
            else:
                msg = "\n".join(errs)
                msg += "'frequencyBand' must be an integer in the range [0, 5] (received {}). \
                    Aborting configuration.".format(str(frequency_band))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            # this never fails, since default value is 0, corresponding to frequency band "1"
            self._frequency_band = self.read_attribute("frequencyBand").value
            log_msg = "'frequencyBand' not given. Using memorized frequencyBand of {}".format(str(self._frequency_band))
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # TODO: validate frequencyOffset

        # Validate streamTuning, if frequencyBand is 4 or 5.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "streamTuning" in argin:
            if self._frequency_band in [4, 5]:
                # check if streamTuning is an array of length 2
                try:
                    assert len(argin["streamTuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "\n".join(errs)
                    msg += "'streamTuning' must be an array of length 2. Aborting configuration."
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureScan execution", PyTango.ErrSeverity.ERR)

                try:
                    if 5.85 <= float(streamTuning[0]) <= 7.25:
                        # TODO: find out what to do
                        pass
                    else:
                        raise ValueError  # this is bad form, but makes it more convenient to handle

                    if 9.55 <= float(streamTuning[1]) <= 14.05:
                        # TODO: find out what to do
                        pass
                    else:
                        raise ValueError  # this is bad form, but makes it more convenient to handle
                except ValueError:
                    msg = "\n".join(errs)
                    msg += "'streamTuning[0]' must be a float between 5.85 and 7.25 (received {}), \
                           and 'streamTuning[1]' must be a float between 9.55 and 14.05 (received {}). \
                           Aborting configuration.".format(str(streamTuning[0]), str(streamTuning[1]))
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureScan execution", PyTango.ErrSeverity.ERR)
            else:
                log_msg = "'frequencyBand' is not 4 or 5, but 'streamTuning' was given. Ignoring."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        elif self._frequency_band in [4, 5]:
            msg = "\n".join(errs)
            msg += "'streamTuning' must be given for a 'frequencyBand' of {}. \
                Aborting configuration".format(str(self._frequency_band))
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

        # TODO: validate frequencyBandOffset.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.

        # TODO: validate dopplerPhaseCorrection
        # TODO: validate rfiFlaggingMask

        # Validate searchWindow.
        # If not given, don't configure search windows.
        # If malformed, don't configure search windows, but append an error.
        if "searchWindow" in argin:
            # check if searchWindow is an array of maximum length 2
            try:
                assert len(argin["searchWindow"]) <= 2

                for search_window in argin["searchWindow"]:
                    # Validate searchWindowID.
                    # If not given, ignore the entire search window and append an error.
                    # If malformed, ignore the entire search window and append an error.
                    if "searchWindowID" in search_window:
                        if search_window["searchWindowID"] in [1, 2]:
                            # TODO: find out what to do
                            pass
                        else:  # searchWindowID not in valid range
                            log_msg = "'searchWindowID' must be one of [1, 2] (received {}). \
                                Ignoring search window".format(str(search_window["searchWindowID"]))
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:  # searchWindowID not given
                        log_msg = "Search window specified, but 'searchWindowID' not given. Ignoring search window."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate searchWindowTuning.
                    # If not given, ignore the entire search window and append an error.
                    # If malformed, ignore the entire search window and append an error.
                    if "searchWindowTuning" in search_window:
                        # TODO: find out what the valid range is
                        pass
                    else:  # searchWindowTuning not given
                        log_msg = "Search window specified, but 'searchWindowTuning' not given. Ignoring search window."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate enableTDC.
                    # If not given, use a default value.
                    # If malformed, use a default value, but append an error.
                    if "enableTDC" in search_window:
                        if search_window["enableTDC"] in [True, False]:
                            # TODO: find out what to do
                            pass
                        else:
                            # TODO: find out what to do
                            log_msg = "'enableTDC' must be one of [True, False] (received {}). \
                                Defaulting to False.".format(str(search_window["enableTDC"]))
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                    else:  # enableTDC not given
                        # TODO: find out what to do
                        log_msg = "Search window specified, but 'enableTDC' not given. Defaulting to False."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

                    # Validate numberBits.
                    # If not given, ignore the entire search window and append an error.
                    # If malformed, ignore the entire search window and append an error.
                    if "numberBits" in search_window:
                        if search_window["numberBits"] in [2, 4, 8]:
                            # TODO: find out what to do
                            pass
                        else:
                            log_msg = "'numberBits' must be one of [2, 4, 8] (received {}). \
                                Ignoring search window.".format(str(search_window["numberBits"]))
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:  # numberBits not given
                        log_msg = "Search window specified, but 'numberBits' not given. Ignoring search window."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate destinationAddress.
                    # If not given, do nothing.
                    # If malformed, do nothing, but append an error.
                    if "destinationAddress" in search_window:
                        # TODO: find out valid ranges and what to do
                        pass
                    else:  # destinationAddress not given
                        log_msg = "Search window specified, but 'destinationAddress' not given. Proceeding."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except (TypeError, AssertionError):
                log_msg = "'searchWindow' must be an array of maximum length 2."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

        else:  # searchWindow not given
            pass  # don't do anything

        # Validate FSP.
        # If not given, append an error.
        # If malformed, append an error.
        if "fsp" in argin:
            # TODO: validate number of FSPs
            valid_count = 0

            for fsp in argin["fsp"]:
                # Validate fspID.
                # If not given, ignore the FSP and append an error.
                # If malformed, ignore the FSP and append an error.
                if "fspID" in fsp:
                    if fsp["fspID"] in list(range(1, self._count_fsp + 1)):
                        # TODO: find out what to do
                        pass
                    else:
                        log_msg = "'fspID' must be an integer in the range [1, {}]. \
                            Ignoring FSP.".format(str(self._count_fsp))
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue
                else:
                    log_msg = "FSP specified, but 'fspID' not given. Ignoring FSP."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
                    continue

                # Validate functionMode
                # If not given, ignore the FSP and append an error.
                # If malformed, ignore the FSP and append an error.
                if "functionMode" in fsp:
                    if fsp["functionMode"] in list(range(5)):  # TODO: double check the size of the enumeration
                        # TODO: find out what to do
                        pass
                    else:
                        log_msg = "'functionMode' must be an integer in the range [0, 4]. Ignoring FSP."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue
                else:
                    log_msg = "FSP specified, but 'functionMode' not given. Ignoring FSP."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
                    continue

                # Validate receptors
                # If not given, use all receptors assigned to the subarray.
                # If malformed, use all receptors assigned to the subarray, but append an error.
                if "receptors" in fsp:
                    # TODO: find out what to do
                    pass
                else:
                    # TODO: find out what to do
                    log_msg = "'receptors' not given. Using all available receptors."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

                # Validate frequencySliceID
                # If not given, ignore the FSP and append an error.
                # If malformed, ignore the FSP and append an error.
                if "frequencySliceID" in fsp:
                    num_frequency_slices = [4, 5, 7, 12, 26, 26]
                    if fsp["frequencySliceID"] in list(range(1, num_frequency_slices[self._frequency_band] + 1)):
                        # TODO: find out what to do
                        pass
                    else:
                        log_msg = "'frequencySliceID' must be an integer in the range [1, {}] \
                            for a 'frequencyBand' of {}. Ignoring FSP.".format(
                                str(num_frequency_slices[self._frequency_band]),
                                str(self._frequency_band)
                            )
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue
                else:
                    log_msg = "FSP specified, but 'frequencySliceID' not given. Ignoring FSP."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
                    continue
        else:
            log_msg = "'fsp' not given. Proceeding, but with limited functionality."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
            errs.append(log_msg)

        # PROTECTED REGION END #    //  CbfSubarray.ConfigureScan

    # PROTECTED REGION END #    //  CbfSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------








    # ----------
    # Attributes
    # ----------
















    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band",
        memorized=True,
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    scanID = attribute(
        dtype='uint64',
        access=AttrWriteType.READ_WRITE,
        label="Scan ID",
        memorized=True,
        doc="Scan ID",
    )



    receptors = attribute(
        dtype=('int',),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
        self.set_state(DevState.INIT)

        self._frequency_band = 0
        self._scan_ID = 0
        self._receptors = []

        self._proxy_cbf_master = PyTango.DeviceProxy("mid_csp_cbf/master/main")

        self._count_vcc = 197
        self._count_fsp = 27
        self._fqdn_vcc = ["mid_csp_cbf/vcc/" + str(i + 1).zfill(3) for i in range(self._count_vcc)]
        self._fqdn_fsp = ["mid_csp_cbf/fsp/" + str(i + 1).zfill(2) for i in range(self._count_fsp)]

        self.set_state(DevState.OFF)
        # PROTECTED REGION END #    //  CbfSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_frequencyBand(self):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_read) ENABLED START #
        return self._frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def write_frequencyBand(self, value):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_write) ENABLED START #
        self._frequency_band = value
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_write

    def read_scanID(self):
        # PROTECTED REGION ID(CbfSubarray.scanID_read) ENABLED START #
        return self._scan_ID
        # PROTECTED REGION END #    //  CbfSubarray.scanID_read

    def write_scanID(self, value):
        # PROTECTED REGION ID(CbfSubarray.scanID_write) ENABLED START #
        self._scan_ID = value
        # PROTECTED REGION END #    //  CbfSubarray.scanID_write

    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read


    # --------
    # Commands
    # --------

    @command(
    dtype_in='str', 
    doc_in="Scan configuration", 
    dtype_out='str', 
    doc_out="Status", 
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        # argin will be a JSON object, with schema TBD
        return ""
        # PROTECTED REGION END #    //  CbfSubarray.ConfigureScan

    @command(
        dtype_in=('int',),
        doc_in="List of receptor IDs",
    )
    @DebugIt()
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.AddReceptors) ENABLED START #
        errs = []  # list of error messages
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = PyTango.DeviceProxy("mid_csp_cbf/vcc/" + str(vccID).zfill(3))
                subarrayID = vccProxy.subarrayMembership

                # only add receptor if it does not already belong to a different subarray
                if subarrayID not in [0, int(self.get_name()[-2:])]:
                    errs.append("Receptor {} already in use by subarray {}.".format(str(receptorID), str(subarrayID)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)

                        # change subarray membership of vcc
                        # last two chars of fqdn is subarrayID
                        vccProxy.subarrayMembership = int(self.get_name()[-2:])
                    else:
                        log_msg = "Receptor {} already assigned to subarray.".format(str(receptorID))
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        # transition to ON if at least one receptor is assigned
        if self._receptors:
            self.set_state(DevState.ON)

        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, int(PyTango.LogLevel.LOG_ERROR))
            PyTango.Except.throw_exception("Command failed", msg, "AddReceptors execution", PyTango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CbfSubarray.AddReceptors

    @command(
        dtype_in=('int',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.RemoveReceptors) ENABLED START #
        receptor_to_vcc = dict([int(ID) for ID in pair.split(":")] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            if receptorID in self._receptors:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = PyTango.DeviceProxy("mid_csp_cbf/vcc/" + str(vccID).zfill(3))

                self._receptors.remove(receptorID)

                # reset subarray membership of vcc
                vccProxy.subarrayMembership = 0
            else:
                log_msg = "Receptor {} not assigned to subarray. Skipping.".format(str(receptorID))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # transitions to OFF if not assigned any receptors
        if not self._receptors:
            self.set_state(DevState.OFF)
        # PROTECTED REGION END #    //  CbfSubarray.RemoveReceptors

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
        dtype_out='str',
        doc_out="Status",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        """
        The input JSON object has the following schema:
        {
            "scanID": int,
            "receptors": [int, int, int, ...],
            "frequencyBand": int,
            "frequencyOffset": [int, int, int, ...],  (per receptor)
            "streamTuning: [float, float],
            "frequencyBandOffset": [int, int],
            "dopplerPhaseCorrection": [float, float, float, float],
            "rfiFlaggingMask": [
                {
                    "receptorID": int,
                    "frequencySliceID": int,
                    ...
                },
                ... (x <number of receptors>*<number of frequency slices>)
            ],
            "searchWindow": [
                {
                    "searchWindowID": int,
                    "searchWindowTuning": int,
                    "enableTDC": bool,
                    "numberBits": int,
                    "destinationAddress": [str, str, str]
                },
                {
                    ...
                }
            ],
            "fsp": [
                {
                    "fspID": int,
                    "functionMode": int,
                    "receptors": [int, int, int, ...],
                    "frequencySliceID": int,
                    "bandwidth": int,
                    "zoomWindowTuning": int,
                    "integrationTime": int,
                    "channelAveragingMap": [
                        [int, int],
                        [int, int],
                        [int, int],
                        ... (x20)
                    ],
                    "destinationAddress": [str, str, str],
                    "delayTrackingCalibration": [float, float, float, ... (x6)]
                },
                ... (x <number of frequency slices> (more for different processing modes))
            ]
        }
        """
        errs = []

        # Validate scanID.
        # If not given, use memorized scanID if valid.
        # If malformed, abort the scan configuration.
        if "scanID" in argin:
            try:
                val = int(argin["scanID"])
                if val > 0:  # scanID must be positive
                    self._scan_ID = val
                else:  # scanID not positive
                    msg = "\n".join(errs)
                    msg += "'scanID' must be positive (received {}). Aborting configuration.".format(str(val))
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureScan execution", PyTango.ErrSeverity.ERR)
            except ValueError:  # scanID not an int (or something that can be converted to an int)
                msg = "\n".join(errs)
                msg += "'scanID' must be an integer (received {}). Aborting configuration.".format(str(argin["scanID"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # scanID not given
            memorized_ID = self.read_attribute("scanID").value
            # memorized scanID must be non-zero
            if memorized_ID == 0:
                msg = "\n".join(errs)
                msg += "'scanID' must be given (memorized scanID is zero). Aborting configuration."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
            else:
                self._scan_ID = memorized_ID
                log_msg = "'scanID' not given. Using memorized scanID of {}".format(str(self._scan_ID))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate receptors.
        # If not given, use previously assigned receptors.
        # If malformed, use previously assigned receptors, but append an error.
        if "receptors" in argin:
            try:
                self.command_inout("AddReceptors", argin["receptors"])
            except DevFailed as df:  # receptors is malformed
                self.dev_logging(df.args[0].desc, PyTango.LogLevel.LOG_ERROR)
                errs.append(df.args[0].desc)
        # check if at least one receptor is assigned
        if not self._receptors:
            msg = "\n".join(errs)
            msg += "At least one receptor must be assigned to the subarray. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

        # Validate frequencyBand.
        # If not given, use memorized frequencyBand.
        # If malformed, abort the scan configuration.
        if "frequencyBand" in argin:
            if argin["frequencyBand"] in list(range(6)):  # frequencyBand must be in range [0, 5]
                self._frequency_band = argin["frequencyBand"]
            else:
                msg = "\n".join(errs)
                msg += "'frequencyBand' must be an integer in the range [0, 5] (received {}). \
                    Aborting configuration.".format(str(frequency_band))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            # this never fails, since default value is 0, corresponding to frequency band "1"
            self._frequency_band = self.read_attribute("frequencyBand").value
            log_msg = "'frequencyBand' not given. Using memorized frequencyBand of {}".format(str(self._frequency_band))
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # TODO: validate frequencyOffset

        # Validate streamTuning, if frequencyBand is 4 or 5.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "streamTuning" in argin:
            if self._frequency_band in [4, 5]:
                # check if streamTuning is an array of length 2
                try:
                    assert len(argin["streamTuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "\n".join(errs)
                    msg += "'streamTuning' must be an array of length 2. Aborting configuration."
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureScan execution", PyTango.ErrSeverity.ERR)

                try:
                    if 5.85 <= float(streamTuning[0]) <= 7.25:
                        # TODO: find out what to do
                        pass
                    else:
                        raise ValueError  # this is bad form, but makes it more convenient to handle

                    if 9.55 <= float(streamTuning[1]) <= 14.05:
                        # TODO: find out what to do
                        pass
                    else:
                        raise ValueError  # this is bad form, but makes it more convenient to handle
                except ValueError:
                    msg = "\n".join(errs)
                    msg += "'streamTuning[0]' must be a float between 5.85 and 7.25 (received {}), \
                           and 'streamTuning[1]' must be a float between 9.55 and 14.05 (received {}). \
                           Aborting configuration.".format(str(streamTuning[0]), str(streamTuning[1]))
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg,
                                                   "ConfigureScan execution", PyTango.ErrSeverity.ERR)
            else:
                log_msg = "'frequencyBand' is not 4 or 5, but 'streamTuning' was given. Ignoring."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        elif self._frequency_band in [4, 5]:
            msg = "\n".join(errs)
            msg += "'streamTuning' must be given for a 'frequencyBand' of {}. \
                Aborting configuration".format(str(self._frequency_band))
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

        # TODO: validate frequencyBandOffset.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.

        # TODO: validate dopplerPhaseCorrection
        # TODO: validate rfiFlaggingMask

        # Validate searchWindow.
        # If not given, don't configure search windows.
        # If malformed, don't configure search windows, but append an error.
        if "searchWindow" in argin:
            # check if searchWindow is an array of maximum length 2
            try:
                assert len(argin["searchWindow"]) <= 2

                for search_window in argin["searchWindow"]:
                    # Validate searchWindowID.
                    # If not given, ignore the entire search window and append an error.
                    # If malformed, ignore the entire search window and append an error.
                    if "searchWindowID" in search_window:
                        if search_window["searchWindowID"] in [1, 2]:
                            # TODO: find out what to do
                            pass
                        else:  # searchWindowID not in valid range
                            log_msg = "'searchWindowID' must be one of [1, 2] (received {}). \
                                Ignoring search window".format(str(search_window["searchWindowID"]))
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:  # searchWindowID not given
                        log_msg = "Search window specified, but 'searchWindowID' not given. Ignoring search window."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate searchWindowTuning.
                    # If not given, ignore the entire search window and append an error.
                    # If malformed, ignore the entire search window and append an error.
                    if "searchWindowTuning" in search_window:
                        # TODO: find out what the valid range is
                        pass
                    else:  # searchWindowTuning not given
                        log_msg = "Search window specified, but 'searchWindowTuning' not given. Ignoring search window."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate enableTDC.
                    # If not given, use a default value.
                    # If malformed, use a default value, but append an error.
                    if "enableTDC" in search_window:
                        if search_window["enableTDC"] in [True, False]:
                            # TODO: find out what to do
                            pass
                        else:
                            # TODO: find out what to do
                            log_msg = "'enableTDC' must be one of [True, False] (received {}). \
                                Defaulting to False.".format(str(search_window["enableTDC"]))
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                    else:  # enableTDC not given
                        # TODO: find out what to do
                        log_msg = "Search window specified, but 'enableTDC' not given. Defaulting to False."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

                    # Validate numberBits.
                    # If not given, ignore the entire search window and append an error.
                    # If malformed, ignore the entire search window and append an error.
                    if "numberBits" in search_window:
                        if search_window["numberBits"] in [2, 4, 8]:
                            # TODO: find out what to do
                            pass
                        else:
                            log_msg = "'numberBits' must be one of [2, 4, 8] (received {}). \
                                Ignoring search window.".format(str(search_window["numberBits"]))
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:  # numberBits not given
                        log_msg = "Search window specified, but 'numberBits' not given. Ignoring search window."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate destinationAddress.
                    # If not given, do nothing.
                    # If malformed, do nothing, but append an error.
                    if "destinationAddress" in search_window:
                        # TODO: find out valid ranges and what to do
                        pass
                    else:  # destinationAddress not given
                        log_msg = "Search window specified, but 'destinationAddress' not given. Proceeding."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except (TypeError, AssertionError):
                log_msg = "'searchWindow' must be an array of maximum length 2."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

        else:  # searchWindow not given
            pass  # don't do anything

        # Validate FSP.
        # If not given, append an error.
        # If malformed, append an error.
        if "fsp" in argin:
            # TODO: validate number of FSPs
            valid_count = 0

            for fsp in argin["fsp"]:
                # Validate fspID.
                # If not given, ignore the FSP and append an error.
                # If malformed, ignore the FSP and append an error.
                if "fspID" in fsp:
                    if fsp["fspID"] in list(range(1, self._count_fsp + 1)):
                        # TODO: find out what to do
                        pass
                    else:
                        log_msg = "'fspID' must be an integer in the range [1, {}]. \
                            Ignoring FSP.".format(str(self._count_fsp))
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue
                else:
                    log_msg = "FSP specified, but 'fspID' not given. Ignoring FSP."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
                    continue

                # Validate functionMode
                # If not given, ignore the FSP and append an error.
                # If malformed, ignore the FSP and append an error.
                if "functionMode" in fsp:
                    if fsp["functionMode"] in list(range(5)):  # TODO: double check the size of the enumeration
                        # TODO: find out what to do
                        pass
                    else:
                        log_msg = "'functionMode' must be an integer in the range [0, 4]. Ignoring FSP."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue
                else:
                    log_msg = "FSP specified, but 'functionMode' not given. Ignoring FSP."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
                    continue

                # Validate receptors
                # If not given, use all receptors assigned to the subarray.
                # If malformed, use all receptors assigned to the subarray, but append an error.
                if "receptors" in fsp:
                    # TODO: find out what to do
                    pass
                else:
                    # TODO: find out what to do
                    log_msg = "'receptors' not given. Using all available receptors."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

                # Validate frequencySliceID
                # If not given, ignore the FSP and append an error.
                # If malformed, ignore the FSP and append an error.
                if "frequencySliceID" in fsp:
                    num_frequency_slices = [4, 5, 7, 12, 26, 26]
                    if fsp["frequencySliceID"] in list(range(1, num_frequency_slices[self._frequency_band] + 1)):
                        # TODO: find out what to do
                        pass
                    else:
                        log_msg = "'frequencySliceID' must be an integer in the range [1, {}] \
                            for a 'frequencyBand' of {}. Ignoring FSP.".format(
                                str(num_frequency_slices[self._frequency_band]),
                                str(self._frequency_band)
                            )
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue
                else:
                    log_msg = "FSP specified, but 'frequencySliceID' not given. Ignoring FSP."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
                    continue
        else:
            log_msg = "'fsp' not given. Proceeding, but with limited functionality."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
            errs.append(log_msg)

        # PROTECTED REGION END #    //  CbfSubarray.ConfigureScan

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main

if __name__ == '__main__':
    main()
