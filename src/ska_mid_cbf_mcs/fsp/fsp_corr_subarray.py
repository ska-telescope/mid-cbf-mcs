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
from __future__ import annotations

import json

# Additional import
# PROTECTED REGION ID(FspCorrSubarray.additionnal_import) ENABLED START #
import os
from typing import List, Optional, Tuple

# tango imports
import tango
from ska_tango_base import CspSubElementObsDevice, SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState, PowerMode
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager import (
    FspCorrSubarrayComponentManager,
)

file_path = os.path.dirname(os.path.abspath(__file__))


# PROTECTED REGION END #  //  FspCorrSubarray.additionnal_import

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

    SubID = device_property(dtype="uint16")

    FspID = device_property(dtype="uint16")

    CbfControllerAddress = device_property(
        dtype="str",
        doc="FQDN of CBF Controller",
        default_value="mid_csp_cbf/controller/main",
    )

    # TODO - note the connection to the CbfSubarray device is not being used
    CbfSubarrayAddress = device_property(
        dtype="str", doc="FQDN of CBF Subarray"
    )

    VCC = device_property(dtype=("str",))

    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=("uint16",),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )

    frequencyBand = attribute(
        dtype="DevEnum",
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=[
            "1",
            "2",
            "3",
            "4",
            "5a",
            "5b",
        ],
    )

    band5Tuning = attribute(
        dtype=("float",),
        max_dim_x=2,
        access=AttrWriteType.READ,
        label="Stream tuning (GHz)",
        doc="Stream tuning (GHz)",
    )

    frequencyBandOffsetStream1 = attribute(
        dtype="int",
        access=AttrWriteType.READ,
        label="Frequency offset for stream 1 (Hz)",
        doc="Frequency offset for stream 1 (Hz)",
    )

    frequencyBandOffsetStream2 = attribute(
        dtype="int",
        access=AttrWriteType.READ,
        label="Frequency offset for stream 2 (Hz)",
        doc="Frequency offset for stream 2 (Hz)",
    )

    frequencySliceID = attribute(
        dtype="uint16",
        access=AttrWriteType.READ,
        label="Frequency slice ID",
        doc="Frequency slice ID",
    )

    corrBandwidth = attribute(
        dtype="uint16",
        access=AttrWriteType.READ,
        label="Bandwidth to be correlated",
        doc="Bandwidth to be correlated is <Full Bandwidth>/2^bandwidth",
    )

    zoomWindowTuning = attribute(
        dtype="uint",
        access=AttrWriteType.READ,
        label="Zoom window tuning (kHz)",
        doc="Zoom window tuning (kHz)",
    )

    integrationTime = attribute(
        dtype="uint16",
        access=AttrWriteType.READ,
        label="Integration time (ms)",
        doc="Integration time (ms)",
    )

    channelAveragingMap = attribute(
        dtype=(("uint16",),),
        max_dim_x=2,
        max_dim_y=20,
        access=AttrWriteType.READ,
        label="Channel averaging map",
        doc="Channel averaging map",
    )

    visDestinationAddress = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses",
        doc="Destination addresses for visibilities, given as a JSON object",
    )

    fspChannelOffset = attribute(
        dtype="DevLong",
        access=AttrWriteType.READ_WRITE,
        label="fspChannelOffset",
        doc="fsp Channel offset, integer, multiple of 14480",
    )

    outputLinkMap = attribute(
        dtype=(("DevULong64",),),
        access=AttrWriteType.READ,
        max_dim_x=2,
        max_dim_y=40,
    )

    scanID = attribute(
        dtype="DevLong64",
        access=AttrWriteType.READ_WRITE,
        label="scanID",
        doc="scan ID, set when transition to SCANNING is performed",
    )

    configID = attribute(
        dtype="str",
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

        device_args = (
            self,
            self.op_state_model,
            self.obs_state_model,
            self.logger,
        )
        self.register_command_object(
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object("Scan", self.ScanCommand(*device_args))
        self.register_command_object(
            "EndScan", self.EndScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

        device_args = (self, self.op_state_model, self.logger)
        self.register_command_object("On", self.OnCommand(*device_args))
        self.register_command_object("Off", self.OffCommand(*device_args))
        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the FspCorrSubarray's init_device() "command".
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

            super().do()

            device = self.target
            device._configuring_from_idle = False

            self.logger.debug("Entering InitCommand()")

            message = "FspCorrSubarry Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

            # PROTECTED REGION END #    //  FspCorrSubarray.init_device

    def always_executed_hook(self: FspCorrSubarray) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        # PROTECTED REGION END #    //  FspCorrSubarray.always_executed_hook

    def create_component_manager(
        self: FspCorrSubarray,
    ) -> FspCorrSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return FspCorrSubarrayComponentManager(
            self.logger,
            self.push_change_event,
            self._communication_status_changed,
            self._component_power_mode_changed,
            self._component_fault,
        )

    def delete_device(self: FspCorrSubarray) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.delete_device) ENABLED START #
        """Hook to delete device."""

        # PROTECTED REGION END #    //  FspCorrSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self: FspCorrSubarray) -> List[int]:
        # PROTECTED REGION ID(FspCorrSubarray.receptors_read) ENABLED START #
        """
        Read the receptors attribute.

        :return: the list of receptors
        :rtype: List[int]
        """
        return self.component_manager.receptors
        # PROTECTED REGION END #    //  FspCorrSubarray.receptors_read

    def read_frequencyBand(self: FspCorrSubarray) -> tango.DevEnum:
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBand_read) ENABLED START #
        """
        Read the frequencyBand attribute.

        :return: the frequency band
        :rtype: tango.DevEnum
        """
        return self.component_manager.frequency_band
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBand_read

    def read_band5Tuning(self: FspCorrSubarray) -> List[float]:
        # PROTECTED REGION ID(FspCorrSubarray.band5Tuning_read) ENABLED START #
        """
        Read the band5Tuning attribute.

        :return: the band5Tuning attribute (array of float,
            first element corresponds to the first stream,
            second to the second stream).
        :rtype: List[float]
        """
        return self.component_manager.stream_tuning
        # PROTECTED REGION END #    //  FspCorrSubarray.band5Tuning_read

    def read_frequencyBandOffsetStream1(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBandOffsetStream1) ENABLED START #
        """
        Read the frequencyBandOffsetStream1 attribute.

        :return: the frequencyBandOffsetStream1 attribute
        :rtype: int
        """
        return self.component_manager.frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBandOffsetStream1

    def read_frequencyBandOffsetStream2(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.frequencyBandOffsetStream2) ENABLED START #
        """
        Read the frequencyBandOffsetStream2 attribute.

        :return: the frequencyBandOffsetStream2 attribute.
        :rtype: int
        """
        return self.component_manager.frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencyBandOffsetStream2

    def read_frequencySliceID(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.frequencySliceID_read) ENABLED START #
        """
        Read the frequencySliceID attribute.

        :return: the frequencySliceID attribute.
        :rtype: int
        """
        return self.component_manager.frequency_slice_id
        # PROTECTED REGION END #    //  FspCorrSubarray.frequencySliceID_read

    def read_corrBandwidth(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.corrBandwidth_read) ENABLED START #
        """
        Read the corrBandwidth attribute.

        :return: the corrBandwidth attribute
            (bandwidth to be correlated is <Full Bandwidth>/2^bandwidth).
        :rtype: int
        """
        return self.component_manager.bandwidth
        # PROTECTED REGION END #    //  FspCorrSubarray.corrBandwidth_read

    def read_zoomWindowTuning(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.zoomWindowTuning_read) ENABLED START #
        """
        Read the zoomWindowTuning attribute.

        :return: the zoomWindowTuning attribute
        :rtype: int
        """
        return self.component_manager.zoom_window_tuning
        # PROTECTED REGION END #    //  FspCorrSubarray.zoomWindowTuning_read

    def read_integrationTime(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.integrationTime_read) ENABLED START #
        """
        Read the integrationTime attribute.

        :return: the integrationTime attribute (millisecond).
        :rtype: int
        """
        return self.component_manager.integration_time
        # PROTECTED REGION END #    //  FspCorrSubarray.integrationTime_read

    def read_channelAveragingMap(self: FspCorrSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(FspCorrSubarray.channelAveragingMap_read) ENABLED START #
        """
        Read the channelAveragingMap attribute.

        :return: the channelAveragingMap attribute.
            Consists of 2*20 array of integers(20 tupples representing 20* 744 channels).
            The first element is the ID of the first channel in a channel group.
            The second element is the averaging factor
        :rtype: List[List[int]]
        """
        return self.component_manager.channel_averaging_map
        # PROTECTED REGION END #    //  FspCorrSubarray.channelAveragingMap_read

    def read_visDestinationAddress(self: FspCorrSubarray) -> str:
        # PROTECTED REGION ID(FspCorrSubarray.visDestinationAddress_read) ENABLED START #
        """
        Read the visDestinationAddress attribute.

        :return: the visDestinationAddress attribute.
            (JSON object containing info about current SDP destination addresses being used).
        :rtype: str
        """
        return json.dumps(self.component_manager.vis_destination_address)
        # PROTECTED REGION END #    //  FspCorrSubarray.visDestinationAddress_read

    def write_visDestinationAddress(self: FspCorrSubarray, value: str) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.visDestinationAddress_write) ENABLED START #
        """
        Write the visDestinationAddress attribute.

        :param value: the visDestinationAddress attribute value.
            (JSON object containing info about current SDP destination addresses being used).
        """
        self.component_manager.vis_destination_address = json.loads(value)
        # PROTECTED REGION END #    //  FspCorrSubarray.visDestinationAddress_write

    def read_fspChannelOffset(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(Fsp.fspChannelOffset_read) ENABLED START #
        """
        Read the fspChannelOffset attribute.

        :return: the fspChannelOffset attribute.
        :rtype: int
        """
        return self.component_manager.fsp_channel_offset
        # PROTECTED REGION END #    //  Fsp.fspChannelOffset_read

    def write_fspChannelOffset(self: FspCorrSubarray, value: int) -> None:
        # PROTECTED REGION ID(Fsp.fspChannelOffset_write) ENABLED START #
        """
        Write the fspChannelOffset attribute.

        :param value: the fspChannelOffset attribute value.
        """
        self.component_manager.fsp_channel_offset = value
        # PROTECTED REGION END #    //  Fsp.fspChannelOffset_write

    def read_outputLinkMap(self: FspCorrSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_read) ENABLED START #
        """
        Read the outputLinkMap attribute.

        :return: the outputLinkMap attribute.
        :rtype: List[List[int]]
        """
        return self.component_manager.output_link_map
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_read

    def write_outputLinkMap(
        self: FspCorrSubarray, value: List[List[int]]
    ) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.outputLinkMap_write) ENABLED START #
        """
        Write the outputLinkMap attribute.

        :param value: the outputLinkMap attribute value.
        """
        self.component_manager.output_link_map = value
        # PROTECTED REGION END #    //  FspCorrSubarray.outputLinkMap_write

    def read_scanID(self: FspCorrSubarray) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.scanID_read) ENABLED START #
        """
        Read the scanID attribute.

        :return: the scanID attribute.
        :rtype: int
        """
        return self.component_manager.scan_id
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_read

    def write_scanID(self: FspCorrSubarray, value: int) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.scanID_write) ENABLED START #
        """
        Write the scanID attribute.

        :param value: the scanID attribute value.
        """
        self.component_manager.scan_id = value
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_write

    def read_configID(self: FspCorrSubarray) -> str:
        # PROTECTED REGION ID(FspCorrSubarray.configID_read) ENABLED START #
        """
        Read the configID attribute.

        :return: the configID attribute.
        :rtype: str
        """
        return self.component_manager.config_id
        # PROTECTED REGION END #    //  FspCorrSubarray.configID_read

    def write_configID(self: FspCorrSubarray, value: str) -> None:
        # PROTECTED REGION ID(FspCorrSubarray.configID_write) ENABLED START #
        """
        Write the configID attribute.

        :param value: the configID attribute value.
        """
        self.component_manager.config_id = value
        # PROTECTED REGION END #    //  FspCorrSubarray.configID_write

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

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the FspCorrSubarray's On() command.
        """

        def do(
            self: FspCorrSubarray.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = (
                ResultCode.OK,
                "FspCorrSubarray On command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.ON)

            self.logger.info(message)
            return (result_code, message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the FspCorrSubarray's Off() command.
        """

        def do(
            self: FspCorrSubarray.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = (
                ResultCode.OK,
                "FspCorrSubarray Off command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.OFF)

            self.logger.info(message)
            return (result_code, message)

    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the FspCorrSubarray's Standby() command.
        """

        def do(
            self: FspCorrSubarray.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = (
                ResultCode.OK,
                "FspCorrSubarray Standby command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.STANDBY)

            self.logger.info(message)
            return (result_code, message)

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspCorrSubarray's ConfigureScan() command.
        """

        def do(
            self: FspCorrSubarray.ConfigureScanCommand, argin: str
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

            (result_code, message) = device.component_manager.configure_scan(
                argin
            )

            if result_code == ResultCode.OK:
                device._last_scan_configuration = argin
                device._component_configured(True)

            return (result_code, message)

        def validate_input(
            self: FspCorrSubarray.ConfigureScanCommand, argin: str
        ) -> Tuple[bool, str]:
            """
            Validate the configuration parameters against allowed values, as needed.

            :param argin: The JSON formatted string with configuration for the device.
                :type argin: 'DevString'
            :return: A tuple containing a boolean and a string message.
            :rtype: (bool, str)
            """
            try:
                json.loads(argin)
            except json.JSONDecodeError:
                msg = (
                    "Scan configuration object is not a valid JSON object."
                    " Aborting configuration."
                )
                return (False, msg)

            # TODO validate the fields

            return (True, "Configuration validated OK")

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out="A tuple containing a return code and a string message indicating status. "
        "The message is for information purpose only.",
    )
    @DebugIt()
    def ConfigureScan(self: FspCorrSubarray, argin: str) -> None:
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
        (valid, message) = command.validate_input(argin)
        if not valid:
            self.logger.error(message)
            tango.Except.throw_exception(
                "Command failed",
                message,
                "ConfigureScan" + " execution",
                tango.ErrSeverity.ERR,
            )
        else:
            if self._obs_state == ObsState.IDLE:
                self._configuring_from_idle = True
            else:
                self._configuring_from_idle = False

        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class ScanCommand(CspSubElementObsDevice.ScanCommand):
        """
        A class for the FspCorrSubarray's Scan() command.
        """

        def do(
            self: FspCorrSubarray.ScanCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :param argin: The scan ID
            :type argin: str

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            self.logger.debug("Entering ScanCommand()")

            device = self.target

            (result_code, message) = device.component_manager.scan(int(argin))

            if result_code == ResultCode.OK:
                device._component_scanning(True)

            return (result_code, message)

    class EndScanCommand(CspSubElementObsDevice.EndScanCommand):
        """
        A class for the FspCorrSubarray's Scan() command.
        """

        def do(
            self: FspCorrSubarray.EndScanCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            self.logger.debug("Entering EndScanCommand()")

            device = self.target

            (result_code, message) = device.component_manager.end_scan()

            if result_code == ResultCode.OK:
                device._component_scanning(False)

            return (result_code, message)

    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the FspCorrSubarray's GoToIdle command.
        """

        def do(
            self: FspCorrSubarray.GoToIdleCommand,
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

            (result_code, message) = device.component_manager.go_to_idle()

            if result_code == ResultCode.OK:
                device._component_configured(False)

            return (result_code, message)

    # TODO - currently not used
    def is_getLinkAndAddress_allowed(self: FspCorrSubarray) -> bool:
        """
        Determine if getLinkAndAddress is allowed
        (allowed if destination addresses are received,
        meaning outputLinkMap also received (checked in subarray validate scan)).

        :return: if getLinkAndAddress is allowed
        :rtype: bool
        """
        if self._vis_destination_address["outputHost"] == []:
            return False
        return True

    @command(
        dtype_in="DevULong",
        doc_in="channel ID",
        dtype_out="DevString",
        doc_out="output link and destination addresses in JSON",
    )
    def getLinkAndAddress(self: FspCorrSubarray, argin: int) -> str:
        # PROTECTED REGION ID(FspCorrSubarray.getLinkAndAddress) ENABLED START #
        """
        Get output link and destination addresses in JSON based on a channel ID.

        :param argin: the channel id.

        :return: the output link and destination addresses in JSON.
        :rtype: str
        """
        if argin < 0 or argin > 14479:
            msg = "channelID should be between 0 to 14479"
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "getLinkAndAddress",
                tango.ErrSeverity.ERR,
            )
            return

        result = {
            "outputLink": 0,
            "outputHost": "",
            "outputMac": "",
            "outputPort": 0,
        }
        # Get output link by finding the first element[1] that's greater than argin
        link = 0
        for element in self._output_link_map:
            if argin >= element[0]:
                link = element[1]
            else:
                break
        result["outputLink"] = link
        # Get 3 addresses by finding the first element[1] that's greater than argin
        host = ""
        for element in self._vis_destination_address["outputHost"]:
            if argin >= element[0]:
                host = element[1]
            else:
                break
        result["outputHost"] = host

        mac = ""
        for element in self._vis_destination_address["outputMac"]:
            if argin >= element[0]:
                mac = element[1]
            else:
                break
        result["outputMac"] = mac

        # Port is different. the array is given as [[start_channel, start_value, increment],[start_channel, start_value, increment],.....]
        # value = start_value + (channel - start_channel)*increment
        triple = []  # find the triple with correct start_value
        for element in self._vis_destination_address["outputPort"]:
            if argin >= element[0]:
                triple = element
            else:
                break

        result["outputPort"] = triple[1] + (argin - triple[0]) * triple[2]

        return str(result)

    # ----------
    # Callbacks
    # ----------

    def _component_configured(self: FspCorrSubarray, configured: bool) -> None:
        """
        Handle notification that the component has started or stopped configuring.

        This is callback hook.

        :param configured: whether this component is configured
        :type configured: bool
        """
        if configured:
            if self._configuring_from_idle:
                self.obs_state_model.perform_action("component_configured")
        else:
            self.obs_state_model.perform_action("component_unconfigured")

    def _component_scanning(self: FspCorrSubarray, scanning: bool) -> None:
        """
        Handle notification that the component has started or stopped scanning.

        This is a callback hook.

        :param scanning: whether this component is scanning
        :type scanning: bool
        """
        if scanning:
            self.obs_state_model.perform_action("component_scanning")
        else:
            self.obs_state_model.perform_action("component_not_scanning")

    def _component_fault(self: FspCorrSubarray, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state")

    def _component_obsfault(self: FspCorrSubarray) -> None:
        """
        Handle notification that the component has obsfaulted.

        This is a callback hook.
        """
        self.obs_state_model.perform_action("component_obsfault")

    def _communication_status_changed(
        self: FspCorrSubarray,
        communication_status: CommunicationStatus,
    ) -> None:
        """
        Handle change in communications status between component manager and component.

        This is a callback hook, called by the component manager when
        the communications status changes. It is implemented here to
        drive the op_state.

        :param communication_status: the status of communications
            between the component manager and its component.
        """

        self._communication_status = communication_status

        if communication_status == CommunicationStatus.DISABLED:
            self.op_state_model.perform_action("component_disconnected")
        elif communication_status == CommunicationStatus.NOT_ESTABLISHED:
            self.op_state_model.perform_action("component_unknown")

    def _component_power_mode_changed(
        self: FspCorrSubarray,
        power_mode: PowerMode,
    ) -> None:
        """
        Handle change in the power mode of the component.

        This is a callback hook, called by the component manager when
        the power mode of the component changes. It is implemented here
        to drive the op_state.

        :param power_mode: the power mode of the component.
        """
        self._component_power_mode = power_mode

        if self._communication_status == CommunicationStatus.ESTABLISHED:
            action_map = {
                PowerMode.OFF: "component_off",
                PowerMode.STANDBY: "component_standby",
                PowerMode.ON: "component_on",
                PowerMode.UNKNOWN: "component_unknown",
            }

            self.op_state_model.perform_action(action_map[power_mode])
        # PROTECTED REGION END #    //  FspCorrSubarray.getLinkAndAddress


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspCorrSubarray.main) ENABLED START #
    return run((FspCorrSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspCorrSubarray.main


if __name__ == "__main__":
    main()
