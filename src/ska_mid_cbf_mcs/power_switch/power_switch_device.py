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

import time
from typing import Optional, Tuple

# tango imports
import tango
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import BaseCommand, ResponseCommand, ResultCode

# Additional import
# PROTECTED REGION ID(PowerSwitch.additionnal_import) ENABLED START #
from ska_tango_base.control_model import PowerMode, SimulationMode
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
        self._component_power_mode: Optional[PowerMode] = None
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

        device_args = (self.component_manager, self.logger)
        self.register_command_object(
            "TurnOnOutlet", self.TurnOnOutletCommand(*device_args)
        )
        self.register_command_object(
            "TurnOffOutlet", self.TurnOffOutletCommand(*device_args)
        )
        self.register_command_object(
            "GetOutletPowerMode", self.GetOutletPowerModeCommand(*device_args)
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
        self: PowerSwitch, power_mode: PowerMode
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

    def write_simulationMode(self: PowerSwitch, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device. When simulation mode is set to
        True, the power switch software simulator is used in place of the hardware.
        When simulation mode is set to False, the real power switch driver is used.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        super().write_simulationMode(value)
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

            device = self.target
            device.write_simulationMode(True)

            return (result_code, message)

    class TurnOnOutletCommand(ResponseCommand):
        """
        The command class for the TurnOnOutlet command.

        Turn on an individual outlet, specified by the outlet ID
        """

        def do(
            self: PowerSwitch.TurnOnOutletCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Implement TurnOnOutlet command functionality.

            :param argin: the outlet ID of the outlet to switch on

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target

            try:
                result, msg = component_manager.turn_on_outlet(argin)
                if result != ResultCode.OK:
                    return (result, msg)

                power_mode = component_manager.get_outlet_power_mode(argin)
                if power_mode != PowerMode.ON:
                    # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
                    time.sleep(5)
                    if power_mode != PowerMode.ON:
                        return (
                            ResultCode.FAILED,
                            f"Power on failed, outlet is in power mode {power_mode}",
                        )
            except AssertionError as e:
                self.logger.error(e)
                return (
                    ResultCode.FAILED,
                    "Unable to read outlet state after power on",
                )

            return (result, msg)

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn on.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOnOutlet(
        self: PowerSwitch, argin: str
    ) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(PowerSwitch.TurnOnOutlet) ENABLED START #
        handler = self.get_command_object("TurnOnOutlet")
        return_code, message = handler(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  PowerSwitch.TurnOnOutlet

    class TurnOffOutletCommand(ResponseCommand):
        """
        The command class for the TurnOffOutlet command.

        Turn off an individual outlet, specified by the outlet ID.
        """

        def do(
            self: PowerSwitch.TurnOffOutletCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Implement TurnOffOutlet command functionality.

            :param argin: the outlet ID of the outlet to switch off

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target

            try:
                result, msg = component_manager.turn_off_outlet(argin)
                if result != ResultCode.OK:
                    return (result, msg)

                power_mode = component_manager.get_outlet_power_mode(argin)
                if power_mode != PowerMode.OFF:
                    # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
                    time.sleep(5)
                    power_mode = component_manager.get_outlet_power_mode(argin)
                    if power_mode != PowerMode.OFF:
                        return (
                            ResultCode.FAILED,
                            f"Power off failed, outlet is in power mode {power_mode}",
                        )
            except AssertionError as e:
                self.logger.error(e)
                return (
                    ResultCode.FAILED,
                    "Unable to read outlet state after power off",
                )

            return (result, msg)

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn off.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOffOutlet(
        self: PowerSwitch, argin: str
    ) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(PowerSwitch.TurnOffOutlet) ENABLED START #
        handler = self.get_command_object("TurnOffOutlet")
        return_code, message = handler(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  PowerSwitch.TurnOffOutlet

    class GetOutletPowerModeCommand(BaseCommand):
        """
        The command class for the GetOutletPowerMode command.

        Get the power mode of an individual outlet, specified by the outlet ID.
        """

        def do(
            self: PowerSwitch.GetOutletPowerModeCommand, argin: str
        ) -> PowerMode:
            """
            Implement GetOutletPowerMode command functionality.

            :param argin: the outlet ID to get the state of

            :return: power mode of the outlet
            """
            component_manager = self.target
            try:
                return component_manager.get_outlet_power_mode(argin)
            except AssertionError as e:
                self.logger.error(e)
                return PowerMode.UNKNOWN

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to get the power mode of.",
        dtype_out="DevULong",
        doc_out="Power mode of the outlet.",
    )
    @DebugIt()
    def GetOutletPowerMode(self: PowerSwitch, argin: str) -> int:
        # PROTECTED REGION ID(PowerSwitch.GetOutletPowerMode) ENABLED START #
        handler = self.get_command_object("GetOutletPowerMode")
        return int(handler(argin))
        # PROTECTED REGION END #    //  PowerSwitch.GetOutletPowerMode


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(PowerSwitch.main) ENABLED START #
    return run((PowerSwitch,), args=args, **kwargs)
    # PROTECTED REGION END #    //  PowerSwitch.main


if __name__ == "__main__":
    main()
