# -*- coding: utf-8 -*-
#
# This file is part of the FspPstSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Mid.CBF MCS

"""
from __future__ import annotations  # allow forward references in type hints

import json

# Additional import
# PROTECTED REGION ID(FspPstSubarray.additionnal_import) ENABLED START #
import os
from typing import List, Optional, Tuple

# PyTango imports
import tango
from ska_tango_base import CspSubElementObsDevice, SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState, PowerMode, SimulationMode
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.fsp.fsp_pst_subarray_component_manager import (
    FspPstSubarrayComponentManager,
)

file_path = os.path.dirname(os.path.abspath(__file__))


# PROTECTED REGION END #  //  FspPstSubarray.additionnal_import

__all__ = ["FspPstSubarray", "main"]


class FspPstSubarray(CspSubElementObsDevice):
    """
    FspPstSubarray TANGO device class for the FspPstSubarray prototype
    """

    # PROTECTED REGION ID(FspPstSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPstSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(dtype="uint16")

    FspID = device_property(dtype="uint16")

    CbfControllerAddress = device_property(
        dtype="str", default_value="mid_csp_cbf/controller/main"
    )

    CbfSubarrayAddress = device_property(dtype="str")

    VCC = device_property(dtype=("str",))

    # ----------
    # Attributes
    # ----------

    outputEnable = attribute(
        dtype="bool",
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    vccIDs = attribute(
        dtype=("uint16",),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="VCC IDs",
        doc="List of VCCs used for PST beamforming",
    )

    timingBeams = attribute(
        dtype=("str",),
        max_dim_x=16,
        label="TimingBeams",
        doc="List of timing beams assigned to FSP PST Subarray.",
    )

    timingBeamID = attribute(
        dtype=("uint16",),
        max_dim_x=16,
        label="TimingBeamID",
        doc="Identifiers of timing beams assigned to FSP PST Subarray",
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: FspPstSubarray) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        # note: registering commands with target = self,
        # as opposed to base class approach, with target = component manager

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
        A class for the FspPstSubarray's init_device() "command".
        """

        def do(
            self: FspPstSubarray.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            super().do()

            device = self.target
            device._configuring_from_idle = False

            # Setting initial simulation mode to True
            device.write_simulationMode(SimulationMode.TRUE)

            message = "FspPstSubarray Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self: FspPstSubarray) -> None:
        # PROTECTED REGION ID(FspPstSubarray.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        # PROTECTED REGION END #    //  FspPstSubarray.always_executed_hook

    def create_component_manager(
        self: FspPstSubarray,
    ) -> FspPstSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return FspPstSubarrayComponentManager(
            self.logger,
            self.FspID,
            self.push_change_event,
            self._communication_status_changed,
            self._component_power_mode_changed,
            self._component_fault,
            self._component_obsfault,
        )

    def delete_device(self: FspPstSubarray) -> None:
        # PROTECTED REGION ID(FspPstSubarray.delete_device) ENABLED START #
        """Hook to delete device."""
        # PROTECTED REGION END #    //  FspPstSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_outputEnable(self: FspPstSubarray) -> bool:
        # PROTECTED REGION ID(FspPstSubarray.outputEnable_read) ENABLED START #
        """
        Read the outputEnable attribute. Used to enable/disable
        transmission of the output products.

        :return: the outputEnable attribute.
        :rtype: bool
        """
        return self.component_manager.output_enable
        # PROTECTED REGION END #    //  FspPstSubarray.outputEnable_read

    def read_vccIDs(self: FspPstSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPstSubarray.vccIDs_read) ENABLED START #
        """
        Read the vccIDs attribute; FSP deals with VCC, not DISH (receptor) IDs.

        :return: the list of assigned VCC IDs
        :rtype: List[int]
        """
        return self.component_manager.vcc_ids
        # PROTECTED REGION END #    //  FspPstSubarray.vccIDs_read

    # TODO: do we need write_receptors? All receptor adding is handled by component
    # manager. Other Fsp subarray devices do not have this
    def write_receptors(self: FspPstSubarray, value: List[int]) -> None:
        # PROTECTED REGION ID(FspPstSubarray.receptors_write) ENABLED START #
        """
        Write the receptors attribute.

        :param value: the receptors attribute value.
        """
        self.component_manager.receptors = value

    #     # PROTECTED REGION END #    //  FspPstSubarray.receptors_write

    def read_timingBeams(self: FspPstSubarray) -> List[str]:
        # PROTECTED REGION ID(FspPstSubarray.timingBeams_read) ENABLED START #
        """
        Read the timingBeams attribute.

        :return: the timingBeams attribute.
        :rtype: List[int]
        """
        return self.component_manager.timing_beams
        # PROTECTED REGION END #    //  FspPstSubarray.timingBeams_read

    def read_timingBeamID(self: FspPstSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPstSubarray.timingBeamID_read) ENABLED START #
        """
        Read the list of Timing Beam IDs.

        :return: the timingBeamID attribute.
        :rtype: List[int]
        """
        return self.component_manager.timing_beam_id
        # PROTECTED REGION END #    //  FspPstSubarray.timingBeamID_read

    def read_scanID(self: FspPstSubarray) -> int:
        # PROTECTED REGION ID(FspPstSubarray.scanID_read) ENABLED START #
        """
        Read the scanID attribute.

        :return: the scanID attribute.
        :rtype: int
        """
        return self.component_manager.scan_id
        # PROTECTED REGION END #    //  FspPstSubarray.scanID_read

    def write_scanID(self: FspPstSubarray, value: int) -> None:
        # PROTECTED REGION ID(FspPstSubarray.scanID_write) ENABLED START #
        """
        Write the scanID attribute.

        :param value: the scanID attribute value.
        """
        self.component_manager.scan_id = value
        # PROTECTED REGION END #    //  FspPstSubarray.scanID_writes

    # --------
    # Commands
    # --------

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the FspPstSubarray's On() command.
        """

        def do(
            self: FspPstSubarray.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering OnCommand()")

            (result_code, message) = (
                ResultCode.OK,
                "FspPstSubarray On command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.ON)

            self.logger.info(message)
            return (result_code, message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the FspPstSubarray's Off() command.
        """

        def do(
            self: FspPstSubarray.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering OffCommand()")

            (result_code, message) = (
                ResultCode.OK,
                "FspPstSubarray Off command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.OFF)

            self.logger.info(message)
            return (result_code, message)

    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the FspPstSubarray's Standby() command.
        """

        def do(
            self: FspPstSubarray.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering StandbyCommand()")

            (result_code, message) = (
                ResultCode.OK,
                "FspPstSubarray Standby command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.STANDBY)

            self.logger.info(message)
            return (result_code, message)

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspPstSubarray's ConfigureScan() command.
        """

        """Input a serilized JSON object. """

        def do(self: FspPstSubarray, argin: str) -> Tuple[ResultCode, str]:
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
            self: FspPstSubarray.ConfigureScanCommand, argin: str
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
    def ConfigureScan(
        self: FspPstSubarray, argin: str
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
        (valid, message) = command.validate_input(argin)
        if not valid:
            self.logger.error(message)
            tango.Except.throw_exception(
                "Command failed",
                message,
                "ConfigureScan execution",
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
        A class for the FspPstSubarray's Scan() command.
        """

        def do(
            self: FspPstSubarray.ScanCommand, argin: int
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :param argin: The scan ID
            :type argin: int

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            self.logger.debug("Entering ScanCommand()")

            device = self.target

            (result_code, message) = device.component_manager.scan(argin)

            if result_code == ResultCode.OK:
                device._component_scanning(True)

            return (result_code, message)

    @command(
        dtype_in="DevShort",
        doc_in="An integer with the scan ID",
        dtype_out="DevVarLongStringArray",
        doc_out="A tuple containing a return code and a string message indicating status."
        "The message is for information purpose only.",
    )
    @DebugIt()
    def Scan(self, argin):
        # PROTECTED REGION ID(CspSubElementObsDevice.Scan) ENABLED START #
        """
        Start an observing scan.

        :param argin: A string with the scan ID
        :type argin: 'DevShort'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("Scan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class EndScanCommand(CspSubElementObsDevice.EndScanCommand):
        """
        A class for the FspPstSubarray's EndScan() command.
        """

        def do(
            self: FspPstSubarray.EndScanCommand,
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
        A class for the FspPstSubarray's GoToIdle command.
        """

        def do(
            self: FspPstSubarray.GoToIdleCommand,
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

    class ObsResetCommand(CspSubElementObsDevice.ObsResetCommand):
        """A class for FspPstSubarray's ObsReset() command."""

        def do(self):
            """
            Stateless hook for ObsReset() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            (result_code, message) = component_manager.obsreset()

            return (result_code, message)

    class AbortCommand(CspSubElementObsDevice.AbortCommand):
        """A class for FspPstSubarray's Abort() command."""

        def do(self):
            """
            Stateless hook for Abort() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            (result_code, message) = component_manager.abort()

            return (result_code, message)

    # ----------
    # Callbacks
    # ----------

    def _component_configured(self: FspPstSubarray, configured: bool) -> None:
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

    def _component_scanning(self: FspPstSubarray, scanning: bool) -> None:
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

    def _component_fault(self: FspPstSubarray, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state")

    def _component_obsfault(self: FspPstSubarray, faulty: bool) -> None:
        """
        Handle notification that the component has obsfaulted.

        This is a callback hook.
        """
        self.component_manager.obs_faulty = faulty
        if faulty:
            self.obs_state_model.perform_action("component_obsfault")
            self.set_status("The device is in FAULT state")

    def _communication_status_changed(
        self: FspPstSubarray, communication_status: CommunicationStatus
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
        self: FspPstSubarray, power_mode: PowerMode
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


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPstSubarray.main) ENABLED START #
    return run((FspPstSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPstSubarray.main


if __name__ == "__main__":
    main()
