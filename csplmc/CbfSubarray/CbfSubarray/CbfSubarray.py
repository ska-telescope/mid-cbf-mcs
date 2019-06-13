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
import copy

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

    def __doppler_phase_correction_event_callback(self, event):
        if not event.err:
            try:
                # TODO: find out what to do with the coefficients
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)
                self._report_doppler_phase_correction = event.attr_value.value
            except Exception as e:
                self.dev_logging(str(e), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

    def __delay_model_event_callback(self, event):
        if not event.err:
            try:
                # TODO: find out what to do with the coefficients
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)
                self._report_delay_model = event.attr_value.value
            except Exception as e:
                self.dev_logging(str(e), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

    def __state_change_event_callback(self, event):
        if not event.err:
            try:
                device_name = event.device.dev_name()
                if "healthstate" in event.attr_name:
                    if "vcc" in device_name:
                        self._vcc_health_state[device_name] = event.attr_value.value
                    elif "fsp" in device_name:
                        self._fsp_health_state[device_name] = event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received health state change for unknown device " + str(
                            event.attr_name)
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
                        return
                elif "state" in event.attr_name:
                    if "vcc" in device_name:
                        self._vcc_state[device_name] = event.attr_value.value
                    elif "fsp" in device_name:
                        self._fsp_state[device_name] = event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received state change for unknown device " + str(event.attr_name)
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
                        return

                log_msg = "New value for " + str(event.attr_name) + " of device " + device_name + \
                          " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)

            except Exception as except_occurred:
                self.dev_logging(str(except_occurred), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

    # PROTECTED REGION END #    //  CbfSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16',
    )


    CbfMasterAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Master",
        default_value="mid_csp_cbf/master/main"
    )


    # ----------
    # Attributes
    # ----------
















    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    scanID = attribute(
        dtype='uint',
        access=AttrWriteType.READ,
        label="Scan ID",
        doc="Scan ID",
    )

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    reportDopplerPhaseCorrection = attribute(
        dtype=('float',),
        access=AttrWriteType.READ,
        max_dim_x=4,
        label="Doppler phase correction coefficients",
        doc="Doppler phase correction coefficients (received from TM TelState)",
    )

    reportDelayModel = attribute(
        dtype='str',
        access=AttrWriteType.READ,
        label="Delay model coefficients",
        doc="Delay model coefficients (received from TM TelState)"
    )

    vccState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
        label="VCC state",
        polling_period=1000,
        doc="Report the state of the assigned VCCs as an array of DevState",
    )

    vccHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC health status",
        polling_period=1000,
        abs_change=1,
        doc="Report the health state of assigned VCCs as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    fspState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
        label="FSP state",
        polling_period=1000,
        doc="Report the state of the assigned FSPs",
    )

    fspHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP health status",
        polling_period=1000,
        abs_change=1,
        doc="Report the health state of the assigned FSPs.",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
        self.set_state(DevState.INIT)

        # get subarray ID
        if self.SubID:
            self._subarray_id = self.SubID
        else:
            self._subarray_id = int(self.get_name()[-2:])  # last two chars of FQDN

        # initialize attribute values
        self._receptors = []
        self._frequency_band = 0
        self._report_doppler_phase_correction = [0, 0, 0, 0]
        self._report_delay_model = "{}"
        self._vcc_state = {}  # device_name:state
        self._vcc_health_state = {}  # device_name:healthState
        self._fsp_state = {}  # device_name:state
        self._fsp_health_state = {}  # device_name:healthState

        # device proxy for easy reference to CBF Master
        self._proxy_cbf_master = PyTango.DeviceProxy(self.CbfMasterAddress)

        self._count_vcc = 197
        self._count_fsp = 27
        self._fqdn_vcc = [*map(lambda i: "mid_csp_cbf/vcc/{:03d}".format(i + 1),
                               range(self._count_vcc))]
        self._fqdn_fsp = [*map(lambda i: "mid_csp_cbf/fsp/{:02d}".format(i + 1),
                               range(self._count_fsp))]
        self._fqdn_fsp_subarray = [*map(lambda i: "mid_csp_cbf/fspSubarray/{0:02d}_\
            {1:02d}".format(i + 1, self._subarray_id), range(self._count_fsp))]

        self._proxies_vcc = [*map(PyTango.DeviceProxy, self._fqdn_vcc)]
        self._proxies_fsp = [*map(PyTango.DeviceProxy, self._fqdn_fsp)]
        self._proxies_fsp_subarray = [*map(PyTango.DeviceProxy, self._fqdn_fsp_subarray)]

        self._proxies_assigned_vcc = []
        self._proxies_assigned_fsp = []
        self._proxies_assigned_fsp_subarray = []

        # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
        self._events_telstate = {}

        # store the subscribed state change events as vcc_ID:[event_ID, event_ID] key:value pairs
        self._events_state_change_vcc = {}

        # store the subscribed state change events as fsp_ID:[event_ID, event_ID] key:value pairs
        self._events_state_change_fsp = {}

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

    def read_scanID(self):
        # PROTECTED REGION ID(CbfSubarray.scanID_read) ENABLED START #
        return self._scan_ID
        # PROTECTED REGION END #    //  CbfSubarray.scanID_read

    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(CbfSubarray.receptors_write) ENABLED START #
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  CbfSubarray.receptors_write

    def read_reportDopplerPhaseCorrection(self):
        # PROTECTED REGION ID(CbfSubarray.reportDopplerPhaseCorrection_read) ENABLED START #
        return self._report_doppler_phase_correction
        # PROTECTED REGION END #    //  CbfSubarray.reportDopplerPhaseCorrection_read

    def read_reportDelayModel(self):
        # PROTECTED REGION ID(CbfSubarray.reportDelayModel_read) ENABLED START #
        return self._report_delay_model
        # PROTECTED REGION END #    //  CbfSubarray.reportDelayModel_read

    def read_vccState(self):
        # PROTECTED REGION ID(CbfSubarray.vccState_read) ENABLED START #
        return list(self._vcc_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccState_read

    def read_vccHealthState(self):
        # PROTECTED REGION ID(CbfSubarray.vccHealthState_read) ENABLED START #
        return list(self._vcc_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccHealthState_read

    def read_fspState(self):
        # PROTECTED REGION ID(CbfSubarray.fspState_read) ENABLED START #
        return list(self._fsp_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspState_read

    def read_fspHealthState(self):
        # PROTECTED REGION ID(CbfSubarray.fspHealthState_read) ENABLED START #
        return list(self._fsp_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspHealthState_read



    # --------
    # Commands
    # --------

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    @DebugIt()
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.AddReceptors) ENABLED START #
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = self._proxies_vcc[vccID - 1]
                subarrayID = vccProxy.subarrayMembership

                # only add receptor if it does not already belong to a different subarray
                if subarrayID not in [0, self._subarray_id]:
                    errs.append("Receptor {} already in use by subarray {}.".format(
                        str(receptorID), str(subarrayID)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)
                        self._proxies_assigned_vcc.append(vccProxy)

                        # change subarray membership of vcc
                        vccProxy.subarrayMembership = self._subarray_id

                        # subscribe to VCC state and healthState changes
                        event_id_state, event_id_health_state = vccProxy.subscribe_event(
                            "State",
                            PyTango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback
                        ), vccProxy.subscribe_event(
                            "healthState",
                            PyTango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback
                        )
                        self._events_state_change_vcc[vccID] = [event_id_state,
                                                                event_id_health_state]
                    else:
                        log_msg = "Receptor {} already assigned to current subarray.".format(
                            str(receptorID))
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        # transition to ON if at least one receptor is assigned
        if self._receptors:
            self.set_state(DevState.ON)

        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, int(PyTango.LogLevel.LOG_ERROR))
            PyTango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                           PyTango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CbfSubarray.AddReceptors

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.RemoveReceptors) ENABLED START #
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            if receptorID in self._receptors:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = self._proxies_vcc[vccID - 1]

                self._receptors.remove(receptorID)
                self._proxies_assigned_vcc.remove(vccProxy)

                # reset subarray membership of vcc
                vccProxy.subarrayMembership = 0

                # unsubscribe from events
                vccProxy.unsubscribe_event(self._events_state_change_vcc[vccID][0])  # state
                vccProxy.unsubscribe_event(self._events_state_change_vcc[vccID][1])  # healthState
                del self._events_state_change_vcc[vccID]
                del self._vcc_state[self._fqdn_vcc[vccID - 1]]
                del self._vcc_health_state[self._fqdn_vcc[vccID - 1]]
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

        # unsubscribe from TelState events
        for event_id in self._events_telstate.keys():
            self._events_telstate[event_id].unsubscribe_event(event_id)
        self._events_telstate = {}

        # unsubscribe from FSP state change events
        for fspID, fsp_events in self._events_state_change_fsp:
            proxy_fsp = self._proxies_fsp[fspID - 1]
            proxy_fsp.unsubscribe_event(self._events_state_change_fsp[fspID][0])  # state
            proxy_fsp.unsubscribe_event(self._events_state_change_fsp[fspID][1])  # healthState
            del self._events_state_change_fsp[fspID]
            del self._fsp_state[self._fqdn_fsp[fspID - 1]]
            del self._fsp_health_state[self._fqdn_fsp[fspID - 1]]

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
            if self._scan_ID:  # scanID was memorized and non-zero
                log_msg = "'scanID' not given. Using memorized scanID of {}".format(str(self._scan_ID))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
            else:
                msg = "\n".join(errs)
                msg += "'scanID' must be given. Aborting configuration."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)

        # Validate frequencyBand.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "frequencyBand" in argin:
            if argin["frequencyBand"] in list(range(6)):  # frequencyBand must be in range [0, 5]
                self._frequency_band = argin["frequencyBand"]
                for vcc in self._proxies_assigned_vcc:
                    vcc.SetFrequencyBand(argin["frequencyBand"])
            else:
                msg = "\n".join(errs)
                msg += "'frequencyBand' must be an integer in the range [0, 5] (received {}). \
                    Aborting configuration.".format(str(argin["frequency_band"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg,
                                               "ConfigureScan execution", PyTango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            msg = "\n".join(errs)
            msg += "'frequencyBand' must be given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", PyTango.ErrSeverity.ERR)

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
                    self.__doppler_phase_correction_event_callback
                )
                self._events_telstate[event_id] = attribute_proxy
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
                    self.__delay_model_event_callback
                )
                self._events_telstate[event_id] = attribute_proxy
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

        if "rfiFlaggingMask" in argin:
            for vcc in self._proxies_assigned_vcc:
                vcc.rfiFlaggingMask = json.dumps(argin["rfiFlaggingMask"])
        else:  # rfiFlaggingMask not given
            log_msg = "'rfiFlaggingMask' not given."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate searchWindow.
        # If not given, don't configure search windows.
        # If malformed, don't configure search windows, but append an error.
        if "searchWindow" in argin:
            # check if searchWindow is an array of maximum length 2
            try:
                assert len(argin["searchWindow"]) <= 2

                for search_window in argin["searchWindow"]:
                    search_window_config = copy.deepcopy(search_window)
                    for i in range(len(self._proxies_assigned_vcc)):
                        search_window_config["destinationAddress"] = \
                            search_window["destinationAddress"][i]

                        # pass on configuration to VCC
                        self._proxies_assigned_vcc[i].ConfigureSearchWindow(
                            json.dumps(search_window_config)
                        )

            except (TypeError, AssertionError):  # searchWindow not the right length or not an array
                log_msg = "'searchWindow' must be an array of maximum length 2. \
                    Not configuring search windows."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

            except PyTango.DevFailed as df:  # ConfigureSearchWindow threw an exception
                log_msg = "An exception occurred while configuring search windows: \n" + \
                    str(df.value.args[0].desc)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

            except Exception as e:  # a number of other things can go wrong
                log_msg = "An unknown exception occurred while configuring search windows: \n" + \
                    str(e)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

        else:  # searchWindow not given
            log_msg = "'searchWindow' not given."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate FSP.
        # If not given, append an error.
        # If malformed, append an error.
        if "fsp" in argin:
            try:
                for fsp in argin["fsp"]:
                    # Validate fspID.
                    # If not given, ignore the FSP and append an error.
                    # If malformed, ignore the FSP and append an error.
                    if "fspID" in fsp:
                        if int(fsp["fspID"]) in list(range(1, self._count_fsp + 1)):
                            fspID = int(fsp["fspID"])
                            proxy_fsp = self._proxies_fsp[fspID - 1]
                            proxy_fsp_subarray = self._proxies_fsp_subarray[fspID - 1]
                            self._proxies_assigned_fsp.append(proxy_fsp)
                            self._proxies_assigned_fsp_subarray.append(proxy_fsp_subarray)

                            # change FSP subarray membership
                            proxy_fsp.AddSubarrayMembership(self._subarray_id)
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
                        if int(fsp["functionMode"]) in list(range(5)):
                            proxy_fsp.SetFunctionMode(int(fsp["functionMode"]))
                        else:
                            log_msg = "'functionMode' must be an integer in the range [0, 4] \
                                (received {}). Ignoring FSP.".format(fsp["functionMode"])
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue
                    else:
                        log_msg = "FSP specified, but 'functionMode' not given. Ignoring FSP."
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # pass on configuration to FSP Subarray
                    proxy_fsp_subarray.ConfigureScan(fsp)

                    # subscribe to FSP state and healthState changes
                    event_id_state, event_id_health_state = proxy_fsp.subscribe_event(
                        "State",
                        PyTango.EventType.CHANGE_EVENT,
                        self.__state_change_event_callback
                    ), proxy_fsp.subscribe_event(
                        "healthState",
                        PyTango.EventType.CHANGE_EVENT,
                        self.__state_change_event_callback
                    )
                    self._events_state_change_fsp[int(fsp["fspID"])] = [event_id_state,
                                                                        event_id_health_state]

            except TypeError:  # fsp not an array
                log_msg = "'fsp' must be an array."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

            except PyTango.DevFailed as df:  # FspSubarray.ConfigureScan threw an exception
                log_msg = "An exception occurred while configuring FSPs: \n" + \
                    str(df.value.args[0].desc)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)

        else:  # fsp not given
            log_msg = "'fsp' not given."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
            errs.append(log_msg)

        # raise an error if something went wrong
        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

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
