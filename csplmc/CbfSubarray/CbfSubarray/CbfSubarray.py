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
                for vcc in self._proxies_assigned_vcc:
                    vcc.dopplerPhaseCorrection = event.attr_value.value
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)
            except Exception as e:
                self.dev_logging(str(e), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

    def __delay_model_event_callback(self, event):
        if not event.err:
            try:
                for fsp_subarray in self._proxies_assigned_fsp_subarray:
                    fsp_subarray.delayModel = event.attr_value.value
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_DEBUG)
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
        self._scan_ID = 0
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
        self._fqdn_fsp_subarray = [*map(lambda i: "mid_csp_cbf/fspSubarray/{0:02d}_"
                                   "{1:02d}".format(i + 1, self._subarray_id),
                                        range(self._count_fsp))]

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
            "scanID": int,
            "frequencyBand": str,
            "band5Tuning: [float, float],
            "frequencyBandOffsetStream1": int,
            "frequencyBandOffsetStream2": int,
            "dopplerPhaseCorrSubscriptionPoint": str,
            "delayModelSubscriptionPoint": str,
            "visDestinationAddressSubscriptionPoint": str,
            "rfiFlaggingMask": {
                ...
            },
            "searchWindow": [
                {
                    "searchWindowID": int,
                    "searchWindowTuning": int,
                    "tdcEnable": bool,
                    "tdcNumBits": int,
                    "tdcPeriodBeforeEpoch": int,
                    "tdcPeriodAfterEpoch": int,
                    "tdcDestinationAddress": [
                        {
                            "receptorID": int,
                            "destinationAddress": [str, str, str]
                        }
                    ]
                },
                {
                    ...
                }
            ],
            "fsp": [
                {
                    "fspID": int,
                    "functionMode": str,
                    "receptors": [int, int, int, ...],
                    "frequencySliceID": int,
                    "corrBandwidth": int,
                    "zoomWindowTuning": int,
                    "integrationTime": int,
                    "channelAveragingMap": [
                        [int, int],
                        [int, int],
                        [int, int],
                        ...
                    ]
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

        # change FSP subarray membership
        for proxy_fsp in self._proxies_assigned_fsp:
            proxy_fsp.RemoveSubarrayMembership(self._subarray_id)
        self._proxies_assigned_fsp = []

        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            # this is a fatal error
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        errs = []

        # Validate scanID.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "scanID" in argin:
            if int(argin["scanID"]) <= 0:  # scanID not positive
                msg = "\n".join(errs)
                msg += "'scanID' must be positive (received {}). "\
                    "Aborting configuration.".format(int(argin["scanID"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
            elif any(map(lambda i: i == int(argin["scanID"]),
                         self._proxy_cbf_master.subarrayScanID)):  # scanID already taken
                msg = "\n".join(errs)
                msg += "'scanID' must be unique (received {}). "\
                    "Aborting configuration.".format(int(argin["scanID"]))
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
            else:  # scanID is valid
                self._scan_ID = int(argin["scanID"])
        else:  # scanID not given
            msg = "\n".join(errs)
            msg += "'scanID' must be given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate frequencyBand.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if "frequencyBand" in argin:
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            if argin["frequencyBand"] in frequency_bands:
                self._frequency_band = frequency_bands.index(argin["frequencyBand"])
                for vcc in self._proxies_assigned_vcc:
                    vcc.SetFrequencyBand(argin["frequencyBand"])
            else:
                msg = "\n".join(errs)
                msg += "'frequencyBand' must be one of {} (received {}). "\
                    "Aborting configuration.".format(frequency_bands, argin["frequency_band"])
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
        else:  # frequencyBand not given
            msg = "\n".join(errs)
            msg += "'frequencyBand' must be given. Aborting configuration."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # ======================================================================= #
        # At this point, self._scan_ID, self._receptors, and self._frequency_band #
        # are guaranteed to be properly configured.                               #
        # ======================================================================= #

        # Validate band5Tuning, if frequencyBand is 5a or 5b.
        # If not given, abort the scan configuration.
        # If malformed, abort the scan configuration.
        if self._frequency_band in [4, 5]:  # frequency band is 5a or 5b
            if "band5Tuning" in argin:
                # check if streamTuning is an array of length 2
                try:
                    assert len(argin["band5Tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "\n".join(errs)
                    msg += "'band5Tuning' must be an array of length 2. Aborting configuration."
                    # this is a fatal error
                    self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                    PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                   PyTango.ErrSeverity.ERR)

                stream_tuning = [*map(float, argin["band5Tuning"])]
                if self._frequency_band == 4:
                    if all([5.85 <= stream_tuning[i] <= 7.25 for i in [0, 1]]):
                        for vcc in self._proxies_assigned_vcc:
                            vcc.band5Tuning = stream_tuning
                    else:
                        msg = "\n".join(errs)
                        msg += "Elements in 'band5Tuning must be floats between 5.85 and 7.25 "\
                            "(received {} and {}) for a 'frequencyBand' of 5a. "\
                            "Aborting configuration.".format(stream_tuning[0], stream_tuning[1])
                        # this is a fatal error
                        self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                        PyTango.Except.throw_exception("Command failed", msg,
                                                       "ConfigureScan execution",
                                                       PyTango.ErrSeverity.ERR)
                else:  # self._frequency_band == 5
                    if all([9.55 <= stream_tuning[i] <= 14.05 for i in [0, 1]]):
                        for vcc in self._proxies_assigned_vcc:
                            vcc.band5Tuning = stream_tuning
                    else:
                        msg = "\n".join(errs)
                        msg += "Elements in 'band5Tuning must be floats between 9.55 and 14.05 "\
                            "(received {} and {}) for a 'frequencyBand' of 5b. "\
                            "Aborting configuration.".format(stream_tuning[0], stream_tuning[1])
                        # this is a fatal error
                        self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                        PyTango.Except.throw_exception("Command failed", msg,
                                                       "ConfigureScan execution",
                                                       PyTango.ErrSeverity.ERR)
            else:
                msg = "\n".join(errs)
                msg += "'band5Tuning' must be given for a 'frequencyBand' of {}. "\
                    "Aborting configuration".format(["5a", "5b"][self._frequency_band - 4])
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)

        # Validate frequencyBandOffsetStream1.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "frequencyBandOffsetStream1" in argin:
            # TODO: validate input
            for vcc in self._proxies_assigned_vcc:
                vcc.frequencyBandOffsetStream1 = int(argin["frequencyBandOffsetStream1"])
        else:  # frequencyBandOffsetStream1 not given
            for vcc in self._proxies_assigned_vcc:
                vcc.frequencyBandOffsetStream1 = 0
            log_msg = "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate frequencyBandOffsetStream2.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if self._frequency_band in [4, 5]:
            if "frequencyBandOffsetStream2" in argin:
                # TODO: validate input
                for vcc in self._proxies_assigned_vcc:
                    vcc.frequencyBandOffsetStream2 = int(argin["frequencyBandOffsetStream2"])
            else:  # frequencyBandOffsetStream2 not given
                for vcc in self._proxies_assigned_vcc:
                    vcc.frequencyBandOffsetStream2 = 0
                log_msg = "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate dopplerPhaseCorrSubscriptionPoint
        # If not given, do nothing.
        # If malformed, do nothing, but append an error.
        if "dopplerPhaseCorrSubscriptionPoint" in argin:
            try:
                attribute_proxy = PyTango.AttributeProxy(argin["dopplerPhaseCorrSubscriptionPoint"])
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
                log_msg = "Attribute {} not found for 'dopplerPhaseCorrSubscriptionPoint'. "\
                    "Proceeding.".format(argin["dopplerPhaseCorrSubscriptionPoint"])
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)
        else:  # dopplerPhaseCorrection not given
            log_msg = "'dopplerPhaseCorrectionSubscriptionPoint' not given. Proceeding."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate delayModelSubscriptionPoint
        # If not given, append an error.
        # If malformed, append an error.
        if "delayModelSubscriptionPoint" in argin:
            try:
                attribute_proxy = PyTango.AttributeProxy(argin["delayModelSubscriptionPoint"])
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
                log_msg = "Attribute {} not found for 'delayModelSubscriptionPoint'. "\
                    "Proceeding".format(argin["delayModelSubscriptionPoint"])
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)
        else:
            log_msg = "'delayModelSubscriptionPoint' not given. Proceeding.".format(
                argin["delayModelSubscriptionPoint"])
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
            errs.append(log_msg)

        # TODO: Validate visDestinationAddressSubscriptionPoint
        # If not given, append an error.
        # If malformed, append an error.

        # Validate rfiFlaggingMask
        # If not given, do nothing.
        # If malformed, do nothing, but append an error
        if "rfiFlaggingMask" in argin:
            for vcc in self._proxies_assigned_vcc:
                vcc.rfiFlaggingMask = json.dumps(argin["rfiFlaggingMask"])
        else:  # rfiFlaggingMask not given
            log_msg = "'rfiFlaggingMask' not given. Proceeding."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # Validate searchWindow.
        # If not given, don't configure search windows.
        # If malformed, don't configure search windows, but append an error.
        if "searchWindow" in argin:
            # check if searchWindow is an array of maximum length 2
            try:
                assert len(argin["searchWindow"]) <= 2

                for search_window in argin["searchWindow"]:
                    for vcc in self._proxies_assigned_vcc:
                        try:
                            # pass on configuration to VCC
                            vcc.ConfigureSearchWindow(json.dumps(search_window))
                        except PyTango.DevFailed:  # exception in ConfigureSearchWindow
                            log_msg = "An exception occurred while configuring search "\
                                "windows:\n" + str(sys.exc_info()[1].args[0].desc)
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)

            except (TypeError, AssertionError):  # searchWindow not the right length or not an array
                log_msg = "'searchWindow' must be an array of maximum length 2. "\
                    "Not configuring search windows."
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
                    try:
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
                                log_msg = "'fspID' must be an integer in the range [1, {}]. "\
                                    "Ignoring FSP.".format(str(self._count_fsp))
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
                            function_modes = ["CORR", "PSS-BF", "PST-BF", "VLBI"]
                            if fsp["functionMode"] in function_modes:
                                proxy_fsp.SetFunctionMode(fsp["functionMode"])
                            else:
                                log_msg = "'functionMode' must be one of {} (received {}). "\
                                    "Ignoring FSP.".format(function_modes, fsp["functionMode"])
                                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                                errs.append(log_msg)
                                continue
                        else:
                            log_msg = "FSP specified, but 'functionMode' not given. Ignoring FSP."
                            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                            errs.append(log_msg)
                            continue

                        fsp["frequencyBand"] = argin["frequencyBand"]
                        if "receptors" not in fsp:
                            fsp["receptors"] = self._receptors

                        # pass on configuration to FSP Subarray
                        proxy_fsp_subarray.ConfigureScan(json.dumps(fsp))

                        # subscribe to FSP state and healthState changes
                        # if code flow reaches this point, FSP configuration was successful
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

                    except PyTango.DevFailed:  # exception in ConfigureScan
                        log_msg = "An exception occurred while configuring FSPs: \n" + \
                            sys.exc_info()[1].args[0].desc
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)

            except Exception as e:  # a number of other things can go wrong
                log_msg = "An unknown exception occurred while configuring FSPs: \n" + \
                    str(e)
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
