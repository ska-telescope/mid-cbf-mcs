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

    # --------------
    # Initialization
    # --------------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the CbfController's Init() command.
        """

        def do(
            self: CbfDevice.InitCommand,
            *args: any,
            **kwargs: any,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string message indicating status.
                     The message is for information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, msg) = super().do(*args, **kwargs)

            self._device._simulation_mode = SimulationMode.TRUE

            return (result_code, msg)

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

    # --------
    # Commands
    # --------

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def On(self: CbfDevice) -> DevVarLongStringArrayType:
        """
        Turn device on.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["On command rejected, as it is unimplemented for this device."],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Off(self: CbfDevice) -> DevVarLongStringArrayType:
        """
        Turn device off.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["Off command rejected, as it is unimplemented for this device."],
        )

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
