# -*- coding: utf-8 -*-
#
# This file is part of the FspPssSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: Ryam Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada

FspPssSubarray Tango device prototype

FspPssSubarray TANGO device class for the FspPssSubarray prototype
"""
from __future__ import annotations  # allow forward references in type hints

import json

# Additional import
# PROTECTED REGION ID(FspPssSubarray.additionnal_import) ENABLED START #
from typing import List, Optional, Tuple

# tango imports
import tango
from ska_tango_base import CspSubElementObsDevice, SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState, PowerMode, SimulationMode
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.fsp.fsp_pss_subarray_component_manager import (
    FspPssSubarrayComponentManager,
)

# PROTECTED REGION END #    //  FspPssSubarray.additionnal_import

__all__ = ["FspPssSubarray", "main"]


class FspPssSubarray(CspSubElementObsDevice):
    """
    FspPssSubarray TANGO device class for the FspPssSubarray prototype
    """

    # PROTECTED REGION ID(FspPssSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPssSubarray.class_variable

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

    # TODO: CbfSubarrayAddress prop not being used
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
    searchBeams = attribute(
        dtype=("str",),
        access=AttrWriteType.READ,
        max_dim_x=192,
        label="SearchBeams",
        doc="List of searchBeams assigned to fspsubarray",
    )
    searchWindowID = attribute(
        dtype="uint16",
        access=AttrWriteType.READ,
        max_dim_x=2,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    searchBeamID = attribute(
        dtype=("uint16",),
        access=AttrWriteType.READ,
        max_dim_x=192,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    outputEnable = attribute(
        dtype="bool",
        access=AttrWriteType.READ,
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: FspPssSubarray) -> None:
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
        A class for the FspPssSubarray's init_device() "command".
        """

        def do(
            self: FspPssSubarray.InitCommand,
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

            message = "FspPssSubarry Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

        # PROTECTED REGION END #    //  FspPssSubarray.init_device

    def always_executed_hook(self: FspPssSubarray) -> None:
        # PROTECTED REGION ID(FspPssSubarray.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        # PROTECTED REGION END #    //  FspPssSubarray.always_executed_hook

    def create_component_manager(
        self: FspPssSubarray,
    ) -> FspPssSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return FspPssSubarrayComponentManager(
            self.logger,
            self.FspID,
            self.push_change_event,
            self._communication_status_changed,
            self._component_power_mode_changed,
            self._component_fault,
        )

    def delete_device(self: FspPssSubarray) -> None:
        # PROTECTED REGION ID(FspPssSubarray.delete_device) ENABLED START #
        """Hook to delete device."""
        # PROTECTED REGION END #    //  FspPssSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self: FspPssSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPssSubarray.receptors_read) ENABLED START #
        """
        Read the receptors attribute.

        :return: the receptors attribute.
        :rtype: List[int]
        """
        return self.component_manager.receptors
        # PROTECTED REGION END #    //  FspPssSubarray.receptors_read

    def read_searchBeams(self: FspPssSubarray) -> List[str]:
        # PROTECTED REGION ID(FspPssSubarray.searchBeams_read) ENABLED START #
        """
        Read the searchBeams attribute.

        :return: the searchBeams attribute.
        :rtype: List[str]
        """
        return self.component_manager.search_beams
        # PROTECTED REGION END #    //  FspPssSubarray.searchBeams_read

    def read_searchBeamID(self: FspPssSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPssSubarray.read_searchBeamID ENABLED START #
        """
        Read the searchBeamID attribute.

        :return: the searchBeamID attribute.
        :rtype: List[int]
        """
        return self.component_manager.search_beam_id
        # PROTECTED REGION END #    //  FspPssSubarray.read_searchBeamID

    def read_searchWindowID(self: FspPssSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchWindowID) ENABLED START #
        """
        Read the searchWindowID attribute.

        :return: the searchWindowID attribute.
        :rtype: List[int]
        """
        return self.component_manager.search_window_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchWindowID

    def read_outputEnable(self: FspPssSubarray) -> bool:
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_outputEnable) ENABLED START #
        """
        Read the outputEnable attribute. Used to enable/disable
        transmission of the output products.

        :return: the outputEnable attribute.
        :rtype: bool
        """
        return self.component_manager.output_enable

    def read_scanID(self: FspPssSubarray) -> int:
        # PROTECTED REGION ID(FspPssSubarray.scanID_read) ENABLED START #
        """
        Read the scanID attribute.

        :return: the scanID attribute.
        :rtype: int
        """
        return self.component_manager.scan_id
        # PROTECTED REGION END #    //  FspPssSubarray.scanID_read

    def write_scanID(self: FspPssSubarray, value: int) -> None:
        # PROTECTED REGION ID(FspPssSubarray.scanID_write) ENABLED START #
        """
        Write the scanID attribute.

        :param value: the scanID attribute value.
        """
        self.component_manager.scan_id = value
        # PROTECTED REGION END #    //  FspPssSubarray.scanID_writes

    def read_configID(self: FspPssSubarray) -> str:
        # PROTECTED REGION ID(FspPssSubarray.scanID_read) ENABLED START #
        """
        Read the configID attribute.

        :return: the configID attribute.
        :rtype: str
        """
        return self.component_manager.config_id
        # PROTECTED REGION END #    //  FspPssSubarray.scanID_read

    def write_configID(self: FspPssSubarray, value: str) -> None:
        # PROTECTED REGION ID(FspPssSubarray.scanID_write) ENABLED START #
        """
        Write the configID attribute.

        :param value: the configID attribute value.
        """
        self.component_manager.config_id = value
        # PROTECTED REGION END #    //  FspPssSubarray.scanID_writes

    # --------
    # Commands
    # --------

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the FspPssSubarray's On() command.
        """

        def do(
            self: FspPssSubarray.OnCommand,
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
                "FspPssSubarray On command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.ON)

            self.logger.info(message)
            return (result_code, message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the FspPssSubarray's Off() command.
        """

        def do(
            self: FspPssSubarray.OffCommand,
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
                "FspPssSubarray Off command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.OFF)

            self.logger.info(message)
            return (result_code, message)

    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the FspPssSubarray's Standby() command.
        """

        def do(
            self: FspPssSubarray.StandbyCommand,
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
                "FspPssSubarray Standby command completed OK",
            )

            self.target._component_power_mode_changed(PowerMode.STANDBY)

            self.logger.info(message)
            return (result_code, message)

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspPssSubarray's ConfigureScan() command.
        """

        """Input a serilized JSON object. """

        def do(
            self: FspPssSubarray.ConfigureScanCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string.
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
            self: FspPssSubarray.ConfigureScanCommand, argin: str
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
        self: FspPssSubarray, argin: str
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
        A class for the FspPssSubarray's Scan() command.
        """

        def do(
            self: FspPssSubarray.ScanCommand, argin: int
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
        A class for the FspPssSubarray's Scan() command.
        """

        def do(
            self: FspPssSubarray.EndScanCommand,
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
        A class for the FspPssSubarray's GoToIdle command.
        """

        def do(
            self: FspPssSubarray.GoToIdleCommand,
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

    class AbortCommand(CspSubElementObsDevice.AbortCommand):
        """A class for FspPssSubarray's Abort() command."""

        def do(self):
            """
            Calls component manager abort() command functionality.

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

    def _component_configured(self: FspPssSubarray, configured: bool) -> None:
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

    def _component_scanning(self: FspPssSubarray, scanning: bool) -> None:
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

    def _component_fault(self: FspPssSubarray, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state")

    def _component_obsfault(self: FspPssSubarray) -> None:
        """
        Handle notification that the component has obsfaulted.

        This is a callback hook.
        """
        self.obs_state_model.perform_action("component_obsfault")

    def _communication_status_changed(
        self: FspPssSubarray, communication_status: CommunicationStatus
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
        self: FspPssSubarray, power_mode: PowerMode
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
    # PROTECTED REGION ID(FspPssSubarray.main) ENABLED START #
    return run((FspPssSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPssSubarray.main


if __name__ == "__main__":
    main()
