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
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState
from skabase.SKASubarray.SKASubarray import SKASubarray
# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #

    def doppler_phase_correction_event_callback(self, event):
        if not event.err:
            try:
                # TODO: find out what to do with the coefficients
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)
                # self._dummy_1 += 1
            except Exception as e:
                self.dev_logging(str(e), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

    def delay_model_event_callback(self, event):
        if not event.err:
            try:
                # TODO: find out what to do with the coefficients
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)
                # self._dummy_2 += 1
            except Exception as e:
                self.dev_logging(str(e), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

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

    """
    dummy_1 = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
    )

    dummy_2 = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
    )
    """

    receptors = attribute(
        dtype=('int',),
        access=AttrWriteType.READ_WRITE,
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
        # self._dummy_1 = 0
        # self._dummy_2 = 0

        self._proxy_cbf_master = PyTango.DeviceProxy("mid_csp_cbf/master/main")

        self._count_vcc = 197
        self._count_fsp = 27
        self._fqdn_vcc = ["mid_csp_cbf/vcc/" + str(i + 1).zfill(3) for i in range(self._count_vcc)]
        self._fqdn_fsp = ["mid_csp_cbf/fsp/" + str(i + 1).zfill(2) for i in range(self._count_fsp)]

        # store the subscribed events as ID:attribute_proxy key:value pairs
        self._events = {}

        self.set_state(DevState.OFF)
        self._obs_state = ObsState.IDLE.value
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

    def write_receptors(self, value):
        # PROTECTED REGION ID(CbfSubarray.receptors_write) ENABLED START #
        self.RemoveReceptors(self._receptors)  # remove all receptors
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  CbfSubarray.receptors_write

    """
    def read_dummy_1(self):
        return self._dummy_1

    def read_dummy_2(self):
        return self._dummy_2
    """

    # --------
    # Commands
    # --------

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
                        log_msg = "Receptor {} already assigned to current subarray.".format(str(receptorID))
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

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  CbfSubarray.RemoveAllReceptors

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        """
        The input JSON object has the following schema:
        {
            "scanID": int,  // unique positive integer identifier for the scan
            "receptors": [int, int, int, ...],  // array of receptor IDs to add to the subarray
            "frequencyBand": int,  // integer in the range [0, 5], enumerated for frequency bands
            "frequencyOffset": [int, int, int, ...],  // frequency offset (k) specified per receptor
            "streamTuning: [float, float],  // stream tuning for frequency bands "5a" (4) and "5b" (5) (GHz); must have length 2
            "frequencyBandOffset": [int, int],  // frequency band offset (Hz); for frequency bands "5a" and "5b", must be an array of length 2
                                                // for other frequency bands, can be a scalar or an array
                                                // defaults to 0 if not specified
            "dopplerPhaseCorrectionSubscriptionPoint": str,  // FQDN of Doppler phase correction coefficients attribute of TM TelState
            "delayModelSubscriptionPoint": str  // FQDN of delay model coefficients attribute of TM TelState
            "rfiFlaggingMask": [  // exact schema of RFI flagging mask is TBD; specified per receptor per frequency slice
                {
                    "receptorID": int,
                    "frequencySliceID": int,
                    ...
                },
                ...
            ],
            "searchWindow": [  // array of maximum length 2, each element corresponding to a search window
                {
                    "searchWindowID": int,  // search window identifier; either 1 or 2, unique to the subarray
                    "searchWindowTuning": int,  // search window tuning (Hz) within observed frequency band
                    "enableTDC": bool,  // enable transient data capture
                    "numberBits": int,  // number of bits for transient data capture; one of [2, 4, 8]
                    "periodBeforeEpoch": int,  // period before epoch (s) for which data is saved
                                               // defaults to 2 if not specified
                    "periodAfterEpoch": int,  // period after epoch (s) for which data is saved
                                              // defaults to 22 if not specified
                    "destinationAddress": [  // array of [MAC address, IP address, port number] of destination addresses,
                        [str, str, str],     // specified per receptor
                        [str, str, str],
                        [str, str, str],
                        ...
                    ]
                },
                {
                    ...
                }
            ],
            "fsp": [  // array of objects to configure FSPs
                {
                    "fspID": int,  // positive integer specifying which FSP to configure
                    "functionMode": int,  // integer in the range [0, 4], enumerated for processing modes
                    "receptors": [int, int, int, ...],  // array of receptors IDs to use
                                                        // defaults to all receptors in subarray if not specified
                    "frequencySliceID": int,  // positive integer specifying which frequency slice to use as input
                    "bandwidth": int,  // integer in the range [0, 6]; the bandwidth to be correlated is <full bandwidth>/(2**bandwidth)
                    "zoomWindowTuning": int,  // zoom window tuning (kHz) within observed frequency band
                    "integrationTime": int,  // integration time for products (ms)
                    "channelAveragingMap": [  // array of [channel ID, averaging factor], specified per channel group (20 in total)
                        [int, int],           // channel ID is a positive integer, identifying the first channel of the group
                        [int, int],           // averaging factor is one of [0, 1, 2, 3, 4, 5, 6, 8]
                        [int, int],
                        ...
                    ],
                    "destinationAddress": [str, str, str]  // array of [MAC address, IP address, port number] of destination addresses
                },
                {
                    ...
                },
                ...
            ]
        }
        """
        # transition state to CONFIGURING
        self._obs_state = ObsState.CONFIGURING.value

        # unsubscribe from all previously subscribed events
        for event_id in self._events.keys():
            self._events[event_id].unsubscribe_event(event_id)

        self._events = {}

        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            # this is a fatal error
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

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
            memorized_ID = self.read_attribute("scanID").value  # TODO: fix this line
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
        # Abort the scan configuration if no receptor is assigned.
        if "receptors" in argin:
            try:
                self.AddReceptors(list(map(int, argin["receptors"])))
            except PyTango.DevFailed as df:  # receptors is malformed
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
                    Aborting configuration.".format(str(argin["frequency_band"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            # this never fails, since default value is 0, corresponding to frequency band "1"
            self._frequency_band = self.read_attribute("frequencyBand").value  # TODO: fix this line
            log_msg = "'frequencyBand' not given. Using memorized frequencyBand of {}".format(str(self._frequency_band))
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # ======================================================================= #
        # At this point, self._scan_ID, self._receptors, and self._frequency_band #
        # are guaranteed to be properly configured.                               #
        # ======================================================================= #

        # Validate frequencyOffset
        # If not given, and not previously configured, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "frequencyOffset" in argin:
            try:
                assert len(argin["frequencyOffset"]) == len(self._receptors)
                # TODO: find out valid ranges and what to do
            except (TypeError, AssertionError):  # frequencyOffset is not the right length or not an array
                msg = "\n".join(errs)
                msg += "'frequencyOffset' must be an array of length {}. \
                                    Aborting configuration.".format(str(len(self._receptors)))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # frequencyOffset not given - check if previously configured
            # TODO: write this block
            pass

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

                streamTuning = argin["streamTuning"]
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

        # Validate frequencyBandOffset.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "frequencyBandOffset" in argin:
            if self._frequency_band in [4, 5]:  # frequency band is 5a or 5b -> needs to be a 2-element array
                try:
                    assert len(argin["frequencyBandOffset"]) == 2
                    # TODO: find out valid ranges and what to do
                except (TypeError, AssertionError):  # frequencyBandOffset not the right length or not an array
                    # find out what to do
                    log_msg = "'frequencyBandOffset' must be an array of length 2 for a 'frequencyBand' of {}. \
                        Defaulting to 0 for both streams".format(str(self._frequency_band))
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)
            else:  # frequency band is 1, 2, 3, or 4 -> can be a scalar or an array
                try:
                    offset = argin["frequencyBandOffset"][0]
                except TypeError:  # frequencyBandOffset is a scalar
                    offset = argin["frequencyBandOffset"]

                # TODO: find out valid ranges and what to do
        else:  # frequencyBandOffset not given
            # TODO: find out what to do
            log_msg = "'frequencyBandOffset' not specified. Defaulting to 0 for both streams."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate dopplerPhaseCorrectionSubscriptionPoint
        # If not given, do nothing and append an error.
        # If malformed, do nothing and append an error.
        if "dopplerPhaseCorrectionSubscriptionPoint" in argin:
            try:
                attribute_proxy = PyTango.AttributeProxy(str(argin["dopplerPhaseCorrectionSubscriptionPoint"]))
                attribute_proxy.ping()

                # set up attribute polling and change events
                attribute_proxy.poll(1000)  # polling period in milliseconds, may change later
                attribute_info = attribute_proxy.get_config()
                """
                change_event_info = PyTango.ChangeEventInfo()
                change_event_info.abs_change = "1"  # subscribe to all changes
                attribute_info.events.ch_event = change_event_info
                """
                periodic_event_info = PyTango.PeriodicEventInfo()
                periodic_event_info.period = "10000"  # periodic event every 10 seconds
                attribute_info.events.per_event = periodic_event_info

                attribute_proxy.set_config(attribute_info)

                # subscribe to the event
                event_id = attribute_proxy.subscribe_event(
                    PyTango.EventType.PERIODIC_EVENT,
                    self.doppler_phase_correction_event_callback
                )
                self._events[event_id] = attribute_proxy
            except PyTango.DevFailed:  # attribute doesn't exist
                log_msg = "Attribute {} not found for 'dopplerPhaseCorrectionSubscriptionPoint'. \
                    Proceeding.".format(argin["dopplerPhaseCorrectionSubscriptionPoint"])
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)
        else:  # dopplerPhaseCorrection not given
            log_msg = "'dopplerPhaseCorrectionSubscriptionPoint' not given. Proceeding."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
            errs.append(log_msg)

        # Validate delayModelSubscriptionPoint
        # If not given, ignore the FSP and append an error.
        # If malformed, ignore the FSP and append an error.
        if "delayModelSubscriptionPoint" in argin:
            try:
                attribute_proxy = PyTango.AttributeProxy(str(argin["delayModelSubscriptionPoint"]))
                attribute_proxy.ping()

                # set up attribute polling and change events
                attribute_proxy.poll(1000)  # polling period in milliseconds, may change later
                attribute_info = attribute_proxy.get_config()
                """
                change_event_info = PyTango.ChangeEventInfo()
                change_event_info.abs_change = "1"  # subscribe to all changes
                attribute_info.events.ch_event = change_event_info
                """
                periodic_event_info = PyTango.PeriodicEventInfo()
                periodic_event_info.period = "10000"  # periodic event every 10 seconds
                attribute_info.events.per_event = periodic_event_info

                attribute_proxy.set_config(attribute_info)

                # subscribe to the event
                event_id = attribute_proxy.subscribe_event(
                    PyTango.EventType.PERIODIC_EVENT,
                    self.delay_model_event_callback
                )
                self._events[event_id] = attribute_proxy
            except PyTango.DevFailed:  # attribute doesn't exist
                msg = "\n".join(errs)
                msg += "Attribute {} not found for 'delayModelSubscriptionPoint'. \
                    Aborting configuration.".format(argin["delayModelSubscriptionPoint"])
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:
            msg = "\n".join(errs)
            msg += "'delayModelSubscriptionPoint' not given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

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

            except (TypeError, AssertionError):  # searchWindow not the right length or not an array
                log_msg = "'searchWindow' must be an array of maximum length 2. Not configuring search windows."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

        else:  # searchWindow not given
            pass  # don't do anything

        # Validate FSP.
        # If not given, append an error.
        # If malformed, append an error.
        if "fsp" in argin:
            try:
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

                    # Validate bandwidth
                    # If not given, ignore the FSP and append an error.
                    # If malformed, ignore the FSP and append an error.
                    if "bandwidth" in fsp:
                        if fsp["bandwidth"] in list(range(0, 7)):
                            # TODO: find out what to do
                            pass
                        else:
                            log_msg = "'bandwidth' must be an integer in the range [0, 6]. Ignoring FSP."
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:
                        log_msg = "FSP specified, but 'bandwidth' not given. Ignoring FSP."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # TODO: validate zoomWindowTuning

                    # Validate integrationTime
                    # If not given, ignore the FSP and append an error.
                    # If malformed, ignore the FSP and append an error.
                    if "integrationTime" in fsp:
                        if fsp["integrationTime"] in list(range(140, 1401, 140)):
                            # TODO: find out what to do
                            pass
                        else:
                            log_msg = "'integrationTime' must be an integer in the range [1, 10] multiplied by 140. \
                                Ignoring FSP."
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:
                        log_msg = "FSP specified, but 'integrationTime' not given. Ignoring FSP."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # Validate channelAveragingMap
                    # If not given, use a default value.
                    # If malformed, use a default value, but append an error.
                    if "channelAveragingMap" in fsp:
                        try:
                            # validate dimensions
                            assert len(fsp["channelAveragingMap"]) == 20
                            for i in range(20):
                                if len(fsp["channelAveragingMap"][i]) == 2:
                                    # TODO: find out valid ranges for channel ID and what to do
                                    # validate averaging factor
                                    if fsp["channelAveragingMap"][i] in [0, 1, 2, 3, 4, 5, 6, 8]:
                                        # TODO: find out what to do
                                        pass
                                    else:
                                        # TODO: find out what to do, replace placeholder string
                                        log_msg = "'channelAveragingMap'[n][1] must be one of [0, 1, 2, 3, 4, 5, 6, 8]. \
                                            Defaulting to 0 for channel {0}.".format("placeholder")
                                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                                        errs.append(log_msg)
                                else:  # no channel ID or averaging factor given
                                    # TODO: find out what to do
                                    pass
                        except (TypeError, AssertionError):  # dimensions not correct
                            # TODO: find out what to do
                            log_msg = "'channelAveragingMap' must be an array of length 20. \
                                Defaulting to averaging factor = 0 for all channels."
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)

                    # Validate destinationAddress.
                    # If not given, ignore the FSP and append an error.
                    # If malformed, ignore the FSP and append an error.
                    if "destinationAddress" in fsp:
                        # TODO: find out valid ranges and what to do
                        pass
                    else:  # destinationAddress not given
                        log_msg = "FSP specified, but 'destinationAddress' not given. Ignoring FSP."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    valid_count += 1

                # check if enough FSP configurations were successful
                num_frequency_slices = [4, 5, 7, 12, 26, 26]
                if valid_count == num_frequency_slices[self._frequency_band]:
                    pass
                elif valid_count < num_frequency_slices[self._frequency_band]:
                    log_msg = "Not enough FSPs were properly configured for the frequencyBand \
                        (expected {}, received {}). Proceeding, but with limited functionality.".format(
                            str(num_frequency_slices[self._frequency_band]),
                            str(valid_count)
                        )
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                    errs.append(log_msg)

            except TypeError:  # fsp not an array
                log_msg = "'fsp' must be an array. Proceeding, but with limited functionality."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

        else:  # fsp not given
            log_msg = "'fsp' not given. Proceeding, but with limited functionality."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
            errs.append(log_msg)

        # raise an error if something went wrong
        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution", PyTango.ErrSeverity.ERR)

        # transition state to READY
        self._obs_state = ObsState.READY.value
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
