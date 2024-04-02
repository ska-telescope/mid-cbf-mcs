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

import logging
from time import sleep
from typing import Any, Callable, Optional, Tuple

from ska_tango_base import SKABaseDevice

# tango imports
from ska_tango_base.base import CommandTracker
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
            self.PowerSwitchModel,
            self.PowerSwitchIp,
            self.PowerSwitchLogin,
            self.PowerSwitchPassword,
            self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )

    def init_command_objects(self: PowerSwitch) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()
        self.register_command_object(
            "TurnOnOutlet",
            SubmittedSlowCommand(
                "TurnOnOutlet",
                self._command_tracker,
                self.component_manager,
                "turn_on_outlet",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "TurnOffOutlet",
            SubmittedSlowCommand(
                "TurnOffOutlet",
                self._command_tracker,
                self.component_manager,
                "turn_off_outlet",
                logger=self.logger,
            ),
        )
        device_args = (self.component_manager, self.logger)
        self.register_command_object(
            "GetOutletPowerState",
            self.GetOutletPowerStateCommand(*device_args),
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

    def _component_power_mode_changed(
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

    def _component_fault(self: PowerSwitch, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")

    # ------------------
    # Attributes methods
    # ------------------

    def read_simulationMode(self: PowerSwitch) -> SimulationMode:
        """
        Get the simulation mode.

        :return: the current simulation mode
        """
        return self.component_manager.simulation_mode

    def write_simulationMode(self: PowerSwitch, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device. When simulation mode is set to
        True, the power switch software simulator is used in place of the hardware.
        When simulation mode is set to False, the real power switch driver is used.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
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

            device = self._device
            device.write_simulationMode(True)

            return (result_code, message)

    class TurnOnOutletCommand(SubmittedSlowCommand):
        """
        The command class for the TurnOnOutlet command.

        Turn on an individual outlet, specified by the outlet ID
        """

        def __init__(  # pylint: disable=too-many-arguments
            self: PowerSwitch.TurnOnOutletCommand,
            command_tracker: CommandTracker,
            component_manager: PowerSwitchComponentManager,
            callback: Callable[[bool], None] | None = None,
            logger: logging.Logger | None = None,
            schema: dict[str, Any] | None = None,
        ) -> None:
            """
            Initialise a new instance.

            :param command_tracker: the device's command tracker
            :param component_manager: the device's component manager
            :param callback: an optional callback to be called when this
                command starts and finishes.
            :param logger: a logger for this command to log with.
            :param schema: an optional JSON schema for the command
                argument.
            """
            logger.info("1. HERE")
            super().__init__(
                "TurnOnOutlet",
                command_tracker,
                component_manager,
                "turn_on_outlet",
                callback=callback,
                logger=logger,
            )

        # def do(
        #     self: PowerSwitch.TurnOnOutletCommand, argin: str
        # ) -> Tuple[ResultCode, str]:
        #     """
        #     Implement TurnOnOutlet command functionality.

        #     :param argin: the outlet ID of the outlet to switch on

        #     :return: A tuple containing a return code and a string
        #         message indicating status. The message is for
        #         information purpose only.
        #     """
        #     component_manager = self.target

        #     try:
        #         result, msg = component_manager.turn_on_outlet(argin)
        #         if result != ResultCode.OK:
        #             return (result, msg)

        #         power_mode = component_manager.get_outlet_power_mode(argin)
        #         if power_mode != PowerState.ON:
        #             # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
        #             self.logger.info(
        #                 "The outlet's power mode is not 'on' as expected. Waiting for 5 seconds before rechecking the power mode..."
        #             )
        #             time.sleep(5)
        #             power_mode = component_manager.get_outlet_power_mode(argin)
        #             if power_mode != PowerState.ON:
        #                 return (
        #                     ResultCode.FAILED,
        #                     f"Power on failed, outlet is in power mode {power_mode}",
        #                 )
        #     except AssertionError as e:
        #         self.logger.error(e)
        #         return (
        #             ResultCode.FAILED,
        #             "Unable to read outlet state after power on",
        #         )

        #     return (result, msg)

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn on.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOnOutlet(self: PowerSwitch, argin: str) -> None:
        # PROTECTED REGION ID(PowerSwitch.TurnOnOutlet) ENABLED START #
        self.logger.info("2. HERE")
        handler = self.get_command_object("TurnOnOutlet")
        self.logger.info("3. HERE")
        self.logger.info(f"HANDLER={handler}")
        result_code, message = handler(argin)
        self.logger.info("4. HERE")
        if result_code != ResultCode.OK:
            self.logger.info(f"Result={result_code}")
            return ([result_code], [message])
        power_mode = self.get_outlet_power_mode(argin)
        if power_mode != PowerState.ON:
            # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
            self.logger.info(
                "The outlet's power mode is not 'on' as expected. Waiting for 5 seconds before rechecking the power mode..."
            )
            sleep(5)
            power_mode = self.get_outlet_power_mode(argin)
            if power_mode != PowerState.ON:
                return (
                    [ResultCode.FAILED],
                    [f"Power on failed, outlet is in power mode {power_mode}"],
                )
        self.logger.info("5. HERE")
        return [[result_code], [message]]
        # PROTECTED REGION END #    //  PowerSwitch.TurnOnOutlet

    # class TurnOffOutletCommand(SubmittedSlowCommand):
    #     """
    #     The command class for the TurnOffOutlet command.

    #     Turn off an individual outlet, specified by the outlet ID.
    #     """

    #     def do(
    #         self: PowerSwitch.TurnOffOutletCommand, argin: str
    #     ) -> Tuple[ResultCode, str]:
    #         """
    #         Implement TurnOffOutlet command functionality.

    #         :param argin: the outlet ID of the outlet to switch off

    #         :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #         """
    #         component_manager = self.target

    #         try:
    #             result, msg = component_manager.turn_off_outlet(argin)
    #             if result != ResultCode.OK:
    #                 return (result, msg)

    #             power_mode = component_manager.get_outlet_power_mode(argin)
    #             if power_mode != PowerState.OFF:
    #                 # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
    #                 self.logger.info(
    #                     "The outlet's power mode is not 'off' as expected. Waiting for 5 seconds before rechecking the power mode..."
    #                 )
    #                 time.sleep(5)
    #                 power_mode = component_manager.get_outlet_power_mode(argin)
    #                 if power_mode != PowerState.OFF:
    #                     return (
    #                         ResultCode.FAILED,
    #                         f"Power off failed, outlet is in power mode {power_mode}",
    #                     )
    #         except AssertionError as e:
    #             self.logger.error(e)
    #             return (
    #                 ResultCode.FAILED,
    #                 "Unable to read outlet state after power off",
    #             )

    #         return (result, msg)

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn off.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOffOutlet(self: PowerSwitch, argin: str) -> None:
        # PROTECTED REGION ID(PowerSwitch.TurnOffOutlet) ENABLED START #
        handler = self.get_command_object("TurnOffOutlet")
        result_code, message = handler(argin)
        return [[result_code], [message]]
        # PROTECTED REGION END #    //  PowerSwitch.TurnOffOutlet

    class GetOutletPowerStateCommand(FastCommand):
        """
        The command class for the GetOutletPowerState command.

        Get the power mode of an individual outlet, specified by the outlet ID.
        """

        def do(
            self: PowerSwitch.GetOutletPowerStateCommand, argin: str
        ) -> PowerState:
            """
            Implement GetOutletPowerState command functionality.

            :param argin: the outlet ID to get the state of

            :return: power mode of the outlet
            """
            component_manager = self.target
            try:
                return component_manager.get_outlet_power_mode(argin)
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
