# -*- coding: utf-8 -*-
#
# This file is part of the FspSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" FspSubarray Tango device prototype

FspSubarray TANGO device class for the FspSubarray prototype
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
# PROTECTED REGION ID(FspSubarray.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode, ObsState, const
from skabase.SKASubarray.SKASubarray import SKASubarray

# PROTECTED REGION END #    //  FspSubarray.additionnal_import

__all__ = ["FspSubarray", "main"]


class FspSubarray(SKASubarray):
    """
    FspSubarray TANGO device class for the FspSubarray prototype
    """
    __metaclass__ = DeviceMeta
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

    destinationAddress = attribute(
        dtype=('str',),
        max_dim_x=3,
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination addresses (MAC address, IP address, port) for visibilities"
    )

    delayModel = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Delay model coefficients",
        doc="Delay model coefficients, given as a JSON object"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(FspSubarray.init_device) ENABLED START #

        # get relevant IDs
        self._subarray_id = self.SubID
        self._fsp_id = self.FspID

        self.FREQUENCY_SLICE_BW = const.FREQUENCY_SLICE_BW
        self.MIN_INT_TIME = const.MIN_INT_TIME
        self.NUM_CHANNEL_GROUPS = const.NUM_CHANNEL_GROUPS
        self.NUM_FINE_CHANNELS = const.NUM_FINE_CHANNELS
        self.NUM_PHASE_BINS = const.NUM_PHASE_BINS
        self.NUM_OUTPUT_LINKS = const.NUM_OUTPUT_LINKS

        # initialize attribute values
        self._receptors = []
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_slice_ID = 0
        self._bandwidth = 0
        self._zoom_window_tuning = 0
        self._integration_time = 0
        self._channel_averaging_map = [
            [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
            for i in range(self.NUM_CHANNEL_GROUPS)
        ]
        self._destination_address = ["", "", ""]
        self._delay_model = ""

        # device proxy for easy reference to CBF Master
        self._proxy_cbf_master = PyTango.DeviceProxy(self.CbfMasterAddress)

        self._master_max_capabilities = dict(
            pair.split(":") for pair in
            self._proxy_cbf_master.get_property("MaxCapabilities")["MaxCapabilities"]
        )
        self._count_vcc = int(self._master_max_capabilities["VCC"])
        self._fqdn_vcc = list(self.VCC)[:self._count_vcc]
        self._proxies_vcc = [*map(PyTango.DeviceProxy, self._fqdn_vcc)]

        # device proxy for easy reference to CBF Subarray
        self._proxy_cbf_subarray = PyTango.DeviceProxy(self.CbfSubarrayAddress)
        # PROTECTED REGION END #    //  FspSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspSubarray.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspSubarray.delete_device) ENABLED START #
        pass
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

    def read_destinationAddress(self):
        # PROTECTED REGION ID(FspSubarray.destinationAddress_read) ENABLED START #
        return self._destination_address
        # PROTECTED REGION END #    //  FspSubarray.destinationAddress_read

    def write_destinationAddress(self, value):
        # PROTECTED REGION ID(FspSubarray.destinationAddress_write) ENABLED START #
        self._destination_address = value
        # PROTECTED REGION END #    //  FspSubarray.destinationAddress_write

    def read_delayModel(self):
        # PROTECTED REGION ID(FspSubarray.delayModel_read) ENABLED START #
        return self._delay_model
        # PROTECTED REGION END #    //  FspSubarray.delayModel_read

    def write_delayModel(self, value):
        # PROTECTED REGION ID(FspSubarray.delayModel_write) ENABLED START #
        self._delay_model = value
        # PROTECTED REGION END #    //  FspSubarray.delayModel_write

    # --------
    # Commands
    # --------

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    @DebugIt()
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
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, int(PyTango.LogLevel.LOG_ERROR))
            PyTango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                           PyTango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  FspSubarray.AddReceptors

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
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # PROTECTED REGION END #    //  FspSubarray.RemoveReceptors

    @command()
    def RemoveAllReceptors(self):
        # PROTECTED REGION ID(FspSubarray.RemoveAllReceptors) ENABLED START #
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspSubarray.RemoveAllReceptors

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(FspSubarray.ConfigureScan) ENABLED START #
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

        # Validate frequencyBand
        # If not given, ignore the FSP and append an error (due to implementation details, this
        # never happens).
        # If malformed, ignore the FSP and append an error (due to implementation details, this
        # never happens).
        if "frequencyBand" in argin:
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            if argin["frequencyBand"] in frequency_bands:
                self._frequency_band = frequency_bands.index(argin["frequencyBand"])
            else:
                msg = "\n".join(errs)
                msg += "'frequencyBand' must be one of {} (received {}). "\
                    "Aborting configuration.".format(frequency_bands, argin["frequency_band"])
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            msg = "\n".join(errs)
            msg += "FSP specified, but 'frequencyBand' not given. Ignoring FSP."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate band5Tuning.
        # Due to implementation details, this is always given (when required) and valid.
        if self._frequency_band in [4, 5]:
            self._stream_tuning = argin["band5Tuning"]

        # Validate receptors
        # If not given, ignore the FSP and append an error (due to implementation details, this
        # never happens).
        # If malformed, ignore the FSP and append an error.
        if "receptors" in argin:
            try:
                self.RemoveAllReceptors()
                self.AddReceptors(map(int, argin["receptors"]))
            except PyTango.DevFailed as df:  # error in AddReceptors()
                self.RemoveAllReceptors()
                msg = "\n".join(errs)
                msg += sys.exc_info()[1].args[0].desc + "\n'receptors' was malformed. Ignoring FSP."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            self.RemoveAllReceptors()
            msg = "\n".join(errs)
            msg += "FSP specified, but 'receptors' not given. Ignoring FSP."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate frequencySliceID
        # If not given, ignore the FSP and append an error.
        # If malformed, ignore the FSP and append an error.
        if "frequencySliceID" in argin:
            num_frequency_slices = [4, 5, 7, 12, 26, 26]
            if int(argin["frequencySliceID"]) in list(
                    range(1, num_frequency_slices[self._frequency_band] + 1)):
                self._frequency_slice_ID = int(argin["frequencySliceID"])
            else:
                msg = "\n".join(errs)
                msg += "'frequencySliceID' must be an integer in the range [1, {}] "\
                    "for a 'frequencyBand' of {}. Ignoring FSP.".format(
                        str(num_frequency_slices[self._frequency_band]),
                        str(self._frequency_band)
                    )
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            msg = "\n".join(errs)
            msg += "FSP specified, but 'frequencySliceID' not given. Ignoring FSP."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate corrBandwidth
        # If not given, ignore the FSP and append an error.
        # If malformed, ignore the FSP and append an error.
        if "corrBandwidth" in argin:
            if int(argin["corrBandwidth"]) in list(range(0, 7)):
                self._bandwidth = int(argin["corrBandwidth"])
            else:
                msg = "\n".join(errs)
                msg += "'corrBandwidth' must be an integer in the range [0, 6]. Ignoring FSP."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            msg = "\n".join(errs)
            msg += "FSP specified, but 'corrBandwidth' not given. Ignoring FSP."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate zoomWindowTuning
        # If not given when required, ignore the FSP and append an error.
        # If malformed when required, ignore the FSP and append an error.
        if self._bandwidth != 0:  # zoomWindowTuning is required
            if "zoomWindowTuning" in argin:
                # TODO: validate input
                self._zoom_window_tuning = int(argin["zoomWindowTuning"])
            else:
                msg = "\n".join(errs)
                msg += "FSP specified, but 'zoomWindowTuning' not given. Ignoring FSP."
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)

        # Validate integrationTime
        # If not given, ignore the FSP and append an error.
        # If malformed, ignore the FSP and append an error.
        if "integrationTime" in argin:
            if int(argin["integrationTime"]) in list(
                range(self.MIN_INT_TIME, 10*self.MIN_INT_TIME + 1, self.MIN_INT_TIME)
            ):
                self._integration_time = int(argin["integrationTime"])
            else:
                msg = "\n".join(errs)
                msg += "'integrationTime' must be an integer in the range [1, 10] multiplied "\
                    "by {}. Ignoring FSP.".format(self.MIN_INT_TIME)
                # this is a fatal error
                self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
                PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                               PyTango.ErrSeverity.ERR)
        else:
            msg = "\n".join(errs)
            msg += "FSP specified, but 'integrationTime' not given. Ignoring FSP."
            # this is a fatal error
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # Validate channelAveragingMap
        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
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
                        self._channel_averaging_map[i][1] = 0
                        log_msg = "'channelAveragingMap'[{0}][0] is not the channel ID of the "\
                            "first channel in a group. Defaulting to 0 for channel group "\
                            "starting with channel {1}.".format(
                                i,
                                argin["channelAveragingMap"][i][0]
                        )
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
                        continue

                    # validate averaging factor
                    if int(argin["channelAveragingMap"][i][1]) in [0, 1, 2, 3, 4, 6, 8]:
                        self._channel_averaging_map[i][1] = int(argin["channelAveragingMap"][i][1])
                    else:
                        self._channel_averaging_map[i][1] = 0
                        log_msg = "'channelAveragingMap'[{0}][1] must be one of "\
                            "[0, 1, 2, 3, 4, 6, 8]. Defaulting to 0 for channel group starting "\
                            "with channel {1}.".format(
                                i,
                                argin["channelAveragingMap"][i][0]
                            )
                        self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                        errs.append(log_msg)
            except (TypeError, AssertionError):  # dimensions not correct
                self._channel_averaging_map = [
                    [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
                    for i in range(self.NUM_CHANNEL_GROUPS)
                ]
                log_msg = "'channelAveragingMap' must be an 2D array of dimensions 2x{}. "\
                    "Defaulting to averaging factor = 0 for all channel groups.".format(
                        self.NUM_CHANNEL_GROUPS
                    )
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
                errs.append(log_msg)
        else:
            self._channel_averaging_map = [
                [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
                for i in range(self.NUM_CHANNEL_GROUPS)
            ]
            log_msg = "FSP specified, but 'channelAveragingMap not given. Default to averaging "\
                "factor = 0 for all channel groups."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

        # raise an error if something went wrong
        if errs:
            msg = "\n".join(errs)
            self.dev_logging(msg, PyTango.LogLevel.LOG_ERROR)
            PyTango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                           PyTango.ErrSeverity.ERR)

        # PROTECTED REGION END #    //  FspSubarray.ConfigureScan

    @command(
        dtype_out='str',
        doc_out="Output links",
    )
    def GenerateOutputLinks(self):
        # PROTECTED REGION ID(FspSubarray.GenerateOutputLinks) ENABLED START #

        # We can (probably) assume that all the self attributes are set properly at this point.
        # It's envisioned that CbfSubarray.ConfigureScan() will only call this command if
        # FspSubarray.ConfigureScan() did not throw any errors.

        output_links = {
            "fspID": self._fsp_id,
            "frequencySliceID": self._frequency_slice_ID,
            "channel": []
        }

        if self._frequency_band in list(range(4)):  # frequency band is not band 5
            frequency_band_start = [*map(lambda j: j[0]*10**9, [
                const.FREQUENCY_BAND_1_RANGE,
                const.FREQUENCY_BAND_2_RANGE,
                const.FREQUENCY_BAND_3_RANGE,
                const.FREQUENCY_BAND_4_RANGE
            ])][self._frequency_band]

            frequency_slice_start = frequency_band_start + \
                (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,

        else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
            if self._frequency_slice_ID <= 13:  # stream 1
                frequency_band_start = self._stream_tuning[0]*10**9 - \
                    const.BAND_5_STREAM_BANDWIDTH*10**9/2
                frequency_slice_start = frequency_band_start + \
                    (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
            else:  # 14 <= self._frequency_slice <= 26  # stream 2
                frequency_band_start = self._stream_tuning[1]*10**9 - \
                    const.BAND_5_STREAM_BANDWIDTH*10**9/2
                frequency_slice_start = frequency_band_start + \
                    (self._frequency_slice_ID - 14)*const.FREQUENCY_SLICE_BW*10**6

        for channel_group_ID in range(const.NUM_CHANNEL_GROUPS):
            channel_avg = self._channel_averaging_map[channel_group_ID][1]

            if channel_avg:  # send channels to SDP
                for channel_ID in range(
                    int(channel_group_ID*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1,
                    int((channel_group_ID + 1)*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1,
                    channel_avg
                ):
                    channel = {
                        "channelID": channel_ID,
                        "channelBandwidth":
                            self.FREQUENCY_SLICE_BW*10**6/self.NUM_FINE_CHANNELS*channel_avg,
                        "channelCenterFrequency": frequency_slice_start +
                            (channel_ID - 1)*self.FREQUENCY_SLICE_BW*10**6/
                            self.NUM_FINE_CHANNELS*channel_avg +
                            self.FREQUENCY_SLICE_BW*10**6/self.NUM_FINE_CHANNELS*channel_avg/2,
                        "phaseBin": []
                    }
                    for i in range(self.NUM_PHASE_BINS):
                        channel["phaseBin"].append({
                            "phaseBinID": 0,  # phase bin ID unsupported for PI3
                            "cbfOutputLink": randint(1, self.NUM_OUTPUT_LINKS)  # random link
                        })
                    output_links["channel"].append(channel)

            else:  # don't send channels to SDP
                for channel_ID in range(
                    int(channel_group_ID*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1,
                    int((channel_group_ID + 1)*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1
                ):
                    # treat all channels individually (i.e. no averaging)
                    channel = {
                        "channelID": channel_ID,
                        "channelBandwidth":
                            self.FREQUENCY_SLICE_BW*10**6/self.NUM_FINE_CHANNELS,
                        "channelCenterFrequency": frequency_slice_start +
                            (channel_ID - 1)*self.FREQUENCY_SLICE_BW*10**6/self.NUM_FINE_CHANNELS +
                            self.FREQUENCY_SLICE_BW*10**6/self.NUM_FINE_CHANNELS/2,
                        "phaseBin": []
                    }
                    for i in range(self.NUM_PHASE_BINS):
                        channel["phaseBin"].append({
                            "phaseBinID": 0,  # phase bin ID unsupported for PI3
                            "cbfOutputLink": 0  # don't send channel
                        })
                    output_links["channel"].append(channel)

        return json.dumps(output_links)

        # PROTECTED REGION END #    //  FspSubarray.GenerateOutputLinks

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspSubarray.main) ENABLED START #
    return run((FspSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspSubarray.main


if __name__ == '__main__':
    main()
