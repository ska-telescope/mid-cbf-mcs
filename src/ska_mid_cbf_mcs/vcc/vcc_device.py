# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
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

# Vcc TANGO device class

# PROTECTED REGION ID(Vcc.additional_import) ENABLED START #
from __future__ import annotations  # allow forward references in type hints
from typing import List, Tuple, Optional
import json

# Tango imports
import tango
from tango.server import run, attribute, command, device_property
from tango import AttrWriteType

# SKA imports
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.control_model import ObsState, SimulationMode, PowerMode
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_tango_base.csp.obs.obs_state_model import CspSubElementObsStateModel
from ska_tango_base.csp.obs.obs_device import CspSubElementObsDevice
from ska_tango_base.commands import ResultCode

# PROTECTED REGION END #    //  Vcc.additional_import

__all__ = ["Vcc", "main"]


class Vcc(CspSubElementObsDevice):
    """
    Vcc TANGO device class for the prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    VccID = device_property(
        dtype='DevUShort'
    )

    Band1And2Address = device_property(
        dtype='str'
    )

    Band3Address = device_property(
        dtype='str'
    )

    Band4Address = device_property(
        dtype='str'
    )

    Band5Address = device_property(
        dtype='str'
    )

    SW1Address = device_property(
        dtype='str'
    )

    SW2Address = device_property(
        dtype='str'
    )

    # ----------
    # Attributes
    # ----------

    receptorID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Receptor ID",
        doc="Receptor ID",
    )

    subarrayMembership = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="subarrayMembership",
        doc="Subarray membership",
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
        label="Frequency band offset (stream 1) (Hz)",
        doc="Frequency band offset (stream 1) (Hz)"
    )

    frequencyBandOffsetStream2 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="Frequency band offset (stream 2) (Hz)",
        doc="Frequency band offset (stream 2) (Hz)"
    )

    dopplerPhaseCorrection = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction coefficients",
        doc="Doppler phase correction coefficients"
    )

    rfiFlaggingMask = attribute(
        dtype='str',
        access=AttrWriteType.READ,
        label="RFI Flagging Mask",
        doc="RFI Flagging Mask"
    )

    scfoBand1 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="SCFO (band 1)",
        doc="Sample clock frequency offset for band 1",
    )

    scfoBand2 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="SCFO (band 2)",
        doc="Sample clock frequency offset for band 2",
    )

    scfoBand3 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="SCFO (band 3)",
        doc="Sample clock frequency offset for band 3",
    )

    scfoBand4 = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="SCFO (band 4)",
        doc="Sample clock frequency offset for band 4",
    )

    scfoBand5a = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="SCFO (band 5a)",
        doc="Sample clock frequency offset for band 5a",
    )

    scfoBand5b = attribute(
        dtype='int',
        access=AttrWriteType.READ,
        label="SCFO (band 5b)",
        doc="Sample clock frequency offset for band 5b",
    )

    delayModel = attribute(
        dtype=(('double',),),
        max_dim_x=6,
        max_dim_y=26,
        access=AttrWriteType.READ,
        label="Delay model coefficients",
        doc="Delay model coefficients, given per frequency slice"
    )

    jonesMatrix = attribute(
        dtype=(('double',),),
        max_dim_x=16,
        max_dim_y=26,
        access=AttrWriteType.READ,
        label='Jones Matrix elements',
        doc='Jones Matrix elements, given per frequency slice'
    )

    scanID = attribute(
        dtype='DevULong',
        access=AttrWriteType.READ_WRITE,
        label="scanID",
        doc="scan ID",
    )

    configID = attribute(
        dtype='DevString',
        access=AttrWriteType.READ,
        label="config ID",
        doc="config ID",
    )

    # ---------------
    # General methods
    # ---------------

    # PROTECTED REGION ID(Vcc.class_variable) ENABLED START #

    def init_command_objects(self: Vcc) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (
            self,
            self.op_state_model,
            self.logger
        )

        self.register_command_object(
            "On", self.OnCommand(*device_args)
        )

        self.register_command_object(
            "Off", self.OffCommand(*device_args)
        )

        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

        device_args = (
            self,
            self.op_state_model,
            self.obs_state_model,
            self.logger
        )

        self.register_command_object(
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )

        self.register_command_object(
            "Scan", self.ScanCommand(*device_args)
        )

        self.register_command_object(
            "EndScan", self.EndScanCommand(*device_args)
        )

        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

    # PROTECTED REGION END #    //  Vcc.class_variable

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the Vcc's On() command.
        """

        def do(            
            self: Vcc.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.target._component_power_mode_changed(PowerMode.ON)

            return (ResultCode.OK, "OnCommand completed OK")

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the Vcc's Off() command.
        """
        def do(
            self: Vcc.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            self.target._component_power_mode_changed(PowerMode.OFF)

            return (ResultCode.OK, "OffCommand completed OK")

    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the Vcc's Standby() command.
        """
        def do(            
            self: Vcc.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            self.target._component_power_mode_changed(PowerMode.STANDBY)

            return (ResultCode.OK, "StandbyCommand completed OK")

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the Vcc's init_device() "command".
        """

        def do(
            self: Vcc.InitCommand,
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

            # Make a private copy of the device properties:
            self._vcc_id = device.VccID

            # initialize attribute values
            device._subarray_membership = 0
            device._doppler_phase_correction = (0, 0, 0, 0)
            device._delay_model = [[0] * 6 for i in range(26)]
            device._jones_matrix = [[0] * 16 for i in range(26)]
            device._last_scan_configuration = ""

            device.set_change_event("subarrayMembership", True, True)

            return (ResultCode.OK, "Vcc Init command completed OK")


    def create_component_manager(self: Vcc):
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        self._simulation_mode = SimulationMode.FALSE

        self.component_manager = VccComponentManager(
            simulation_mode=self._simulation_mode,
            vcc_band=[
                self.Band1And2Address,
                self.Band3Address,
                self.Band4Address,
                self.Band5Address
            ],
            search_window=[self.SW1Address, self.SW2Address],
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            connect=True
        )

    def _communication_status_changed(
        self: Vcc,
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
        elif communication_status == CommunicationStatus.ESTABLISHED \
            and self._component_power_mode is not None:
            self._component_power_mode_changed(self._component_power_mode)
        else:  # self._component_power_mode is None
            pass  # wait for a power mode update
    
    def _component_power_mode_changed(
        self: Vcc,
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

    def always_executed_hook(self: Vcc) -> None:
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        if not self.component_manager.connected:
            self.component_manager.start_communicating()
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self: Vcc) -> None:
        # PROTECTED REGION ID(Vcc.delete_device) ENABLED START #
        """Hook to delete device."""
        pass
        # PROTECTED REGION END #    //  Vcc.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptorID(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.receptorID_read) ENABLED START #
        """
            Read the receptorID attribute.

            :return: the Vcc's receptor id.
            :rtype: int
        """
        return self.component_manager.receptor_id
        # PROTECTED REGION END #    //  Vcc.receptorID_read

    def write_receptorID(self: Vcc, value: int) -> None:
        # PROTECTED REGION ID(Vcc.receptorID_write) ENABLED START #
        """
            Write the receptorID attribute.

            :param value: the receptorID value.
        """
        self.component_manager.receptor_id = value
        # PROTECTED REGION END #    //  Vcc.receptorID_write

    def read_subarrayMembership(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.subarrayMembership_read) ENABLED START #
        """
            Read the subarrayMembership attribute.

            :return: the subarray membership (0 = no affiliation).
            :rtype: int
        """
        return self._subarray_membership
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_read

    def write_subarrayMembership(self: Vcc, value: int) -> None:
        # PROTECTED REGION ID(Vcc.subarrayMembership_write) ENABLED START #
        """
            Write the subarrayMembership attribute.

            :param value: the subarray membership value (0 = no affiliation).
        """
        self.logger.debug(f"Entering write_subarrayMembership(), value = {value}")
        self._subarray_membership = value
        self.push_change_event("subarrayMembership",value)
        if not value:
            self._update_obs_state(ObsState.IDLE)
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_write

    def read_frequencyBand(self: Vcc) -> tango.DevEnum:
        # PROTECTED REGION ID(Vcc.frequencyBand_read) ENABLED START #
        """
        Read the frequencyBand attribute.

        :return: the frequency band (being 
            :return: the frequency band (being 
        :return: the frequency band (being 
            observed by the current scan, one of 
                observed by the current scan, one of 
            observed by the current scan, one of 
            ["1", "2", "3", "4", "5a", "5b"]).
        :rtype: tango.DevEnum
        """
        return self.component_manager.frequency_band
        # PROTECTED REGION END #    //  Vcc.frequencyBand_read

    def read_band5Tuning(self: Vcc) -> List[float]:
        # PROTECTED REGION ID(Vcc.band5Tuning_read) ENABLED START #
        """
        Read the band5Tuning attribute.

        :return: the band5Tuning attribute (stream tuning (GHz)).
        :rtype: list of float
        """
        return self.component_manager.stream_tuning
        # PROTECTED REGION END #    //  Vcc.band5Tuning_read

    def read_frequencyBandOffsetStream1(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream1_read) ENABLED START #
        """
        Read the frequencyBandOffsetStream1 attribute.

        :return: the frequencyBandOffsetStream1 attribute.
        :rtype: int
        """
        return self.component_manager.frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream1_read

    def read_frequencyBandOffsetStream2(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream2_read) ENABLED START #
        """
        Read the frequencyBandOffsetStream2 attribute.

        :return: the frequencyBandOffsetStream2 attribute.
        :rtype: int
        """
        return self.component_manager.frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream2_read

    def read_dopplerPhaseCorrection(self: Vcc) -> List[float]:
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_read) ENABLED START #
        """
        Read the dopplerPhaseCorrection attribute.

        :return: the dopplerPhaseCorrection attribute.
        :rtype: list of float
        """
        return self._doppler_phase_correction
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_read

    def write_dopplerPhaseCorrection(self: Vcc, value: List[float]) -> None:
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_write) ENABLED START #
        """
        Write the dopplerPhaseCorrection attribute.

        :param value: the dopplerPhaseCorrection attribute value.
        """
        self._doppler_phase_correction = value
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_write

    def read_rfiFlaggingMask(self: Vcc) -> str:
        # PROTECTED REGION ID(Vcc.rfiFlaggingMask_read) ENABLED START #
        """
        Read the rfiFlaggingMask attribute.

        :return: the rfiFlaggingMask attribute.
        :rtype: str/JSON
        """
        return self.component_manager.rfi_flagging_mask
        # PROTECTED REGION END #    //  Vcc.rfiFlaggingMask_read

    def read_scfoBand1(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scfoBand1_read) ENABLED START #
        """
        Read the scfoBand1 attribute.

        :return: the scfoBand1 attribute (sample clock frequency 
            :return: the scfoBand1 attribute (sample clock frequency 
        :return: the scfoBand1 attribute (sample clock frequency 
            offset for band 1).
        :rtype: int
        """
        return self.component_manager.scfo_band_1
        # PROTECTED REGION END #    //  Vcc.scfoBand1_read

    def read_scfoBand2(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scfoBand2_read) ENABLED START #
        """
        Read the scfoBand2 attribute.

        :return: the scfoBand2 attribute (sample clock frequency 
            :return: the scfoBand2 attribute (sample clock frequency 
        :return: the scfoBand2 attribute (sample clock frequency 
            offset for band 2).
        :rtype: int
        """
        return self.component_manager.scfo_band_2
        # PROTECTED REGION END #    //  Vcc.scfoBand2_read

    def read_scfoBand3(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scfoBand3_read) ENABLED START #
        """
        Read the scfoBand3 attribute.

        :return: the scfoBand3 attribute (sample clock frequency 
            :return: the scfoBand3 attribute (sample clock frequency 
        :return: the scfoBand3 attribute (sample clock frequency 
            offset for band 3).
        :rtype: int
        """      
        return self.component_manager.scfo_band_3
        # PROTECTED REGION END #    //  Vcc.scfoBand3_read

    def read_scfoBand4(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scfoBand4_read) ENABLED START #
        """
        Read the scfoBand4 attribute.

        :return: the scfoBand4 attribute (sample clock frequency 
            :return: the scfoBand4 attribute (sample clock frequency 
        :return: the scfoBand4 attribute (sample clock frequency 
            offset for band 4).
        :rtype: int
        """      
        return self.component_manager.scfo_band_4
        # PROTECTED REGION END #    //  Vcc.scfoBand4_read

    def read_scfoBand5a(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scfoBand5a_read) ENABLED START #
        """
        Read the scfoBand5a attribute.

        :return: the scfoBand5a attribute (sample clock frequency 
            :return: the scfoBand5a attribute (sample clock frequency 
        :return: the scfoBand5a attribute (sample clock frequency 
            offset for band 5a).
        :rtype: int
        """     
        return self.component_manager.scfo_band_5a
        # PROTECTED REGION END #    //  Vcc.scfoBand5a_read

    def read_scfoBand5b(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scfoBand5b_read) ENABLED START #
        """
        Read the scfoBand5b attribute.

        :return: the scfoBand5b attribute (sample clock frequency 
            :return: the scfoBand5b attribute (sample clock frequency 
        :return: the scfoBand5b attribute (sample clock frequency 
            offset for band 5b.
        :rtype: int
        """      
        return self.component_manager.scfo_band_5b
        # PROTECTED REGION END #    //  Vcc.scfoBand5b_read

    def read_delayModel(self: Vcc) -> List[List[float]]:
        # PROTECTED REGION ID(Vcc.delayModel_read) ENABLED START #
        """
        Read the delayModel attribute.

        :return: the delayModel attribute (delay model coefficients, 
            :return: the delayModel attribute (delay model coefficients, 
        :return: the delayModel attribute (delay model coefficients, 
            given per frequency slice).
        :rtype: list of list of float
        """
        return self._delay_model
        # PROTECTED REGION END #    //  Vcc.delayModel_read

    def read_jonesMatrix(self: Vcc) -> List[List[float]]:
        # PROTECTED REGION ID(Vcc.jonesMatrix_read) ENABLED START #
        """
        Read the jonesMatrix attribute.

        :return: the jonesMatrix attribute (jones matrix values, 
            :return: the jonesMatrix attribute (jones matrix values, 
        :return: the jonesMatrix attribute (jones matrix values, 
            given per frequency slice).
        :rtype: list of list of float
        """
        return self._jones_matrix
        # PROTECTED REGION END #    //  Vcc.jonesMatrix_read

    def read_scanID(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.scanID_read) ENABLED START #
        """
        Read the scanID attribute.

        :return: the scanID attribute.
        :rtype: int
        """
        return self.component_manager.scan_id
        # PROTECTED REGION END #    //  Vcc.scanID_read

    def write_scanID(self: Vcc, value: int) -> None:
        # PROTECTED REGION ID(Vcc.scanID_write) ENABLED START #
        """
        Write the scanID attribute.

        :param value: the scanID value.
        """
        self.component_manager.scan_id = value
        # PROTECTED REGION END #    //  Vcc.scanID_write

    def read_configID(self: Vcc) -> str:
        # PROTECTED REGION ID(Vcc.configID_read) ENABLED START #
        """
        Read the configID attribute.

        :return: the configID attribute.
        :rtype: str
        """
        return self.component_manager.config_id
        # PROTECTED REGION END #    //  Vcc.configID_read

    # --------
    # Commands
    # --------

    @command(
        dtype_in='str',
        doc_in="Frequency band name"
    )
    def TurnOnBandDevice(self: Vcc, freq_band_name: str) -> Tuple[ResultCode, str]:
        """
        Turn on the corresponding band device and disable all the others.

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.info("Vcc.TurnOnBandDevice")
        return self.component_manager.turn_on_band_device(freq_band_name)
    
    @command(
        dtype_in='str',
        doc_in="Frequency band name"
    )
    def TurnOffBandDevice(self: Vcc, freq_band_name: str) -> Tuple[ResultCode, str]:
        """
        Send OFF signal to the corresponding band

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.info("Vcc.TurnOffBandDevice")
        return self.component_manager.turn_off_band_device(freq_band_name)


    def _deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self.logger.debug("Vcc deconfiguring")

        self.component_manager.deconfigure()

        self._jones_matrix = [[0] * 16 for i in range(26)]
        self._delay_model = [[0] * 6 for i in range(26)]
        self._doppler_phase_correction = (0, 0, 0, 0)


    def _raise_configuration_fatal_error(
        self: Vcc, 
        msg: str,
        cmd: str
    ) -> None:
        """
        Throw an error message if ConfigureScan/ConfigureSearchWindow fails

        :param msg: the error message
        ::param cmd: the failed command
        """
        self.logger.error(msg)
        tango.Except.throw_exception("Command failed", msg, cmd + " execution",
                                    tango.ErrSeverity.ERR)


    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the Vcc's ConfigureScan() command.
        """

        def do(
            self: Vcc.ConfigureScanCommand,
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
            device = self.target
            # By this time, the receptor_ID should be set:
            self.logger.debug(("receptorID = {}".
            format(device.component_manager.receptor_id)))

            # This validation is already performed in the CbfSubarray ConfigureScan.
            # TODO: Improve validation (validation should only be done once,
            # most of the validation can be done through a schema instead of manually
            # through functions).

            (valid, msg) = self._validate_scan_configuration(argin)
            if not valid:
                device._raise_configuration_fatal_error(msg, "ConfigureScan")

            device._deconfigure()

            (result_code, msg) = device.component_manager.configure_scan(argin)

            if result_code == ResultCode.OK:
                # store the configuration on command success
                device._last_scan_configuration = argin
                msg = "Configure command completed OK"

            device.obs_state_model.perform_action("component_configured")

            return(result_code, msg)

        def _validate_scan_configuration(
            self: Vcc.ConfigureScanCommand, 
            argin: str
            ) -> Tuple[bool, str]:
            """
                Validate the configuration parameters against allowed values, as needed.

                :param argin: The JSON formatted string with configuration for the device.
                    :type argin: 'DevString'
                :return: A tuple containing a boolean and a string message.
                :rtype: (bool, str)
            """
            try:
                configuration = json.loads(argin)
            except json.JSONDecodeError:
                msg = "Scan configuration object is not a valid JSON object." \
                " Aborting configuration."
                return (False, msg)

            # Validate config_id.
            if "config_id" not in configuration:
                msg = "'configID' attribute is required."
                return (False, msg)
            
            # Validate frequency_band.
            if "frequency_band" not in configuration:
                msg = "'frequencyBand' attribute is required."
                return (False, msg)
            
            # Validate frequency_band_offset_stream_1.
            if "frequency_band_offset_stream_1" not in configuration:
                configuration["frequency_band_offset_stream_1"] = 0
            if abs(int(configuration["frequency_band_offset_stream_1"])) <= \
                const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream1' must be at " \
                    "most half of the frequency slice bandwidth. Aborting configuration."
                return (False, msg)

            # Validate frequency_band_offset_stream_2.
            if "frequency_band_offset_stream_2" not in configuration:
                configuration["frequency_band_offset_stream_2"] = 0
            if abs(int(configuration["frequency_band_offset_stream_2"])) <= \
                const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream2' must be at " \
                    "most half of the frequency slice bandwidth. Aborting configuration."
                return (False, msg)
            
            # Validate frequency_band.
            valid_freq_bands = ["1", "2", "3", "4", "5a", "5b"]
            if configuration["frequency_band"] not in valid_freq_bands:
                msg = configuration["frequency_band"] + \
                    " not a valid frequency band. Aborting configuration."
                return (False, msg)

            # Validate band_5_tuning, frequency_band_offset_stream_2
            # if frequency_band is 5a or 5b.
            if configuration["frequency_band"] in ["5a", "5b"]:
                # band_5_tuning is optional
                if "band_5_tuning" in configuration:
                    pass
                    # check if stream_tuning is an array of length 2
                    try:
                        assert len(configuration["band_5_tuning"]) == 2
                    except (TypeError, AssertionError):
                        msg = "'band_5_tuning' must be an array of length 2. Aborting configuration."
                        return (False, msg)

                    stream_tuning = [*map(float, configuration["band_5_tuning"])]
                    if configuration["frequency_band"] == "5a":
                        if all(
                                [const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0] <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1] for i in [0, 1]]
                        ):
                            pass
                        else:
                            msg = "Elements in 'band_5_tuning must be floats between " + \
                                f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0]} and " + \
                                f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1]} " + \
                                f"(received {stream_tuning[0]} and {stream_tuning[1]})" + \
                                " for a 'frequencyBand' of 5a. Aborting configuration."
                            return (False, msg)
                    else:  # configuration["frequency_band"] == "5b"
                        if all(
                                [const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0] <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1] for i in [0, 1]]
                        ):
                            pass
                        else:
                            msg = "Elements in 'band_5_tuning must be floats between " + \
                                f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0]} and " + \
                                f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1]} " + \
                                f"(received {stream_tuning[0]} and {stream_tuning[1]})" + \
                                " for a 'frequencyBand' of 5b. Aborting configuration."
                            return (False, msg)
            
            return (True, "Configuration validated OK")

    @command(
        dtype_in='DevString',
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out='DevVarLongStringArray',
        doc_out="A tuple containing a return code and a string message indicating status. "
                "The message is for information purpose only.",
    )
    def ConfigureScan(
        self: Vcc, 
        argin: str
        ) -> Tuple[ResultCode, str]:
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
        # PROTECTED REGION END #    //  Vcc.ConfigureScan


    class ScanCommand(CspSubElementObsDevice.ScanCommand):
        """
        A class for the Vcc's Scan() command.
        """

        def do(
            self: Vcc.ScanCommand,
            argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :param argin: The scan ID as JSON formatted string
            :type argin: str

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            device = self.target
            (result_code, msg) = device.component_manager.scan(int(argin))

            device.obs_state_model.perform_action("component_scanning")

            return(result_code, msg)


    class EndScanCommand(CspSubElementObsDevice.EndScanCommand):
        """
        A class for the Vcc's EndScan() command.
        """
        def do(self: Vcc.EndScanCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for EndScan() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            (result_code, msg) = device.component_manager.end_scan()

            device.obs_state_model.perform_action("component_not_scanning")

            return(result_code, msg)


    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the Vcc's GoToIdle command.
        """

        def do(
            self: Vcc.GoToIdleCommand,
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

            # Reset all values intialized in InitCommand.do():
            device._deconfigure()

            if device._obs_state == ObsState.IDLE:
                return (ResultCode.OK, 
                "GoToIdle command completed OK. Device already IDLE")

            device.obs_state_model.perform_action("component_unconfigured")

            return (ResultCode.OK, "GoToIdle command completed OK")


    def is_UpdateDelayModel_allowed(self: Vcc) -> bool:
        """
        Determine if UpdateDelayModel is allowed
        (allowed when Devstate is ON and ObsState is READY OR SCANNING).

        :return: if UpdateDelayModel is allowed
        :rtype: bool
        """
        self.logger.debug("Entering is_UpdateDelayModel_allowed()")
        self.logger.debug(f"self.dev_state(): {self.dev_state()}")
        if self.get_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.READY, ObsState.SCANNING]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Delay model, given per frequency slice"
    )
    def UpdateDelayModel(
        self: Vcc, 
        argin: str
        ) -> None:
        # PROTECTED REGION ID(Vcc.UpdateDelayModel) ENABLED START #
        """
        Update Vcc's delay model

        :param argin: the delay model JSON
        """

        self.logger.debug("Entering UpdateDelayModel()")
        argin = json.loads(argin)

        self.logger.debug(("receptor_ID = {}".
            format(self.component_manager.receptor_id)))

        for delayDetails in argin:
            self.logger.debug(("delayDetails[receptor] = {}".
            format(delayDetails["receptor"])))

            if delayDetails["receptor"] != self.component_manager.receptor_id:
                continue
            for frequency_slice in delayDetails["receptorDelayDetails"]:
                fsid = frequency_slice["fsid"]
                if 1 <= fsid <= 26:
                    if len(frequency_slice["delayCoeff"]) == 6:
                        self._delay_model[fsid - 1] = \
                            frequency_slice["delayCoeff"]
                    else:
                        log_msg = "'delayCoeff' not valid for frequency slice " + \
                            f"{fsid} of receptor {self.component_manager.receptor_id}"
                        self.logger.error(log_msg)
                else:
                    log_msg = f"'fsid' {fsid} not valid for receptor {self.component_manager.receptor_id}"
                    self.logger.error(log_msg)
        # PROTECTED REGION END #    // Vcc.UpdateDelayModel


    def is_UpdateJonesMatrix_allowed(self: Vcc) -> bool:
        """
            Determine if UpdateJonesMatrix is allowed
            (allowed when Devstate is ON and ObsState is READY OR SCANNING).

            :return: if UpdateJonesMatrix is allowed
            :rtype: bool
        """
        if self.get_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.READY, ObsState.SCANNING]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Jones Matrix, given per frequency slice"
    )
    def UpdateJonesMatrix(
        self: Vcc, 
        argin: str
        ) -> None:
        # PROTECTED REGION ID(Vcc.UpdateJonesMatrix) ENABLED START #
        self.logger.debug("Vcc.UpdateJonesMatrix")
        """
        Update Vcc's jones matrix

        :param argin: the jones matrix JSON
        """

        argin = json.loads(argin)

        for receptor in argin:
            if receptor["receptor"] == self.component_manager.receptor_id:
                for frequency_slice in receptor["receptorMatrix"]:
                    fs_id = frequency_slice["fsid"]
                    matrix = frequency_slice["matrix"]
                    if 1 <= fs_id <= 26:
                        if len(matrix) == 16:
                            self._jones_matrix[fs_id-1] = matrix.copy()
                        else:
                            log_msg = f"'matrix' not valid for frequency slice {fs_id} " + \
                                      f" of receptor {self.component_manager.receptor_id}"
                            self.logger.error(log_msg)
                    else:
                        log_msg = f"'fsid' {fs_id} not valid for receptor {self.component_manager.receptor_id}"
                        self.logger.error(log_msg)
        # PROTECTED REGION END #    // Vcc.UpdateJonesMatrix


    def is_ValidateSearchWindow_allowed(self: Vcc) -> bool:
        """
        Determine if ValidateSearchWindow is allowed

        :return: if ValidateSearchWindow is allowed
        :rtype: bool
        """
        # This command has no constraints:
        return True

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ValidateSearchWindow(
        self: Vcc, 
        argin: str
    ) -> None:
        """
        Validate a search window configuration

        :param argin: JSON object with the search window parameters
        """
        # try to deserialize input string to a JSON object

        self.logger.debug("Entering ValidateSearchWindow()")

        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Search window configuration object is not a valid JSON object."
            self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")

        # Validate searchWindowID.
        if "search_window_id" in argin:
            sw_id = argin["search_window_id"]
            if sw_id in [1, 2]:
                pass
            else:  # searchWindowID not in valid range
                msg = f"'search_window_id' must be one of [1, 2] (received {sw_id})."
                self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")
        else:
            msg = "Search window specified, but 'search_window_id' not given."
            self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")

        # Validate searchWindowTuning.
        if "search_window_tuning" in argin:
            freq_band_name = argin["frequency_band"]
            if freq_band_name not in ["5a", "5b"]:  # frequency band is not band 5
                
                frequencyBand_mi = freq_band_dict()[freq_band_name]
                
                frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(argin["frequency_band"])

                assert frequencyBand_mi == frequencyBand
                
                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ
                ][frequencyBand]

                self.logger.debug(f"start_freq_Hz = {start_freq_Hz}")
                self.logger.debug(f"stop_freq_Hz = {stop_freq_Hz}")

                if start_freq_Hz + argin["frequency_band_offset_stream_1"] <= \
                        int(argin["search_window_tuning"]) <= \
                        stop_freq_Hz + argin["frequency_band_offset_stream_1"]:
                    pass
                else:
                    msg = "'search_window_tuning' must be within observed band."
                    self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                if argin["band_5_tuning"] == [0,0]: # band 5 tuning not specified in configuration
                    pass
                else:
                    frequency_band_range_1 = (
                        argin["band_5_tuning"][0] * 10 ** 9 + argin["frequency_band_offset_stream_1"] - \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                        argin["band_5_tuning"][0] * 10 ** 9 + argin["frequency_band_offset_stream_1"] + \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                    )

                    frequency_band_range_2 = (
                        argin["band_5_tuning"][1] * 10 ** 9 + argin["frequency_band_offset_stream_2"] - \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                        argin["band_5_tuning"][1] * 10 ** 9 + argin["frequency_band_offset_stream_2"] + \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                    )

                    if (frequency_band_range_1[0] <= \
                        int(argin["search_window_tuning"]) <= \
                        frequency_band_range_1[1]) or \
                            (frequency_band_range_2[0] <= \
                            int(argin["search_window_tuning"]) <= \
                            frequency_band_range_2[1]):
                        pass
                    else:
                        msg = "'searchWindowTuning' must be within observed band."
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg,
                                                    "ConfigureSearchWindow execution",
                                                    tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'search_window_tuning' not given."
            self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")

        # Validate tdcEnable.
        if "tdc_enable" in argin:
            if argin["tdc_enable"] in [True, False]:
                pass
            else:
                msg = "Search window specified, but 'tdc_enable' not given."
                self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")
        else:
            msg = "Search window specified, but 'tdc_enable' not given."
            self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")

        # Validate tdcNumBits.
        if argin["tdc_enable"]:
            if "tdc_num_bits" in argin:
                tdc_num_bits = argin["tdc_num_bits"]
                if tdc_num_bits in [2, 4, 8]:
                    pass
                else:
                    msg = f"'tdcNumBits' must be one of [2, 4, 8] (received {tdc_num_bits})."
                    self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")
            else:
                msg = "Search window specified with TDC enabled, but 'tdcNumBits' not given."
                self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")

        # Validate tdcPeriodBeforeEpoch.
        if "tdc_period_before_epoch" in argin:
            tdc_pbe = argin["tdc_period_before_epoch"]
            if tdc_pbe > 0:
                pass
            else:
                msg = f"'tdcPeriodBeforeEpoch' must be a positive integer (received {tdc_pbe})."
                self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")
        else:
            pass

        # Validate tdcPeriodAfterEpoch.
        if "tdc_period_after_epoch" in argin:
            tdc_pae = argin["tdc_period_after_epoch"]
            if tdc_pae > 0:
                pass
            else:
                msg = f"'tdcPeriodAfterEpoch' must be a positive integer (received {tdc_pae})."
                self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")
        else:
            pass

        # Validate tdcDestinationAddress.
        if argin["tdc_enable"]:
            try:
                for receptor in argin["tdc_destination_address"]:
                    if int(receptor["receptor_id"]) == self.component_manager.receptor_id:
                    # TODO: validate input
                        pass
                    else:  # receptorID not found
                        pass
            except KeyError:
                # tdcDestinationAddress not given or receptorID not in tdcDestinationAddress
                msg = "Search window specified with TDC enabled, but 'tdcDestinationAddress' " \
                      "not given or missing receptors."
                self._raise_configuration_fatal_error(msg, "ConfigureSearchWindow")


    def is_ConfigureSearchWindow_allowed(self: Vcc) -> bool:
        """
        Determine if ConfigureSearchWindow is allowed 
        (allowed if DevState is ON and ObsState is CONFIGURING)

        :return: if ConfigureSearchWindow is allowed
        :rtype: bool
        """
        if self.get_state() == tango.DevState.ON and \
            (self._obs_state == ObsState.CONFIGURING or \
            self._obs_state == ObsState.READY):
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ConfigureSearchWindow(
        self: Vcc, 
        argin: str
    ) -> Tuple[ResultCode, str]:
        # PROTECTED REGION ID(Vcc.ConfigureSearchWindow) ENABLED START #
        """
        Configure a search window by sending parameters from the input(JSON) to SearchWindow device. 
            This function is called by the subarray after the configuration has already been validated, 
            so the checks here have been removed to reduce overhead.

        :param argin: JSON object with the search window parameters

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.info("Entering ConfigureSearchWindow()")
        return self.component_manager.configure_search_window(argin)

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main

if __name__ == '__main__':
    main()