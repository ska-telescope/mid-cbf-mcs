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
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple

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

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base import CspSubElementObsDevice
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# PROTECTED REGION END #    //  FspCorrSubarray.additionnal_import

__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(CspSubElementObsDevice):
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

    CbfControllerAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Controller",
        default_value="mid_csp_cbf/controller/main"
    )

    # TODO - note the connection to the CbfSubarray device is not being used
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
        access=AttrWriteType.READ,
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

    def init_command_objects(self: FspCorrSubarray) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.state_model, self.logger)
        self.register_command_object(
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the Vcc's init_device() "command".
        """

        def do(
            self: FspCorrSubarray.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            device = self.target

            # Make a private copy of the device properties:
            device._subarray_id = device.SubID
            device._fsp_id = device.FspID

            # initialize attribute values
            device._receptors = []
            device._freq_band_name = ""
            device._frequency_band = 0
            device._stream_tuning = (0, 0)
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._frequency_slice_ID = 0
            device._bandwidth = 0
            device._bandwidth_actual = const.FREQUENCY_SLICE_BW
            device._zoom_window_tuning = 0
            device._integration_time = 0
            device._scan_id = 0
            device._config_id = ""
            device._channel_averaging_map = [
                [int(i*const.NUM_FINE_CHANNELS/const.NUM_CHANNEL_GROUPS) + 1, 0]
                for i in range(const.NUM_CHANNEL_GROUPS)
            ]
            # destination addresses includes the following three
            device._vis_destination_address = {"outputHost": [], "outputMac": [], "outputPort": []}
            device._fsp_channel_offset = 0
            # outputLinkMap is a 2*40 array. Pogo generates tuple;
            # Changed into list to facilitate writing
            device._output_link_map = [[0,0] for i in range(40)]

            # For each channel sent to SDP: 
            # [chanID, bw, cf, cbfOutLink, sdpIp, sdpPort] # TODO
            device._channel_info = []

            # device proxy for connection to CbfController
            device._proxy_cbf_controller = CbfDeviceProxy(
                fqdn=device.CbfControllerAddress,
                logger=device.logger
            )
            device._controller_max_capabilities = dict(
                pair.split(":") for pair in 
                device._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
            )

            # Connect to all VCC devices turned on by CbfController:
            device._count_vcc = int(device._controller_max_capabilities["VCC"])
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._proxies_vcc = [
                CbfDeviceProxy(
                    logger=device.logger, 
                    fqdn=address) for address in device._fqdn_vcc
            ]

            message = "FspCorrSubarry Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)
            
            # PROTECTED REGION END #    //  FspCorrSubarray.init_device

    def always_executed_hook(self: FspCorrSubarray) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.always_executed_hook) ENABLED START #
        """hook before any commands"""
        pass
        # PROTECTED REGION END #    //  FspCorrSubarray.always_executed_hook

    def delete_device(self: FspCorrSubarray) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspCorrSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self: FspCorrSubarray) -> List[int]:
        # PROTECTED REGION ID(FspCorrSubarray.receptors_read) ENABLED START #
        """return receptros attribute.(array of int)"""
        return self._receptors
        # PROTECTED REGION END #    //  FspCorrSubarray.receptors_read

    def read_frequencyBand(self: FspCorrSubarray) -> tango.DevEnum:
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBand_read) ENABLED START #
        """Return frequencyBand attribute(DevEnum)."""
        return self._frequency_band
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBand_read

    def read_band5Tuning(self: FspCorrSubarray) -> List[float]:
        # PROTECTED REGION ID(FspCorrSubarray.band5Tuning_read) ENABLED START #
        """Return band5Tuning attribute(array of float, first element corresponds to the first stream, second to the second stream).""" 
        return self._stream_tuning
        # PROTECTED REGION END #    //  FspCorrSubarray.band5Tuning_read

    def read_frequencyBandOffsetStream1(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBandOffsetStream1) ENABLED START #
        """Return frequencyBandOffsetStream1 attribute"""
        return self._frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBandOffsetStream1

    def read_frequencyBandOffsetStream2(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBandOffsetStream2) ENABLED START #
        """Return frequencyBandOffsetStream2 attribute"""
        return self._frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBandOffsetStream2

    def read_frequencySliceID(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.frequencySliceID_read) ENABLED START #
        """Return frequencySliceID attribute"""
        return self._frequency_slice_ID
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencySliceID_read

    def read_corrBandwidth(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.corrBandwidth_read) ENABLED START #
        """Return corrBandwidth attribute(Bandwidth to be correlated is <Full Bandwidth>/2^bandwidth)."""
        return self._bandwidth
        # PROTECTED REGION END #    //  FspCorrSubarray.corrBandwidth_read

    def read_zoomWindowTuning(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.zoomWindowTuning_read) ENABLED START #
        """Return zoomWindowTuning attribute."""
        return self._zoom_window_tuning
        # PROTECTED REGION END #    //  FspCorrSubarray.zoomWindowTuning_read

    def read_integrationTime(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.integrationTime_read) ENABLED START #
        """Return integrationTime attribute(millisecond)."""
        return self._integration_time
        # PROTECTED REGION END #    //  FspCorrSubarray.integrationTime_read

    def read_channelAveragingMap(self: FspCorrSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(FspCorrSubarray.channelAveragingMap_read) ENABLED START #
        """Return channelAveragingMap. 
           Consists of 2*20 array of integers(20 tupples representing 20* 744 channels). 
           The first element is the ID of the first channel in a channel group. The second element is the averaging factor"""
        return self._channel_averaging_map
        # PROTECTED REGION END #    //  FspCorrSubarray.channelAveragingMap_read

    def read_visDestinationAddress(self: FspCorrSubarray) -> str:
        # PROTECTED REGION ID(FspCorrSubarray.visDestinationAddress_read) ENABLED START #
        """Return VisDestinationAddress attribute(JSON object containing info about current SDP destination addresses being used)."""
        return json.dumps(self._vis_destination_address)
        # PROTECTED REGION END #    //  FspCorrSubarray.visDestinationAddress_read

    def write_visDestinationAddress(self: FspCorrSubarray, value: str) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.visDestinationAddress_write) ENABLED START #
        """Set VisDestinationAddress attribute(JSON object containing info about current SDP destination addresses being used)."""
        self._vis_destination_address = json.loads(value)
        # PROTECTED REGION END #    //  FspCorrSubarray.visDestinationAddress_write

    def read_fspChannelOffset(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(Fsp.fspChannelOffset_read) ENABLED START #
        """Return the fspChannelOffset attribute."""
        return self._fsp_channel_offset
        # PROTECTED REGION END #    //  Fsp.fspChannelOffset_read

    def write_fspChannelOffset(self: FspCorrSubarray, value: int) -> None:
        # PROTECTED REGION ID(Fsp.fspChannelOffset_write) ENABLED START #
        """Set the fspChannelOffset attribute."""
        self._fsp_channel_offset=value
        # PROTECTED REGION END #    //  Fsp.fspChannelOffset_write

    def read_outputLinkMap(self: FspCorrSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_read) ENABLED START #
        """Return the outputLinkMap attribute."""
        return self._output_link_map
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_read

    def write_outputLinkMap(self: FspCorrSubarray, value: List[List[int]]) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_write) ENABLED START #
        """Set the outputLinkMap attribute."""
        self._output_link_map=value
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_write

    def read_scanID(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.scanID_read) ENABLED START #
        """Return the scanID attribute."""
        return self._scan_id
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_read

    def write_scanID(self: FspCorrSubarray, value: int) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.scanID_write) ENABLED START #
        """Set the scanID attribute."""
        self._scan_id=value
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_write

    def read_configID(self: FspCorrSubarray) -> str:
        # PROTECTED REGION ID(FspCorrSubarray.configID_read) ENABLED START #
        """Return the configID attribute."""
        return self._config_id
        # PROTECTED REGION END #    //  FspCorrSubarray.configID_read

    def write_configID(self: FspCorrSubarray, value: str) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.configID_write) ENABLED START #
        """Set the configID attribute."""
        self._config_id=value
        # PROTECTED REGION END #    //  FspCorrSubarray.configID_write

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def AddReceptors(
        self: FspCorrSubarray, 
        argin: List[int]
        ) -> None:
        """add specified receptors to the FSP subarray. Input is array of int."""
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
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

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
    )
    def RemoveReceptors(
        self: FspCorrSubarray, 
        argin: List[int]
        )-> None:
        """Remove Receptors. Input is array of int"""
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)

    @command()
    def RemoveAllReceptors(self: FspCorrSubarray) -> None:
        """Remove all Receptors of this subarray"""
        self.RemoveReceptors(self._receptors[:])

    # TODO: Reinstate AddChannels?
    # def is_AddChannels_allowed(self): # ???
    #     pass
    #     """Allowed when devState is ON, obsState is CONFIGURING"""
    #     if self.dev_state() == tango.DevState.ON and\
    #             self.state_model._obs_state == ObsState.CONFIGURING.value:
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
    #             self.state_model._obs_state == ObsState.CONFIGURING.value:
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
    # self.state_model._obs_state = ObsState.READY.value
    # # PROTECTED REGION END #    //  FspCorrSubarray.AddChannelAddresses

    # --------
    # Commands
    # --------

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspCorrSubarray's ConfigureScan() command.
        """

        """Input a serilized JSON object. """

        def do(
            self: FspCorrSubarray.ConfigureScanCommand,
            argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string
            :type argin: str

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            self.logger.debug("Entering ConfigureScanCommand()")

            device = self.target

            # validate the input args

            # NOTE: This function is called after the
            # configuration has already  been validated, 
            # so the checks here have been removed to
            #  reduce overhead TODO:  to change where the
            # validation is done

            argin = json.loads(argin)

            # Configure frequencyBand.
            device._freq_band_name = argin["frequency_band"]
            device._frequency_band = freq_band_dict()[device._freq_band_name]

            # Configure streamTuning.
            device._stream_tuning = argin["band_5_tuning"]

            # Configure frequencyBandOffsetStream1.
            device._frequency_band_offset_stream_1 = int(argin["frequency_band_offset_stream_1"])

            # Configure frequencyBandOffsetStream2.
            device._frequency_band_offset_stream_2 = int(argin["frequency_band_offset_stream_2"])

            # Configure receptors.
            
            # TODO: RemoveAllReceptors should not be needed because it is
            #        applied in GoToIdle()
            device.RemoveAllReceptors()
            device.AddReceptors(map(int, argin["receptor_ids"]))

            # Configure frequencySliceID.
            device._frequency_slice_ID = int(argin["frequency_slice_id"])
            # Configure corrBandwidth.
            device._bandwidth = int(argin["zoom_factor"])
            device._bandwidth_actual = int(const.FREQUENCY_SLICE_BW/2**int(argin["zoom_factor"]))

            # Configure zoomWindowTuning.
            if device._bandwidth != 0:  # zoomWindowTuning is required
                if device._frequency_band in list(range(4)):  # frequency band is not band 5
                    device._zoom_window_tuning = int(argin["zoom_window_tuning"])

                    frequency_band_start = [*map(lambda j: j[0]*10**9, [
                        const.FREQUENCY_BAND_1_RANGE,
                        const.FREQUENCY_BAND_2_RANGE,
                        const.FREQUENCY_BAND_3_RANGE,
                        const.FREQUENCY_BAND_4_RANGE
                    ])][device._frequency_band] + device._frequency_band_offset_stream_1
                    frequency_slice_range = (
                        frequency_band_start + \
                            (device._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                        frequency_band_start +
                            device._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                    )

                    if frequency_slice_range[0] + \
                            device._bandwidth_actual*10**6/2 <= \
                            int(argin["zoom_window_tuning"])*10**3 <= \
                            frequency_slice_range[1] - \
                            device._bandwidth_actual*10**6/2:
                        # this is the acceptable range
                        pass
                    else:
                        # log a warning message
                        log_msg = "'zoomWindowTuning' partially out of observed frequency slice. "\
                            "Proceeding."
                        self.logger.warn(log_msg)
                else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                    device._zoom_window_tuning = argin["zoom_window_tuning"]

                    frequency_slice_range_1 = (
                        device._stream_tuning[0]*10**9 + device._frequency_band_offset_stream_1 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            (device._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                        device._stream_tuning[0]*10**9 + device._frequency_band_offset_stream_1 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            device._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                    )

                    frequency_slice_range_2 = (
                        device._stream_tuning[1]*10**9 + device._frequency_band_offset_stream_2 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            (device._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                        device._stream_tuning[1]*10**9 + device._frequency_band_offset_stream_2 - \
                            const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                            device._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                    )

                    if (frequency_slice_range_1[0] + \
                            device._bandwidth_actual*10**6/2 <= \
                            int(argin["zoom_window_tuning"])*10**3 <= \
                            frequency_slice_range_1[1] - \
                            device._bandwidth_actual*10**6/2) or\
                            (frequency_slice_range_2[0] + \
                            device._bandwidth_actual*10**6/2 <= \
                            int(argin["zoom_window_tuning"])*10**3 <= \
                            frequency_slice_range_2[1] - \
                            device._bandwidth_actual*10**6/2):
                        # this is the acceptable range
                        pass
                    else:
                        # log a warning message
                        log_msg = "'zoomWindowTuning' partially out of observed frequency slice. "\
                            "Proceeding."
                        self.logger.warn(log_msg)

            # Configure integrationTime.
            device._integration_time = int(argin["integration_factor"])

            # Configure fspChannelOffset
            device._fsp_channel_offset = int(argin["channel_offset"])
                
            #TODO implement output products transmission

            # Configure destination addresses
            if "output_host" in argin:
                device._vis_destination_address["outputHost"] = argin["output_host"]
            # not specified, so set default or keep the previous one
            elif device._vis_destination_address["outputHost"] == []:
                device._vis_destination_address["outputHost"] = [[0, "192.168.0.1"]]

            # ouputMac is optional
            if "output_mac" in argin:
                device._vis_destination_address["outputMac"] = argin["output_mac"]
            # not specified, so set default or keep the previous one
            elif device._vis_destination_address["outputMac"] == []:
                device._vis_destination_address["outputMac"] = [[0, "06-00-00-00-00-01"]]

            if "output_port" in argin:
                device._vis_destination_address["outputPort"] = argin["output_port"]
            elif device._vis_destination_address["outputPort"] == []:
                device._vis_destination_address["outputPort"] = [[0, 9000, 1]]

            # Configure channelAveragingMap.
            if "channel_averaging_map" in argin:
                # for i in range(20):
                #     device._channel_averaging_map[i][1] = int(argin["channelAveragingMap"][i][1])
                device._channel_averaging_map = argin["channel_averaging_map"]
            else:
                device._channel_averaging_map = [
                    [int(i*const.NUM_FINE_CHANNELS/const.NUM_CHANNEL_GROUPS) + 1, 0]
                    for i in range(const.NUM_CHANNEL_GROUPS)
                ]
                log_msg = "FSP specified, but 'channelAveragingMap not given. Default to averaging "\
                    "factor = 0 for all channel groups."
                self.logger.warn(log_msg)

            # Configure outputLinkMap
            device._output_link_map = argin["output_link_map"]

            # Configure configID. This is not initally in the FSP portion of the input JSON, but added in function CbfSuarray._validate_configScan
            device._config_id = argin["config_id"]

            # TODO - reinstate the validate_input() and move all the
            #        validations to it
            # (result_code, msg) = self.validate_input(argin) # TODO

            result_code = ResultCode.OK # TODO  - temp - remove
            msg = "Configure command completed OK" # TODO temp, remove

            if result_code == ResultCode.OK:
                # store the configuration on command success
                device._last_scan_configuration = argin
                msg = "Configure command completed OK"

            return(result_code, msg)

        def validate_input(
            self: FspCorrSubarray.ConfigureScanCommand, 
            argin: str
            ) -> None:
            """
            Validate the configuration parameters against allowed values, as needed.

            :param argin: The JSON formatted string with configuration for the device.
            :type argin: 'DevString'
            :return: A tuple containing a return code and a string message.
            :rtype: (ResultCode, str)
            """
            device = self.target

            # TODO -add the actual validation
            return (ResultCode.OK, "ConfigureScan arguments validation successfull")

    @command(
        dtype_in='DevString',
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out='DevVarLongStringArray',
        doc_out="A tuple containing a return code and a string message indicating status. "
                "The message is for information purpose only.",
    )
    
    @DebugIt()
    def ConfigureScan(
        self: FspCorrSubarray, 
        argin: str
        ) -> None:
        # PROTECTED REGION ID(Vcc.ConfigureScan) ENABLED START #
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.
        :type argin: 'DevString'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the FspCorrSubarray's GoToIdle command.
        """

        def do(
            self: FspCorrSubarray.ConfigureScanCommand
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for GoToIdle() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")

            device = self.target

            # Reset all private data defined in InitCommand.do()
            # and which are then set via ConfigureScan()

            device._freq_band_name = ""
            device._frequency_band = 0
            device._stream_tuning = (0, 0)
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._frequency_slice_ID = 0
            device._bandwidth = 0
            device._bandwidth_actual = const.FREQUENCY_SLICE_BW
            device._zoom_window_tuning = 0
            device._integration_time = 0
            device._scan_id = 0
            device._config_id = ""

            device._channel_averaging_map = [
                [int(i*const.NUM_FINE_CHANNELS/const.NUM_CHANNEL_GROUPS) + 1, 0]
                for i in range(const.NUM_CHANNEL_GROUPS)
            ]
            # destination addresses includes the following three
            device._vis_destination_address = {"outputHost":[], "outputMac": [], "outputPort":[]}
            device._fsp_channel_offset = 0
            # outputLinkMap is a 2*40 array. Pogo generates tuple;
            # Changed into list to facilitate writing
            device._output_link_map = [[0,0] for i in range(40)]

            device._channel_info = []
            #device._channel_info.clear() #TODO:  not yet populated

            # Reset self._receptors
            device.RemoveAllReceptors()

            if device.state_model.obs_state == ObsState.IDLE:
                return (ResultCode.OK, 
                "GoToIdle command completed OK. Device already IDLE")

            return (ResultCode.OK, "GoToIdle command completed OK")
            
    # TODO - currently not used
    def is_getLinkAndAddress_allowed(self: FspCorrSubarray) -> bool:
        """Allowed if destination addresses are received, meaning outputLinkMap 
        also received (checked in subarray validate scan)."""
        if self._vis_destination_address["outputHost"]==[]:
            return False
        return True
    @command(
        dtype_in='DevULong',
        doc_in="channel ID",
        dtype_out='DevString',
        doc_out="output link and destination addresses in JSON",
    )
    def getLinkAndAddress(
        self: FspCorrSubarray, 
        argin: int
        ) -> str:
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
            tango.Except.throw_exception("Command failed", msg, 
            "getLinkAndAddress", tango.ErrSeverity.ERR)
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
