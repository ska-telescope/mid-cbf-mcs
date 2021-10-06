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

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device, DeviceMeta
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
from ska_tango_base import SKABaseDevice

# Additional import
# PROTECTED REGION ID(PowerSwitch.additionnal_import) ENABLED START #
from ska_tango_base.control_model import SimulationMode
from ska_tango_base.commands import ResultCode, BaseCommand, ResponseCommand
from ska_mid_cbf_mcs.commons.global_enum import PowerMode
from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import PowerSwitchComponentManager
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

    PowerSwitchIp = device_property(
        dtype='str',
    )

    # ----------
    # Attributes
    # ----------

    isCommunicating = attribute(
        dtype='DevBoolean',
        access=AttrWriteType.READ,
        label="is communicating",
        doc="Whether or not the power switch can be communicated with",
    )

    numOutlets = attribute(
        dtype='DevULong',
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
        # PROTECTED REGION ID(PowerSwitch.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  PowerSwitch.always_executed_hook

    def delete_device(self: PowerSwitch) -> None:
        # PROTECTED REGION ID(PowerSwitch.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  PowerSwitch.delete_device

    def create_component_manager(self: PowerSwitch) -> PowerSwitchComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device
        """
        return PowerSwitchComponentManager(
            self._simulation_mode,
            self.PowerSwitchIp,
            self.logger
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

    # ------------------
    # Attributes methods
    # ------------------

    def write_simulationMode(self: PowerSwitch, value: SimulationMode) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
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
        def do(self: PowerSwitch.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            super().do()

            # TODO: remove once updating to new base class version
            device = self.target
            device.component_manager = device.create_component_manager()

            return (ResultCode.OK, "PowerSwitch initialization OK")

    class TurnOnOutletCommand(ResponseCommand):
        """
        The command class for the TurnOnOutlet command.

        Turn on an individual outlet, specified by the outlet ID (range 0 to
        numOutlets - 1).
        """

        def do(
            self: PowerSwitch.TurnOnOutletCommand,
            argin: int
        ) -> tuple[ResultCode, str]:
            """
            Implement TurnOnOutlet command functionality.

            :param argin: the outlet ID of the outlet to switch on

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.turn_on_outlet(argin)

    @command(
    dtype_in='DevULong', 
    doc_in="Outlet to turn on.", 
    dtype_out='DevVarLongStringArray', 
    doc_out="Tuple containing a return code and a string message indicating the status of the command.", 
    )
    @DebugIt()
    def TurnOnOutlet(self: PowerSwitch, argin: int) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(PowerSwitch.TurnOnOutlet) ENABLED START #
        handler = self.get_command_object("TurnOnOutlet")
        return_code, message = handler(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  PowerSwitch.TurnOnOutlet


    class TurnOffOutletCommand(ResponseCommand):
        """
        The command class for the TurnOffOutlet command.

        Turn off an individual outlet, specified by the outlet ID (range 0 to
        numOutlets - 1).
        """

        def do(
            self: PowerSwitch.TurnOffOutletCommand,
            argin: int
        ) -> tuple[ResultCode, str]:
            """
            Implement TurnOffOutlet command functionality.

            :param argin: the outlet ID of the outlet to switch off

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.turn_off_outlet(argin)

    @command(
    dtype_in='DevULong', 
    doc_in="Outlet to turn off.", 
    dtype_out='DevVarLongStringArray', 
    doc_out="Tuple containing a return code and a string message indicating the status of the command.", 
    )
    @DebugIt()
    def TurnOffOutlet(self: PowerSwitch, argin: int) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(PowerSwitch.TurnOffOutlet) ENABLED START #
        handler = self.get_command_object("TurnOffOutlet")
        return_code, message = handler(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  PowerSwitch.TurnOffOutlet


    class GetOutletPowerModeCommand(BaseCommand):
        """
        The command class for the GetOutletPowerMode command.

        Get the power mode of an individual outlet, specified by the outlet ID 
        (range 0 to numOutlets - 1).
        """

        def do(
            self: PowerSwitch.GetOutletPowerModeCommand,
            argin: int
        ) -> PowerMode:
            """
            Implement GetOutletPowerMode command functionality.

            :param argin: the outlet ID to get the state of

            :return: power mode of the outlet
            """
            component_manager = self.target
            return component_manager.get_outlet_power_mode(argin)

    @command(
    dtype_in='DevULong', 
    doc_in="Outlet to get the power mode of.", 
    dtype_out='DevULong', 
    doc_out="Power mode of the outlet.", 
    )
    @DebugIt()
    def GetOutletPowerMode(self: PowerSwitch, argin: int) -> int:
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

if __name__ == '__main__':
    main()
