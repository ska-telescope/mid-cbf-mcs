# -*- coding: utf-8 -*-
#
# This file is part of the CbfSubarray project
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
from skabase.control_model import ObsState, AdminMode
from skabase.SKASubarray.SKASubarray import SKASubarray

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

    def __void_callback(self, event):
        # This callback is only meant to be used to test if a subscription is valid
        if not event.err:
            pass
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def __doppler_phase_correction_event_callback(self, event):
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

    def __delay_model_event_callback(self, event):
        if not event.err:
            if self._obs_state not in [ObsState.READY.value, ObsState.SCANNING.value]:
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
                        target=self.__update_delay_model,
                        args=(int(delay_model["epoch"]), json.dumps(delay_model["delayDetails"]))
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

    def __update_delay_model(self, epoch, model):
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

    def __vis_destination_address_event_callback(self, event):
        if not event.err:
            if self._obs_state not in [ObsState.CONFIGURING.value, ObsState.READY.value]:
                log_msg = "Ignoring destination addresses (obsState not correct)."
                self.logger.info(log_msg)
                return
            if not self._published_output_links:
                log_msg = "Ignoring destination addresses (output links not published yet)."
                self.logger.warn(log_msg)
                return
            try:
                log_msg = "Received destination addresses for visibilities."
                self.logger.info(log_msg)

                value = str(event.attr_value.value)
                if value == self._last_received_vis_destination_address:
                    log_msg = "Ignoring destination addresses (identical to previous)."
                    self.logger.info(log_msg)
                    return

                self._last_received_vis_destination_address = value
                destination_addresses = json.loads(value)

                # No exception should technically ever be raised here.
                if destination_addresses["scanId"] != self._scan_ID:
                    raise ValueError("scan ID is not correct")
                for fsp in destination_addresses["receiveAddresses"]:
                    proxy_fsp_subarray = self._proxies_fsp_subarray[fsp["fspId"] - 1]
                    if proxy_fsp_subarray not in self._proxies_assigned_fsp_subarray:
                        raise ValueError("FSP {} does not belong to subarray {}.".format(
                            fsp["fspId"], self._subarray_id
                        )
                        )
                    log_msg = "Configuring destination addresses for FSP {}...".format(
                        fsp["fspId"]
                    )
                    self.logger.info(log_msg)
                    proxy_fsp_subarray.AddChannelAddresses(value)

                log_msg = "Done configuring destination addresses."
                self.logger.info(log_msg)

                # transition to obsState=READY
                self._obs_state = ObsState.READY.value
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.logger.error(log_msg)

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

    def __generate_output_links(self, scan_cfg):
        # At this point, we can assume that the scan configuration is valid and that the FSP
        # attributes have been set properly.
        output_links_all = {
            "scanID": self._scan_ID,
            "fsp": []
        }

        for fsp in scan_cfg["fsp"]:
            if fsp["functionMode"] == "CORR":
                output_links = {
                    "fspID": int(fsp["fspID"]),
                    "frequencySliceID": int(fsp["frequencySliceID"]),
                    "cbfOutLink": []
                }
                links = [[] for i in range(const.NUM_OUTPUT_LINKS)]
                channel_averaging_map_default = [
                    [int(i * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS) + 1, 0]
                    for i in range(const.NUM_CHANNEL_GROUPS)
                ]

                if "channelAveragingMap" in fsp:
                    channel_averaging_map = fsp["channelAveragingMap"]
                else:
                    channel_averaging_map = channel_averaging_map_default

                bandwidth = const.FREQUENCY_SLICE_BW * 10 ** 6 / 2 ** int(fsp["corrBandwidth"])

                if not int(fsp["corrBandwidth"]):  # correlate the full bandwidth
                    if self._frequency_band in list(range(4)):  # frequency band is not band 5
                        frequency_slice_start = [*map(lambda j: j[0] * 10 ** 9, [
                            const.FREQUENCY_BAND_1_RANGE,
                            const.FREQUENCY_BAND_2_RANGE,
                            const.FREQUENCY_BAND_3_RANGE,
                            const.FREQUENCY_BAND_4_RANGE
                        ])][self._frequency_band] + \
                                                (int(
                                                    fsp["frequencySliceID"]) - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6 + \
                                                self._frequency_band_offset_stream_1

                    else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                        if int(fsp["frequencySliceID"]) <= 13:  # stream 1
                            frequency_slice_start = scan_cfg["band5Tuning"][0] * 10 ** 9 - \
                                                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                                    (int(fsp[
                                                             "frequencySliceID"]) - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6 + \
                                                    self._frequency_band_offset_stream_1
                        else:  # 14 <= self._frequency_slice <= 26  # stream 2
                            frequency_slice_start = scan_cfg["band5Tuning"][1] * 10 ** 9 - \
                                                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                                    (int(fsp[
                                                             "frequencySliceID"]) - 14) * const.FREQUENCY_SLICE_BW * 10 ** 6 + \
                                                    self._frequency_band_offset_stream_2
                else:  # correlate a portion of the full bandwidth
                    # since the checks were already done, this is actually simpler
                    frequency_slice_start = int(fsp["zoomWindowTuning"]) * 10 ** 3 - bandwidth / 2

                next_channel_start = frequency_slice_start

                for channel_group_ID in range(const.NUM_CHANNEL_GROUPS):
                    channel_avg = channel_averaging_map[channel_group_ID][1]

                    if channel_avg:  # send channels to SDP
                        channel_bandwidth = bandwidth / const.NUM_FINE_CHANNELS * channel_avg

                        for channel_ID in range(
                                int(channel_group_ID * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS) + 1,
                                int((channel_group_ID + 1) * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS) \
                                + 1,
                                channel_avg
                        ):
                            log_msg = "Assigning output link for channel {} of FSP {}...".format(
                                channel_ID, fsp["fspID"]
                            )
                            self.logger.warn(log_msg)

                            channel = {
                                "chanID": channel_ID,
                                "bw": int(channel_bandwidth),
                                "cf": int(next_channel_start + channel_bandwidth / 2)
                            }
                            links[randint(0, const.NUM_OUTPUT_LINKS - 1)].append(channel)
                            next_channel_start += channel_bandwidth
                    else:  # don't send channels to SDP
                        next_channel_start += bandwidth / const.NUM_CHANNEL_GROUPS

                for link_ID in range(1, const.NUM_OUTPUT_LINKS + 1):
                    if links[link_ID - 1]:
                        output_links["cbfOutLink"].append({
                            "linkID": link_ID,
                            "channel": links[link_ID - 1]
                        })

                output_links_all["fsp"].append(output_links)

        # output_links_all has the outputlinks information for all the FSP
        # assigned to the subarray.
        json_output_links = json.dumps(output_links_all)
        data = tango.DeviceData()
        data.insert(tango.DevString, json_output_links)
        self._group_fsp_subarray.command_inout("AddChannels", data)

        log_msg = "Done assigning output links."
        self.logger.info(log_msg)
        # publish the output links
        self._output_links_distribution = output_links_all
        self.push_change_event("outputLinksDistribution", json_output_links)
        self._published_output_links = True

    def __validate_scan_configuration(self, argin):
        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        for proxy in self._proxies_assigned_vcc:
            if proxy.State() != tango.DevState.ON:
                msg = "VCC {} is not ON. Aborting configuration.".format(
                    self._proxies_vcc.index(proxy) + 1
                )
                self.__raise_configure_scan_fatal_error(msg)

        # Validate scanID.
        if "scanID" in argin:
            if int(argin["scanID"]) <= 0:  # scanID not positive
                msg = "'scanID' must be positive (received {}). " \
                      "Aborting configuration.".format(int(argin["scanID"]))
                self.__raise_configure_scan_fatal_error(msg)
            elif any(map(lambda i: i == int(argin["scanID"]),
                         self._proxy_cbf_master.subarrayScanID)) and \
                    int(argin["scanID"]) != self._scan_ID:  # scanID already taken
                msg = "'scanID' must be unique (received {}). " \
                      "Aborting configuration.".format(int(argin["scanID"]))
                self.__raise_configure_scan_fatal_error(msg)
            else:
                pass
        else:
            msg = "'scanID' must be given. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        # Validate frequencyBand.
        if "frequencyBand" in argin:
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            if argin["frequencyBand"] in frequency_bands:
                pass
            else:
                msg = "'frequencyBand' must be one of {} (received {}). " \
                      "Aborting configuration.".format(frequency_bands, argin["frequency_band"])
                self.__raise_configure_scan_fatal_error(msg)
        else:
            msg = "'frequencyBand' must be given. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        # Validate band5Tuning, if frequencyBand is 5a or 5b.
        if argin["frequencyBand"] in ["5a", "5b"]:
            if "band5Tuning" in argin:
                # check if streamTuning is an array of length 2
                try:
                    assert len(argin["band5Tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                    self.__raise_configure_scan_fatal_error(msg)

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
                        self.__raise_configure_scan_fatal_error(msg)
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
                        self.__raise_configure_scan_fatal_error(msg)
            else:
                msg = "'band5Tuning' must be given for a 'frequencyBand' of {}. " \
                      "Aborting configuration".format(argin["frequencyBand"])
                self.__raise_configure_scan_fatal_error(msg)

        # Validate frequencyBandOffsetStream1.
        if "frequencyBandOffsetStream1" in argin:
            if abs(int(argin["frequencyBandOffsetStream1"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream1' must be at most half " \
                      "of the frequency slice bandwidth. Aborting configuration."
                self.__raise_configure_scan_fatal_error(msg)
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
                    self.__raise_configure_scan_fatal_error(msg)
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
                        self.__void_callback
                    )
                )
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = "Attribute {} not found or not set up correctly for " \
                      "'dopplerPhaseCorrSubscriptionPoint'. Aborting configuration.".format(
                    argin["dopplerPhaseCorrSubscriptionPoint"]
                )
                self.__raise_configure_scan_fatal_error(msg)
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
                        self.__void_callback
                    )
                )

            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = "Attribute {} not found or not set up correctly for " \
                      "'delayModelSubscriptionPoint'. Aborting configuration.".format(
                    argin["delayModelSubscriptionPoint"]
                )
                self.__raise_configure_scan_fatal_error(msg)
        else:
            msg = "'delayModelSubscriptionPoint' not given. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        # Validate visDestinationAddressSubscriptionPoint.
        if "visDestinationAddressSubscriptionPoint" in argin:
            try:
                attribute_proxy = tango.AttributeProxy(
                    argin["visDestinationAddressSubscriptionPoint"]
                )
                attribute_proxy.ping()
                attribute_proxy.unsubscribe_event(
                    attribute_proxy.subscribe_event(
                        tango.EventType.CHANGE_EVENT,
                        self.__void_callback
                    )
                )
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = "Attribute {} not found or not set up correctly for " \
                      "'visDestinationAddressSubscriptionPoint'. Aborting configuration.".format(
                    argin["visDestinationAddressSubscriptionPoint"]
                )
                self.__raise_configure_scan_fatal_error(msg)
        else:
            msg = "'visDestinationAddressSubscriptionPoint' not given. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        # Validate rfiFlaggingMask.

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

                            self.__raise_configure_scan_fatal_error(msg)
                    # If the search window configuration is valid for all VCCs,
                    # is is guaranteed to be valid for the CBF Subarray.
                    # self.ConfigureSearchWindow(json.dumps(search_window))

            except (TypeError, AssertionError):  # searchWindow not the right length or not an array
                msg = "'searchWindow' must be an array of maximum length 2. " \
                      "Aborting configuration."
                self.__raise_configure_scan_fatal_error(msg)
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
                            proxy_fsp_subarray = self._proxies_fsp_subarray[fspID - 1]
                        else:
                            msg = "'fspID' must be an integer in the range [1, {}]. " \
                                  "Aborting configuration.".format(str(self._count_fsp))
                            self.__raise_configure_scan_fatal_error(msg)
                    else:
                        msg = "FSP specified, but 'fspID' not given. " \
                              "Aborting configuration."
                        self.__raise_configure_scan_fatal_error(msg)

                    if proxy_fsp.State() != tango.DevState.ON:
                        msg = "FSP {} is not ON. Aborting configuration.".format(fspID)
                        self.__raise_configure_scan_fatal_error(msg)

                    if proxy_fsp_subarray.State() != tango.DevState.ON:
                        msg = "Subarray {} of FSP {} is not ON. Aborting configuration.".format(
                            self._subarray_id, fspID
                        )
                        self.__raise_configure_scan_fatal_error(msg)

                    # Validate functionMode.
                    function_modes = ["CORR", "PSS-BF", "PST-BF", "VLBI"]
                    if "functionMode" in fsp:
                        if fsp["functionMode"] in function_modes:
                            if function_modes.index(fsp["functionMode"]) + 1 == \
                                    proxy_fsp.functionMode or \
                                    proxy_fsp.functionMode == 0:
                                pass
                            else:
                                #TODO need to add this check for fspSubarrayPSS and VLBI and PST once implemented
                                for fsp_subarray_corr_proxy in self._proxies_fsp_subarray:
                                    if fsp_subarray_corr_proxy.obsState != ObsState.IDLE:
                                        msg = "A different subarray is using FSP {} for a " \
                                              "different function mode. Aborting configuration.".format(
                                               fsp["fspID"]
                                               )
                                        self.__raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "'functionMode' must be one of {} (received {}). " \
                                  "Aborting configuration.".format(
                                function_modes, fsp["functionMode"]
                            )
                            self.__raise_configure_scan_fatal_error(msg)
                    else:
                        msg = "FSP specified, but 'functionMode' not given. " \
                              "Aborting configuration."
                        self.__raise_configure_scan_fatal_error(msg)

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

                    # pass on configuration to FSP Subarray
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
                            self.__raise_configure_scan_fatal_error(msg)

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
                                if fsp["frequencyBand"] in list(range(4)):  # frequency band is not band 5
                                    frequency_band_start = [*map(lambda j: j[0] * 10 ** 9, [
                                        const.FREQUENCY_BAND_1_RANGE,
                                        const.FREQUENCY_BAND_2_RANGE,
                                        const.FREQUENCY_BAND_3_RANGE,
                                        const.FREQUENCY_BAND_4_RANGE
                                    ])][fsp["frequencyBand"]] + fsp["frequencyBandOffsetStream1"]
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

                        # Validate channelAveragingMap.
                        if "channelAveragingMap" in fsp:
                            try:
                                # validate dimensions
                                assert len(fsp["channelAveragingMap"]) == self.NUM_CHANNEL_GROUPS
                                for i in range(20):
                                    assert len(fsp["channelAveragingMap"][i]) == 2

                                for i in range(20):
                                    # validate channel ID of first channel in group
                                    if int(fsp["channelAveragingMap"][i][0]) == \
                                            i * self.NUM_FINE_CHANNELS / self.NUM_CHANNEL_GROUPS + 1:
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
                                msg = "'channelAveragingMap' must be an 2D array of dimensions 2x{}.".format(
                                    self.NUM_CHANNEL_GROUPS
                                )
                                self.logger.error(msg)
                                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                             tango.ErrSeverity.ERR)

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
                                self.__raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "Search window not specified for Fsp PSS config"
                            self.__raise_configure_scan_fatal_error(msg)

                        if "searchBeamID" in fsp:
                            if 1 <= int(fsp["searchBeamID"]) <= 1500:
                                # Set searchBeamID attribute
                                pass
                            else:  # searchWindowID not in valid range
                                msg = "'searchBeamID' must be within range 1-1500 (received {}).".format(
                                    str(fsp["searchBeamID"])
                                )
                                self.__raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "Search beam ID not specified for Fsp PSS config"
                            self.__raise_configure_scan_fatal_error(msg)

                            # Validate receptors.
                            # This is always given, due to implementation details.
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
                            self.__raise_configure_scan_fatal_error(msg)
                        if "outputEnable" in fsp:
                            if fsp["outputEnable"] is False or fsp["outputEnable"] is True:
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                self.__raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "'outputEnable' not specified for Fsp PSS config"
                            self.__raise_configure_scan_fatal_error(msg)
                        if "averagingInterval" in fsp:
                            if isinstance(fsp["averagingInterval"], int):
                                pass
                            else:
                                msg = "'averagingInterval' is not a valid integer"
                                self.__raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "'averagingInterval' not specified for Fsp PSS config"
                            self.__raise_configure_scan_fatal_error(msg)
                        if "searchBeamDestinationAddress" in fsp:
                            if validate_ip(fsp["searchBeamDestinationAddress"]):
                                pass
                            else:
                                msg = "'searchBeamDestinationAddress' is not a valid IP address"
                                self.__raise_configure_scan_fatal_error(msg)
                        else:
                            msg = "'searchBeamDestinationAddress' not specified for Fsp PSS config"
                            self.__raise_configure_scan_fatal_error(msg)
                        self._pss_config.append(fsp)
                        self._pss_fsp_list.append(fsp["fspID"])

                    proxy_fsp.unsubscribe_event(
                        proxy_fsp.subscribe_event(
                            "State",
                            tango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback
                        )
                    )
                    proxy_fsp.unsubscribe_event(
                        proxy_fsp.subscribe_event(
                            "healthState",
                            tango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback
                        )
                    )

                except tango.DevFailed:  # exception in ConfigureScan
                    msg = "An exception occurred while configuring FSPs:\n{}\n" \
                          "Aborting configuration".format(sys.exc_info()[1].args[0].desc)

                    self.__raise_configure_scan_fatal_error(msg)
        else:
            msg = "'fsp' not given. Aborting configuration."
            self.__raise_configure_scan_fatal_error(msg)

        # At this point, everything has been validated.

    def __raise_configure_scan_fatal_error(self, msg):
        self.logger.error(msg)
        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                     tango.ErrSeverity.ERR)

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

    FspSubarrayCorr = device_property(
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

    outputLinksDistribution = attribute(
        dtype='str',
        label="Distribution of output links",
        doc="Distribution of output links, given as a JSON object",
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
        doc="fsp[1][x] = CORR [2[x] = PSS [1][x] = PST [1][x] = VLBI",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
        self.set_state(DevState.INIT)

        self._storage_logging_level = tango.LogLevel.LOG_DEBUG
        self._element_logging_level = tango.LogLevel.LOG_DEBUG
        self._central_logging_level = tango.LogLevel.LOG_DEBUG

        # get subarray ID
        if self.SubID:
            self._subarray_id = self.SubID
        else:
            self._subarray_id = int(self.get_name()[-2:])  # last two chars of FQDN

     # initialize attribute values
        self._receptors = []
        self._frequency_band = 0
        self._scan_ID = 0
        self._fsp_list = [[], [], [], []]
        self._output_links_distribution = {"scanID": 0}
        self._vcc_state = {}  # device_name:state
        self._vcc_health_state = {}  # device_name:healthState
        self._fsp_state = {}  # device_name:state
        self._fsp_health_state = {}  # device_name:healthState
        # store list of fsp configs being used for each function mode
        self._pss_config = []
        self._corr_config = []
        # store list of fsp being used for each function mode
        self._corr_fsp_list = []
        self._pss_fsp_list = []
        self._published_output_links = False
        self._last_received_vis_destination_address = "{}"
        self._last_received_delay_model = "{}"

        self._mutex_delay_model_config = Lock()

        # for easy self-reference
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._stream_tuning = [0, 0]

        # device proxy for easy reference to CBF Master
        self._proxy_cbf_master = tango.DeviceProxy(self.CbfMasterAddress)

        self.MIN_INT_TIME = const.MIN_INT_TIME
        self.NUM_CHANNEL_GROUPS = const.NUM_CHANNEL_GROUPS
        self.NUM_FINE_CHANNELS = const.NUM_FINE_CHANNELS

        self._proxy_sw_1 = tango.DeviceProxy(self.SW1Address)
        self._proxy_sw_2 = tango.DeviceProxy(self.SW2Address)

        # JSON FSP configurations for PSS, COR, PST, VLBI
        self._proxy_pss_config = tango.DeviceProxy(self.PssConfigAddress)
        self._proxy_corr_config = tango.DeviceProxy(self.CorrConfigAddress)

        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )

        self._count_vcc = int(self._master_max_capabilities["VCC"])
        self._count_fsp = int(self._master_max_capabilities["FSP"])
        self._fqdn_vcc = list(self.VCC)[:self._count_vcc]
        self._fqdn_fsp = list(self.FSP)[:self._count_fsp]
        self._fqdn_fsp_subarray = list(self.FspSubarrayCorr)

        self._proxies_vcc = [*map(tango.DeviceProxy, self._fqdn_vcc)]
        self._proxies_fsp = [*map(tango.DeviceProxy, self._fqdn_fsp)]
        self._proxies_fsp_subarray = [*map(tango.DeviceProxy, self._fqdn_fsp_subarray)]

        self._proxies_assigned_vcc = []
        self._proxies_assigned_fsp = []
        self._proxies_assigned_fsp_subarray = []

        # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
        self._events_telstate = {}

        # store the subscribed state change events as vcc_ID:[event_ID, event_ID] key:value pairs
        self._events_state_change_vcc = {}

        # store the subscribed state change events as fsp_ID:[event_ID, event_ID] key:value pairs
        self._events_state_change_fsp = {}

        # initialize groups
        self._group_vcc = tango.Group("VCC")
        self._group_fsp = tango.Group("FSP")
        self._group_fsp_subarray = tango.Group("FSP Subarray")

        self._obs_state = ObsState.IDLE.value
        self._admin_mode = AdminMode.ONLINE.value
        self.set_state(tango.DevState.OFF)

        # don't need this anymore (since everything is reset when the device is deleted)

        # to match VCC and CBF Master configuration
        # needed if device is re-initialized after adding receptors
        # (which technically should never happen)
        # I'm not sure how event subscriptions work when the device is re-initialized.
        # try:
        # self._proxy_cbf_master.ping()
        # vcc_subarray_membership = self._proxy_cbf_master.reportVCCSubarrayMembership
        # vcc_to_receptor = dict([*map(int, pair.split(":"))] for pair in
        # self._proxy_cbf_master.vccToReceptor)
        # receptors_to_add = [
        # vcc_to_receptor[i + 1] for i in range(len(vcc_subarray_membership))
        # if vcc_subarray_membership[i] == self._subarray_id
        # ]
        # self.AddReceptors(receptors_to_add)
        # self._scan_ID = self._proxy_cbf_master.subarrayScanID[self._subarray_id - 1]
        # except tango.DevFailed:
        # pass  # CBF Master not available, so just leave receptors and scanID alone

        # PROTECTED REGION END #    //  CbfSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.DISABLE)
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

    def read_outputLinksDistribution(self):
        # PROTECTED REGION ID(CbfSubarray.outputLinksDistribution_read) ENABLED START #
        return json.dumps(self._output_links_distribution)
        # PROTECTED REGION END #    //  CbfSubarray.outputLinksDistribution_read

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

    def read_fspList(self):
        # PROTECTED REGION ID(CbfSubarray.fspList_read) ENABLED START #
        return self._fsp_list
        # PROTECTED REGION END #    //  CbfSubarray.fspList_read


    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        if self.dev_state() == tango.DevState.DISABLE:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(CbfSubarray.On) ENABLED START #
        if self._obs_state != ObsState.IDLE.value:
            msg = "Device not in IDLE obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "On execution",
                                         tango.ErrSeverity.ERR)

        self._proxy_sw_1.SetState(tango.DevState.DISABLE)
        self._proxy_sw_2.SetState(tango.DevState.DISABLE)
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  CbfSubarray.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.OFF:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(CbfSubarray.Off) ENABLED START #
        if self._obs_state != ObsState.IDLE.value:
            msg = "Device not in IDLE obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "Off execution",
                                         tango.ErrSeverity.ERR)

        self._proxy_sw_1.SetState(tango.DevState.OFF)
        self._proxy_sw_2.SetState(tango.DevState.OFF)
        self.set_state(tango.DevState.DISABLE)
        # PROTECTED REGION END #    //  CbfSubarray.Off

    def is_AddReceptors_allowed(self):
        if self.dev_state() in [tango.DevState.OFF, tango.DevState.ON]:
            return True
        return False

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.AddReceptors) ENABLED START #
        if self._obs_state != ObsState.IDLE.value:
            msg = "Device not in IDLE obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                         tango.ErrSeverity.ERR)

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
                        # change subarray membership of vcc
                        vccProxy.subarrayMembership = self._subarray_id

                        # !!!!!!!!!!!!!
                        # Change done on 09/27/2109 as a consequence of the new TANGO and tango images release
                        # Note:json does not recognize NumPy data types. Convert the number to a Python int 
                        # before serializing the object.
                        # The list of receptors is serialized when the FSPs are configured for a scan.
                        # !!!!!!!!!!!!!

                        self._receptors.append(int(receptorID))
                        self._proxies_assigned_vcc.append(vccProxy)
                        self._group_vcc.add(self._fqdn_vcc[vccID - 1])

                        # subscribe to VCC state and healthState changes
                        event_id_state, event_id_health_state = vccProxy.subscribe_event(
                            "State",
                            tango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback
                        ), vccProxy.subscribe_event(
                            "healthState",
                            tango.EventType.CHANGE_EVENT,
                            self.__state_change_event_callback
                        )
                        self._events_state_change_vcc[vccID] = [event_id_state,
                                                                event_id_health_state]
                    else:
                        log_msg = "Receptor {} already assigned to current subarray.".format(
                            str(receptorID))
                        self.logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        # transition to ON if at least one receptor is assigned
        if self._receptors:
            self.set_state(DevState.ON)

        if errs:
            msg = "\n".join(errs)
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                         tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  CbfSubarray.AddReceptors

    def is_RemoveReceptors_allowed(self):
        if self.dev_state() in [tango.DevState.OFF, tango.DevState.ON]:
            return True
        return False

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(CbfSubarray.RemoveReceptors) ENABLED START #
        if self._obs_state != ObsState.IDLE.value:
            msg = "Device not in IDLE obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "RemoveReceptors execution",
                                         tango.ErrSeverity.ERR)

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

        # transitions to OFF if not assigned any receptors
        if not self._receptors:
            self.set_state(DevState.OFF)
        # PROTECTED REGION END #    //  CbfSubarray.RemoveReceptors

    def is_RemoveAllReceptors_allowed(self):
        if self.dev_state() in [tango.DevState.OFF, tango.DevState.ON]:
            return True
        return False

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
        if self._obs_state != ObsState.IDLE.value:
            msg = "Device not in IDLE obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "RemoveAllReceptors execution",
                                         tango.ErrSeverity.ERR)

        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  CbfSubarray.RemoveAllReceptors

    def is_ConfigureScan_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
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
                            "tdcDestinationAddress": ["str", "str", "str"]
                        },
                        {
                            ...
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
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            msg = "Device not in IDLE or READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                         tango.ErrSeverity.ERR)

        # Only after successful validation of the received configuration,
        # subarray is configured.
        self._pss_config = []
        self._corr_config = []
        self._corr_fsp_list = []
        self._pss_fsp_list = []
        self._corr_fsp_list = []
        self._fsp_list = [[], [], [], []]

        self.__validate_scan_configuration(argin)

        # Call this just to release all FSPs and unsubscribe to events.
        # We transition to obsState=CONFIGURING immediately after anyways.
        self.GoToIdle()

        # transition to obsState=CONFIGURING
        self._obs_state = ObsState.CONFIGURING.value
        self.push_change_event("obsState", self._obs_state)
        data = tango.DeviceData()
        data.insert(tango.DevUShort, ObsState.CONFIGURING.value)
        self._group_vcc.command_inout("SetObservingState", data)

        argin = json.loads(argin)

        # Configure scanID.
        self._scan_ID = int(argin["scanID"])

        # Configure frequencyBand.
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        self._frequency_band = frequency_bands.index(argin["frequencyBand"])
        data = tango.DeviceData()
        data.insert(tango.DevString, argin["frequencyBand"])
        self._group_vcc.command_inout("SetFrequencyBand", data)

        # Configure band5Tuning, if frequencyBand is 5a or 5b.
        if self._frequency_band in [4, 5]:
            stream_tuning = [*map(float, argin["band5Tuning"])]
            self._stream_tuning = stream_tuning
            self._group_vcc.write_attribute("band5Tuning", stream_tuning)

        # Configure frequencyBandOffsetStream1.
        if "frequencyBandOffsetStream1" in argin:
            self._frequency_band_offset_stream_1 = int(argin["frequencyBandOffsetStream1"])
            self._group_vcc.write_attribute(
                "frequencyBandOffsetStream1",
                int(argin["frequencyBandOffsetStream1"])
            )
        else:
            self._frequency_band_offset_stream_1 = 0
            self._group_vcc.write_attribute("frequencyBandOffsetStream1", 0)
            log_msg = "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            self.logger.warn(log_msg)

        # Validate frequencyBandOffsetStream2.
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if self._frequency_band in [4, 5]:
            if "frequencyBandOffsetStream2" in argin:
                self._frequency_band_offset_stream_2 = int(argin["frequencyBandOffsetStream2"])
                self._group_vcc.write_attribute(
                    "frequencyBandOffsetStream2",
                    int(argin["frequencyBandOffsetStream2"])
                )
            else:
                self._frequency_band_offset_stream_2 = 0
                self._group_vcc.write_attribute("frequencyBandOffsetStream2", 0)
                log_msg = "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
                self.logger.warn(log_msg)
        else:
            self._frequency_band_offset_stream_2 = 0
            self._group_vcc.write_attribute("frequencyBandOffsetStream2", 0)

        # Configure dopplerPhaseCorrSubscriptionPoint.
        if "dopplerPhaseCorrSubscriptionPoint" in argin:
            attribute_proxy = tango.AttributeProxy(argin["dopplerPhaseCorrSubscriptionPoint"])
            attribute_proxy.ping()
            event_id = attribute_proxy.subscribe_event(
                tango.EventType.CHANGE_EVENT,
                self.__doppler_phase_correction_event_callback
            )
            self._events_telstate[event_id] = attribute_proxy

        # Configure delayModelSubscriptionPoint.
        self._last_received_delay_model = "{}"
        attribute_proxy = tango.AttributeProxy(argin["delayModelSubscriptionPoint"])
        attribute_proxy.ping()
        event_id = attribute_proxy.subscribe_event(
            tango.EventType.CHANGE_EVENT,
            self.__delay_model_event_callback
        )
        self._events_telstate[event_id] = attribute_proxy

        # Configure visDestinationAddressSubscriptionPoint.
        self._published_output_links = False
        self._last_received_vis_destination_address = "{}"
        attribute_proxy = tango.AttributeProxy(argin["visDestinationAddressSubscriptionPoint"])
        attribute_proxy.ping()
        event_id = attribute_proxy.subscribe_event(
            tango.EventType.CHANGE_EVENT,
            self.__vis_destination_address_event_callback
        )
        self._events_telstate[event_id] = attribute_proxy

        # Configure rfiFlaggingMask.
        if "rfiFlaggingMask" in argin:
            self._group_vcc.write_attribute(
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
                self._group_vcc.command_inout("ConfigureSearchWindow", data)
                self.ConfigureSearchWindow(json.dumps(search_window))
        else:
            log_msg = "'searchWindow' not given."
            self.logger.warn(log_msg)

        # The VCCs are done configuring at this point
        data = tango.DeviceData()
        data.insert(tango.DevUShort, ObsState.READY.value)
        self._group_vcc.command_inout("SetObservingState", data)

        # pass on configuration to individual function mode class to configure the FSP Subarray

        if len(self._pss_config) != 0:
            self._proxy_pss_config.ConfigureFSP(json.dumps(self._pss_config))

        if len(self._corr_config) != 0:
            self._proxy_corr_config.ConfigureFSP(json.dumps(self._corr_config))

        #TODO add PST and VLBI to this once they are implemented
        self._fsp_list[0].append(self._corr_fsp_list)
        self._fsp_list[1].append(self._pss_fsp_list)

        # Configure FSP.
        for fsp in argin["fsp"]:
            # Configure fspID.
            fspID = int(fsp["fspID"])
            proxy_fsp = self._proxies_fsp[fspID - 1]
            proxy_fsp_subarray = self._proxies_fsp_subarray[fspID - 1]
            self._proxies_assigned_fsp.append(proxy_fsp)
            self._proxies_assigned_fsp_subarray.append(proxy_fsp_subarray)
            self._group_fsp.add(self._fqdn_fsp[fspID - 1])
            self._group_fsp_subarray.add(self._fqdn_fsp_subarray[fspID - 1])

            # change FSP subarray membership
            proxy_fsp.AddSubarrayMembership(self._subarray_id)

            # Configure functionMode.
            proxy_fsp.SetFunctionMode(fsp["functionMode"])

            fsp["frequencyBand"] = argin["frequencyBand"]
            if "frequencyBandOffsetStream1" in argin:
                fsp["frequencyBandOffsetStream1"] = self._frequency_band_offset_stream_1
            else:
                fsp["frequencyBandOffsetStream1"] = 0
            if "frequencyBandOffsetStream2" in argin:
                fsp["frequencyBandOffsetStream2"] = self._frequency_band_offset_stream_2
            else:
                fsp["frequencyBandOffsetStream2"] = 0
            if "receptors" not in fsp:
                fsp["receptors"] = self._receptors
            if self._frequency_band in [4, 5]:
                fsp["band5Tuning"] = self._stream_tuning

            # subscribe to FSP state and healthState changes
            event_id_state, event_id_health_state = proxy_fsp.subscribe_event(
                "State",
                tango.EventType.CHANGE_EVENT,
                self.__state_change_event_callback
            ), proxy_fsp.subscribe_event(
                "healthState",
                tango.EventType.CHANGE_EVENT,
                self.__state_change_event_callback
            )
            self._events_state_change_fsp[int(fsp["fspID"])] = [event_id_state,
                                                                event_id_health_state]

        # At this point, we can basically assume everything is properly configured
        # This has been phased out, now passing to function mode classes first
        self.__generate_output_links(argin)  # published output links to outputLinksDistribution

        # This state transition will be later
        # 03-23-2020:
        # CbfSubarray moves to READY only after the publication of the visibilities
        # addresses generated by SDP.
        # self._obs_state = ObsState.READY.value

        # PROTECTED REGION END #    //  CbfSubarray.ConfigureScan

    def is_ConfigureSearchWindow_allowed(self):
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
        if self._obs_state != ObsState.CONFIGURING.value:
            msg = "Device not in CONFIGURING obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

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

    def is_EndScan_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(CbfSubarray.EndScan) ENABLED START #
        if self._obs_state != ObsState.SCANNING.value:
            msg = "Device not in SCANNING obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "EndScan execution",
                                         tango.ErrSeverity.ERR)

        self._group_vcc.command_inout("EndScan")
        self._group_fsp_subarray.command_inout("EndScan")

        self._obs_state = ObsState.READY.value
        # PROTECTED REGION END #    //  CbfSubarray.EndScan

    def is_Scan_allowed(self):
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Activation time of the scan, as seconds since the Linux epoch"
    )
    def Scan(self, argin):
        # PROTECTED REGION ID(CbfSubarray.Scan) ENABLED START #
        """
        if self._obs_state != ObsState.READY.value:
            msg = "A scan is not ready to be started."
            self.logger(msg, tango.LogLevel.LOG_ERROR)
            tango.Except.throw_exception("Command failed", msg, "Scan execution",
                                           tango.ErrSeverity.ERR)
        """
        if self._obs_state != ObsState.READY.value:
            msg = "Device not in READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "Scan execution",
                                         tango.ErrSeverity.ERR)

        # TODO: actually use argin
        # For MVP, ignore argin (activation time)
        self._group_vcc.command_inout("Scan")
        self._group_fsp_subarray.command_inout("Scan")

        self._obs_state = ObsState.SCANNING.value
        # PROTECTED REGION END #    //  CbfSubarray.Scan

    def is_GoToIdle_allowed(self):
        if self.dev_state() in [tango.DevState.OFF, tango.DevState.ON]:
            return True
        return False

    @command()
    def GoToIdle(self):
        # PROTECTED REGION ID(CbfSubarray.GoToIdle) ENABLED START #
        if self._obs_state not in [ObsState.IDLE.value, ObsState.READY.value]:
            msg = "Device not in IDLE or READY obsState."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "GoToIdle execution",
                                           tango.ErrSeverity.ERR)
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
        self._group_fsp_subarray.command_inout("GoToIdle")

        # change FSP subarray membership
        data = tango.DeviceData()
        data.insert(tango.DevUShort, self._subarray_id)
        self._group_fsp.command_inout("RemoveSubarrayMembership", data)
        self._group_fsp.remove_all()
        self._proxies_assigned_fsp.clear()

        # remove channel info from FSP subarrays
        # already done in GoToIdle
        self._group_fsp_subarray.remove_all()
        self._proxies_assigned_fsp_subarray.clear()

        self._scan_ID = 0
        self._output_links_distribution = {"scanID": 0}
        self._last_received_vis_destination_address = "{}"
        self._last_received_delay_model = "{}"
        self._published_output_links = False

        # TODO need to add this check for fspSubarrayPSS and VLBI and PST once implemented
        for fsp_subarray_corr_proxy in self._proxies_fsp_subarray:
            fsp_subarray_corr_proxy.GoToIdle()

        # transition to obsState=IDLE
        self._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  CbfSubarray.EndSB


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == '__main__':
    main()
