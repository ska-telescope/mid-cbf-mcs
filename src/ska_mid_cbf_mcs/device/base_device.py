# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

"""
CbfDevice

Generic Tango device for Mid.CBF
"""

from __future__ import annotations

from typing import cast

from ska_control_model import ResultCode, SimulationMode
from ska_tango_base.base.base_component_manager import BaseComponentManager
from ska_tango_base.base.base_device import (
    DevVarLongStringArrayType,
    SKABaseDevice,
)
from ska_tango_base.commands import FastCommand
from tango import DebugIt
from tango.server import attribute, command, device_property

__all__ = ["CbfDevice", "CbfFastCommand", "main"]


class CbfFastCommand(FastCommand):
    """Overrides base FastCommand to instantiate component manager"""

    def __init__(
        self: CbfFastCommand,
        *args,
        component_manager: BaseComponentManager,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.component_manager = component_manager


class CbfDevice(SKABaseDevice):
    """
    A generic base device for Mid.CBF.
    Extends SKABaseDevice to override certain key values.
    """

    # -----------------
    # Device Properties
    # -----------------

    DeviceID = device_property(dtype="uint16", default_value=1)

    # ----------
    # Attributes
    # ----------

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: CbfDevice) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: CbfDevice, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.debug(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: CbfDevice) -> None:
        """
        Set up the command objects."
        """
        super().init_command_objects()

        # Overriding base On/Off SubmittedSlowCommand register with FastCommand objects
        self.register_command_object(
            "On",
            self.OnCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )
        self.register_command_object(
            "Off",
            self.OffCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    # --------
    # Commands
    # --------

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Standby(self: CbfDevice) -> DevVarLongStringArrayType:
        """
        Put the device into standby mode; currently unimplemented in Mid.CBF

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            [
                "Standby command rejected; Mid.CBF does not currently implement standby state."
            ],
        )

    class OnCommand(FastCommand):
        """
        A class for the CbfDevice's on command.
        """

        def __init__(
            self: CbfDevice.OnCommand,
            *args,
            component_manager: BaseComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: CbfDevice.OnCommand,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.on()

    class OffCommand(FastCommand):
        """
        A class for the CbfDevice's off command.
        """

        def __init__(
            self: CbfDevice.OffCommand,
            *args,
            component_manager: BaseComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: CbfDevice.OffCommand,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.off()


# ----------
# Run server
# ----------


def main(*args: str, **kwargs: str) -> int:
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments

    :return: exit code
    """
    return cast(int, CbfDevice.run_server(args=args or None, **kwargs))


if __name__ == "__main__":
    main()
