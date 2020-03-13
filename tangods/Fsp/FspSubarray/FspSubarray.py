# -*- coding: utf-8 -*-
#
# This file is part of the FspSubarray project
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

""" FspSubarray Tango device prototype

FspSubarray TANGO device class for the FspSubarray prototype
"""

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(FspSubarray.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import const
from skabase.control_model import HealthState, AdminMode, ObsState
from skabase.SKASubarray.SKASubarray import SKASubarray

# PROTECTED REGION END #    //  FspSubarray.additionnal_import

__all__ = ["FspSubarray", "main"]


class FspSubarray(SKASubarray):
    """
    FspSubarray TANGO device class for the FspSubarray prototype
    """
    # PROTECTED REGION ID(FspSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16'
    )

    FspID = device_property(
        dtype='uint16'
    )

    CbfMasterAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Master",
        default_value="mid_csp_cbf/master/main"
    )

    CbfSubarrayAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Subarray"
    )

    VCC = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
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
        access=AttrWriteType.READ,
        label="Stream tuning (GHz)",
        doc="Stream tuning (GHz)"
    )

    frequencyBandOffsetStream1 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="Frequency offset for stream 1 (Hz)",
        doc="Frequency offset for stream 1 (Hz)"
    )

    frequencyBandOffsetStream2 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="Frequency offset for stream 2 (Hz)",
        doc="Frequency offset for stream 2 (Hz)"
    )

    frequencySliceID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
        label="Frequency slice ID",
        doc="Frequency slice ID"
    )

    corrBandwidth = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
        label="Bandwidth to be correlated",
        doc="Bandwidth to be correlated is <Full Bandwidth>/2^bandwidth"
    )

    zoomWindowTuning = attribute(
        dtype='uint',
        access=AttrWriteType.READ,
        label="Zoom window tuning (kHz)",
        doc="Zoom window tuning (kHz)"
    )

    integrationTime = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
        label="Integration time (ms)",
        doc="Integration time (ms)"
    )

    channelAveragingMap = attribute(
        dtype=(('uint16',),),
        max_dim_x=2,
        max_dim_y=20,
        access=AttrWriteType.READ,
        label="Channel averaging map",
        doc="Channel averaging map"
    )

    visDestinationAddress = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination addresses for visibilities, given as a JSON object"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(FspSubarray.init_device) ENABLED START #
        self.set_state(tango.DevState.INIT)

        # get relevant IDs
        self._subarray_id = self.SubID
        self._fsp_id = self.FspID

        self.MIN_INT_TIME = const.MIN_INT_TIME
        self.NUM_CHANNEL_GROUPS = const.NUM_CHANNEL_GROUPS
        self.NUM_FINE_CHANNELS = const.NUM_FINE_CHANNELS

        # initialize attribute values
        self._receptors = []
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._frequency_slice_ID = 0
        self._bandwidth = 0
        self._bandwidth_actual = const.FREQUENCY_SLICE_BW
        self._zoom_window_tuning = 0
        self._integration_time = 0
        self._channel_averaging_map = [
            [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
            for i in range(self.NUM_CHANNEL_GROUPS)
        ]
        self._vis_destination_address = []

        # For each channel sent to SDP: [chanID, bw, cf, cbfOutLink, sdpIp, sdpPort]
        self._channel_info = []

        # device proxy for easy reference to CBF Master
        self._proxy_cbf_master = tango.DeviceProxy(self.CbfMasterAddress)

        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )
        self._count_vcc = int(self._master_max_capabilities["VCC"])
        self._fqdn_vcc = list(self.VCC)[:self._count_vcc]
        self._proxies_vcc = [*map(tango.DeviceProxy, self._fqdn_vcc)]

        # device proxy for easy reference to CBF Subarray
        self._proxy_cbf_subarray = tango.DeviceProxy(self.CbfSubarrayAddress)

        self._obs_state = ObsState.IDLE.value
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspSubarray.delete_device) ENABLED START #
        self.goToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self):
        # PROTECTED REGION ID(FspSubarray.receptors_read) ENABLED START #
        return self._receptors
        # PROTECTED REGION END #    //  FspSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(FspSubarray.receptors_write) ENABLED START #
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  FspSubarray.receptors_write

    def read_frequencyBand(self):
        # PROTECTED REGION ID(FspSubarray.frequencyBand_read) ENABLED START #
        return self._frequency_band
        # PROTECTED REGION END #    //  FspSubarray.frequencyBand_read

    def read_band5Tuning(self):
        # PROTECTED REGION ID(FspSubarray.band5Tuning_read) ENABLED START #
        return self._stream_tuning
        # PROTECTED REGION END #    //  FspSubarray.band5Tuning_read

    def read_frequencyBandOffsetStream1(self):
        # PROTECTED REGION ID(FspSubarray.frequencyBandOffsetStream1) ENABLED START #
        return self._frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  FspSubarray.frequencyBandOffsetStream1

    def read_frequencyBandOffsetStream2(self):
        # PROTECTED REGION ID(FspSubarray.frequencyBandOffsetStream2) ENABLED START #
        return self._frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  FspSubarray.frequencyBandOffsetStream2

    def read_frequencySliceID(self):
        # PROTECTED REGION ID(FspSubarray.frequencySliceID_read) ENABLED START #
        return self._frequency_slice_ID
        # PROTECTED REGION END #    //  FspSubarray.frequencySliceID_read

    def read_corrBandwidth(self):
        # PROTECTED REGION ID(FspSubarray.corrBandwidth_read) ENABLED START #
        return self._bandwidth
        # PROTECTED REGION END #    //  FspSubarray.corrBandwidth_read

    def read_zoomWindowTuning(self):
        # PROTECTED REGION ID(FspSubarray.zoomWindowTuning_read) ENABLED START #
        return self._zoom_window_tuning
        # PROTECTED REGION END #    //  FspSubarray.zoomWindowTuning_read

    def read_integrationTime(self):
        # PROTECTED REGION ID(FspSubarray.integrationTime_read) ENABLED START #
        return self._integration_time
        # PROTECTED REGION END #    //  FspSubarray.integrationTime_read

    def read_channelAveragingMap(self):
        # PROTECTED REGION ID(FspSubarray.channelAveragingMap_read) ENABLED START #
        return self._channel_averaging_map
        # PROTECTED REGION END #    //  FspSubarray.channelAveragingMap_read

    def read_visDestinationAddress(self):
        # PROTECTED REGION ID(FspSubarray.visDestinationAddress_read) ENABLED START #
        return json.dumps(self._vis_destination_address)
        # PROTECTED REGION END #    //  FspSubarray.visDestinationAddress_read

    def write_visDestinationAddress(self, value):
        # PROTECTED REGION ID(FspSubarray.visDestinationAddress_write) ENABLED START #
        self._vis_destination_address = json.loads(value)
        # PROTECTED REGION END #    //  FspSubarray.visDestinationAddress_write

    # --------
    # Commands
    # --------

    def is_On_allowed(self):
        if self.dev_state() == tango.DevState.OFF and\
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def On(self):
        # PROTECTED REGION ID(FspSubarray.On) ENABLED START #
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  FspSubarray.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(FspSubarray.Off) ENABLED START #
        # This command can only be called when obsState=IDLE
        # self.goToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspSubarray.Off

    def is_AddReceptors_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def AddReceptors(self, argin):
        # PROTECTED REGION ID(FspSubarray.AddReceptors) ENABLED START #
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_master.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                subarrayID = self._proxies_vcc[vccID - 1].subarrayMembership

                # only add receptor if it belongs to the CBF subarray
                if subarrayID != self._subarray_id:
                    errs.append("Receptor {} does not belong to subarray {}.".format(
                        str(receptorID), str(self._subarray_id)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)
                    else:
                        log_msg = "Receptor {} already assigned to current FSP subarray.".format(
                            str(receptorID))
                        self.logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                           tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  FspSubarray.AddReceptors

    def is_RemoveReceptors_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(self, argin):
        # PROTECTED REGION ID(FspSubarray.RemoveReceptors) ENABLED START #
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  FspSubarray.RemoveReceptors

    def is_RemoveAllReceptors_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [
                    ObsState.IDLE.value,
                    ObsState.CONFIGURING.value,
                    ObsState.READY.value
                ]:
            return True
        return False

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(FspSubarray.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspSubarray.RemoveAllReceptors

    def is_AddChannels_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.CONFIGURING.value:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Channel frequency info"
    )
    def AddChannels(self, argin):
        # PROTECTED REGION ID(FspSubarray.AddChannels) ENABLED START #
        # obsState should already be CONFIGURING

        self._channel_info.clear()
        argin = json.loads(argin)

        for fsp in argin["fsp"]:
            if fsp["fspID"] == self._fsp_id:
                for link in fsp["cbfOutLink"]:
                    for channel in link["channel"]:
                        self._channel_info.append([
                            channel["chanID"],
                            channel["bw"],
                            channel["cf"],
                            link["linkID"],
                            # configure the addresses later
                            "",
                            0
                        ])

        # I'm pretty sure the list is sorted by first element anyway,
        # but specify that just in case, I guess.
        self._channel_info.sort(key=lambda x: x[0])
        # PROTECTED REGION END #    //  FspSubarray.AddChannels

    def is_AddChannelAddresses_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.CONFIGURING.value:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Channel address info"
    )
    def AddChannelAddresses(self, argin):
        # PROTECTED REGION ID(FspSubarray.AddChannelAddresses) ENABLED START #
        # obsState should already be CONFIGURING

        argin = json.loads(argin)

        for fsp in argin["receiveAddresses"]:
            if fsp["fspId"] == self._fsp_id:
                channel_ID_list = [*map(lambda x: x[0], self._channel_info)]
                for host in fsp["hosts"]:
                    for channel in host["channels"]:
                        try:
                            i = channel_ID_list.index(channel["startChannel"])
                            for j in range(i, i + channel["numChannels"]):
                                self._channel_info[j][4] = host["host"]
                                self._channel_info[j][5] = \
                                    channel["portOffset"] + self._channel_info[j][0]
                        # Possible errors:
                        #     Channel ID not found.
                        #     Number of channels exceeds configured channels.
                        # (probably among others)
                        except Exception as e:
                            msg = "An error occurred while configuring destination addresses:"\
                                "\n{}\n".format(str(e))
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg,
                                                           "AddChannelAddresses execution",
                                                           tango.ErrSeverity.ERR)
                self._vis_destination_address = fsp["hosts"]

        # get list of unconfigured channels
        unconfigured_channels = [channel[0] for channel in self._channel_info if channel[4] == ""]
        if unconfigured_channels:
            # raise an error if some channels are unconfigured
            msg = "The following channels are missing destination addresses:\n{}".format(
                unconfigured_channels
            )
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg,
                                           "AddChannelAddressInfo execution",
                                           tango.ErrSeverity.ERR)

        # transition to obsState=READY
        self._obs_state = ObsState.READY.value
        # PROTECTED REGION END #    //  FspSubarray.AddChannelAddresses

    def is_ValidateScan_allowed(self):
        # This command has no side effects, so just allow it anytime
        return True

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    def ValidateScan(self, argin):
        # PROTECTED REGION ID(FspSubarray.ValidateScan) ENABLED START #
        # try to deserialize input string to a JSON object
        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg,
                                           "ConfigureScan execution", tango.ErrSeverity.ERR)
        if argin["functionMode"] == "CORR":
            # Validate receptors.
            # This is always given, due to implementation details.
            try:
                self.RemoveAllReceptors()
                self.AddReceptors(list(map(int, argin["receptors"])))
                self.RemoveAllReceptors()
            except tango.DevFailed as df:  # error in AddReceptors()
                self.RemoveAllReceptors()
                msg = sys.exc_info()[1].args[0].desc + "\n'receptors' was malformed."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                tango.ErrSeverity.ERR)
            frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(argin["frequencyBand"])

            # Validate frequencySliceID.
            if "frequencySliceID" in argin:
                num_frequency_slices = [4, 5, 7, 12, 26, 26]
                if int(argin["frequencySliceID"]) in list(
                        range(1, num_frequency_slices[frequencyBand] + 1)):
                    pass
                else:
                    msg = "'frequencySliceID' must be an integer in the range [1, {}] "\
                        "for a 'frequencyBand' of {}.".format(
                            str(num_frequency_slices[frequencyBand]),
                            str(argin["frequencyBand"])
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
            if "corrBandwidth" in argin:
                if int(argin["corrBandwidth"]) in list(range(0, 7)):
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
            if argin["corrBandwidth"]:  # zoomWindowTuning is required
                if "zoomWindowTuning" in argin:
                    if argin["frequencyBand"] in list(range(4)):  # frequency band is not band 5
                        frequency_band_start = [*map(lambda j: j[0]*10**9, [
                            const.FREQUENCY_BAND_1_RANGE,
                            const.FREQUENCY_BAND_2_RANGE,
                            const.FREQUENCY_BAND_3_RANGE,
                            const.FREQUENCY_BAND_4_RANGE
                        ])][argin["frequencyBand"]] + argin["frequencyBandOffsetStream1"]
                        frequency_slice_range = (
                            frequency_band_start + \
                                (argin["frequencySliceID"] - 1)*const.FREQUENCY_SLICE_BW*10**6,
                            frequency_band_start +
                                argin["frequencySliceID"]*const.FREQUENCY_SLICE_BW*10**6
                        )

                        if frequency_slice_range[0] <= \
                                int(argin["zoomWindowTuning"])*10**3 <= \
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
                            argin["band5Tuning"][0]*10**9 + argin["frequencyBandOffsetStream1"] - \
                                const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                                (argin["frequencySliceID"] - 1)*const.FREQUENCY_SLICE_BW*10**6,
                            argin["band5Tuning"][0]*10**9 + argin["frequencyBandOffsetStream1"] - \
                                const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                                argin["frequencySliceID"]*const.FREQUENCY_SLICE_BW*10**6
                        )

                        frequency_slice_range_2 = (
                            argin["band5Tuning"][1]*10**9 + argin["frequencyBandOffsetStream2"] - \
                                const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                                (argin["frequencySliceID"] - 1)*const.FREQUENCY_SLICE_BW*10**6,
                            argin["band5Tuning"][1]*10**9 + argin["frequencyBandOffsetStream2"] - \
                                const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                                argin["frequencySliceID"]*const.FREQUENCY_SLICE_BW*10**6
                        )

                        if (frequency_slice_range_1[0] <= \
                                int(argin["zoomWindowTuning"])*10**3 <= \
                                frequency_slice_range_1[1]) or\
                                (frequency_slice_range_2[0] <= \
                                int(argin["zoomWindowTuning"])*10**3 <= \
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
            if "integrationTime" in argin:
                if int(argin["integrationTime"]) in list(
                    range(self.MIN_INT_TIME, 10*self.MIN_INT_TIME + 1, self.MIN_INT_TIME)
                ):
                    pass
                else:
                    msg = "'integrationTime' must be an integer in the range [1, 10] multiplied "\
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
            if "channelAveragingMap" in argin:
                try:
                    # validate dimensions
                    assert len(argin["channelAveragingMap"]) == self.NUM_CHANNEL_GROUPS
                    for i in range(20):
                        assert len(argin["channelAveragingMap"][i]) == 2

                    for i in range(20):
                        # validate channel ID of first channel in group
                        if int(argin["channelAveragingMap"][i][0]) == \
                                i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS + 1:
                            pass  # the default value is already correct
                        else:
                            msg = "'channelAveragingMap'[{0}][0] is not the channel ID of the "\
                                "first channel in a group (received {1}).".format(
                                    i,
                                    argin["channelAveragingMap"][i][0]
                                )
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg,
                                                           "ConfigureScan execution",
                                                           tango.ErrSeverity.ERR)

                        # validate averaging factor
                        if int(argin["channelAveragingMap"][i][1]) in [0, 1, 2, 3, 4, 6, 8]:
                            pass
                        else:
                            msg = "'channelAveragingMap'[{0}][1] must be one of "\
                                "[0, 1, 2, 3, 4, 6, 8] (received {1}).".format(
                                    i,
                                    argin["channelAveragingMap"][i][1]
                                )
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg,
                                                           "ConfigureScan execution",
                                                           tango.ErrSeverity.ERR)
                except (TypeError, AssertionError):  # dimensions not correct
                    msg = "'channelAveragingMap' must be an 2D array of dimensions 2x{}.".format(
                            self.NUM_CHANNEL_GROUPS
                        )
                    self.logger.error(log_msg)
                    tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                   tango.ErrSeverity.ERR)
            else:
                pass

        # PROTECTED REGION END #    //  FspSubarray.ValidateScan

    def is_ConfigureScan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(FspSubarray.ConfigureScan) ENABLED START #
        # This function is called after the configuration has already been validated,
        # so the checks here have been removed to reduce overhead.

        # transition to obsState=CONFIGURING
        self._obs_state = ObsState.CONFIGURING.value
        self.push_change_event("obsState", self._obs_state)

        argin = json.loads(argin)

        # TODO: Make output links work with PSS and PST
        if argin["functionMode"] == "CORR":

            # Configure frequencyBand.
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            self._frequency_band = frequency_bands.index(argin["frequencyBand"])

            # Configure band5Tuning.
            if self._frequency_band in [4, 5]:
                self._stream_tuning = argin["band5Tuning"]

            # Configure frequencyBandOffsetStream1.
            self._frequency_band_offset_stream_1 = int(argin["frequencyBandOffsetStream1"])

            # Configure frequencyBandOffsetStream2.
            if self._frequency_band in [4, 5]:
                self._frequency_band_offset_stream_2 = int(argin["frequencyBandOffsetStream2"])

        # Configure receptors.
        self.RemoveAllReceptors()
        self.AddReceptors(map(int, argin["receptors"]))
        # Configure frequencySliceID.

        if argin["functionMode"] == "CORR":
            self._frequency_slice_ID = int(argin["frequencySliceID"])
            # Configure corrBandwidth.
            self._bandwidth = int(argin["corrBandwidth"])
            self._bandwidth_actual = int(const.FREQUENCY_SLICE_BW/2**int(argin["corrBandwidth"]))

            # Configure zoomWindowTuning.
            if self._bandwidth != 0:  # zoomWindowTuning is required
                if self._frequency_band in list(range(4)):  # frequency band is not band 5
                    self._zoom_window_tuning = int(argin["zoomWindowTuning"])

                    frequency_band_start = [*map(lambda j: j[0]*10**9, [
                        const.FREQUENCY_BAND_1_RANGE,
                        const.FREQUENCY_BAND_2_RANGE,
                        const.FREQUENCY_BAND_3_RANGE,
                        const.FREQUENCY_BAND_4_RANGE
                    ])][self._frequency_band] + self._frequency_band_offset_stream_1
                    frequency_slice_range = (
                        frequency_band_start + \
                            (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                        frequency_band_start +
                            self._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                    )

                    if frequency_slice_range[0] + \
                            self._bandwidth_actual*10**6/2 <= \
                            int(argin["zoomWindowTuning"])*10**3 <= \
                            frequency_slice_range[1] - \
                            self._bandwidth_actual*10**6/2:
                        # this is the acceptable range
                        pass
                    else:
                        # log a warning message
                        log_msg = "'zoomWindowTuning' partially out of observed frequency slice. "\
                            "Proceeding."
                        self.logger.warn(log_msg)
                else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                    self._zoom_window_tuning = argin["zoomWindowTuning"]

                    frequency_slice_range_1 = (
                        self._stream_tuning[0]*10**9 + self._frequency_band_offset_stream_1 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                        self._stream_tuning[0]*10**9 + self._frequency_band_offset_stream_1 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            self._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                    )

                    frequency_slice_range_2 = (
                        self._stream_tuning[1]*10**9 + self._frequency_band_offset_stream_2 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                        self._stream_tuning[1]*10**9 + self._frequency_band_offset_stream_2 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            self._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                    )

                    if (frequency_slice_range_1[0] + \
                            self._bandwidth_actual*10**6/2 <= \
                            int(argin["zoomWindowTuning"])*10**3 <= \
                            frequency_slice_range_1[1] - \
                            self._bandwidth_actual*10**6/2) or\
                            (frequency_slice_range_2[0] + \
                            self._bandwidth_actual*10**6/2 <= \
                            int(argin["zoomWindowTuning"])*10**3 <= \
                            frequency_slice_range_2[1] - \
                            self._bandwidth_actual*10**6/2):
                        # this is the acceptable range
                        pass
                    else:
                        # log a warning message
                        log_msg = "'zoomWindowTuning' partially out of observed frequency slice. "\
                            "Proceeding."
                        self.logger.warn(log_msg)

            # Configure integrationTime.
            self._integration_time = int(argin["integrationTime"])

            # Configure channelAveragingMap.
            if "channelAveragingMap" in argin:
                for i in range(20):
                    self._channel_averaging_map[i][1] = int(argin["channelAveragingMap"][i][1])
            else:
                self._channel_averaging_map = [
                    [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
                    for i in range(self.NUM_CHANNEL_GROUPS)
                ]
                log_msg = "FSP specified, but 'channelAveragingMap not given. Default to averaging "\
                    "factor = 0 for all channel groups."
                self.logger.warn(log_msg)

        # This state transition will be later
        self._obs_state = ObsState.READY.value

        # PROTECTED REGION END #    //  FspSubarray.ConfigureScan

    def is_EndScan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.SCANNING.value:
            return True
        return False

    @command()
    def EndScan(self):
        # PROTECTED REGION ID(FspSubarray.EndScan) ENABLED START #
        self._obs_state = ObsState.READY.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspSubarray.EndScan

    def is_Scan_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.READY.value:
            return True
        return False

    @command()
    def Scan(self):
        # PROTECTED REGION ID(FspSubarray.Scan) ENABLED START #
        self._obs_state = ObsState.SCANNING.value
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspSubarray.Scan

    def is_goToIdle_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command()
    def goToIdle(self):
        # PROTECTED REGION ID(FspSubarray.goToIdle) ENABLED START #
        # transition to obsState=IDLE
        self._channel_info.clear()
        self._obs_state = ObsState.IDLE.value
        # PROTECTED REGION END #    //  FspSubarray.goToIdle

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspSubarray.main) ENABLED START #
    return run((FspSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspSubarray.main


if __name__ == '__main__':
    main()
