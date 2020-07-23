# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# CbfSubarray Tango device prototype
# CBFSubarray TANGO device class for the CBFSubarray prototype


# tango imports
import tango
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

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import const
from ska.base.control_model import ObsState, AdminMode
from ska.base import SKASubarray
from ska.base.commands import ResultCode, BaseCommand, ResponseCommand, ActionCommand

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
        Sets up the command objects
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
            self.StartScanCommand(*device_args)
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
        if not event.err:
            if self.state_model._obs_state not in [ObsState.READY.value, ObsState.SCANNING.value]:
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
                        args=(int(delay_model["epoch"]), json.dumps(delay_model["delayDetails"]))
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def _update_delay_model(self, epoch, model):
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
        self._group_vcc.command_inout("UpdateDelayModel", data)
        self._mutex_delay_model_config.release()



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



    def _validate_scan_configuration(self, argin):
        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        for proxy in self._proxies_assigned_vcc:
            if proxy.State() != tango.DevState.ON:
                msg = "VCC {} is not ON. Aborting configuration.".format(
                    self._proxies_vcc.index(proxy) + 1
                )
                self._raise_configure_scan_fatal_error(msg)

        # Validate configID.
        # Note!!! this is an exception in the JSON input. in the input it is called "id", 
        # the corresponding attribute in the code is configID(to avoid having an attribute name too short).
        if "id" in argin:
            self._config_ID=str(argin["id"])
            # if int(argin["configID"]) <= 0:  # configID not positive
            #     msg = "'configID' must be positive (received {}). " \
            #           "Aborting configuration.".format(int(argin["configID"]))
            #     self._raise_configure_scan_fatal_error(msg)
            # elif any(map(lambda i: i == int(argin["configID"]),
            #              self._proxy_cbf_master.subarrayconfigID)) and \
            #         int(argin["configID"]) != self._config_ID:  # configID already taken
            #     msg = "'configID' must be unique (received {}). " \
            #           "Aborting configuration.".format(int(argin["configID"]))
            #     self._raise_configure_scan_fatal_error(msg)
            # else:
            #     pass

        else:
            msg = "'id'(configID attribute) must be given. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        # Validate frequencyBand.
        if "frequencyBand" in argin:
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            if argin["frequencyBand"] in frequency_bands:
                pass
            else:
                msg = "'frequencyBand' must be one of {} (received {}). " \
                      "Aborting configuration.".format(frequency_bands, argin["frequency_band"])
                self._raise_configure_scan_fatal_error(msg)
        else:
            msg = "'frequencyBand' must be given. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        # Validate band5Tuning, if frequencyBand is 5a or 5b.
        if argin["frequencyBand"] in ["5a", "5b"]:
            # band5Tuning is optional
            if "band5Tuning" in argin:
                # check if streamTuning is an array of length 2
                try:
                    assert len(argin["band5Tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                    self._raise_configure_scan_fatal_error(msg)

                stream_tuning = [*map(float, argin["band5Tuning"])]
                if argin["frequencyBand"] == "5a":
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
                else:  # argin["frequencyBand"] == "5b"
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
                # set band5Tuning to zero for the rest of the test. This won't change the argin in function "configureScan(argin)"
                argin["band5Tuning"]=[0,0]

        # Validate frequencyBandOffsetStream1.
        if "frequencyBandOffsetStream1" in argin:
            if abs(int(argin["frequencyBandOffsetStream1"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream1' must be at most half " \
                      "of the frequency slice bandwidth. Aborting configuration."
                self._raise_configure_scan_fatal_error(msg)
        else:
            pass

        # Validate frequencyBandOffsetStream2.
        if argin["frequencyBand"] in ["5a", "5b"]:
            if "frequencyBandOffsetStream2" in argin:
                if abs(int(argin["frequencyBandOffsetStream2"])) <= \
                        const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                    pass
                else:
                    msg = "Absolute value of 'frequencyBandOffsetStream2' must be at most " \
                          "half of the frequency slice bandwidth. Aborting configuration."
                    self._raise_configure_scan_fatal_error(msg)
            else:
                pass
        else:
            pass

        # Validate dopplerPhaseCorrSubscriptionPoint.
        if "dopplerPhaseCorrSubscriptionPoint" in argin:
            try:
                attribute_proxy = tango.AttributeProxy(argin["dopplerPhaseCorrSubscriptionPoint"])
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
                    argin["dopplerPhaseCorrSubscriptionPoint"]
                )
                self._raise_configure_scan_fatal_error(msg)
        else:
            pass

        # Validate delayModelSubscriptionPoint.
        if "delayModelSubscriptionPoint" in argin:
            try:
                attribute_proxy = tango.AttributeProxy(argin["delayModelSubscriptionPoint"])
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
                    argin["delayModelSubscriptionPoint"]
                )
                self._raise_configure_scan_fatal_error(msg)
        else:
            msg = "'delayModelSubscriptionPoint' not given. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)



        # Validate searchWindow.
        if "searchWindow" in argin:
            # check if searchWindow is an array of maximum length 2
            try:
                assert len(argin["searchWindow"]) <= 2

                for search_window in argin["searchWindow"]:
                    for vcc in self._proxies_assigned_vcc:
                        try:
                            search_window["frequencyBand"] = argin["frequencyBand"]
                            if "frequencyBandOffsetStream1" in argin:
                                search_window["frequencyBandOffsetStream1"] = \
                                    argin["frequencyBandOffsetStream1"]
                            else:
                                search_window["frequencyBandOffsetStream1"] = 0
                            if "frequencyBandOffsetStream2" in argin:
                                search_window["frequencyBandOffsetStream2"] = \
                                    argin["frequencyBandOffsetStream2"]
                            else:
                                search_window["frequencyBandOffsetStream2"] = 0
                            if argin["frequencyBand"] in ["5a", "5b"]:
                                search_window["band5Tuning"] = argin["band5Tuning"]

                            # pass on configuration to VCC
                            vcc.ValidateSearchWindow(json.dumps(search_window))

                        except tango.DevFailed:  # exception in Vcc.ConfigureSearchWindow
                            msg = "An exception occurred while configuring VCC search " \
                                  "windows:\n{}\n. Aborting configuration.".format(
                                str(sys.exc_info()[1].args[0].desc)
                            )

                            self._raise_configure_scan_fatal_error(msg)
                    # If the search window configuration is valid for all VCCs,
                    # is is guaranteed to be valid for the CBF Subarray.
                    # self.ConfigureSearchWindow(json.dumps(search_window))

            except (TypeError, AssertionError):  # searchWindow not the right length or not an array
                msg = "'searchWindow' must be an array of maximum length 2. " \
                      "Aborting configuration."
                self._raise_configure_scan_fatal_error(msg)
        else:
            pass

        # Validate fsp.
        if "fsp" in argin:
            for fsp in argin["fsp"]:
                try:
                    # Validate fspID.
                    if "fspID" in fsp:
                        if int(fsp["fspID"]) in list(range(1, self._count_fsp + 1)):
                            fspID = int(fsp["fspID"])
                            proxy_fsp = self._proxies_fsp[fspID - 1]
                            if fsp["functionMode"] == "CORR":
                                proxy_fsp_subarray = self._proxies_fsp_corr_subarray[fspID - 1]
                            elif fsp["functionMode"] == "PSS-BF":
                                proxy_fsp_subarray = self._proxies_fsp_pss_subarray[fspID - 1]
                        else:
                            msg = "'fspID' must be an integer in the range [1, {}]. " \
                                  "Aborting configuration.".format(str(self._count_fsp))
                            self._aise_configure_scan_fatal_error(msg)
                    else:
                        msg = "FSP specified, but 'fspID' not given. " \
                              "Aborting configuration."
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
                    if "functionMode" in fsp:
                        if fsp["functionMode"] in function_modes:
                            if function_modes.index(fsp["functionMode"]) + 1 == \
                                    proxy_fsp.functionMode or \
                                    proxy_fsp.functionMode == 0:
                                pass
                            else:
                                #TODO need to add this check for VLBI and PST once implemented
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
                        else:
                            msg = "'functionMode' must be one of {} (received {}). " \
                                  "Aborting configuration.".format(
                                function_modes, fsp["functionMode"]
                            )
                            self._raise_configure_scan_fatal_error(msg)
                    else:
                        msg = "FSP specified, but 'functionMode' not given. " \
                              "Aborting configuration."
                        self._raise_configure_scan_fatal_error(msg)

                    fsp["frequencyBand"] = argin["frequencyBand"]
                    if "frequencyBandOffsetStream1" in argin:
                        fsp["frequencyBandOffsetStream1"] = argin["frequencyBandOffsetStream1"]
                    else:
                        fsp["frequencyBandOffsetStream1"] = 0
                    if "frequencyBandOffsetStream2" in argin:
                        fsp["frequencyBandOffsetStream2"] = argin["frequencyBandOffsetStream2"]
                    else:
                        fsp["frequencyBandOffsetStream2"] = 0
                    if "receptors" not in fsp:
                        fsp["receptors"] = self._receptors
                    if argin["frequencyBand"] in ["5a", "5b"]:
                        fsp["band5Tuning"] = argin["band5Tuning"]

                    ############ pass on configuration to FSP Subarray #############
                    ########## Correlation ##########
                    if fsp["functionMode"] == "CORR":
                        if "receptors" in fsp:
                            try:
                                proxy_fsp_subarray.RemoveAllReceptors()
                                proxy_fsp_subarray.AddReceptors(list(map(int, fsp["receptors"])))
                                proxy_fsp_subarray.RemoveAllReceptors()
                                for receptorCheck in fsp["receptors"]:
                                    if receptorCheck not in self._receptors:
                                        msg = ("Receptor {} does not belong to subarray {}.".format(
                                            str(self._receptors[receptorCheck]), str(self._subarray_id)))
                                        self.logger.error(msg)
                                        tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                                                     tango.ErrSeverity.ERR)
                            except tango.DevFailed:  # error in AddReceptors()
                                proxy_fsp_subarray.RemoveAllReceptors()
                                msg = sys.exc_info()[1].args[0].desc + "\n'receptors' was malformed."
                                self.logger.error(msg)
                                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                             tango.ErrSeverity.ERR)
                        else:
                            msg = "'receptors' not specified for Fsp PSS config"
                            self._raise_configure_scan_fatal_error(msg)

                        frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(fsp["frequencyBand"])

                        # Validate frequencySliceID.
                        if "frequencySliceID" in fsp:
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
                        else:
                            msg = "FSP specified, but 'frequencySliceID' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                         tango.ErrSeverity.ERR)

                        # Validate corrBandwidth.
                        if "corrBandwidth" in fsp:
                            if int(fsp["corrBandwidth"]) in list(range(0, 7)):
                                pass
                            else:
                                msg = "'corrBandwidth' must be an integer in the range [0, 6]."
                                # this is a fatal error
                                self.logger.error(msg)
                                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                             tango.ErrSeverity.ERR)
                        else:
                            msg = "FSP specified, but 'corrBandwidth' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                         tango.ErrSeverity.ERR)

                        # Validate zoomWindowTuning.
                        if fsp["corrBandwidth"]:  # zoomWindowTuning is required
                            if "zoomWindowTuning" in fsp:
                                if fsp["frequencyBand"] not in ["5a", "5b"]:  # frequency band is not band 5
                                    frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(fsp["frequencyBand"])
                                    frequency_band_start = [*map(lambda j: j[0] * 10 ** 9, [
                                        const.FREQUENCY_BAND_1_RANGE,
                                        const.FREQUENCY_BAND_2_RANGE,
                                        const.FREQUENCY_BAND_3_RANGE,
                                        const.FREQUENCY_BAND_4_RANGE
                                    ])][frequencyBand] + fsp["frequencyBandOffsetStream1"]
                                    # ])][fsp["frequencyBand"]] + fsp["frequencyBandOffsetStream1"]
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
                                    if argin["band5Tuning"] == [0,0]: # band5Tuning not specified
                                        pass
                                    else:
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
                        if "integrationTime" in fsp:
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
                        else:
                            msg = "FSP specified, but 'integrationTime' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                         tango.ErrSeverity.ERR)
                        # Validate fspChannelOffset
                        if "fspChannelOffset" in fsp:
                            try: 
                                if int(fsp["fspChannelOffset"])>=0: 
                                    pass
                                #has to be a multiple of 14880
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
                        else:
                            msg = "FSP specified, but 'fspChannelOffset' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                         tango.ErrSeverity.ERR)

                        # validate outputlink
                        if "outputLinkMap" in fsp:
                            
                            # check the format
                            try:
                                for element in fsp["outputLinkMap"]:
                                    a=int(element[0])
                            except:
                                msg = "'outputLinkMap' format not correct."
                                self.logger.error(msg)
                                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                            tango.ErrSeverity.ERR)
                        else:
                            msg = "FSP specified for Correlation, but 'outputLinkMap' not given."
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
                                    # if int(fsp["channelAveragingMap"][i][0]) == \
                                    #         i * self.NUM_FINE_CHANNELS / self.NUM_CHANNEL_GROUPS:
                                    #     pass  # the default value is already correct
                                    # else:
                                    #     msg = "'channelAveragingMap'[{0}][0] is not the channel ID of the " \
                                    #           "first channel in a group (received {1}).".format(
                                    #         i,
                                    #         fsp["channelAveragingMap"][i][0]
                                    #     )
                                    #     self.logger.error(msg)
                                    #     tango.Except.throw_exception("Command failed", msg,
                                    #                                  "ConfigureScan execution",
                                    #                                  tango.ErrSeverity.ERR)

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

                        # validate destination addresses: outputHost, outputMac, outputPort
                        if "outputHost" in fsp:
                            pass
                        else:
                            msg = "FSP specified for Correlation, but 'outputHost' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                         tango.ErrSeverity.ERR)
                        # outputMac is optional
                        if "outputMac" in fsp:
                            pass

                        else:
                            msg = "FSP specified for Correlation, but 'outputMac' not given."
                            self.logger.warn(msg)
                            
                        if "outputPort" in fsp:
                            pass

                        else:
                            msg = "FSP specified for Correlation, but 'outputPort' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                         tango.ErrSeverity.ERR)

                        # Add configID to fsp. It is not included in the "FSP" portion in configScan JSON
                        fsp["configID"]=argin["id"]


                        self._corr_config.append(fsp)
                        self._corr_fsp_list = [fsp["fspID"]]




                    if fsp["functionMode"] == "PSS-BF":
                        if "searchWindowID" in fsp:
                            if int(fsp["searchWindowID"]) in [1, 2]:
                                pass
                            else:  # searchWindowID not in valid range
                                msg = "'searchWindowID' must be one of [1, 2] (received {}).".format(
                                    str(fsp["searchWindowID"])
                                )
                                self._raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "Search window not specified for Fsp PSS config"
                            self._raise_configure_scan_fatal_error(msg)
                        if "searchBeam" in fsp:
                            if len(fsp["searchBeam"]) <= 192:
                                for searchBeam in fsp["searchBeam"]:
                                    if "searchBeamID" in searchBeam:
                                        if 1 <= int(searchBeam["searchBeamID"]) <= 1500:
                                            # Set searchBeamID attribute
                                            pass
                                        else:  # searchbeamID not in valid range
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
                                    else:
                                        msg = "Search beam ID not specified for Fsp PSS config"
                                        self._raise_configure_scan_fatal_error(msg)

                                        # Validate receptors.
                                        # This is always given, due to implementation details.
                                    if "receptors" in searchBeam:
                                        try:
                                            proxy_fsp_subarray.RemoveAllReceptors()
                                            proxy_fsp_subarray.AddReceptors(list(map(int, searchBeam["receptors"])))
                                            proxy_fsp_subarray.RemoveAllReceptors()
                                            for receptorCheck in searchBeam["receptors"]:
                                                if receptorCheck not in self._receptors:
                                                    msg = ("Receptor {} does not belong to subarray {}.".format(
                                                        str(self._receptors[receptorCheck]), str(self._subarray_id)))
                                                    self.logger.error(msg)
                                                    tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                                                                 tango.ErrSeverity.ERR)
                                        except tango.DevFailed:  # error in AddReceptors()
                                            proxy_fsp_subarray.RemoveAllReceptors()
                                            msg = sys.exc_info()[1].args[0].desc + "\n'receptors' was malformed."
                                            self.logger.error(msg)
                                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                                         tango.ErrSeverity.ERR)
                                    else:
                                        msg = "'receptors' not specified for Fsp PSS config"
                                        self._raise_configure_scan_fatal_error(msg)
                                    if "outputEnable" in searchBeam:
                                        if searchBeam["outputEnable"] is False or searchBeam["outputEnable"] is True:
                                            pass
                                        else:
                                            msg = "'outputEnabled' is not a valid boolean"
                                            self._raise_configure_scan_fatal_error(msg)
                                    else:
                                        msg = "'outputEnable' not specified for Fsp PSS config"
                                        self._raise_configure_scan_fatal_error(msg)
                                    if "averagingInterval" in searchBeam:
                                        if isinstance(searchBeam["averagingInterval"], int):
                                            pass
                                        else:
                                            msg = "'averagingInterval' is not a valid integer"
                                            self._raise_configure_scan_fatal_error(msg)
                                    else:
                                        msg = "'averagingInterval' not specified for Fsp PSS config"
                                        self._raise_configure_scan_fatal_error(msg)
                                    if "searchBeamDestinationAddress" in searchBeam:
                                        if validate_ip(searchBeam["searchBeamDestinationAddress"]):
                                            pass
                                        else:
                                            msg = "'searchBeamDestinationAddress' is not a valid IP address"
                                            self._raise_configure_scan_fatal_error(msg)
                                    else:
                                        msg = "'searchBeamDestinationAddress' not specified for Fsp PSS config"
                                        self._raise_configure_scan_fatal_error(msg)
                            else:
                                msg = "More than 192 SearchBeams defined in PSS-BF config"
                                self._raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "'searchBeam' not defined in PSS-BF config"
                            self._raise_configure_scan_fatal_error(msg)

                        self._pss_config.append(fsp)
                        self._pss_fsp_list.append(fsp["fspID"])

                    proxy_fsp.unsubscribe_event(
                        proxy_fsp.subscribe_event(
                            "State",
                            tango.EventType.CHANGE_EVENT,
                            self._state_change_event_callback
                        )
                    )
                    proxy_fsp.unsubscribe_event(
                        proxy_fsp.subscribe_event(
                            "healthState",
                            tango.EventType.CHANGE_EVENT,
                            self._state_change_event_callback
                        )
                    )

                except tango.DevFailed:  # exception in ConfigureScan
                    msg = "An exception occurred while configuring FSPs:\n{}\n" \
                          "Aborting configuration".format(sys.exc_info()[1].args[0].desc)

                    self._raise_configure_scan_fatal_error(msg)
        else:
            msg = "'fsp' not given. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        # At this point, everything has been validated.

    def _raise_configure_scan_fatal_error(self, msg):
        self.logger.error(msg)
        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                     tango.ErrSeverity.ERR)

    # PROTECTED REGION END #    //  CbfSubarray.class_variable


    def _deconfigure(self):
        """Helper function to unsubscribe events and release resources."""
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
        self._group_vcc.command_inout("GoToIdle")
        self._group_fsp_corr_subarray.command_inout("GoToIdle")
        self._group_fsp_pss_subarray.command_inout("GoToIdle")

        # change FSP subarray membership
        data = tango.DeviceData()
        data.insert(tango.DevUShort, self._subarray_id)
        self.logger.info(data)
        self._group_fsp.command_inout("RemoveSubarrayMembership", data)
        self._group_fsp.remove_all()
        self._proxies_assigned_fsp.clear()

        # remove channel info from FSP subarrays
        # already done in GoToIdle
        self._group_fsp_corr_subarray.remove_all()
        self._group_fsp_pss_subarray.remove_all()
        self._proxies_assigned_fsp_corr_subarray.clear()

        # configID needs to set to empty string (FSPCorrSubarray's configID set to empty automatically by calling gotoIDLE)
        self._config_ID = ""
        self._group_vcc.write_attribute("configID","")


        self._last_received_delay_model = "{}"

        # TODO need to add this check for fspSubarrayPSS and VLBI and PST once implemented
        for fsp_corr_subarray_proxy in self._proxies_fsp_corr_subarray:
            if fsp_corr_subarray_proxy.State() == tango.DevState.ON:
                fsp_corr_subarray_proxy.GoToIdle()
        for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
            if fsp_pss_subarray_proxy.State() == tango.DevState.ON:
                fsp_pss_subarray_proxy.GoToIdle()

        # reset scanID in case it's not reset
        self.scanID = 0

    def _remove_repectors_helper(self, argin):
        """Helper function to remove receptors for removeAllReceptors. Takes in a list of integers.
        RemoveAllReceptors can't call RemoveReceptors anymore for lmc 0.6.0 because RemoveAllReceptors enters resourcing state before calling RemoveReceptors.
        Therefore this helper is useful."""
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

                vccProxy.subarrayMembership = 0

                self._receptors.remove(receptorID)
                self._proxies_assigned_vcc.remove(vccProxy)
                self._group_vcc.remove(self._fqdn_vcc[vccID - 1])
            else:
                log_msg = "Receptor {} not assigned to subarray. Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)

        # transitions to EMPTY if not assigned any receptors
        if not self._receptors:
            self.state_model._set_obs_state(ObsState.EMPTY)


    # Used by commands that needs resource manager in SKASubarray base class (for example AddReceptors command). 
    # The base class define len as len(resource_manager), so we need to change that here.
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

    CorrConfigAddress = device_property(
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

    # outputLinksDistribution = attribute( #???
    #     dtype='str',
    #     label="Distribution of output links",
    #     doc="Distribution of output links, given as a JSON object",
    # )

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
        doc="fsp[1][x] = CORR [2[x] = PSS [1][x] = PST [1][x] = VLBI",
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
        def do(self):
            """
            entry point; 
            initialize the attributes and the properties of the CbfSubarray
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
            device._pss_config = []
            device._corr_config = []
            # store list of fsp being used for each function mode
            device._corr_fsp_list = []
            device._pss_fsp_list = []
            device._latest_scan_config=""
            # device._published_output_links = False# ???
            # device._last_received_vis_destination_address = "{}"#???
            device._last_received_delay_model = "{}"

            device._mutex_delay_model_config = Lock()

            # for easy device-reference
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._stream_tuning = [0, 0]

            # device proxy for easy reference to CBF Master
            device._proxy_cbf_master = tango.DeviceProxy(device.CbfMasterAddress)

            device.MIN_INT_TIME = const.MIN_INT_TIME
            device.NUM_CHANNEL_GROUPS = const.NUM_CHANNEL_GROUPS
            device.NUM_FINE_CHANNELS = const.NUM_FINE_CHANNELS

            device._proxy_sw_1 = tango.DeviceProxy(device.SW1Address)
            device._proxy_sw_2 = tango.DeviceProxy(device.SW2Address)

            # JSON FSP configurations for PSS, COR, PST, VLBI
            device._proxy_pss_config = tango.DeviceProxy(device.PssConfigAddress)
            device._proxy_corr_config = tango.DeviceProxy(device.CorrConfigAddress) # address of CbfSubarrayCoorConfig device in Subarray Multi

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


            device._proxies_vcc = [*map(tango.DeviceProxy, device._fqdn_vcc)]
            device._proxies_fsp = [*map(tango.DeviceProxy, device._fqdn_fsp)]
            device._proxies_fsp_corr_subarray = [*map(tango.DeviceProxy, device._fqdn_fsp_corr_subarray)]
            device._proxies_fsp_pss_subarray = [*map(tango.DeviceProxy, device._fqdn_fsp_pss_subarray)]

            device._proxies_assigned_vcc = []
            device._proxies_assigned_fsp = []
            device._proxies_assigned_fsp_corr_subarray = []
            device._proxies_assigned_fsp_pss_subarray = []

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


            return (ResultCode.OK, "successfull")






    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        """hook to delete device. Set State to DISABLE, romove all receptors, go to OBsState IDLE"""
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.DISABLE)
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

    # def read_outputLinksDistribution(self):# ???
    #     # PROTECTED REGION ID(CbfSubarray.outputLinksDistribution_read) ENABLED START #
    #     """Return outputLinksDistribution attribute: a JSON object containning info about the fine channels configured to be sent to SDP, including output links."""
    #     return json.dumps(self._output_links_distribution)
    #     # PROTECTED REGION END #    //  CbfSubarray.outputLinksDistribution_read

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

    def is_On_allowed(self):
        """allowed if DevState is OFF"""
        if self.dev_state() == tango.DevState.OFF:
            return True
        return False

    class OnCommand(SKASubarray.OnCommand):
        def do(self):
            (result_code,message)=super().do()
            device = self.target
            device._proxy_sw_1.SetState(tango.DevState.DISABLE)
            device._proxy_sw_2.SetState(tango.DevState.DISABLE)
            return (result_code,message)




    def is_Off_allowed(self):
        """allowed if DevState is ON"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    class OffCommand(SKASubarray.OffCommand):
        def do(self):
            (result_code,message)=super().do()
            device = self.target
            device._proxy_sw_1.SetState(tango.DevState.OFF)
            device._proxy_sw_2.SetState(tango.DevState.OFF)
            return (result_code,message)

 

    ##########################################  Receptors   ####################################################
        

    class RemoveReceptorsCommand(SKASubarray.ReleaseResourcesCommand):
        def do(self, argin):
            device=self.target
            # if self.state_model._obs_state != ObsState.IDLE.value:
            #     msg = "Device not in IDLE obsState."
            #     self.logger.error(msg)
            #     tango.Except.throw_exception("Command failed", msg, "RemoveReceptors execution",
            #                                 tango.ErrSeverity.ERR)

            device._remove_repectors_helper(argin)
            message = "CBFSubarray RemoveReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)
            # PROTECTED REGION END #    //  CbfSubarray.RemoveReceptors

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.RemoveReceptors) ENABLED START #
        """remove from list of receptors. Turn Subarray OFF if no receptors assigned"""
        command = self.get_command_object("RemoveReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]



    # def is_RemoveAllReceptors_allowed(self):
    #     """allowed if state is ON or OFF"""
    #     if self.dev_state() in [tango.DevState.OFF, tango.DevState.ON]:
    #         return True
    #     return False

    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
        """Remove all receptors. Turn Subarray OFF if no receptors assigned"""
        # if self.state_model._obs_state != ObsState.IDLE.value:
        #     msg = "Device not in IDLE obsState."
        #     self.logger.error(msg)
        #     tango.Except.throw_exception("Command failed", msg, "RemoveAllReceptors execution",
        #                                  tango.ErrSeverity.ERR)

        command = self.get_command_object("RemoveAllReceptors")
        (return_code, message) = command()
        return [[return_code], [message]]  
        # PROTECTED REGION END #    //  CbfSubarray.RemoveAllReceptors

    class RemoveAllReceptorsCommand(SKASubarray.ReleaseResourcesCommand):
        def do(self):
            device=self.target
            self.logger.info("removeAllReceptors")

            # For LMC0.6.0: use a helper instead of a command so that it doesn't care about the obsState
            device._remove_repectors_helper(device._receptors[:])


            message = "CBFSubarray RemoveAllReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message


    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    def AddReceptors(self, argin):
        """
        Assign resources to this subarray
        """
        command = self.get_command_object("AddReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]    

    # didn't inherit SKASubarray._ResourcingCommand because will give error on len(self.target)
    class AddReceptorsCommand(SKASubarray.AssignResourcesCommand):
        # def __init__(self,target,state_model,logger=None):
        #     super().__init__(target, state_model, "assign", logger=logger)

        def do(self, argin):
            device=self.target
            # Code here
            errs = []  # list of error messages
            receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                                device._proxy_cbf_master.receptorToVcc)
            for receptorID in argin:
                try:
                    vccID = receptor_to_vcc[receptorID]
                    vccProxy = device._proxies_vcc[vccID - 1]
                    subarrayID = vccProxy.subarrayMembership

                    # only add receptor if it does not already belong to a different subarray
                    if subarrayID not in [0, device._subarray_id]:
                        errs.append("Receptor {} already in use by subarray {}.".format(
                            str(receptorID), str(subarrayID)))
                    else:
                        if receptorID not in device._receptors:
                            # change subarray membership of vcc
                            vccProxy.subarrayMembership = device._subarray_id

                            # !!!!!!!!!!!!!
                            # Change done on 09/27/2109 as a consequence of the new TANGO and tango images release
                            # Note:json does not recognize NumPy data types. Convert the number to a Python int 
                            # before serializing the object.
                            # The list of receptors is serialized when the FSPs are configured for a scan.
                            # !!!!!!!!!!!!!

                            device._receptors.append(int(receptorID))
                            device._proxies_assigned_vcc.append(vccProxy)
                            device._group_vcc.add(device._fqdn_vcc[vccID - 1])

                            # subscribe to VCC state and healthState changes
                            event_id_state, event_id_health_state = vccProxy.subscribe_event(
                                "State",
                                tango.EventType.CHANGE_EVENT,
                                device._state_change_event_callback
                            ), vccProxy.subscribe_event(
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

            # # transition to ON if at least one receptor is assigned
            # if device._receptors:
            #     device.set_state(DevState.ON)

            if errs:
                msg = "\n".join(errs)
                self.logger.error(msg)
                # tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                #                             tango.ErrSeverity.ERR)
                
                return (ResultCode.FAILED, msg)

            message = "CBFSubarray AddReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)







    ###################### Configure #########################

    # def is_Configure_allowed(self):
    #     """allowed if DevState is ON"""
    #     if self.dev_state() == tango.DevState.ON:
    #         return True
    #     return False
    class ConfigureScanCommand(SKASubarray.ConfigureCommand):
        def do(self, argin):
            # (result_code,message)=super().do(argin)
            device=self.target
            # Code here
            device._pss_config = []
            device._corr_config = []
            device._corr_fsp_list = []
            device._pss_fsp_list = []
            device._corr_fsp_list = []
            device._fsp_list = [[], [], [], []]

            ################# validate scan configuration first ##########################
            try:
                device._validate_scan_configuration(argin)
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self.logger.warn("validate scan configuration error")
                # device._raise_configure_scan_fatal_error(msg)
                


            # Call this just to release all FSPs and unsubscribe to events. Can't call GoToIdle, otherwise there will be state transition problem. 
            device._deconfigure()

            # transition to obsState=CONFIGURING - don't have to do
            
            data = tango.DeviceData()
            data.insert(tango.DevUShort, ObsState.CONFIGURING.value)
            device._group_vcc.command_inout("SetObservingState", data)

            argin = json.loads(argin)
            # set band5Tuning to [0,0] if not specified
            if "band5Tuning" not in argin: 
                argin["band5Tuning"]=[0,0]

            # Configure configID.
            device._config_ID = str(argin["id"])

            # Configure frequencyBand.
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            device._frequency_band = frequency_bands.index(argin["frequencyBand"])
            data = tango.DeviceData()
            data.insert(tango.DevString, argin["frequencyBand"])
            device._group_vcc.command_inout("SetFrequencyBand", data)

            # Configure band5Tuning, if frequencyBand is 5a or 5b.
            if device._frequency_band in [4, 5]:
                stream_tuning = [*map(float, argin["band5Tuning"])]
                device._stream_tuning = stream_tuning
                device._group_vcc.write_attribute("band5Tuning", stream_tuning)

            # Configure frequencyBandOffsetStream1.
            if "frequencyBandOffsetStream1" in argin:
                device._frequency_band_offset_stream_1 = int(argin["frequencyBandOffsetStream1"])
                device._group_vcc.write_attribute(
                    "frequencyBandOffsetStream1",
                    int(argin["frequencyBandOffsetStream1"])
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
                if "frequencyBandOffsetStream2" in argin:
                    device._frequency_band_offset_stream_2 = int(argin["frequencyBandOffsetStream2"])
                    device._group_vcc.write_attribute(
                        "frequencyBandOffsetStream2",
                        int(argin["frequencyBandOffsetStream2"])
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
            if "dopplerPhaseCorrSubscriptionPoint" in argin:
                attribute_proxy = tango.AttributeProxy(argin["dopplerPhaseCorrSubscriptionPoint"])
                attribute_proxy.ping()
                event_id = attribute_proxy.subscribe_event(
                    tango.EventType.CHANGE_EVENT,
                    device._doppler_phase_correction_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure delayModelSubscriptionPoint.
            device._last_received_delay_model = "{}"
            attribute_proxy = tango.AttributeProxy(argin["delayModelSubscriptionPoint"])
            attribute_proxy.ping() #To be sure the connection is good(don't know if the device is running)
            event_id = attribute_proxy.subscribe_event(
                tango.EventType.CHANGE_EVENT,
                device._delay_model_event_callback
            )
            device._events_telstate[event_id] = attribute_proxy



            # Configure rfiFlaggingMask.
            if "rfiFlaggingMask" in argin:
                device._group_vcc.write_attribute(
                    "rfiFlaggingMask",
                    json.dumps(argin["rfiFlaggingMask"])
                )
            else:
                log_msg = "'rfiFlaggingMask' not given. Proceeding."
                self.logger.warn(log_msg)

            # Configure searchWindow.
            if "searchWindow" in argin:
                for search_window in argin["searchWindow"]:
                    # pass on configuration to VCC
                    data = tango.DeviceData()
                    data.insert(tango.DevString, json.dumps(search_window))
                    device._group_vcc.command_inout("ConfigureSearchWindow", data)
                    device.ConfigureSearchWindow(json.dumps(search_window))
            else:
                log_msg = "'searchWindow' not given."
                self.logger.warn(log_msg)

            # Configure configID
            device._group_vcc.write_attribute("configID",argin["id"])

            # The VCCs are done configuring at this point
            data = tango.DeviceData()
            data.insert(tango.DevUShort, ObsState.READY.value)
            device._group_vcc.command_inout("SetObservingState", data)

            ###################### FSP Subarray ####################
            # pass on configuration to individual function mode class to configure the FSP Subarray

            if len(device._pss_config) != 0:
                device._proxy_pss_config.ConfigureFSP(json.dumps(device._pss_config))

            if len(device._corr_config) != 0: 
                #_proxy_corr_config is address of CbfSubarrayCoorConfig device in Subarray Multi
                #_corr_config is fsp part of the JSON, formed by the function _validate_scan_configuration
                device._proxy_corr_config.ConfigureFSP(json.dumps(device._corr_config)) 

            #TODO add PST and VLBI to this once they are implemented
            device._fsp_list[0].append(device._corr_fsp_list)
            device._fsp_list[1].append(device._pss_fsp_list)


            ####################### FSP ############################
            # Configure FSP.
            for fsp in argin["fsp"]:
                # Configure fspID.
                fspID = int(fsp["fspID"])
                proxy_fsp = device._proxies_fsp[fspID - 1]
                proxy_fsp_corr_subarray = device._proxies_fsp_corr_subarray[fspID - 1]
                proxy_fsp_pss_subarray = device._proxies_fsp_pss_subarray[fspID - 1]
                device._proxies_assigned_fsp.append(proxy_fsp)
                device._proxies_assigned_fsp_corr_subarray.append(proxy_fsp_corr_subarray)
                device._proxies_assigned_fsp_pss_subarray.append(proxy_fsp_pss_subarray)
                device._group_fsp.add(device._fqdn_fsp[fspID - 1])
                device._group_fsp_corr_subarray.add(device._fqdn_fsp_corr_subarray[fspID - 1])
                device._group_fsp_pss_subarray.add(device._fqdn_fsp_pss_subarray[fspID - 1])

                # change FSP subarray membership
                proxy_fsp.AddSubarrayMembership(device._subarray_id)

                # Configure functionMode.
                proxy_fsp.SetFunctionMode(fsp["functionMode"])

                fsp["frequencyBand"] = argin["frequencyBand"]
                if "frequencyBandOffsetStream1" in argin:
                    fsp["frequencyBandOffsetStream1"] = device._frequency_band_offset_stream_1
                else:
                    fsp["frequencyBandOffsetStream1"] = 0
                if "frequencyBandOffsetStream2" in argin:
                    fsp["frequencyBandOffsetStream2"] = device._frequency_band_offset_stream_2
                else:
                    fsp["frequencyBandOffsetStream2"] = 0
                if "receptors" not in fsp:
                    fsp["receptors"] = device._receptors
                if device._frequency_band in [4, 5]:
                    fsp["band5Tuning"] = device._stream_tuning

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

           
            # This state transition will be later
            # 03-23-2020:
            # CbfSubarray moves to READY only after the publication of the visibilities
            # addresses generated by SDP.


            #save it into lastestScanConfig
            device._latest_scan_config=str(argin)
            message = "CBFSubarray Configure command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)




    # def is_ConfigureScan_allowed(self):
    #     """allowed if state is ON"""
    #     if self.dev_state() == tango.DevState.ON:
    #         return True
    #     return False

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        # """
        """Change state to CONFIGURING.
        Configure attributes from input JSON. Subscribe events. Configure VCC, VCC subarray, FSP, FSP Subarray. 
        publish output links.
        """
        # if self.state_model._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
        #     msg = "Device not in IDLE or READY obsState."
        #     self.logger.error(msg)
        #     tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
        #                                  tango.ErrSeverity.ERR)

        # Only after successful validation of the received configuration,
        # subarray is configured.
        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]    









    def is_ConfigureSearchWindow_allowed(self):
        """subarray has to be On to configure searchwindow"""
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ConfigureSearchWindow(self, argin):
        # PROTECTED REGION ID(CbfSubarray.ConfigureSearchWindow) ENABLED START #
        # This function is called after the configuration has already been validated,
        # so the checks here have been removed to reduce overhead.
        """revceives a JSON object to configure a search window"""
        # if self.state_model._obs_state != ObsState.CONFIGURING.value:
        #     msg = "Device not in CONFIGURING obsState."
        #     self.logger.error(msg)
        #     tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
        #                                  tango.ErrSeverity.ERR)

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

        # `Configure tdcDestinationAddress.`
        if argin["tdcEnable"]:
            # TODO: validate input
            proxy_sw.tdcDestinationAddress = \
                json.dumps(argin["tdcDestinationAddress"])

        # PROTECTED REGION END #    //  CbfSubarray.ConfigureSearchWindow

    ###################### Scan ######################### 
    def is_Scan_allowed(self):
        """allowed if Subarray is ON, and ObsState Ready."""
        if self.dev_state() == tango.DevState.ON:
            if self.state_model._obs_state==ObsState.READY.value:
                return True
        return False

    @command(
        dtype_in='uint',
        doc_in="Scan ID",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )
    def Scan(self, argin):
        """
        Start Scan
        """
        command = self.get_command_object("StartScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class StartScanCommand(SKASubarray.ScanCommand):
        def do(self, argin):
            # overwrites the do hook
            # (result_code,message)=super().do() 
            device=self.target

            # Do the following
            device._scan_ID=int(argin)
            data = tango.DeviceData()
            data.insert(tango.DevUShort, argin)
            device._group_vcc.command_inout("Scan", data)
            device._group_fsp_corr_subarray.command_inout("Scan", data)
            device._group_fsp_pss_subarray.command_inout("Scan")

            message = "Scan command successfull"
            self.logger.info(message)
            return (ResultCode.STARTED, message)



    ###################### EndScan ######################### 
    def is_EndScan_allowed(self):
        """allowed if SUbarray is ON"""
        if self.dev_state() == tango.DevState.ON and self.state_model._obs_state==ObsState.SCANNING:
            return True
        return False


    class EndScanCommand(SKASubarray.EndScanCommand):
        def do(self):
            (result_code,message)=super().do()
            device=self.target
            # Code here
            device._group_vcc.command_inout("EndScan")
            device._group_fsp_corr_subarray.command_inout("EndScan")
            device._group_fsp_pss_subarray.command_inout("EndScan")
            device._scan_ID=0

            message = "EndScan command OK"
            self.logger.info(message)
            return (ResultCode.OK, message)




    ############################## GO To Idle #########################


    # def is_GoToIdle_allowed(self):
    #     """allowed if state is ON or OFF"""
    #     if self.dev_state() in [tango.DevState.OFF, tango.DevState.ON]:
    #         return True
    #     return False


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
        def do(self):
            device=self.target
            device._deconfigure()

            message = "GoToIdle command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)


############################### abort, restart and reset ###########################################

    class AbortCommand(SKASubarray.AbortCommand):
        def do(self):
            (result_code,message)=super().do()
            device = self.target
            return (result_code,message)

    
    # RestartCommand already registered in SKASubarray, so no "def restart" needed
    class RestartCommand(SKASubarray.RestartCommand):
        def do(self):
            device = self.target

            # We might have interrupted a long-running command such as a Configure
            # or a Scan, so we need to clean up from that.

            # Now totally deconfigure
            device._deconfigure()

            # and release all receptors
            device._remove_repectors_helper(device._receptors[:])

            message = "Restart command completed OK"
            self.logger.info(message)
            return (ResultCode.OK,message)


    class ObsResetCommand(SKASubarray.ObsResetCommand):
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

            # Now totally deconfigure
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
