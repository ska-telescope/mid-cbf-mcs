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

import json
from typing import List, Optional, Tuple

# Tango imports
import tango
from ska_tango_base.commands import BaseCommand, ResponseCommand, ResultCode
from ska_tango_base.control_model import ObsState, PowerMode, SimulationMode
from ska_tango_base.csp.obs.obs_device import CspSubElementObsDevice
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

# SKA imports
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager

# PROTECTED REGION END #    //  Vcc.additional_import

__all__ = ["Vcc", "main"]


class Vcc(CspSubElementObsDevice):
    """
    Vcc TANGO device class for the prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    VccID = device_property(dtype="DevUShort")

    TalonLRUAddress = device_property(dtype="str")

    VccControllerAddress = device_property(dtype="str")

    Band1And2Address = device_property(dtype="str")

    Band3Address = device_property(dtype="str")

    Band4Address = device_property(dtype="str")

    Band5Address = device_property(dtype="str")

    SW1Address = device_property(dtype="str")

    SW2Address = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    receptorID = attribute(
        dtype="uint16",
        access=AttrWriteType.READ_WRITE,
        label="Receptor ID",
        doc="Receptor ID",
    )

    subarrayMembership = attribute(
        dtype="uint16",
        access=AttrWriteType.READ_WRITE,
        label="subarrayMembership",
        doc="Subarray membership",
    )

    frequencyOffsetK = attribute(
        dtype="int",
        access=AttrWriteType.READ_WRITE,
        label="Frequency offset (k)",
        doc="Frequency offset (k) of this receptor",
    )

    frequencyOffsetDeltaF = attribute(
        dtype="int",
        access=AttrWriteType.READ_WRITE,
        label="Frequency offset (delta f)",
        doc="Frequency offset (delta f) of this receptor",
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
        label="Frequency band offset (stream 1) (Hz)",
        doc="Frequency band offset (stream 1) (Hz)",
    )

    frequencyBandOffsetStream2 = attribute(
        dtype="int",
        access=AttrWriteType.READ,
        label="Frequency band offset (stream 2) (Hz)",
        doc="Frequency band offset (stream 2) (Hz)",
    )

    dopplerPhaseCorrection = attribute(
        dtype=("float",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction coefficients",
        doc="Doppler phase correction coefficients",
    )

    rfiFlaggingMask = attribute(
        dtype="str",
        access=AttrWriteType.READ,
        label="RFI Flagging Mask",
        doc="RFI Flagging Mask",
    )

    delayModel = attribute(
        dtype="str",
        access=AttrWriteType.READ,
        label="Delay model coefficients",
        doc="Delay model coefficients, given per frequency slice",
    )

    jonesMatrix = attribute(
        dtype=str,
        access=AttrWriteType.READ,
        label="Jones Matrix elements",
        doc="Jones Matrix elements, given per frequency slice",
    )

    scanID = attribute(
        dtype="DevULong",
        access=AttrWriteType.READ,
        label="scanID",
        doc="scan ID",
    )

    configID = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        label="config ID",
        doc="config ID",
    )

    simulationMode = attribute(
        dtype=SimulationMode,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        doc="Reports the simulation mode of the device. \nSome devices may implement "
        "both modes, while others will have simulators that set simulationMode "
        "to True while the real devices always set simulationMode to False.",
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

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object("On", self.OnCommand(*device_args))

        self.register_command_object("Off", self.OffCommand(*device_args))

        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

        self.register_command_object(
            "ConfigureBand", self.ConfigureBandCommand(*device_args)
        )

        self.register_command_object(
            "UpdateDopplerPhaseCorrection",
            self.UpdateDopplerPhaseCorrectionCommand(*device_args),
        )

        self.register_command_object(
            "UpdateDelayModel", self.UpdateDelayModelCommand(*device_args)
        )

        self.register_command_object(
            "UpdateJonesMatrix", self.UpdateJonesMatrixCommand(*device_args)
        )

        self.register_command_object(
            "ConfigureSearchWindow",
            self.ConfigureSearchWindowCommand(*device_args),
        )

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

        self.register_command_object("Abort", self.AbortCommand(*device_args))

        self.register_command_object(
            "ObsReset", self.ObsResetCommand(*device_args)
        )

        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

    # PROTECTED REGION END #    //  Vcc.class_variable

    def create_component_manager(self: Vcc) -> VccComponentManager:
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return VccComponentManager(
            talon_lru=self.TalonLRUAddress,
            vcc_controller=self.VccControllerAddress,
            vcc_band=[
                self.Band1And2Address,
                self.Band3Address,
                self.Band4Address,
                self.Band5Address,
            ],
            search_window=[self.SW1Address, self.SW2Address],
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )

    def always_executed_hook(self: Vcc) -> None:
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self: Vcc) -> None:
        # PROTECTED REGION ID(Vcc.delete_device) ENABLED START #
        """Hook to delete device."""
        # PROTECTED REGION END #    //  Vcc.delete_device

    # ---------
    # Callbacks
    # ---------

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
        elif (
            communication_status == CommunicationStatus.ESTABLISHED
            and self._component_power_mode is not None
        ):
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

    def _component_fault(self: Vcc, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")

    # ------------------
    # Attributes methods
    # ------------------

    def write_simulationMode(self: Vcc, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        super().write_simulationMode(value)
        self.component_manager.simulation_mode = value

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
        self.logger.debug(
            f"Entering write_subarrayMembership(), value = {value}"
        )
        self._subarray_membership = value
        self.push_change_event("subarrayMembership", value)
        self.component_manager.deconfigure()
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_write

    def read_frequencyOffsetK(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.frequencyOffsetK_read) ENABLED START #
        """
        Read the frequencyOffsetK attribute.

        :return: the frequency offset k-value
        :rtype: int
        """
        return self.component_manager.frequency_offset_k
        # PROTECTED REGION END #    //  Vcc.frequencyOffsetK_read

    def write_frequencyOffsetK(self: Vcc, value: int) -> None:
        # PROTECTED REGION ID(Vcc.frequencyOffsetK_write) ENABLED START #
        """
        Write the frequencyOffsetK attribute.

        :param value: the frequency offset k-value
        """
        self.component_manager.frequency_offset_k = value
        # PROTECTED REGION END #    //  Vcc.frequencyOffsetK_write

    def read_frequencyOffsetDeltaF(self: Vcc) -> int:
        # PROTECTED REGION ID(Vcc.frequencyOffsetDeltaF_read) ENABLED START #
        """
        Read the frequencyOffsetDeltaF attribute.

        :return: the frequency offset delta-f value
        :rtype: int
        """
        return self.component_manager.frequency_offset_delta_f
        # PROTECTED REGION END #    //  Vcc.frequencyOffsetDeltaF_read

    def write_frequencyOffsetDeltaF(self: Vcc, value: int) -> None:
        # PROTECTED REGION ID(Vcc.frequencyOffsetDeltaF_write) ENABLED START #
        """
        Write the frequencyOffsetDeltaF attribute.

        :param value: the frequency offset delta-f value
        """
        self.component_manager.frequency_offset_delta_f = value
        # PROTECTED REGION END #    //  Vcc.frequencyOffsetDeltaF_write

    def read_frequencyBand(self: Vcc) -> tango.DevEnum:
        # PROTECTED REGION ID(Vcc.frequencyBand_read) ENABLED START #
        """
        Read the frequencyBand attribute.

        :return: the frequency band (being observed by the current scan, one of
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
        return self.component_manager.doppler_phase_correction
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_read

    def write_dopplerPhaseCorrection(self: Vcc, value: List[float]) -> None:
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_write) ENABLED START #
        """
        Write the dopplerPhaseCorrection attribute.

        :param value: the dopplerPhaseCorrection attribute value.
        """
        self.component_manager.doppler_phase_correction = value
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

    def read_delayModel(self: Vcc) -> str:
        # PROTECTED REGION ID(Vcc.delayModel_read) ENABLED START #
        """
        Read the delayModel attribute.

        :return: the delayModel attribute (delay model coefficients,
            :return: the delayModel attribute (delay model coefficients,
        :return: the delayModel attribute (delay model coefficients,
            given per frequency slice).
        :rtype: list of list of float
        """
        return self.component_manager.delay_model
        # PROTECTED REGION END #    //  Vcc.delayModel_read

    def read_jonesMatrix(self: Vcc) -> str:
        # PROTECTED REGION ID(Vcc.jonesMatrix_read) ENABLED START #
        """
        Read the jonesMatrix attribute.

        :return: the jonesMatrix attribute (jones matrix values,
            given per frequency slice).
        :rtype: str
        """
        return self.component_manager.jones_matrix
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

            (result_code, msg) = super().do()

            device = self.target

            # Make a private copy of the device properties:
            device._vcc_id = device.VccID

            # initialize attribute values
            device._subarray_membership = 0
            device._last_scan_configuration = ""

            device._configuring_from_idle = False

            device.write_simulationMode(True)

            device.set_change_event("subarrayMembership", True, True)

            return (result_code, msg)

    class OnCommand(CspSubElementObsDevice.OnCommand):
        """
        A class for the Vcc's on command.
        """

        def do(
            self: Vcc.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            self.logger.info("Entering Vcc.OnCommand")
            return self.target.component_manager.on()

    class OffCommand(CspSubElementObsDevice.OffCommand):
        """
        A class for the Vcc's off command.
        """

        def do(
            self: Vcc.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.target.component_manager.off()

    class StandbyCommand(CspSubElementObsDevice.StandbyCommand):
        """
        A class for the Vcc's standby command.
        """

        def do(
            self: Vcc.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.target.component_manager.standby()

    class ConfigureBandCommand(ResponseCommand):
        """
        A class for the Vcc's ConfigureBand() command.

        Turn on the corresponding band device and disable all the others.
        """

        def do(
            self: Vcc.ConfigureBandCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureBand() command functionality.

            :param freq_band_name: the frequency band name

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.target.component_manager.configure_band(argin)

    @command(
        dtype_in="DevString",
        doc_in="Frequency band string.",
    )
    @DebugIt()
    def ConfigureBand(self, freq_band_name: str) -> Tuple[ResultCode, str]:
        # PROTECTED REGION ID(CspSubElementObsDevice.ConfigureBand) ENABLED START #
        """
        Turn on the corresponding band device and disable all the others.

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("ConfigureBand")
        (result_code, message) = command(freq_band_name)
        return [[result_code], [message]]
        # PROTECTED REGION END #    //  CspSubElementObsDevice.ConfigureBand

    def _raise_configuration_fatal_error(
        self: Vcc, msg: str, cmd: str
    ) -> None:
        """
        Throw an error message if ConfigureScan/ConfigureSearchWindow fails

        :param msg: the error message
        ::param cmd: the failed command
        """
        self.logger.error(msg)
        tango.Except.throw_exception(
            "Command failed", msg, cmd + " execution", tango.ErrSeverity.ERR
        )

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the Vcc's ConfigureScan() command.
        """

        def do(
            self: Vcc.ConfigureScanCommand, argin: str
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
            device.logger.debug(
                f"receptorID: {device.component_manager.receptor_id}"
            )

            (result_code, msg) = device.component_manager.configure_scan(argin)

            if result_code == ResultCode.OK:
                # store the configuration on command success
                device._last_scan_configuration = argin
                if device._configuring_from_idle:
                    device.obs_state_model.perform_action(
                        "component_configured"
                    )

            return (result_code, msg)

        def validate_input(
            self: Vcc.ConfigureScanCommand, argin: str
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
                msg = (
                    "Scan configuration object is not a valid JSON object."
                    " Aborting configuration."
                )
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
            if (
                abs(int(configuration["frequency_band_offset_stream_1"]))
                <= const.FREQUENCY_SLICE_BW * 10**6 / 2
            ):
                pass
            else:
                msg = (
                    "Absolute value of 'frequencyBandOffsetStream1' must be at "
                    "most half of the frequency slice bandwidth. Aborting configuration."
                )
                return (False, msg)

            # Validate frequency_band_offset_stream_2.
            if "frequency_band_offset_stream_2" not in configuration:
                configuration["frequency_band_offset_stream_2"] = 0
            if (
                abs(int(configuration["frequency_band_offset_stream_2"]))
                <= const.FREQUENCY_SLICE_BW * 10**6 / 2
            ):
                pass
            else:
                msg = (
                    "Absolute value of 'frequencyBandOffsetStream2' must be at "
                    "most half of the frequency slice bandwidth. Aborting configuration."
                )
                return (False, msg)

            # Validate frequency_band.
            valid_freq_bands = ["1", "2", "3", "4", "5a", "5b"]
            if configuration["frequency_band"] not in valid_freq_bands:
                msg = (
                    configuration["frequency_band"]
                    + " not a valid frequency band. Aborting configuration."
                )
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

                    stream_tuning = [
                        *map(float, configuration["band_5_tuning"])
                    ]
                    if configuration["frequency_band"] == "5a":
                        if all(
                            [
                                const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0]
                                <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1]
                                for i in [0, 1]
                            ]
                        ):
                            pass
                        else:
                            msg = (
                                "Elements in 'band_5_tuning must be floats between "
                                + f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0]} and "
                                + f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1]} "
                                + f"(received {stream_tuning[0]} and {stream_tuning[1]})"
                                + " for a 'frequencyBand' of 5a. Aborting configuration."
                            )
                            return (False, msg)
                    else:  # configuration["frequency_band"] == "5b"
                        if all(
                            [
                                const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0]
                                <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1]
                                for i in [0, 1]
                            ]
                        ):
                            pass
                        else:
                            msg = (
                                "Elements in 'band_5_tuning must be floats between "
                                + f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0]} and "
                                + f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1]} "
                                + f"(received {stream_tuning[0]} and {stream_tuning[1]})"
                                + " for a 'frequencyBand' of 5b. Aborting configuration."
                            )
                            return (False, msg)

            return (True, "Configuration validated OK")

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out="A tuple containing a return code and a string message indicating status. "
        "The message is for information purpose only.",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(CspSubElementObsDevice.ConfigureScan) ENABLED START #
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.
        :type argin: 'DevString'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        # This validation is already performed in the CbfSubarray ConfigureScan.
        # TODO: Improve validation (validation should only be done once,
        # most of the validation can be done through a schema instead of manually
        # through functions).
        command = self.get_command_object("ConfigureScan")

        (valid, message) = command.validate_input(argin)
        if not valid:
            self._raise_configuration_fatal_error(message, "ConfigureScan")
        else:
            if self._obs_state == ObsState.IDLE:
                self._configuring_from_idle = True
            else:
                self._configuring_from_idle = False
            (result_code, message) = command(argin)
            # store the configuration on command success
            self._last_scan_configuration = argin

        return [[result_code], [message]]
        # PROTECTED REGION END #    //  CspSubElementObsDevice.ConfigureScan

    class ScanCommand(CspSubElementObsDevice.ScanCommand):
        """
        A class for the Vcc's Scan() command.
        """

        def do(self: Vcc.ScanCommand, argin: str) -> Tuple[ResultCode, str]:
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

            if result_code == ResultCode.STARTED:
                device.obs_state_model.perform_action("component_scanning")

            return (result_code, msg)

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

            if result_code == ResultCode.OK:
                device.obs_state_model.perform_action("component_not_scanning")

            return (result_code, msg)

    class ObsResetCommand(CspSubElementObsDevice.ObsResetCommand):
        """A class for the VCC's ObsReset command."""

        def do(self):
            """
            Stateless hook for ObsReset() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return device.component_manager.obsreset()

    class AbortCommand(CspSubElementObsDevice.AbortCommand):
        """A class for the VCC's Abort command."""

        def do(self):
            """
            Stateless hook for Abort() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return device.component_manager.abort()

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
            device.component_manager.deconfigure()

            if device._obs_state == ObsState.IDLE:
                return (
                    ResultCode.OK,
                    "GoToIdle command completed OK. Device already IDLE",
                )

            device.obs_state_model.perform_action("component_unconfigured")

            return (ResultCode.OK, "GoToIdle command completed OK")

    class UpdateDopplerPhaseCorrectionCommand(BaseCommand):
        """
        A class for the Vcc's UpdateDopplerPhaseCorrection() command.

        Update Vcc's doppler phase correction.
        """

        def is_allowed(self: Vcc.UpdateDopplerPhaseCorrectionCommand) -> bool:
            """
            Determine if UpdateDopplerPhaseCorrection is allowed
            (allowed when Devstate is ON and ObsState is READY OR SCANNING).

            :return: if UpdateDopplerPhaseCorrection is allowed
            :rtype: bool
            """
            if (
                self.target.get_state() == tango.DevState.ON
                and self.target._obs_state
                in [ObsState.READY, ObsState.SCANNING]
            ):
                return True
            return False

        def do(
            self: Vcc.UpdateDopplerPhaseCorrectionCommand, argin: str
        ) -> None:
            """
            Stateless hook for UpdateDopplerPhaseCorrection() command functionality.

            :param argin: the doppler phase correction JSON
            """
            if self.is_allowed():
                self.target.component_manager.update_doppler_phase_correction(
                    argin
                )

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the Doppler phase correction model.",
    )
    @DebugIt()
    def UpdateDopplerPhaseCorrection(self, argin: str):
        # PROTECTED REGION ID(CspSubElementObsDevice.UpdateDopplerPhaseCorrection) ENABLED START #
        """
        Update Vcc's doppler phase correction.
        """
        self.get_command_object("UpdateDopplerPhaseCorrection")(argin)
        # PROTECTED REGION END #    //  CspSubElementObsDevice.UpdateDopplerPhaseCorrection

    class UpdateDelayModelCommand(BaseCommand):
        """
        A class for the Vcc's UpdateDelayModel() command.

        Update Vcc's delay model.
        """

        def is_allowed(self: Vcc.UpdateDelayModelCommand) -> bool:
            """
            Determine if UpdateDelayModel is allowed
            (allowed when Devstate is ON and ObsState is READY OR SCANNING).

            :return: if UpdateDelayModel is allowed
            :rtype: bool
            """
            if (
                self.target.get_state() == tango.DevState.ON
                and self.target._obs_state
                in [ObsState.READY, ObsState.SCANNING]
            ):
                return True
            return False

        def do(self: Vcc.UpdateDelayModelCommand, argin: str) -> None:
            """
            Stateless hook for UpdateDelayModel() command functionality.

            :param argin: the delay model JSON
            """
            if self.is_allowed():
                self.target.component_manager.update_delay_model(argin)

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the delay model.",
    )
    @DebugIt()
    def UpdateDelayModel(self, argin: str):
        # PROTECTED REGION ID(CspSubElementObsDevice.UpdateDelayModel) ENABLED START #
        """
        Update Vcc's delay model.
        """
        self.get_command_object("UpdateDelayModel")(argin)
        # PROTECTED REGION END #    //  CspSubElementObsDevice.UpdateDelayModel

    class UpdateJonesMatrixCommand(BaseCommand):
        """
        A class for the Vcc's UpdateJonesMatrix() command.

        Update Vcc's Jones matrix.
        """

        def is_allowed(self: Vcc.UpdateJonesMatrixCommand) -> bool:
            """
            Determine if UpdateJonesMatrix is allowed
            (allowed when Devstate is ON and ObsState is READY OR SCANNING).

            :return: if UpdateJonesMatrix is allowed
            :rtype: bool
            """
            if (
                self.target.get_state() == tango.DevState.ON
                and self.target._obs_state
                in [ObsState.READY, ObsState.SCANNING]
            ):
                return True
            return False

        def do(self: Vcc.UpdateJonesMatrixCommand, argin: str) -> None:
            """
            Stateless hook for UpdateJonesMatrix() command functionality.

            :param argin: the Jones Matrix JSON
            """
            if self.is_allowed():
                self.target.component_manager.update_jones_matrix(argin)

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the delay model.",
    )
    @DebugIt()
    def UpdateJonesMatrix(self, argin: str):
        # PROTECTED REGION ID(CspSubElementObsDevice.UpdateJonesMatrix) ENABLED START #
        """
        Update Vcc's Jones matrix.
        """
        self.get_command_object("UpdateJonesMatrix")(argin)
        # PROTECTED REGION END #    //  CspSubElementObsDevice.UpdateJonesMatrix

    class ConfigureSearchWindowCommand(ResponseCommand):
        """
        A class for the Vcc's ConfigureSearchWindow() command.

        Configure a search window by sending parameters from the input(JSON) to
        SearchWindow device.
        This function is called by the subarray after the configuration has
        already been validated.
        """

        def is_allowed(self: Vcc.ConfigureSearchWindowCommand) -> bool:
            """
            Determine if ConfigureSearchWindow is allowed
            (allowed if DevState is ON and ObsState is CONFIGURING)

            :return: if ConfigureSearchWindow is allowed
            :rtype: bool
            """
            if self.target.get_state() == tango.DevState.ON and (
                self.target._obs_state == ObsState.CONFIGURING
                or self.target._obs_state == ObsState.READY
            ):
                return True
            return False

        def validate_input(
            self: Vcc.ConfigureSearchWindowCommand, argin: str
        ) -> Tuple[bool, str]:
            """
            Validate a search window configuration

            :param argin: JSON object with the search window parameters
            """
            device = self.target

            # try to deserialize input string to a JSON object
            try:
                argin = json.loads(argin)
            except json.JSONDecodeError:  # argument not a valid JSON object
                msg = "Search window configuration object is not a valid JSON object."
                return (False, msg)

            # Validate searchWindowID.
            if "search_window_id" in argin:
                sw_id = argin["search_window_id"]
                if sw_id in [1, 2]:
                    pass
                else:  # searchWindowID not in valid range
                    msg = f"'search_window_id' must be one of [1, 2] (received {sw_id})."
                    return (False, msg)
            else:
                msg = "Search window specified, but 'search_window_id' not given."
                return (False, msg)

            # Validate searchWindowTuning.
            if "search_window_tuning" in argin:
                freq_band_name = argin["frequency_band"]
                if freq_band_name not in [
                    "5a",
                    "5b",
                ]:  # frequency band is not band 5
                    frequencyBand_mi = freq_band_dict()[freq_band_name][
                        "band_index"
                    ]

                    frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(
                        argin["frequency_band"]
                    )

                    assert frequencyBand_mi == frequencyBand

                    start_freq_Hz, stop_freq_Hz = [
                        const.FREQUENCY_BAND_1_RANGE_HZ,
                        const.FREQUENCY_BAND_2_RANGE_HZ,
                        const.FREQUENCY_BAND_3_RANGE_HZ,
                        const.FREQUENCY_BAND_4_RANGE_HZ,
                    ][frequencyBand]

                    device.logger.debug(f"start_freq_Hz = {start_freq_Hz}")
                    device.logger.debug(f"stop_freq_Hz = {stop_freq_Hz}")

                    if (
                        start_freq_Hz + argin["frequency_band_offset_stream_1"]
                        <= int(argin["search_window_tuning"])
                        <= stop_freq_Hz
                        + argin["frequency_band_offset_stream_1"]
                    ):
                        pass
                    else:
                        msg = "'search_window_tuning' must be within observed band."
                        return (False, msg)
                # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                else:
                    if argin["band_5_tuning"] == [
                        0,
                        0,
                    ]:  # band 5 tuning not specified in configuration
                        pass
                    else:
                        frequency_band_range_1 = (
                            argin["band_5_tuning"][0] * 10**9
                            + argin["frequency_band_offset_stream_1"]
                            - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                            argin["band_5_tuning"][0] * 10**9
                            + argin["frequency_band_offset_stream_1"]
                            + const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                        )

                        frequency_band_range_2 = (
                            argin["band_5_tuning"][1] * 10**9
                            + argin["frequency_band_offset_stream_2"]
                            - const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                            argin["band_5_tuning"][1] * 10**9
                            + argin["frequency_band_offset_stream_2"]
                            + const.BAND_5_STREAM_BANDWIDTH * 10**9 / 2,
                        )

                        if (
                            frequency_band_range_1[0]
                            <= int(argin["search_window_tuning"])
                            <= frequency_band_range_1[1]
                        ) or (
                            frequency_band_range_2[0]
                            <= int(argin["search_window_tuning"])
                            <= frequency_band_range_2[1]
                        ):
                            pass
                        else:
                            msg = "'searchWindowTuning' must be within observed band."
                            device.logger.error(msg)
                            tango.Except.throw_exception(
                                "Command failed",
                                msg,
                                "ConfigureSearchWindow execution",
                                tango.ErrSeverity.ERR,
                            )
            else:
                msg = "Search window specified, but 'search_window_tuning' not given."
                return (False, msg)

            # Validate tdcEnable.
            if "tdc_enable" in argin:
                if argin["tdc_enable"] in [True, False]:
                    pass
                else:
                    msg = (
                        "Search window specified, but 'tdc_enable' not given."
                    )
                    return (False, msg)
            else:
                msg = "Search window specified, but 'tdc_enable' not given."
                return (False, msg)

            # Validate tdcNumBits.
            if argin["tdc_enable"]:
                if "tdc_num_bits" in argin:
                    tdc_num_bits = argin["tdc_num_bits"]
                    if tdc_num_bits in [2, 4, 8]:
                        pass
                    else:
                        msg = f"'tdcNumBits' must be one of [2, 4, 8] (received {tdc_num_bits})."
                        return (False, msg)
                else:
                    msg = "Search window specified with TDC enabled, but 'tdcNumBits' not given."
                    return (False, msg)

            # Validate tdcPeriodBeforeEpoch.
            if "tdc_period_before_epoch" in argin:
                tdc_pbe = argin["tdc_period_before_epoch"]
                if tdc_pbe > 0:
                    pass
                else:
                    msg = f"'tdcPeriodBeforeEpoch' must be a positive integer (received {tdc_pbe})."
                    return (False, msg)
            else:
                pass

            # Validate tdcPeriodAfterEpoch.
            if "tdc_period_after_epoch" in argin:
                tdc_pae = argin["tdc_period_after_epoch"]
                if tdc_pae > 0:
                    pass
                else:
                    msg = f"'tdcPeriodAfterEpoch' must be a positive integer (received {tdc_pae})."
                    return (False, msg)
            else:
                pass

            # Validate tdcDestinationAddress.
            if argin["tdc_enable"]:
                try:
                    for receptor in argin["tdc_destination_address"]:
                        # "receptor" value is a pair of str and int
                        receptor_index = receptor["receptor_id"][1]
                        if (
                            receptor_index
                            == device.component_manager.receptor_id
                        ):
                            # TODO: validate tdc_destination_address
                            break
                        else:
                            pass
                except KeyError:
                    # tdcDestinationAddress not given or receptorID not in tdcDestinationAddress
                    msg = (
                        "Search window specified with TDC enabled, but 'tdcDestinationAddress' "
                        "not given or missing receptors."
                    )
                    return (False, msg)

            return (True, "Search window validated.")

        def do(
            self: Vcc.ConfigureSearchWindowCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureSearchWindow() command functionality.

            :param argin: JSON object with the search window parameters

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.target.component_manager.configure_search_window(argin)

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the search window configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out="A tuple containing a return code and a string message indicating status. "
        "The message is for information purpose only.",
    )
    @DebugIt()
    def ConfigureSearchWindow(self, argin):
        # PROTECTED REGION ID(CspSubElementObsDevice.ConfigureScan) ENABLED START #
        """
        Configure the observing device parameters for a search window.

        :param argin: JSON formatted string with the search window configuration.
        :type argin: 'DevString'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        # This validation is already performed in the CbfSubarray ConfigureScan.
        # TODO: Improve validation (validation should only be done once,
        # most of the validation can be done through a schema instead of manually
        # through functions).
        command = self.get_command_object("ConfigureSearchWindow")

        (valid, message) = command.validate_input(argin)
        if not valid:
            self._raise_configuration_fatal_error(
                message, "ConfigureSearchWindow"
            )

        (result_code, message) = command(argin)

        return [[result_code], [message]]
        # PROTECTED REGION END #    //  CspSubElementObsDevice.ConfigureScan


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main


if __name__ == "__main__":
    main()
