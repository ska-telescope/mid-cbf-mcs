# -*- coding: utf-8 -*-
#
# This file is part of the FspCorrSubarray project
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

# """ FspCorrSubarray Tango device prototype

# FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
# """

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
# PROTECTED REGION ID(FspCorrSubarray.additionnal_import) ENABLED START #
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

# PROTECTED REGION END #    //  FspCorrSubarray.additionnal_import

__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(SKASubarray):
    """
    FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
    """
    # PROTECTED REGION ID(FspCorrSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspCorrSubarray.class_variable

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


    fspChannelOffset = attribute(
        dtype='DevLong',
        access=AttrWriteType.READ_WRITE,
        label="fspChannelOffset",
        doc="fsp Channel offset, integer, multiple of 14480",
    )

    outputLinkMap = attribute(
        dtype=(('DevULong64',),),
        access=AttrWriteType.READ,
        max_dim_x=2, max_dim_y=40,
    )

    scanID = attribute(
        dtype='DevLong64',
        access=AttrWriteType.READ_WRITE,
        label="scanID",
        doc="scan ID, set when transition to SCANNING is performed",
    )


    configID = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Config ID",
        doc="set when transition to READY is performed",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKASubarray.init_device(self)
        # PROTECTED REGION ID(FspCorrSubarray.init_device) ENABLED START #
        """Initialize attributes. ObsState=IDLE, state=OFF"""
        self.set_state(tango.DevState.INIT)

        # get relevant IDs
        self._subarray_id = self.SubID
        self._fsp_id = self.FspID

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
        self._scan_id = 0
        self._config_id = ""
        self._channel_averaging_map = [
            [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
            for i in range(self.NUM_CHANNEL_GROUPS)
        ]
        # destination addresses includes the following three
        self._vis_destination_address = {"outputHost":[], "outputMac": [], "outputPort":[]}
        self._fsp_channel_offset = 0
        # outputLinkMap is a 2*40 array. Pogo generates tuple. I changed into list to facilitate writing
        self._output_link_map = [[0,0] for i in range(40)]

        # For each channel sent to SDP: [chanID, bw, cf, cbfOutLink, sdpIp, sdpPort] # ???
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
        # PROTECTED REGION END #    //  FspCorrSubarray.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspCorrSubarray.always_executed_hook) ENABLED START #
        """hook before any commands"""
        pass
        # PROTECTED REGION END #    //  FspCorrSubarray.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspCorrSubarray.delete_device) ENABLED START #
        """set ObsState IDLE, remove all receptors, set state OFF."""
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspCorrSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self):
        # PROTECTED REGION ID(FspCorrSubarray.receptors_read) ENABLED START #
        """return receptros attribute.(array of int)"""
        return self._receptors
        # PROTECTED REGION END #    //  FspCorrSubarray.receptors_read

    def write_receptors(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.receptors_write) ENABLED START #
        """Set receptors attribute; set receptors to a new list of receptors."""
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  FspCorrSubarray.receptors_write

    def read_frequencyBand(self):
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBand_read) ENABLED START #
        """Return frequencyBand attribute(DevEnum)."""
        return self._frequency_band
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBand_read

    def read_band5Tuning(self):
        # PROTECTED REGION ID(FspCorrSubarray.band5Tuning_read) ENABLED START #
        """Return band5Tuning attribute(array of float, first element corresponds to the first stream, second to the second stream).""" 
        return self._stream_tuning
        # PROTECTED REGION END #    //  FspCorrSubarray.band5Tuning_read

    def read_frequencyBandOffsetStream1(self):
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBandOffsetStream1) ENABLED START #
        """Return frequencyBandOffsetStream1 attribute"""
        return self._frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBandOffsetStream1

    def read_frequencyBandOffsetStream2(self):
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBandOffsetStream2) ENABLED START #
        """Return frequencyBandOffsetStream2 attribute"""
        return self._frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBandOffsetStream2

    def read_frequencySliceID(self):
        # PROTECTED REGION ID(FspCorrSubarray.frequencySliceID_read) ENABLED START #
        """Return frequencySliceID attribute"""
        return self._frequency_slice_ID
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencySliceID_read

    def read_corrBandwidth(self):
        # PROTECTED REGION ID(FspCorrSubarray.corrBandwidth_read) ENABLED START #
        """Return corrBandwidth attribute(Bandwidth to be correlated is <Full Bandwidth>/2^bandwidth)."""
        return self._bandwidth
        # PROTECTED REGION END #    //  FspCorrSubarray.corrBandwidth_read

    def read_zoomWindowTuning(self):
        # PROTECTED REGION ID(FspCorrSubarray.zoomWindowTuning_read) ENABLED START #
        """Return zoomWindowTuning attribute."""
        return self._zoom_window_tuning
        # PROTECTED REGION END #    //  FspCorrSubarray.zoomWindowTuning_read

    def read_integrationTime(self):
        # PROTECTED REGION ID(FspCorrSubarray.integrationTime_read) ENABLED START #
        """Return integrationTime attribute(millisecond)."""
        return self._integration_time
        # PROTECTED REGION END #    //  FspCorrSubarray.integrationTime_read

    def read_channelAveragingMap(self):
        # PROTECTED REGION ID(FspCorrSubarray.channelAveragingMap_read) ENABLED START #
        """Return channelAveragingMap. 
           Consists of 2*20 array of integers(20 tupples representing 20* 744 channels). 
           The first element is the ID of the first channel in a channel group. The second element is the averaging factor"""
        return self._channel_averaging_map
        # PROTECTED REGION END #    //  FspCorrSubarray.channelAveragingMap_read

    def read_visDestinationAddress(self):
        # PROTECTED REGION ID(FspCorrSubarray.visDestinationAddress_read) ENABLED START #
        """Return VisDestinationAddress attribute(JSON object containing info about current SDP destination addresses being used)."""
        return json.dumps(self._vis_destination_address)
        # PROTECTED REGION END #    //  FspCorrSubarray.visDestinationAddress_read

    def write_visDestinationAddress(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.visDestinationAddress_write) ENABLED START #
        """Set VisDestinationAddress attribute(JSON object containing info about current SDP destination addresses being used)."""
        self._vis_destination_address = json.loads(value)
        # PROTECTED REGION END #    //  FspCorrSubarray.visDestinationAddress_write

    def read_fspChannelOffset(self):
        # PROTECTED REGION ID(Fsp.fspChannelOffset_read) ENABLED START #
        """Return the fspChannelOffset attribute."""
        return self._fsp_channel_offset
        # PROTECTED REGION END #    //  Fsp.fspChannelOffset_read

    def write_fspChannelOffset(self, value):
        # PROTECTED REGION ID(Fsp.fspChannelOffset_write) ENABLED START #
        """Set the fspChannelOffset attribute."""
        self._fsp_channel_offset=value
        # PROTECTED REGION END #    //  Fsp.fspChannelOffset_write

    def read_outputLinkMap(self):
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_read) ENABLED START #
        """Return the outputLinkMap attribute."""
        return self._output_link_map
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_read

    def write_outputLinkMap(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_write) ENABLED START #
        """Set the outputLinkMap attribute."""
        self._output_link_map=value
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_write

    def read_scanID(self):
        # PROTECTED REGION ID(FspCorrSubarray.scanID_read) ENABLED START #
        """Return the scanID attribute."""
        return self._scan_id
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_read

    def write_scanID(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.scanID_write) ENABLED START #
        """Set the scanID attribute."""
        self._scan_id=value
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_write

    def read_configID(self):
        # PROTECTED REGION ID(FspCorrSubarray.configID_read) ENABLED START #
        """Return the configID attribute."""
        return self._config_id
        # PROTECTED REGION END #    //  FspCorrSubarray.configID_read

    def write_configID(self, value):
        # PROTECTED REGION ID(FspCorrSubarray.configID_write) ENABLED START #
        """Set the configID attribute."""
        self._config_id=value
        # PROTECTED REGION END #    //  FspCorrSubarray.configID_write


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
        # PROTECTED REGION ID(FspCorrSubarray.On) ENABLED START #
        self.set_state(tango.DevState.ON)
        # PROTECTED REGION END #    //  FspCorrSubarray.On

    def is_Off_allowed(self):
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.IDLE.value:
            return True
        return False

    @command()
    def Off(self):
        # PROTECTED REGION ID(FspCorrSubarray.Off) ENABLED START #
        # This command can only be called when obsState=IDLE
        self.GoToIdle()
        self.RemoveAllReceptors()
        self.set_state(tango.DevState.OFF)
        # PROTECTED REGION END #    //  FspCorrSubarray.Off

    def is_AddReceptors_allowed(self):
        """allowed if FSPPssSubarry is ON, ObsState is not SCANNING"""
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
        # PROTECTED REGION ID(FspCorrSubarray.AddReceptors) ENABLED START #
        """add specified receptors to the FSP subarray. Input is array of int."""
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
        # PROTECTED REGION END #    //  FspCorrSubarray.AddReceptors

    def is_RemoveReceptors_allowed(self):
        """allowed if FSPPssSubarry is ON, ObsState is not SCANNING"""
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
        # PROTECTED REGION ID(FspCorrSubarray.RemoveReceptors) ENABLED START #
        """Remove Receptors. Input is array of int"""
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)
        # PROTECTED REGION END #    //  FspCorrSubarray.RemoveReceptors

    def is_RemoveAllReceptors_allowed(self):
        """allowed if FSPPssSubarry is ON, ObsState is not SCANNING"""
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
        # PROTECTED REGION ID(FspCorrSubarray.RemoveAllReceptors) ENABLED START #
        """Remove all Receptors of this subarray"""
        self.RemoveReceptors(self._receptors[:])
        # PROTECTED REGION END #    //  FspCorrSubarray.RemoveAllReceptors

    # def is_AddChannels_allowed(self): # ???
    #     pass
    #     """Allowed when devState is ON, obsState is CONFIGURING"""
    #     if self.dev_state() == tango.DevState.ON and\
    #             self._obs_state == ObsState.CONFIGURING.value:
    #         return True
    #     return False

    # @command(
    #     dtype_in='str',
    #     doc_in="Channel frequency info"
    # )
    # def AddChannels(self, argin):
    #     # PROTECTED REGION ID(FspCorrSubarray.AddChannels) ENABLED START #
    #     # obsState should already be CONFIGURING
    #     """Add/replace channel frequency information to an FSP subarray. Input is JSON object"""
    #     self._channel_info.clear()
    #     argin = json.loads(argin)

    #     for fsp in argin["fsp"]:
    #         if fsp["fspID"] == self._fsp_id:
    #             for link in fsp["cbfOutLink"]:
    #                 for channel in link["channel"]:
    #                     self._channel_info.append([
    #                         channel["chanID"],
    #                         channel["bw"],
    #                         channel["cf"],
    #                         link["linkID"],
    #                         # configure the addresses later
    #                         "",
    #                         0
    #                     ])

    #     # I'm pretty sure the list is sorted by first element anyway,
    #     # but specify that just in case, I guess.
    #     self._channel_info.sort(key=lambda x: x[0])
    #     # PROTECTED REGION END #    //  FspCorrSubarray.AddChannels

    # def is_AddChannelAddresses_allowed(self):
    #     """Allowed when devState is ON, obsState is CONFIGURING"""
    #     if self.dev_state() == tango.DevState.ON and\
    #             self._obs_state == ObsState.CONFIGURING.value:
    #         return True
    #     return False

    # @command(
    #     dtype_in='str',
    #     doc_in="Channel address info"
    # )
    # def AddChannelAddresses(self, argin):
    #     # PROTECTED REGION ID(FspCorrSubarray.AddChannelAddresses) ENABLED START #
    #     # obsState should already be CONFIGURING
    #     """Called by CbfSubarray. Add channel address information to an FSP Subarray. Input is JSON."""
    #     argin = json.loads(argin)

    #     for fsp in argin["receiveAddresses"]:
    #         if fsp["fspId"] == self._fsp_id:
    #             channel_ID_list = [*map(lambda x: x[0], self._channel_info)]
    #             for host in fsp["hosts"]:
    #                 for channel in host["channels"]:
    #                     try:
    #                         i = channel_ID_list.index(channel["startChannel"])
    #                         for j in range(i, i + channel["numChannels"]):
    #                             self._channel_info[j][4] = host["host"]
    #                             self._channel_info[j][5] = \
    #                                 channel["portOffset"] + self._channel_info[j][0]
    #                     # Possible errors:
    #                     #     Channel ID not found.
    #                     #     Number of channels exceeds configured channels.
    #                     # (probably among others)
    #                     except Exception as e:
    #                         msg = "An error occurred while configuring destination addresses:"\
    #                             "\n{}\n".format(str(e))
    #                         self.logger.error(msg)
    #                         tango.Except.throw_exception("Command failed", msg,
    #                                                        "AddChannelAddresses execution",
    #                                                        tango.ErrSeverity.ERR)
    #             self._vis_destination_address = fsp["hosts"]

        # get list of unconfigured channels
        # unconfigured_channels = [channel[0] for channel in self._channel_info if channel[4] == ""]
        # if unconfigured_channels:
        #     # raise an error if some channels are unconfigured
        #     msg = "The following channels are missing destination addresses:\n{}".format(
        #         unconfigured_channels
        #     )
        #     self.logger.error(msg)
        #     tango.Except.throw_exception("Command failed", msg,
        #                                    "AddChannelAddressInfo execution",
        #                                    tango.ErrSeverity.ERR)

        # # transition to obsState=READY
        # self._obs_state = ObsState.READY.value
        # # PROTECTED REGION END #    //  FspCorrSubarray.AddChannelAddresses

    def is_ConfigureScan_allowed(self):
        """Allowed if FSP subarray is ON, obsState is IDLE."""
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
    )
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(FspCorrSubarray.ConfigureScan) ENABLED START #
        # This function is called after the configuration has already been validated,
        # so the checks here have been removed to reduce overhead.
        """Input a JSON. Configure scan for fsp. Called by CbfSubarrayCorrConfig(proxy_fsp_corr_subarray.ConfigureScan(json.dumps(fsp)))"""
        # transition to obsState=CONFIGURING
        self._obs_state = ObsState.CONFIGURING.value
        self.push_change_event("obsState", self._obs_state)

        argin = json.loads(argin)

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


            # Configure fspChannelOffset
            self._fsp_channel_offset= int(argin["fspChannelOffset"])
                
            # Configure destination addresses
            self._vis_destination_address["outputHost"]=argin["outputHost"]
            # ouputMac is optional
            if "outputMac" in argin:
                self._vis_destination_address["outputMac"]=argin["outputMac"]
            else: # not specified, so set default or keep the previous one
                if self._vis_destination_address["outputMac"]==[]:
                    self._vis_destination_address["outputMac"]=[[0, "06-00-00-00-00-01"]]
            self._vis_destination_address["outputPort"]=argin["outputPort"]

            # Configure channelAveragingMap.
            if "channelAveragingMap" in argin:
                # for i in range(20):
                #     self._channel_averaging_map[i][1] = int(argin["channelAveragingMap"][i][1])
                self._channel_averaging_map=argin["channelAveragingMap"]
            else:
                self._channel_averaging_map = [
                    [int(i*self.NUM_FINE_CHANNELS/self.NUM_CHANNEL_GROUPS) + 1, 0]
                    for i in range(self.NUM_CHANNEL_GROUPS)
                ]
                log_msg = "FSP specified, but 'channelAveragingMap not given. Default to averaging "\
                    "factor = 0 for all channel groups."
                self.logger.warn(log_msg)

            # Configure outputLinkMap
            self._output_link_map=argin["outputLinkMap"]

            # Configure configID. This is not initally in the FSP portion of the input JSON, but added in function CbfSuarray._validate_configScan
            self._config_id=argin["configID"]



        # This state transition will be later 
        # 03-23-2020: FspCorrSubarray moves to READY after configuration of the 
        # channels addresses sent by SDP. (ADDChannelAddresses funtion, which is called by the subarray)
        # 06-18-2020: seems like it's not necessary for SDP to trigger ready anymore
        self._obs_state = ObsState.READY.value

        # PROTECTED REGION END #    //  FspCorrSubarray.ConfigureScan

    def is_EndScan_allowed(self):
        """allowed if ON nd ObsState is SCANNING"""
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.SCANNING.value:
            return True
        return False

    @command()
    def EndScan(self):
        """Set ObsState to READY. Set ScanID to zero"""
        # PROTECTED REGION ID(FspCorrSubarray.EndScan) ENABLED START #
        self._obs_state = ObsState.READY.value
        self._scan_id = 0
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspCorrSubarray.EndScan

    def is_Scan_allowed(self):
        """Allowed if DevState ON, ObsState READY"""
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state == ObsState.READY.value:
            return True
        return False

    @command(
        dtype_in='uint16',
        doc_in="Scan ID"
    )
    def Scan(self, argin):
        # PROTECTED REGION ID(FspCorrSubarray.Scan) ENABLED START #
        """Set ObsState to READY, set scanID"""
        self.logger.info("scan in fspcorrsubarray")
        self._obs_state = ObsState.SCANNING.value
        # set scanID
        try:
            self._scan_id=int(argin)
        except:
            msg="The input scanID is not integer."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "FspCorrSubarray Scan execution",
                                         tango.ErrSeverity.ERR)
        
        # nothing else is supposed to happen
        # PROTECTED REGION END #    //  FspCorrSubarray.Scan

    def is_GoToIdle_allowed(self):
        """ON and ObsState IDLE or READY"""
        if self.dev_state() == tango.DevState.ON and\
                self._obs_state in [ObsState.IDLE.value, ObsState.READY.value]:
            return True
        return False

    @command()
    def GoToIdle(self):
        # PROTECTED REGION ID(FspCorrSubarray.GoToIdle) ENABLED START #
        # transition to obsState=IDLE
        """Clear channel. Set Obsstate to IDLE"""
        self._channel_info.clear()
        self._obs_state = ObsState.IDLE.value
        self._config_id=""
        # PROTECTED REGION END #    //  FspCorrSubarray.GoToIdle


    def is_getLinkAndAddress_allowed(self):
        """Allowed if destination addresses are received, meaning outputLinkMap also received (checked in subarray validate scan)."""
        if self._vis_destination_address["outputHost"]==[]:
            return False
        return True
    @command(
        dtype_in='DevULong',
        doc_in="channel ID",
        dtype_out='DevString',
        doc_out="output link and destination addresses in JSON",
    )
    @DebugIt()
    def getLinkAndAddress(self, argin):
        # PROTECTED REGION ID(FspCorrSubarray.getLinkAndAddress) ENABLED START #
        """
        get output link and destination addresses in JSON based on a channel ID

        :param argin: 'DevULong'
        channel ID

        :return:'DevString'
        output link and destination addresses in JSON
        """
        if argin<0 or argin >14479:
            msg="channelID should be between 0 to 14479"
            tango.Except.throw_exception("Command failed", msg, "getLinkAndAddress",
                                           tango.ErrSeverity.ERR)
            return


        result={"outputLink": 0, "outputHost": "", "outputMac": "", "outputPort": 0}
        # Get output link by finding the first element[1] that's greater than argin
        link=0
        for element in self._output_link_map:
            if argin>=element[0]:
                link=element[1]
            else:
                break
        result["outputLink"]=link
        # Get 3 addresses by finding the first element[1] that's greater than argin
        host=""
        for element in self._vis_destination_address["outputHost"]:
            if argin>=element[0]:
                host=element[1]
            else:
                break
        result["outputHost"]=host        
        
        mac=""
        for element in self._vis_destination_address["outputMac"]:
            if argin>=element[0]:
                mac=element[1]
            else:
                break
        result["outputMac"]=mac
        
        # Port is different. the array is given as [[start_channel, start_value, increment],[start_channel, start_value, increment],.....]
        # value = start_value + (channel - start_channel)*increment
        triple=[] # find the triple with correct start_value
        for element in self._vis_destination_address["outputPort"]:
            if argin>=element[0]:
                triple=element
            else:
                break
        
        result["outputPort"]= triple[1] + (argin - triple[0])* triple[2]

        return str(result)
        # PROTECTED REGION END #    //  FspCorrSubarray.getLinkAndAddress
# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspCorrSubarray.main) ENABLED START #
    return run((FspCorrSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspCorrSubarray.main


if __name__ == '__main__':
    main()
