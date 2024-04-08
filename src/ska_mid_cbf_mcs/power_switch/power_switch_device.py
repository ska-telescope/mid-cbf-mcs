# -*- coding: utf-8 -*-
#
# This file is part of the PowerSwitch project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
TANGO device class for controlling and monitoring the web power switch that distributes power to the Talon LRUs.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from ska_tango_base import SKABaseDevice

# tango imports
from ska_tango_base.commands import (
    FastCommand,
    ResultCode,
    SubmittedSlowCommand,
)

# Additional import
# PROTECTED REGION ID(PowerSwitch.additionnal_import) ENABLED START #
from ska_tango_base.control_model import PowerState, SimulationMode
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import (
    PowerSwitchComponentManager,
)

# PROTECTED REGION END #    //  PowerSwitch.additionnal_import

__all__ = ["PowerSwitch", "main"]


class PowerSwitch(SKABaseDevice):
    """
    TANGO device class for controlling and monitoring the web power switch that
    distributes power to the Talon LRUs.
    """

    # PROTECTED REGION ID(PowerSwitch.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  PowerSwitch.class_variable

    # -----------------
    # Device Properties
    # -----------------

    PowerSwitchModel = device_property(dtype="str")
    PowerSwitchIp = device_property(dtype="str")
    PowerSwitchLogin = device_property(dtype="str")
    PowerSwitchPassword = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    isCommunicating = attribute(
        dtype="DevBoolean",
        access=AttrWriteType.READ,
        label="is communicating",
        doc="Whether or not the power switch can be communicated with",
    )

    numOutlets = attribute(
        dtype="DevULong",
        access=AttrWriteType.READ,
        label="num outlets",
        doc="Number of outlets in this power switch",
    )

    # ---------------
    # General methods
    # ---------------

    def always_executed_hook(self: PowerSwitch) -> None:
        """
        Hook to be executed before any attribute access or command.
        """
        # PROTECTED REGION ID(PowerSwitch.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  PowerSwitch.always_executed_hook

    def delete_device(self: PowerSwitch) -> None:
        """
        Uninitialize the device.
        """
        # PROTECTED REGION ID(PowerSwitch.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  PowerSwitch.delete_device

    def create_component_manager(
        self: PowerSwitch,
    ) -> PowerSwitchComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device
        """
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerState] = None
        # Simulation mode default true (using the simulator)
        return PowerSwitchComponentManager(
            model=self.PowerSwitchModel,
            ip=self.PowerSwitchIp,
            login=self.PowerSwitchLogin,
            password=self.PowerSwitchPassword,
            logger=self.logger,
            state_callback=self._update_state,
            admin_mode_callback=self._update_admin_mode,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_status_changed,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self: PowerSwitch) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()
        self.register_command_object(
            "TurnOnOutlet",
            SubmittedSlowCommand(
                command_name="TurnOnOutlet",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="turn_on_outlet",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "TurnOffOutlet",
            SubmittedSlowCommand(
                command_name="TurnOffOutlet",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="turn_off_outlet",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "GetOutletPowerState",
            self.GetOutletPowerStateCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    # ---------
    # Callbacks
    # ---------

    def _communication_status_changed(
        self: PowerSwitch, communication_status: CommunicationStatus
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

    def _component_state_changed(
        self: PowerSwitch, power_mode: PowerState
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
                PowerState.OFF: "component_off",
                PowerState.STANDBY: "component_standby",
                PowerState.ON: "component_on",
                PowerState.UNKNOWN: "component_unknown",
            }

            self.op_state_model.perform_action(action_map[power_mode])

    # ------------------
    # Attributes methods
    # ------------------

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: PowerSwitch) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: PowerSwitch, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    def read_numOutlets(self: PowerSwitch) -> int:
        """
        Get the number of outlets.

        :return: number of outlets
        """
        return self.component_manager.num_outlets

    def read_isCommunicating(self: PowerSwitch) -> bool:
        """
        Get whether or not the power switch is communicating.

        :return: True if power switch can be contacted, False if not
        """
        return self.component_manager.is_communicating

    # --------
    # Commands
    # --------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the PowerSwitch's init_device() "command".
        """

        def do(self: PowerSwitch.InitCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """

            (result_code, message) = super().do()
            self._device._simulation_mode = True

            return (result_code, message)

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn on.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOnOutlet(self: PowerSwitch, argin: str) -> None:
        command_handler = self.get_command_object(command_name="TurnOnOutlet")
        result_code_message, command_id = command_handler(argin)
        return [[result_code_message], [command_id]]

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn off.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    # TODO: Discuss type hint. Thomas sent a hack that can be added to allow 2d arrays without throwing a fit.
    def TurnOffOutlet(self: PowerSwitch, argin: str) -> None:
        command_handler = self.get_command_object(command_name="TurnOffOutlet")
        result_code_message, command_id = command_handler(argin)
        return [[result_code_message], [command_id]]

    class GetOutletPowerStateCommand(FastCommand):
        """
        The command class for the GetOutletPowerState command.

        Get the power mode of an individual outlet, specified by the outlet ID.
        """

        def __init__(
            self: PowerSwitch.GetOutletPowerStateCommand,
            *args: Any,
            component_manager: PowerSwitchComponentManager,
            **kwargs: Any,
        ) -> None:
            self.component_manager = component_manager
            super().__init__(*args, **kwargs)

        def do(
            self: PowerSwitch.GetOutletPowerStateCommand, argin: str
        ) -> PowerState:
            """
            Implement GetOutletPowerState command functionality.

            :param argin: the outlet ID to get the state of

            :return: power mode of the outlet
            """
            try:
                return self.component_manager.get_outlet_power_mode(argin)
            except AssertionError as e:
                self.logger.error(e)
                return PowerState.UNKNOWN

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to get the power mode of.",
        dtype_out="DevULong",
        doc_out="Power mode of the outlet.",
    )
    @DebugIt()
    def GetOutletPowerState(self: PowerSwitch, argin: str) -> int:
        # PROTECTED REGION ID(PowerSwitch.GetOutletPowerState) ENABLED START #
        handler = self.get_command_object("GetOutletPowerState")
        return int(handler(argin))
        # PROTECTED REGION END #    //  PowerSwitch.GetOutletPowerState


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(PowerSwitch.main) ENABLED START #
    return run((PowerSwitch,), args=args, **kwargs)
    # PROTECTED REGION END #    //  PowerSwitch.main


if __name__ == "__main__":
    main()
