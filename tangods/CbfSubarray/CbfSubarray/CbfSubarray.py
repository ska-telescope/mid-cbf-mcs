# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: An Yu An.Yu@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# CbfSubarray Tango device prototype
# CBFSubarray TANGO device class for the CBFSubarray prototype


# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import DevState
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint
from threading import Thread, Lock
import time
import copy

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import const, freq_band_dict
from ska_tango_base.control_model import ObsState, AdminMode
from ska_tango_base import SKASubarray
from ska_tango_base.commands import ResultCode, BaseCommand, ResponseCommand, ActionCommand

# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


def validate_ip(ip):
    splitip = ip.split('.')
    if len(splitip) != 4:
        return False
    for ipparts in splitip:
        if not ipparts.isdigit():
            return False
        ipval = int(ipparts)
        if ipval < 0 or ipval > 255:
            return False
    return True


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """

    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #
    def init_command_objects(self):
        """
        Sets up the command objects. Register the new Commands here.
        """
        super().init_command_objects()
        device_args = (self, self.state_model, self.logger)
        # resource_args = (self.resource_manager, self.state_model, self.logger) 
        # only use resource_args if we want to have separate resource_manager object

        self.register_command_object(
            "Configure",
            self.ConfigureCommand(*device_args)
        )       
        self.register_command_object(
            "AddReceptors",
            self.AddReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveReceptors",
            self.RemoveReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveAllReceptors",
            self.RemoveAllReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "ConfigureScan",
            self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "StartScan",
            self.ScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle",
            self.GoToIdleCommand(*device_args)
        )
        
    # ----------
    # Helper functions
    # ----------

    def _void_callback(self, event):
        # This callback is only meant to be used to test if a subscription is valid
        if not event.err:
            pass
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def _doppler_phase_correction_event_callback(self, event):
        if not event.err:
            try:
                self._group_vcc.write_attribute("dopplerPhaseCorrection", event.attr_value.value)
                log_msg = "Value of " + str(event.attr_name) + " is " + str(event.attr_value.value)
                self.logger.debug(log_msg)
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.desc + item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def _delay_model_event_callback(self, event):

        self.logger.debug("Entering _delay_model_event_callback()")

        if not event.err:
            if self._obs_state not in [ObsState.READY, ObsState.SCANNING]:
                log_msg = "Ignoring delay model (obsState not correct)."
                self.logger.warn(log_msg)
                return
            try:
                log_msg = "Received delay model update."
                self.logger.warn(log_msg)

                value = str(event.attr_value.value)
                if value == self._last_received_delay_model:
                    log_msg = "Ignoring delay model (identical to previous)."
                    self.logger.warn(log_msg)
                    return

                self._last_received_delay_model = value
                delay_model_all = json.loads(value)

                for delay_model in delay_model_all["delayModel"]:
                    t = Thread(
                        target=self._update_delay_model,
                        args=(delay_model["destinationType"], 
                              int(delay_model["epoch"]), 
                              json.dumps(delay_model["delayDetails"])
                        )
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def _update_delay_model(self, destination_type, epoch, model):
        # This method is always called on a separate thread
        log_msg = "Delay model active at {} (currently {})...".format(epoch, int(time.time()))
        self.logger.warn(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = "Updating delay model at specified epoch {}...".format(epoch)
        self.logger.warn(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, model)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_delay_model_config.acquire()
        if destination_type == "vcc":
            self._group_vcc.command_inout("UpdateDelayModel", data)
        elif destination_type == "fsp":
            self._group_fsp.command_inout("UpdateDelayModel", data)
        self._mutex_delay_model_config.release()

    def _jones_matrix_event_callback(self, event):
        self.logger.debug("CbfSubarray._jones_matrix_event_callback")
        if not event.err:
            if self._obs_state not in [ObsState.READY, ObsState.SCANNING]:
                log_msg = "Ignoring Jones matrix (obsState not correct)."
                self.logger.warn(log_msg)
                return
            try:
                log_msg = "Received Jones Matrix update."
                self.logger.warn(log_msg)

                value = str(event.attr_value.value)
                if value == self._last_received_jones_matrix:
                    log_msg = "Ignoring Jones matrix (identical to previous)."
                    self.logger.warn(log_msg)
                    return

                self._last_received_jones_matrix = value
                jones_matrix_all = json.loads(value)

                for jones_matrix in jones_matrix_all["jonesMatrix"]:
                    t = Thread(
                        target=self._update_jones_matrix,
                        args=(jones_matrix["destinationType"], 
                              int(jones_matrix["epoch"]), 
                              json.dumps(jones_matrix["matrixDetails"])
                        )
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def _update_jones_matrix(self, destination_type, epoch, matrix_details):
        #This method is always called on a separate thread
        self.logger.debug("CbfSubarray._update_jones_matrix")
        log_msg = "Jones matrix active at {} (currently {})...".format(epoch, int(time.time()))
        self.logger.warn(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = "Updating Jones Matrix at specified epoch {}, destination ".format(epoch) + destination_type
        self.logger.warn(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, matrix_details)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_jones_matrix_config.acquire()
        if destination_type == "vcc":
            self._group_vcc.command_inout("UpdateJonesMatrix", data)
        elif destination_type == "fsp":
            self._group_fsp.command_inout("UpdateJonesMatrix", data)
        self._mutex_jones_matrix_config.release()

    def _beam_weights_event_callback(self, event):
        self.logger.debug("CbfSubarray._beam_weights_event_callback")
        if not event.err:
            if self._obs_state not in [ObsState.READY, ObsState.SCANNING]:
                log_msg = "Ignoring beam weights (obsState not correct)."
                self.logger.warn(log_msg)
                return
            try:
                log_msg = "Received beam weights update."
                self.logger.warn(log_msg)

                value = str(event.attr_value.value)
                if value == self._last_received_beam_weights:
                    log_msg = "Ignoring beam weights (identical to previous)."
                    self.logger.warn(log_msg)
                    return

                self._last_received_beam_weights = value
                beam_weights_all = json.loads(value)

                for beam_weights in beam_weights_all["beamWeights"]:
                    t = Thread(
                        target=self._update_beam_weights,
                        args=(int(beam_weights["epoch"]), 
                              json.dumps(beam_weights["beamWeightsDetails"])
                        )
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def _update_beam_weights(self, epoch, weights_details):
        #This method is always called on a separate thread
        self.logger.debug("CbfSubarray._update_beam_weights")
        log_msg = "Beam weights active at {} (currently {})...".format(epoch, int(time.time()))
        self.logger.warn(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = "Updating beam weights at specified epoch {}".format(epoch)
        self.logger.warn(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, weights_details)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_beam_weights_config.acquire()
        self._group_fsp.command_inout("UpdateBeamWeights", data)
        self._mutex_beam_weights_config.release()

    def _state_change_event_callback(self, event):
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
                        self.logger.warn(log_msg)
                        return
                elif "state" in event.attr_name:
                    if "vcc" in device_name:
                        self._vcc_state[device_name] = event.attr_value.value
                    elif "fsp" in device_name:
                        self._fsp_state[device_name] = event.attr_value.value
                    else:
                        # should NOT happen!
                        log_msg = "Received state change for unknown device " + str(event.attr_name)
                        self.logger.warn(log_msg)
                        return

                log_msg = "New value for " + str(event.attr_name) + " of device " + device_name + \
                          " is " + str(event.attr_value.value)
                self.logger.warn(log_msg)

            except Exception as except_occurred:
                self.logger.error(str(except_occurred))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)


    #TODO: currently unused; trim to keep only necessary validation
    def _validate_scan_configuration(self, argin):
        # try to deserialize input string to a JSON object
        try:
            configuration = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        for proxy in self._proxies_assigned_vcc:
            if proxy.State() != tango.DevState.ON:
                msg = "VCC {} is not ON. Aborting configuration.".format(
                    self._proxies_vcc.index(proxy) + 1
                )
                self._raise_configure_scan_fatal_error(msg)

        # Validate frequencyBand.
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        if configuration["frequencyBand"] in frequency_bands:
            pass
        else:
            msg = "'frequencyBand' must be one of {} (received {}). " \
                    "Aborting configuration.".format(frequency_bands, configuration["frequency_band"])
            self._raise_configure_scan_fatal_error(msg)
        
        # Validate frequencyBandOffsetStream1.
        if abs(int(configuration["frequencyBandOffsetStream1"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
            pass
        else:
            msg = "Absolute value of 'frequencyBandOffsetStream1' must be at most half " \
                    "of the frequency slice bandwidth. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        # Validate band5Tuning, frequencyBandOffsetStream2 if frequencyBand is 5a or 5b.
        if configuration["frequencyBand"] in ["5a", "5b"]:
            # band5Tuning is optional
            if "band5Tuning" in configuration:
                pass
                # check if streamTuning is an array of length 2
                try:
                    assert len(configuration["band5Tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                    self._raise_configure_scan_fatal_error(msg)

                stream_tuning = [*map(float, configuration["band5Tuning"])]
                if configuration["frequencyBand"] == "5a":
                    if all(
                            [const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0] <= stream_tuning[i]
                             <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1] for i in [0, 1]]
                    ):
                        pass
                    else:
                        msg = "Elements in 'band5Tuning must be floats between {} and {} " \
                              "(received {} and {}) for a 'frequencyBand' of 5a. " \
                              "Aborting configuration.".format(
                            const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0],
                            const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1],
                            stream_tuning[0],
                            stream_tuning[1]
                        )
                        self._raise_configure_scan_fatal_error(msg)
                else:  # configuration["frequencyBand"] == "5b"
                    if all(
                            [const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0] <= stream_tuning[i]
                             <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1] for i in [0, 1]]
                    ):
                        pass
                    else:
                        msg = "Elements in 'band5Tuning must be floats between {} and {} " \
                              "(received {} and {}) for a 'frequencyBand' of 5b. " \
                              "Aborting configuration.".format(
                            const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0],
                            const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1],
                            stream_tuning[0],
                            stream_tuning[1]
                        )
                        self._raise_configure_scan_fatal_error(msg)
            else:
                # set band5Tuning to zero for the rest of the test. This won't 
                # change the argin in function "configureScan(argin)"
                configuration["band5Tuning"] = [0, 0]
            # Validate frequencyBandOffsetStream2.
            if abs(int(configuration["frequencyBandOffsetStream2"])) <= \
                    const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream2' must be at most " \
                        "half of the frequency slice bandwidth. Aborting configuration."
                self._raise_configure_scan_fatal_error(msg)

        # Validate dopplerPhaseCorrSubscriptionPoint.
        try:
            attribute_proxy = tango.AttributeProxy(configuration["dopplerPhaseCorrSubscriptionPoint"])
            attribute_proxy.ping()
            attribute_proxy.unsubscribe_event(
                attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    self._void_callback
                )
            )
        except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
            msg = "Attribute {} not found or not set up correctly for " \
                    "'dopplerPhaseCorrSubscriptionPoint'. Aborting configuration.".format(
                configuration["dopplerPhaseCorrSubscriptionPoint"]
            )
            self._raise_configure_scan_fatal_error(msg)

        # Validate delayModelSubscriptionPoint.
        try:
            attribute_proxy = tango.AttributeProxy(configuration["delayModelSubscriptionPoint"])
            attribute_proxy.ping()
            attribute_proxy.unsubscribe_event(
                attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    self._void_callback
                )
            )
        except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
            msg = "Attribute {} not found or not set up correctly for " \
                    "'delayModelSubscriptionPoint'. Aborting configuration.".format(
                configuration["delayModelSubscriptionPoint"]
            )
            self._raise_configure_scan_fatal_error(msg)

        # Validate jonesMatrixSubscriptionPoint.
        try:
            attribute_proxy = tango.AttributeProxy(configuration["jonesMatrixSubscriptionPoint"])
            attribute_proxy.ping()
            attribute_proxy.unsubscribe_event(
                attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    self._void_callback
                )
            )
        except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
            msg = "Attribute {} not found or not set up correctly for " \
                    "'jonesMatrixSubscriptionPoint'. Aborting configuration.".format(
                configuration["jonesMatrixSubscriptionPoint"]
            )
            self._raise_configure_scan_fatal_error(msg)
        
        # Validate beamWeightsSubscriptionPoint.
        try:
            attribute_proxy = tango.AttributeProxy(configuration["beamWeightsSubscriptionPoint"])
            attribute_proxy.ping()
            attribute_proxy.unsubscribe_event(
                attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    self._void_callback
                )
            )
        except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
            msg = "Attribute {} not found or not set up correctly for " \
                    "'beamWeightsSubscriptionPoint'. Aborting configuration.".format(
                configuration["beamWeightsSubscriptionPoint"]
            )
            self._raise_configure_scan_fatal_error(msg)


        # Validate searchWindow.
        # check if searchWindow is an array of maximum length 2
        if len(configuration["searchWindow"]) > 2:
            msg = "'searchWindow' must be an array of maximum length 2. " \
                    "Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)
        for search_window in configuration["searchWindow"]:
            for vcc in self._proxies_assigned_vcc:
                try:
                    search_window["frequencyBand"] = configuration["frequencyBand"]
                    if "frequencyBandOffsetStream1" in configuration:
                        search_window["frequencyBandOffsetStream1"] = \
                            configuration["frequencyBandOffsetStream1"]
                    else:
                        search_window["frequencyBandOffsetStream1"] = 0
                    if "frequencyBandOffsetStream2" in configuration:
                        search_window["frequencyBandOffsetStream2"] = \
                            configuration["frequencyBandOffsetStream2"]
                    else:
                        search_window["frequencyBandOffsetStream2"] = 0
                    if configuration["frequencyBand"] in ["5a", "5b"]:
                        search_window["band5Tuning"] = configuration["band5Tuning"]

                    # pass on configuration to VCC
                    vcc.ValidateSearchWindow(json.dumps(search_window))

                except tango.DevFailed:  # exception in Vcc.ValidateSearchWindow
                    msg = "An exception occurred while configuring VCC search " \
                            "windows:\n{}\n. Aborting configuration.".format(
                        str(sys.exc_info()[1].args[0].desc)
                    )
                    self._raise_configure_scan_fatal_error(msg)

        # Validate fsp.
        for fsp in configuration["fsp"]:
            try:
                # Validate fspID.
                if int(fsp["fspID"]) in list(range(1, self._count_fsp + 1)):
                    fspID = int(fsp["fspID"])
                    proxy_fsp = self._proxies_fsp[fspID - 1]
                    if fsp["functionMode"] == "CORR":
                        proxy_fsp_subarray = self._proxies_fsp_corr_subarray[fspID - 1]
                    elif fsp["functionMode"] == "PSS-BF":
                        proxy_fsp_subarray = self._proxies_fsp_pss_subarray[fspID - 1]
                    elif fsp["functionMode"] == "PST-BF":
                        proxy_fsp_subarray = self._proxies_fsp_pst_subarray[fspID - 1]
                else:
                    msg = "'fspID' must be an integer in the range [1, {}]. " \
                            "Aborting configuration.".format(str(self._count_fsp))
                    self._raise_configure_scan_fatal_error(msg)

                if proxy_fsp.State() != tango.DevState.ON:
                    msg = "FSP {} is not ON. Aborting configuration.".format(fspID)
                    self._raise_configure_scan_fatal_error(msg)

                if proxy_fsp_subarray.State() != tango.DevState.ON:
                    msg = "Subarray {} of FSP {} is not ON. Aborting configuration.".format(
                        self._subarray_id, fspID
                    )
                    self._raise_configure_scan_fatal_error(msg)

                # Validate functionMode.
                function_modes = ["CORR", "PSS-BF", "PST-BF", "VLBI"]
                if fsp["functionMode"] in function_modes:
                    if function_modes.index(fsp["functionMode"]) + 1 == \
                            proxy_fsp.functionMode or \
                            proxy_fsp.functionMode == 0:
                        pass
                    else:
                        #TODO need to add this check for VLBI once implemented
                        for fsp_corr_subarray_proxy in self._proxies_fsp_corr_subarray:
                            if fsp_corr_subarray_proxy.obsState != ObsState.IDLE:
                                msg = "A different subarray is using FSP {} for a " \
                                        "different function mode. Aborting configuration.".format(
                                        fsp["fspID"]
                                        )
                                self._raise_configure_scan_fatal_error(msg)
                        for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
                            if fsp_pss_subarray_proxy.obsState != ObsState.IDLE:
                                msg = "A different subarray is using FSP {} for a " \
                                        "different function mode. Aborting configuration.".format(
                                        fsp["fspID"]
                                        )
                                self._raise_configure_scan_fatal_error(msg)
                        for fsp_pst_subarray_proxy in self._proxies_fsp_pst_subarray:
                            if fsp_pst_subarray_proxy.obsState != ObsState.IDLE:
                                msg = "A different subarray is using FSP {} for a " \
                                        "different function mode. Aborting configuration.".format(
                                        fsp["fspID"]
                                        )
                                self._raise_configure_scan_fatal_error(msg)
                else:
                    msg = "'functionMode' must be one of {} (received {}). " \
                            "Aborting configuration.".format(
                        function_modes, fsp["functionMode"]
                    )
                    self._raise_configure_scan_fatal_error(msg)

                # TODO - why add these keys to the fsp dict - not good practice!
                # TODO - create a new dict from a deep copy of the fsp dict.
                fsp["frequencyBand"] = configuration["frequencyBand"]
                if "frequencyBandOffsetStream1" in configuration:
                    fsp["frequencyBandOffsetStream1"] = configuration["frequencyBandOffsetStream1"]
                else:
                    fsp["frequencyBandOffsetStream1"] = 0
                if "frequencyBandOffsetStream2" in configuration:
                    fsp["frequencyBandOffsetStream2"] = configuration["frequencyBandOffsetStream2"]
                else:
                    fsp["frequencyBandOffsetStream2"] = 0
                if configuration["frequencyBand"] in ["5a", "5b"]:
                    fsp["band5Tuning"] = configuration["band5Tuning"]

                # --------------------------------------------------------

                ########## CORR ##########

                if fsp["functionMode"] == "CORR":

                    if "receptors" in fsp:
                        for this_rec in fsp["receptors"]:
                            if this_rec not in self._receptors:
                                msg = ("Receptor {} does not belong to subarray {}.".format(
                                    str(self._receptors[this_rec]), str(self._subarray_id)))
                                self.logger.error(msg)
                                self._raise_configure_scan_fatal_error(msg)
                    else:
                        msg = "'receptors' not specified for Fsp CORR config"
                        # TODO - In this case by the ICD, all subarray allocated 
                        #        resources should be used.
                        fsp["receptors"] = self._receptors

                    frequencyBand = freq_band_dict()[fsp["frequencyBand"]]
                    # Validate frequencySliceID.
                    # TODO: move these to consts
                    # See for ex. Fig 8-2 in the Mid.CBF DDD 
                    num_frequency_slices = [4, 5, 7, 12, 26, 26]
                    if int(fsp["frequencySliceID"]) in list(
                            range(1, num_frequency_slices[frequencyBand] + 1)):
                        pass
                    else:
                        msg = "'frequencySliceID' must be an integer in the range [1, {}] " \
                                "for a 'frequencyBand' of {}.".format(
                            str(num_frequency_slices[frequencyBand]),
                            str(fsp["frequencyBand"])
                        )
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # Validate corrBandwidth.
                    if int(fsp["corrBandwidth"]) in list(range(0, 7)):
                        pass
                    else:
                        msg = "'corrBandwidth' must be an integer in the range [0, 6]."
                        # this is a fatal error
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # Validate zoomWindowTuning.
                    if int(fsp["corrBandwidth"]) > 0:  # zoomWindowTuning is required
                        if "zoomWindowTuning" in fsp:

                            if fsp["frequencyBand"] not in ["5a", "5b"]:  # frequency band is not band 5
                                frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(fsp["frequencyBand"])
                                frequency_band_start = [*map(lambda j: j[0] * 10 ** 9, [
                                    const.FREQUENCY_BAND_1_RANGE,
                                    const.FREQUENCY_BAND_2_RANGE,
                                    const.FREQUENCY_BAND_3_RANGE,
                                    const.FREQUENCY_BAND_4_RANGE
                                ])][frequencyBand] + fsp["frequencyBandOffsetStream1"]
                                
                                frequency_slice_range = (
                                    frequency_band_start + \
                                    (fsp["frequencySliceID"] - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6,
                                    frequency_band_start +
                                    fsp["frequencySliceID"] * const.FREQUENCY_SLICE_BW * 10 ** 6
                                )

                                if frequency_slice_range[0] <= \
                                        int(fsp["zoomWindowTuning"]) * 10 ** 3 <= \
                                        frequency_slice_range[1]:
                                    pass
                                else:
                                    msg = "'zoomWindowTuning' must be within observed frequency slice."
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg,
                                                                    "ConfigureScan execution",
                                                                    tango.ErrSeverity.ERR)
                            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                                if configuration["band5Tuning"] == [0,0]: # band5Tuning not specified
                                    pass
                                else:

                                    # TODO: these validations of BW range are done many times
                                    # in many places - use a commom function; also may be possible
                                    # to do them only once (ex. for band5Tuning)

                                    frequency_slice_range_1 = (
                                        fsp["band5Tuning"][0] * 10 ** 9 + fsp["frequencyBandOffsetStream1"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        (fsp["frequencySliceID"] - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6,
                                        fsp["band5Tuning"][0] * 10 ** 9 + fsp["frequencyBandOffsetStream1"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        fsp["frequencySliceID"] * const.FREQUENCY_SLICE_BW * 10 ** 6
                                    )

                                    frequency_slice_range_2 = (
                                        fsp["band5Tuning"][1] * 10 ** 9 + fsp["frequencyBandOffsetStream2"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        (fsp["frequencySliceID"] - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6,
                                        fsp["band5Tuning"][1] * 10 ** 9 + fsp["frequencyBandOffsetStream2"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        fsp["frequencySliceID"] * const.FREQUENCY_SLICE_BW * 10 ** 6
                                    )

                                    if (frequency_slice_range_1[0] <= int(fsp["zoomWindowTuning"]) * 10 ** 3 <=
                                        frequency_slice_range_1[1]) or \
                                            (frequency_slice_range_2[0] <=
                                            int(fsp["zoomWindowTuning"]) * 10 ** 3 <=
                                            frequency_slice_range_2[1]):
                                        pass
                                    else:
                                        msg = "'zoomWindowTuning' must be within observed frequency slice."
                                        self.logger.error(msg)
                                        tango.Except.throw_exception("Command failed", msg,
                                                                    "ConfigureScan execution",
                                                                    tango.ErrSeverity.ERR)
                        else:
                            msg = "FSP specified, but 'zoomWindowTuning' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg,
                                                            "ConfigureScan execution",
                                                            tango.ErrSeverity.ERR)

                    # Validate integrationTime.
                    if int(fsp["integrationTime"]) in list(
                            range (self.MIN_INT_TIME, 10 * self.MIN_INT_TIME + 1, self.MIN_INT_TIME)
                    ):
                        pass
                    else:
                        msg = "'integrationTime' must be an integer in the range [1, 10] multiplied " \
                                "by {}.".format(self.MIN_INT_TIME)
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # Validate fspChannelOffset
                    try: 
                        if int(fsp["fspChannelOffset"])>=0: 
                            pass
                        #TODO has to be a multiple of 14880
                        else:
                            msg="fspChannelOffset must be greater than or equal to zero"
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)
                    except:
                        msg="fspChannelOffset must be an integer"
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # validate outputlink
                    # check the format
                    try:
                        for element in fsp["outputLinkMap"]:
                            a, b = (int(element[0]), int(element[1]))
                    except:
                        msg = "'outputLinkMap' format not correct."
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                    tango.ErrSeverity.ERR)

                    # Validate channelAveragingMap.
                    if "channelAveragingMap" in fsp:
                        try:
                            # validate dimensions
                            for i in range(0,len(fsp["channelAveragingMap"])):
                                assert len(fsp["channelAveragingMap"][i]) == 2

                            # validate averaging factor
                            for i in range(0,len(fsp["channelAveragingMap"])):
                                # validate channel ID of first channel in group
                                if int(fsp["channelAveragingMap"][i][0]) == \
                                        i * self.NUM_FINE_CHANNELS / self.NUM_CHANNEL_GROUPS:
                                    pass  # the default value is already correct
                                else:
                                    msg = "'channelAveragingMap'[{0}][0] is not the channel ID of the " \
                                          "first channel in a group (received {1}).".format(
                                        i,
                                        fsp["channelAveragingMap"][i][0]
                                    )
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg,
                                                                 "ConfigureScan execution",
                                                                 tango.ErrSeverity.ERR)

                                # validate averaging factor
                                if int(fsp["channelAveragingMap"][i][1]) in [0, 1, 2, 3, 4, 6, 8]:
                                    pass
                                else:
                                    msg = "'channelAveragingMap'[{0}][1] must be one of " \
                                            "[0, 1, 2, 3, 4, 6, 8] (received {1}).".format(
                                        i,
                                        fsp["channelAveragingMap"][i][1]
                                    )
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg,
                                                                    "ConfigureScan execution",
                                                                    tango.ErrSeverity.ERR)
                        except (TypeError, AssertionError):  # dimensions not correct
                            msg = "channel Averaging Map dimensions not correct"
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                            tango.ErrSeverity.ERR)

                    # TODO: validate destination addresses: outputHost, outputMac, outputPort?

                # --------------------------------------------------------

                ########## PSS-BF ##########

                if fsp["functionMode"] == "PSS-BF":
                    if int(fsp["searchWindowID"]) in [1, 2]:
                        pass
                    else:  # searchWindowID not in valid range
                        msg = "'searchWindowID' must be one of [1, 2] (received {}).".format(
                            str(fsp["searchWindowID"])
                        )
                        self._raise_configure_scan_fatal_error(msg)
                    if len(fsp["searchBeam"]) <= 192:
                        for searchBeam in fsp["searchBeam"]:
                            if 1 > int(searchBeam["searchBeamID"]) > 1500:
                                # searchbeamID not in valid range
                                msg = "'searchBeamID' must be within range 1-1500 (received {}).".format(
                                    str(searchBeam["searchBeamID"])
                                )
                                self._raise_configure_scan_fatal_error(msg)
                            
                            for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
                                searchBeamID = fsp_pss_subarray_proxy.searchBeamID
                                if searchBeamID is None:
                                    pass
                                else:
                                    for search_beam_ID in searchBeamID:
                                        if int(searchBeam["searchBeamID"]) != search_beam_ID:
                                            pass
                                        elif fsp_pss_subarray_proxy.obsState == ObsState.IDLE:
                                            pass
                                        else:
                                            msg = "'searchBeamID' {} is already being used on another fspSubarray.".format(
                                                str(searchBeam["searchBeamID"])
                                            )
                                            self._raise_configure_scan_fatal_error(msg)
                            
                                # Validate receptors.
                                # This is always given, due to implementation details.
                                #TODO assume always given, as there is currently only support for 1 receptor/beam
                            if "receptors" not in searchBeam:
                                searchBeam["receptors"] = self._receptors

                            # Sanity check:
                            for this_rec in searchBeam["receptors"]:
                                if this_rec not in self._receptors:
                                    msg = ("Receptor {} does not belong to subarray {}.".format(
                                        str(self._receptors[this_rec]), str(self._subarray_id)))
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg, 
                                    "ConfigureScan execution", tango.ErrSeverity.ERR)

                            if searchBeam["outputEnable"] is False or searchBeam["outputEnable"] is True:
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                self._raise_configure_scan_fatal_error(msg)

                            if isinstance(searchBeam["averagingInterval"], int):
                                pass
                            else:
                                msg = "'averagingInterval' is not a valid integer"
                                self._raise_configure_scan_fatal_error(msg)

                            if validate_ip(searchBeam["searchBeamDestinationAddress"]):
                                pass
                            else:
                                msg = "'searchBeamDestinationAddress' is not a valid IP address"
                                self._raise_configure_scan_fatal_error(msg)

                    else:
                        msg = "More than 192 SearchBeams defined in PSS-BF config"
                        self._raise_configure_scan_fatal_error(msg)
                
                # --------------------------------------------------------

                ########## PST-BF ##########

                if fsp["functionMode"] == "PST-BF":
                    if len(fsp["timingBeam"]) <= 16:
                        for timingBeam in fsp["timingBeam"]:
                            if 1 <= int(timingBeam["timingBeamID"]) <= 16:
                                pass
                            else:  # timingBeamID not in valid range
                                msg = "'timingBeamID' must be within range 1-16 (received {}).".format(
                                    str(timingBeam["timingBeamID"])
                                )
                                self._raise_configure_scan_fatal_error(msg)
                            for fsp_pst_subarray_proxy in self._proxies_fsp_pst_subarray:
                                timingBeamID = fsp_pst_subarray_proxy.timingBeamID
                                if timingBeamID is None:
                                    pass
                                else:
                                    for timing_beam_ID in timingBeamID:
                                        if int(timingBeam["timingBeamID"]) != timing_beam_ID:
                                            pass
                                        elif fsp_pst_subarray_proxy.obsState == ObsState.IDLE:
                                            pass
                                        else:
                                            msg = "'timingBeamID' {} is already being used on another fspSubarray.".format(
                                                str(timingBeam["timingBeamID"])
                                            )
                                            self._raise_configure_scan_fatal_error(msg)

                            # Validate receptors.
                            # This is always given, due to implementation details.
                            if "receptors" in timingBeam:
                                for this_rec in timingBeam["receptors"]:
                                    if this_rec not in self._receptors:
                                        msg = ("Receptor {} does not belong to subarray {}.".format(
                                            str(self._receptors[this_rec]), str(self._subarray_id)))
                                        self.logger.error(msg)
                                        self._raise_configure_scan_fatal_error(msg)
                            else:
                                timingBeam["receptors"] = self._receptors

                            if timingBeam["outputEnable"] is False or timingBeam["outputEnable"] is True:
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                self._raise_configure_scan_fatal_error(msg)

                            if validate_ip(timingBeam["timingBeamDestinationAddress"]):
                                pass
                            else:
                                msg = "'timingBeamDestinationAddress' is not a valid IP address"
                                self._raise_configure_scan_fatal_error(msg)

                    else:
                        msg = "More than 16 TimingBeams defined in PST-BF config"
                        self._raise_configure_scan_fatal_error(msg)

            except tango.DevFailed:  # exception in ConfigureScan
                msg = "An exception occurred while configuring FSPs:\n{}\n" \
                        "Aborting configuration".format(sys.exc_info()[1].args[0].desc)

                self._raise_configure_scan_fatal_error(msg)

        # At this point, everything has been validated.

    def _raise_configure_scan_fatal_error(self, msg):
        self.logger.error(msg)
        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                     tango.ErrSeverity.ERR)

    # PROTECTED REGION END #    //  CbfSubarray.class_variable


    def _deconfigure(self):
        """Helper function to unsubscribe events and release resources."""
        
        # TODO: the deconfiguration should happen in reverse order of the
        #       initialization:

        # reset scanID, frequencyBand in case they're not reset
        self._scan_ID = 0
        self._frequency_band = 0

        # unsubscribe from TMC events
        for event_id in list(self._events_telstate.keys()):
            self._events_telstate[event_id].unsubscribe_event(event_id)
        self._events_telstate = {}

        # unsubscribe from FSP state change events
        for fspID in list(self._events_state_change_fsp.keys()):
            proxy_fsp = self._proxies_fsp[fspID - 1]
            proxy_fsp.unsubscribe_event(self._events_state_change_fsp[fspID][0])  # state
            proxy_fsp.unsubscribe_event(self._events_state_change_fsp[fspID][1])  # healthState
            del self._events_state_change_fsp[fspID]
            del self._fsp_state[self._fqdn_fsp[fspID - 1]]
            del self._fsp_health_state[self._fqdn_fsp[fspID - 1]]

        # send assigned VCCs and FSP subarrays to IDLE state
        # TODO: check if vcc fsp is in scanning state (subarray 
        # could be aborted in scanning state) - is this needed?
        self._group_vcc.command_inout("GoToIdle")
        self._group_fsp_corr_subarray.command_inout("GoToIdle")
        self._group_fsp_pss_subarray.command_inout("GoToIdle")
        self._group_fsp_pst_subarray.command_inout("GoToIdle")

        # change FSP subarray membership
        data = tango.DeviceData()
        data.insert(tango.DevUShort, self._subarray_id)
        # self.logger.info(data)
        self._group_fsp.command_inout("RemoveSubarrayMembership", data)
        self._group_fsp.remove_all()


        # remove channel info from FSP subarrays
        # already done in GoToIdle
        self._group_fsp_corr_subarray.remove_all()
        self._group_fsp_pss_subarray.remove_all()
        self._group_fsp_pst_subarray.remove_all()

        # reset all private dat to their initialization values:
        self._scan_ID = 0       
        self._config_ID = ""
        self._last_received_delay_model  = "{}"
        self._last_received_jones_matrix = "{}"
        self._last_received_beam_weights = "{}"

        # TODO: need to add 'GoToIdle' for VLBI and PST once implemented:
        # TODO: what happens if 
        # #     sp_corr_subarray_proxy.State() == tango.DevState.OFF ??
        #       that should not happen
        for fsp_corr_subarray_proxy in self._proxies_fsp_corr_subarray:
            if fsp_corr_subarray_proxy.State() == tango.DevState.ON:
                fsp_corr_subarray_proxy.GoToIdle()
        for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
            if fsp_pss_subarray_proxy.State() == tango.DevState.ON:
                fsp_pss_subarray_proxy.GoToIdle()
        for fsp_pst_subarray_proxy in self._proxies_fsp_pst_subarray:
            if fsp_pst_subarray_proxy.State() == tango.DevState.ON:
                fsp_pst_subarray_proxy.GoToIdle()

    def _remove_receptors_helper(self, argin):
        """Helper function to remove receptors for removeAllReceptors. 
        Takes in a list of integers.
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            if receptorID in self._receptors:
                vccID = receptor_to_vcc[receptorID]
                vccProxy = self._proxies_vcc[vccID - 1]

                # unsubscribe from events
                vccProxy.unsubscribe_event(self._events_state_change_vcc[vccID][0])  # state
                vccProxy.unsubscribe_event(self._events_state_change_vcc[vccID][1])  # healthState
                del self._events_state_change_vcc[vccID]
                del self._vcc_state[self._fqdn_vcc[vccID - 1]]
                del self._vcc_health_state[self._fqdn_vcc[vccID - 1]]

                # reset receptorID and subarrayMembership Vcc attribute:
                vccProxy.receptorID = 0
                vccProxy.subarrayMembership = 0

                self._receptors.remove(receptorID)
                self._proxies_assigned_vcc.remove(vccProxy)
                self._group_vcc.remove(self._fqdn_vcc[vccID - 1])
            else:
                log_msg = "Receptor {} not assigned to subarray. Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)

        # transitions to EMPTY if not assigned any receptors
        if not self._receptors:
            self._update_obs_state(ObsState.EMPTY)


    # Used by commands that needs resource manager in SKASubarray 
    # base class (for example AddReceptors command). 
    # The base class define len as len(resource_manager), 
    # so we need to change that here. TODO - to clarify.
    def __len__(self):
        """
        Returns the number of resources currently assigned. Note that
        this also functions as a boolean method for whether there are
        any assigned resources: ``if len()``.

        :return: number of resources assigned
        :rtype: int
        """

        return len(self._receptors)





    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16',
    )

    CbfMasterAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Master",
        default_value="mid_csp_cbf/sub_elt/master"
    )

    PssConfigAddress = device_property(
        dtype='str'
    )

    PstConfigAddress = device_property(
        dtype='str'
    )

    SW1Address = device_property(
        dtype='str'
    )

    SW2Address = device_property(
        dtype='str'
    )

    VCC = device_property(
        dtype=('str',)
    )

    FSP = device_property(
        dtype=('str',)
    )

    FspCorrSubarray = device_property(
        dtype=('str',)
    )

    FspPssSubarray = device_property(
        dtype=('str',)
    )

    FspPstSubarray = device_property(
        dtype=('str',)
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

    configID = attribute(
        dtype='str',
        access=AttrWriteType.READ,
        label="Config ID",
        doc="config ID",
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

    fspList = attribute(
        dtype=(('uint16',),),
        max_dim_x=4,
        max_dim_y=27,
        label="List of FSP's used by subarray",
        doc="fsp[1][x] = CORR [2][x] = PSS [1][x] = PST [1][x] = VLBI",
    )

    latestScanConfig = attribute(
        dtype='DevString',
        label="lastest Scan Configuration",
        doc="for storing lastest scan configuration",
    )


    # ---------------
    # General methods
    # ---------------
    class InitCommand(SKASubarray.InitCommand):
        """
        A class for the CbfSubarray's init_device() "command".
        """
        def do(self):
            """
            Stateless hook for device initialisation. Initialize the attributes and the properties of the CbfSubarray.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            
            """
            # SKASubarray.init_device(self)
            # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
            # self.set_state(DevState.INIT)
            (result_code, message) = super().do()

            device=self.target

            
            device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            device._element_logging_level = tango.LogLevel.LOG_DEBUG
            device._central_logging_level = tango.LogLevel.LOG_DEBUG

            # get subarray ID
            if device.SubID:
                device._subarray_id = device.SubID
            else:
                device._subarray_id = int(device.get_name()[-2:])  # last two chars of FQDN

        # initialize attribute values
            device._receptors = []
            device._frequency_band = 0
            device._config_ID = ""
            device._scan_ID = 0
            device._fsp_list = [[], [], [], []]
            # device._output_links_distribution = {"configID": ""}# ???
            device._vcc_state = {}  # device_name:state
            device._vcc_health_state = {}  # device_name:healthState
            device._fsp_state = {}  # device_name:state
            device._fsp_health_state = {}  # device_name:healthState
            # store list of fsp configs being used for each function mode
            device._corr_config = []
            device._pss_config = []
            device._pst_config = []
            # store list of fsp being used for each function mode
            device._corr_fsp_list = []
            device._pss_fsp_list = []
            device._pst_fsp_list = []
            device._latest_scan_config=""
            # device._published_output_links = False# ???
            # device._last_received_vis_destination_address = "{}"#???
            device._last_received_delay_model = "{}"
            device._last_received_jones_matrix = "{}"
            device._last_received_beam_weights = "{}"

            device._mutex_delay_model_config = Lock()
            device._mutex_jones_matrix_config = Lock()
            device._mutex_beam_weights_config = Lock()

            # for easy device-reference
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._stream_tuning = [0, 0]

            # device proxy for easy reference to CBF Master
            device._proxy_cbf_master = tango.DeviceProxy(device.CbfMasterAddress)

            device.MIN_INT_TIME = const.MIN_INT_TIME
            device.NUM_CHANNEL_GROUPS = const.NUM_CHANNEL_GROUPS
            device.NUM_FINE_CHANNELS = const.NUM_FINE_CHANNELS

            device._master_max_capabilities = dict(
                pair.split(":") for pair in
                device._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
            )

            device._count_vcc = int(device._master_max_capabilities["VCC"])
            device._count_fsp = int(device._master_max_capabilities["FSP"])
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._fqdn_fsp = list(device.FSP)[:device._count_fsp]
            device._fqdn_fsp_corr_subarray = list(device.FspCorrSubarray)
            device._fqdn_fsp_pss_subarray = list(device.FspPssSubarray)
            device._fqdn_fsp_pst_subarray = list(device.FspPstSubarray)

            device._proxies_vcc = [*map(tango.DeviceProxy, device._fqdn_vcc)]
            device._proxies_fsp = [*map(tango.DeviceProxy, device._fqdn_fsp)]
            device._proxies_fsp_corr_subarray = [*map(tango.DeviceProxy, device._fqdn_fsp_corr_subarray)]
            device._proxies_fsp_pss_subarray = [*map(tango.DeviceProxy, device._fqdn_fsp_pss_subarray)]
            device._proxies_fsp_pst_subarray = [*map(tango.DeviceProxy, device._fqdn_fsp_pst_subarray)]

            # Note vcc connected both individual and in group
            device._proxies_assigned_vcc = [] 
            device._proxies_assigned_fsp = []

            # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
            device._events_telstate = {}

            # store the subscribed state change events as vcc_ID:[event_ID, event_ID] key:value pairs
            device._events_state_change_vcc = {}

            # store the subscribed state change events as fsp_ID:[event_ID, event_ID] key:value pairs
            device._events_state_change_fsp = {}

            # initialize groups
            device._group_vcc = tango.Group("VCC")
            device._group_fsp = tango.Group("FSP")
            device._group_fsp_corr_subarray = tango.Group("FSP Subarray Corr")
            device._group_fsp_pss_subarray = tango.Group("FSP Subarray Pss")
            device._group_fsp_pst_subarray = tango.Group("FSP Subarray Pst")

            return (ResultCode.OK, "successfull")

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        """hook to delete device. Set State to DISABLE, romove all receptors, go to OBsState IDLE"""

        pass
        # PROTECTED REGION END #    //  CbfSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_frequencyBand(self):
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_read) ENABLED START #
        """Return frequency band assigned to this subarray. one of ["1", "2", "3", "4", "5a", "5b", ]"""
        return self._frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def read_configID(self):
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """Return attribute configID"""
        return self._config_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def read_scanID(self):
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """Return attribute scanID"""
        return self._scan_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def read_receptors(self):
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        """Return list of receptors assgined to subarray"""
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(CbfSubarray.receptors_write) ENABLED START #
        """Set receptors of this array to the input value. Input should be an array of int"""
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  CbfSubarray.receptors_write


    def read_vccState(self):
        # PROTECTED REGION ID(CbfSubarray.vccState_read) ENABLED START #
        """Return the attribute vccState": array of DevState"""
        return list(self._vcc_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccState_read

    def read_vccHealthState(self):
        # PROTECTED REGION ID(CbfSubarray.vccHealthState_read) ENABLED START #
        """returns vccHealthState attribute: an array of unsigned short"""
        return list(self._vcc_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccHealthState_read

    def read_fspState(self):
        # PROTECTED REGION ID(CbfSubarray.fspState_read) ENABLED START #
        """Return the attribute fspState": array of DevState"""
        return list(self._fsp_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspState_read

    def read_fspHealthState(self):
        # PROTECTED REGION ID(CbfSubarray.fspHealthState_read) ENABLED START #
        """returns fspHealthState attribute: an array of unsigned short"""
        return list(self._fsp_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspHealthState_read

    def read_fspList(self):
        # PROTECTED REGION ID(CbfSubarray.fspList_read) ENABLED START #
        """return fspList attribute: 2 dimentioanl array the fsp used by all the subarrays"""
        return self._fsp_list
        # PROTECTED REGION END #    //  CbfSubarray.fspList_read

    def read_latestScanConfig(self):
        # PROTECTED REGION ID(CbfSubarray.latestScanConfig_read) ENABLED START #
        """Return the latestScanConfig attribute."""
        return self._latest_scan_config
        # PROTECTED REGION END #    //  CbfSubarray.latestScanConfig_read

    # --------
    # Commands
    # --------

    # TODO - not needed for sw devices (sw devs are disabled becasue same 
    # functionality is in vccSearchWindow; 
    # go by supper class method for now
    # def is_On_allowed(self):
    #     """allowed if DevState is OFF"""
    #     if self.dev_state() == tango.DevState.OFF:
    #         return True
    #     return False

    # class OnCommand(SKASubarray.OnCommand):
    #     """
    #     A class for the SKASubarray's On() command.
    #     """
    #     def do(self):
    #         """
    #         Stateless hook for On() command functionality.

    #         :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #         :rtype: (ResultCode, str)
    #         """
    #         (result_code,message)=super().do()
    #         device = self.target
    #         device._proxy_sw_1.SetState(tango.DevState.DISABLE)
    #         device._proxy_sw_2.SetState(tango.DevState.DISABLE)
    #         return (result_code,message)

    # class OffCommand(SKASubarray.OffCommand):
    #     """
    #     A class for the SKASubarray's Off() command.
    #     """
    #     def do(self):
    #         """
    #         Stateless hook for Off() command functionality.

    #         :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #         :rtype: (ResultCode, str)
    #         """
    #         (result_code,message)=super().do()
    #         device = self.target
    #         device._proxy_sw_1.SetState(tango.DevState.OFF)
    #         device._proxy_sw_2.SetState(tango.DevState.OFF)
    #         return (result_code,message)


    ##################  Receptors Related Commands  ###################
        

    class RemoveReceptorsCommand(SKASubarray.ReleaseResourcesCommand):
        """
        A class for CbfSubarray's ReleaseReceptors() command.
        Equivalent to the ReleaseResourcesCommand in ADR-8.
        """
        def do(self, argin):
            """
            Stateless hook for RemoveReceptors() command functionality.

            :param argin: The receptors to be released
            :type argin: list of int
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device=self.target

            device._remove_receptors_helper(argin)
            message = "CBFSubarray RemoveReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    def RemoveReceptors(self, argin):
        """
        Remove from list of receptors. Turn Subarray to ObsState = EMPTY if no receptors assigned.
        Uses RemoveReceptorsCommand class.
        """
        command = self.get_command_object("RemoveReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )

    @DebugIt()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
        """Remove all receptors. Turn Subarray OFF if no receptors assigned"""

        command = self.get_command_object("RemoveAllReceptors")
        (return_code, message) = command()
        return [[return_code], [message]]  
        # PROTECTED REGION END #    //  CbfSubarray.RemoveAllReceptors

    class RemoveAllReceptorsCommand(SKASubarray.ReleaseResourcesCommand):
        """
        A class for CbfSubarray's ReleaseAllReceptors() command.
        """
        def do(self):
            """
            Stateless hook for ReleaseAllReceptors() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering RemoveAllReceptors()")

            device=self.target

            # For LMC0.6.0: use a helper instead of a command so that it doesn't care about the obsState
            device._remove_receptors_helper(device._receptors[:])

            message = "CBFSubarray RemoveAllReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)


    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )

    @DebugIt()
    def AddReceptors(self, argin):
        """
        Assign Receptors to this subarray. 
        Turn subarray to ObsState = IDLE if previously no receptor is assigned.
        """
        command = self.get_command_object("AddReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]    

    
    class AddReceptorsCommand(SKASubarray.AssignResourcesCommand):
        # NOTE: doesn't inherit SKASubarray._ResourcingCommand 
        # because will give error on len(self.target); TODO: to resolve
        """
        A class for CbfSubarray's AddReceptors() command.
        """
        def do(self, argin):
            """
            Stateless hook for AddReceptors() command functionality.

            :param argin: The receptors to be assigned
            :type argin: list of int
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device=self.target
            # Code here
            errs = []  # list of error messages
            receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                                device._proxy_cbf_master.receptorToVcc)
            for receptorID in argin:
                try:
                    vccID = receptor_to_vcc[receptorID]
                    vccProxy = device._proxies_vcc[vccID - 1]

                    # Update the VCC receptorID attribute:

                    self.logger.debug( ("receptorID = {}, vccProxy.receptorID = {}"
                    .format(receptorID, vccProxy.receptorID)))

                    vccProxy.receptorID = receptorID  # TODO - may not be needed?

                    self.logger.debug( ("receptorID = {}, vccProxy.receptorID = {}"
                    .format(receptorID, vccProxy.receptorID)))

                    subarrayID = vccProxy.subarrayMembership

                    # only add receptor if it does not already belong to a different subarray
                    if subarrayID not in [0, device._subarray_id]:
                        errs.append("Receptor {} already in use by subarray {}.".format(
                            str(receptorID), str(subarrayID)))
                    else:
                        if receptorID not in device._receptors:
                            # change subarray membership of vcc
                            vccProxy.subarrayMembership = device._subarray_id

                            # TODO: is this note still relevant? 
                            # Note:json does not recognize NumPy data types. 
                            # Convert the number to a Python int 
                            # before serializing the object.
                            # The list of receptors is serialized when the FSPs are 
                            # configured for a scan.

                            device._receptors.append(int(receptorID))
                            device._proxies_assigned_vcc.append(vccProxy)
                            device._group_vcc.add(device._fqdn_vcc[vccID - 1])

                            # subscribe to VCC state and healthState changes
                            event_id_state = vccProxy.subscribe_event(
                                "State",
                                tango.EventType.CHANGE_EVENT,
                                device._state_change_event_callback
                            )

                            event_id_health_state = vccProxy.subscribe_event(
                                "healthState",
                                tango.EventType.CHANGE_EVENT,
                                device._state_change_event_callback
                            )

                            device._events_state_change_vcc[vccID] = [event_id_state,
                                                                    event_id_health_state]
                        else:
                            log_msg = "Receptor {} already assigned to current subarray.".format(
                                str(receptorID))
                            self.logger.warn(log_msg)

                except KeyError:  # invalid receptor ID
                    errs.append("Invalid receptor ID: {}".format(receptorID))


            if errs:
                msg = "\n".join(errs)
                self.logger.error(msg)
                # tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                #                             tango.ErrSeverity.ERR)
                
                return (ResultCode.FAILED, msg)

            message = "CBFSubarray AddReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    ############  Configure Related Commands   ##############

    class ConfigureScanCommand(SKASubarray.ConfigureCommand):
        """
        A class for CbfSubarray's ConfigureScan() command.
        """
        def do(self, argin):
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON
            :type argin: str
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            device=self.target

            # Code here
            device._corr_config = []
            device._pss_config = []
            device._pst_config = []
            device._corr_fsp_list = []
            device._pss_fsp_list = []
            device._pst_fsp_list = []
            device._fsp_list = [[], [], [], []]

            #TODO: reimplement once _validate_scan_configuration is refactored
            # validate scan configuration first 
            try:
                device._validate_scan_configuration(argin)
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self.logger.warn("validate scan configuration error")
                # device._raise_configure_scan_fatal_error(msg)

            # Call this just to release all FSPs and unsubscribe to events. 
            # Can't call GoToIdle, otherwise there will be state transition problem. 
            # TODO - to clarify why can't call GoToIdle
            device._deconfigure()

            # TODO - to remove
            # data = tango.DeviceData()
            # data.insert(tango.DevUShort, ObsState.CONFIGURING)
            # device._group_vcc.command_inout("SetObservingState", data)

            configuration = json.loads(argin)
            # set band5Tuning to [0,0] if not specified
            if "band5Tuning" not in configuration: 
                configuration["band5Tuning"] = [0,0]

            # Configure configID.
            device._config_ID = str(configuration["id"])

            # Configure frequencyBand.
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            device._frequency_band = frequency_bands.index(configuration["frequencyBand"])

            config_dict = {"id":configuration["id"], "frequency_band":configuration["frequencyBand"],}
            json_str = json.dumps(config_dict)
            data = tango.DeviceData()
            data.insert(tango.DevString, json_str)
            device._group_vcc.command_inout("ConfigureScan", data)

            time.sleep(3) # TODO - to remove
            
            # TODO: all these VCC params should be passed in via ConfigureScan()
            # Configure band5Tuning, if frequencyBand is 5a or 5b.
            if device._frequency_band in [4, 5]:
                stream_tuning = [*map(float, configuration["band5Tuning"])]
                device._stream_tuning = stream_tuning
                device._group_vcc.write_attribute("band5Tuning", stream_tuning)

            # Configure frequencyBandOffsetStream1.
            if "frequencyBandOffsetStream1" in configuration:
                device._frequency_band_offset_stream_1 = int(configuration["frequencyBandOffsetStream1"])
                device._group_vcc.write_attribute(
                    "frequencyBandOffsetStream1",
                    int(configuration["frequencyBandOffsetStream1"])
                )
            else:
                device._frequency_band_offset_stream_1 = 0
                device._group_vcc.write_attribute("frequencyBandOffsetStream1", 0)
                log_msg = "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
                self.logger.warn(log_msg)

            # Validate frequencyBandOffsetStream2.
            # If not given, use a default value.
            # If malformed, use a default value, but append an error.
            if device._frequency_band in [4, 5]:
                if "frequencyBandOffsetStream2" in configuration:
                    device._frequency_band_offset_stream_2 = int(configuration["frequencyBandOffsetStream2"])
                    device._group_vcc.write_attribute(
                        "frequencyBandOffsetStream2",
                        int(configuration["frequencyBandOffsetStream2"])
                    )
                else:
                    device._frequency_band_offset_stream_2 = 0
                    device._group_vcc.write_attribute("frequencyBandOffsetStream2", 0)
                    log_msg = "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
                    self.logger.warn(log_msg)
            else:
                device._frequency_band_offset_stream_2 = 0
                device._group_vcc.write_attribute("frequencyBandOffsetStream2", 0)

            # Configure dopplerPhaseCorrSubscriptionPoint.
            if "dopplerPhaseCorrSubscriptionPoint" in configuration:
                attribute_proxy = tango.AttributeProxy(configuration["dopplerPhaseCorrSubscriptionPoint"])
                attribute_proxy.ping()
                event_id = attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    device._doppler_phase_correction_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure delayModelSubscriptionPoint.
            if "delayModelSubscriptionPoint" in configuration:
                device._last_received_delay_model = "{}"
                attribute_proxy = tango.AttributeProxy(configuration["delayModelSubscriptionPoint"])
                attribute_proxy.ping() #To be sure the connection is good(don't know if the device is running)
                event_id = attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    device._delay_model_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure jonesMatrixSubscriptionPoint
            if "jonesMatrixSubscriptionPoint" in configuration:
                device._last_received_jones_matrix = "{}"
                attribute_proxy = tango.AttributeProxy(configuration["jonesMatrixSubscriptionPoint"])
                attribute_proxy.ping()
                event_id = attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    device._jones_matrix_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure beamWeightsSubscriptionPoint
            if "beamWeightsSubscriptionPoint" in configuration:
                device._last_received_beam_weights= "{}"
                attribute_proxy = tango.AttributeProxy(configuration["beamWeightsSubscriptionPoint"])
                attribute_proxy.ping()
                event_id = attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    device._beam_weights_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure rfiFlaggingMask.
            if "rfiFlaggingMask" in configuration:
                device._group_vcc.write_attribute(
                    "rfiFlaggingMask",
                    json.dumps(configuration["rfiFlaggingMask"])
                )
            else:
                log_msg = "'rfiFlaggingMask' not given. Proceeding."
                self.logger.warn(log_msg)

            # Configure searchWindow.
            if "searchWindow" in configuration:
                for search_window in configuration["searchWindow"]:
                    search_window["frequencyBand"] = configuration["frequencyBand"]
                    if "frequencyBandOffsetStream1" in configuration:
                        search_window["frequencyBandOffsetStream1"] = \
                            configuration["frequencyBandOffsetStream1"]
                    else:
                        search_window["frequencyBandOffsetStream1"] = 0
                    if "frequencyBandOffsetStream2" in configuration:
                        search_window["frequencyBandOffsetStream2"] = \
                            configuration["frequencyBandOffsetStream2"]
                    else:
                        search_window["frequencyBandOffsetStream2"] = 0
                    if configuration["frequencyBand"] in ["5a", "5b"]:
                        search_window["band5Tuning"] = configuration["band5Tuning"]
                    # pass on configuration to VCC
                    data = tango.DeviceData()
                    data.insert(tango.DevString, json.dumps(search_window))
                    device._group_vcc.command_inout("ConfigureSearchWindow", data)
            else:
                log_msg = "'searchWindow' not given."
                self.logger.warn(log_msg)

            # TODO: the entire vcc configuration should move to Vcc
            # for now, run ConfigScan only wih the following data, so that
            # the obsState are properly (implicitly) updated by the command
            # (And not manually by SetObservingState as before)

            ######## FSP #######
            # Configure FSP.
            for fsp in configuration["fsp"]:
                # Configure fspID.
                fspID = int(fsp["fspID"])
                proxy_fsp = device._proxies_fsp[fspID - 1]

                device._group_fsp.add(device._fqdn_fsp[fspID - 1])
                device._group_fsp_corr_subarray.add(device._fqdn_fsp_corr_subarray[fspID - 1])
                device._group_fsp_pss_subarray.add(device._fqdn_fsp_pss_subarray[fspID - 1])
                device._group_fsp_pss_subarray.add(device._fqdn_fsp_pst_subarray[fspID - 1])

                # change FSP subarray membership
                proxy_fsp.AddSubarrayMembership(device._subarray_id)

                # Configure functionMode.
                proxy_fsp.SetFunctionMode(fsp["functionMode"])

                # subscribe to FSP state and healthState changes
                event_id_state, event_id_health_state = proxy_fsp.subscribe_event(
                    "State",
                    tango.EventType.CHANGE_EVENT,
                    device._state_change_event_callback
                ), proxy_fsp.subscribe_event(
                    "healthState",
                    tango.EventType.CHANGE_EVENT,
                    device._state_change_event_callback
                )
                device._events_state_change_fsp[int(fsp["fspID"])] = [event_id_state,
                                                                    event_id_health_state]
                
                # Add configID to fsp. It is not included in the "FSP" portion in configScan JSON
                fsp["configID"] = configuration["id"]
                fsp["frequencyBand"] = configuration["frequencyBand"]
                fsp["band5Tuning"] = configuration["band5Tuning"]
                if "frequencyBandOffsetStream1" in configuration:
                    fsp["frequencyBandOffsetStream1"] = configuration["frequencyBandOffsetStream1"]
                else:
                    fsp["frequencyBandOffsetStream1"] = 0
                if "frequencyBandOffsetStream2" in configuration:
                    fsp["frequencyBandOffsetStream2"] = configuration["frequencyBandOffsetStream2"]
                else:
                    fsp["frequencyBandOffsetStream2"] = 0

                if fsp["functionMode"] == "CORR":
                    if "receptors" not in fsp:
                        # In this case by the ICD, all subarray allocated resources should be used.
                        fsp["receptors"] = device._receptors
                    device._corr_config.append(fsp)
                    device._corr_fsp_list.append(fsp["fspID"])
                elif fsp["functionMode"] == "PSS-BF":
                    for searchBeam in fsp["searchBeam"]:
                        if "receptors" not in searchBeam:
                            # In this case by the ICD, all subarray allocated resources should be used.
                            searchBeam["receptors"] = device._receptors
                    device._pss_config.append(fsp)
                    device._pss_fsp_list.append(fsp["fspID"])
                elif fsp["functionMode"] == "PST-BF":
                    for timingBeam in fsp["timingBeam"]:
                        if "receptors" not in timingBeam:
                            # In this case by the ICD, all subarray allocated resources should be used.
                            timingBeam["receptors"] = device._receptors
                    device._pst_config.append(fsp)
                    device._pst_fsp_list.append(fsp["fspID"])

            # Call ConfigureScan for all FSP Subarray devices (CORR and PSS)

            # NOTE:_pss_config is a list of fsp config JSON objects, each 
            #      augmented by a number of vcc-fsp common parameters 
            #      created by the function _validate_scan_configuration()
            if len(device._pss_config) != 0:
                for this_fsp in device._pss_config:
                    try:
                        this_proxy = device._proxies_fsp_pss_subarray[int(this_fsp["fspID"])-1]
                        this_proxy.ConfigureScan(json.dumps(this_fsp))
                    except tango.DevFailed:
                        msg = "An exception occurred while configuring  " \
                        "FspPssSubarray; Aborting configuration"
                        device._raise_configure_scan_fatal_error(msg)

            # NOTE: _pst_config is costructed similarly to _pss_config
            if len(device._pst_config) != 0:
                for this_fsp in device._pst_config:
                    try:
                        this_proxy = device._proxies_fsp_pst_subarray[int(this_fsp["fspID"])-1]
                        this_proxy.ConfigureScan(json.dumps(this_fsp))
                    except tango.DevFailed:
                        msg = "An exception occurred while configuring  " \
                        "FspPstSubarray; Aborting configuration"
                        device._raise_configure_scan_fatal_error(msg)

            # NOTE: _corr_config is costructed similarly to _pss_config
            if len(device._corr_config) != 0: 
                #device._proxy_corr_config.ConfigureFSP(json.dumps(device._corr_config))

                # Michelle - WIP - TODO - this is to replace the call to 
                #  _proxy_corr_config.ConfigureFSP()
                for this_fsp in device._corr_config:
                    try:                      
                        this_proxy = device._proxies_fsp_corr_subarray[int(this_fsp["fspID"])-1]
                        this_proxy.ConfigureScan(json.dumps(this_fsp))
                    except tango.DevFailed:
                        msg = "An exception occurred while configuring " \
                        "FspCorrSubarray; Aborting configuration"
                        # msg = "An exception occurred while configuring FspCorrSubarray:\n{}\n" \
                        # "Aborting configuration".format(sys.exc_info()[1].args[0].desc)
                        device._raise_configure_scan_fatal_error(msg)

            # TODO add PST and VLBI to this once they are implemented
            # what are these for?
            device._fsp_list[0].append(device._corr_fsp_list)
            device._fsp_list[1].append(device._pss_fsp_list)
            device._fsp_list[2].append(device._pst_fsp_list)

            #save configuration into latestScanConfig
            device._latest_scan_config = str(configuration)
            message = "CBFSubarray Configure command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )

    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        # """
        """Change state to CONFIGURING.
        Configure attributes from input JSON. Subscribe events. Configure VCC, VCC subarray, FSP, FSP Subarray. 
        publish output links.
        """

        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]    

    class ScanCommand(SKASubarray.ScanCommand):
        """
        A class for CbfSubarray's Scan() command.
        """
        def do(self, argin):
            """
            Stateless hook for Scan() command functionality.

            :param argin: ScanID
            :type argin: int
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            # overwrites the do hook

            device=self.target

            device._scan_ID=int(argin)

            data = tango.DeviceData()
            data.insert(tango.DevString, argin)
            device._group_vcc.command_inout("Scan", data)

            device._group_fsp_corr_subarray.command_inout("Scan", data)
            device._group_fsp_pss_subarray.command_inout("Scan", data)
            device._group_fsp_pst_subarray.command_inout("Scan", data)

            # return message
            message = "Scan command successfull"
            self.logger.info(message)
            return (ResultCode.STARTED, message)

    def is_EndScan_allowed(self):
        """allowed if SUbarray is ON"""
        if self.dev_state() == tango.DevState.ON and self._obs_state==ObsState.SCANNING:
            return True
        return False


    class EndScanCommand(SKASubarray.EndScanCommand):
        """
        A class for CbfSubarray's EndScan() command.
        """
        def do(self):
            (result_code,message)=super().do()
            device=self.target

            # EndScan for all subordinate devices:
            device._group_vcc.command_inout("EndScan")
            device._group_fsp_corr_subarray.command_inout("EndScan")
            device._group_fsp_pss_subarray.command_inout("EndScan")
            device._group_fsp_pst_subarray.command_inout("EndScan")

            device._scan_ID = 0
            device._frequency_band = 0

            message = "EndScan command OK"
            self.logger.info(message)
            return (ResultCode.OK, message)


    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )
    def GoToIdle(self):
        
        """deconfigure a scan, set ObsState to IDLE"""
        
        command = self.get_command_object("GoToIdle")
        (return_code, message) = command()
        return [[return_code], [message]]

    class GoToIdleCommand(SKASubarray.EndCommand):
        """
        A class for SKASubarray's GoToIdle() command.
        """
        def do(self):
            """
            Stateless hook for GoToIdle() command functionality.
            
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")
            
            device=self.target
            device._deconfigure()

            message = "GoToIdle command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    ############### abort, restart and reset #####################

    class AbortCommand(SKASubarray.AbortCommand):
        """
        A class for SKASubarray's Abort() command.
        """
        def do(self):
            """
            Stateless hook for Abort() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            # if aborted from SCANNING, needs to set VCC and PSS subarray 
            # to READY state otherwise when 
            if device.scanID != 0:
                self.logger.info("scanning")
                device._group_vcc.command_inout("EndScan")
                device._group_fsp_corr_subarray.command_inout("EndScan")
                device._group_fsp_pss_subarray.command_inout("EndScan")
                device._group_fsp_pst_subarray.command_inout("EndScan")
            
            (result_code,message)=super().do()
            
            return (result_code,message)

    
    # RestartCommand already registered in SKASubarray, so no "def restart" needed
    class RestartCommand(SKASubarray.RestartCommand):
        """
        A class for CbfSubarray's Restart() command.
        """
        def do(self):
            """
            Stateless hook for Restart() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            # We might have interrupted a long-running command such as a Configure
            # or a Scan, so we need to clean up from that.

            # Now totally deconfigure
            device._deconfigure()

            # and release all receptors
            device._remove_receptors_helper(device._receptors[:])

            message = "Restart command completed OK"
            self.logger.info(message)
            return (ResultCode.OK,message)


    class ObsResetCommand(SKASubarray.ObsResetCommand):
        """
        A class for CbfSubarray's ObsReset() command.
        """
        def do(self):
            """
            Stateless hook for ObsReset() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            # We might have interrupted a long-running command such as a Configure
            # or a Scan, so we need to clean up from that.

            # totally deconfigure
            device._deconfigure()

            message = "ObsReset command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)





# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == '__main__':
    main()
