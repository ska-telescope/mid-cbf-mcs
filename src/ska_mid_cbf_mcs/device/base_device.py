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

from ska_control_model import AdminMode, ResultCode, SimulationMode
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
            self._device._health_state_report = []

            return (result_code, msg)

    # -----------------
    # Device Properties
    # -----------------

    DeviceID = device_property(dtype="uint16", default_value=1)

    # ----------
    # Attributes
    # ----------

    @attribute(dtype=[str])
    def healthStateReport(self: CbfDevice) -> list[str]:
        """
        Read the HealthStateReport of the device.

        :return: HealthStateReport of the device.
        """
        return self._health_state_report

    @healthStateReport.write
    def healthStateReport(self: CbfDevice, value: list[str]) -> None:
        """
        Set the HealthStateReport of the device.

        :param value: a list of strings to overwrite the previous healthStateReport.
        """
        self.logger.info(f"Writing healthStateReport to {value}")
        self._health_state_report = value

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
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    @attribute(dtype=AdminMode, memorized=True, hw_memorized=True)
    def adminMode(self: CbfDevice) -> AdminMode:
        """
        Read the Admin Mode of the device.

        It may interpret the current device condition and condition of all managed
         devices to set this. Most possibly an aggregate attribute.

        :return: Admin Mode of the device
        """
        return self._admin_mode

    @adminMode.write  # type: ignore[no-redef]
    def adminMode(self: CbfDevice, value: AdminMode) -> None:
        """
        Set the Admin Mode of the device.

        :param value: Admin Mode of the device.

        :raises ValueError: for unknown adminMode
        """
        if value == AdminMode.NOT_FITTED:
            self.admin_mode_model.perform_action("to_notfitted")
        elif value == AdminMode.OFFLINE:
            self.component_manager.stop_communicating()
        elif value == AdminMode.ENGINEERING:
            self.admin_mode_model.perform_action("to_engineering")
            self.component_manager.start_communicating()
        elif value == AdminMode.ONLINE:
            self.component_manager.start_communicating()
        elif value == AdminMode.RESERVED:
            self.admin_mode_model.perform_action("to_reserved")
        else:
            raise ValueError(f"Unknown adminMode {value}")

    # ----------------------
    # Unimplemented Commands
    # ----------------------

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

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Reset(self: CbfDevice) -> DevVarLongStringArrayType:
        """
        Reset the device; currently unimplemented in Mid.CBF

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            [
                "Reset command rejected, as it is unimplemented for this device."
            ],
        )

    # ----------
    # Callbacks
    # ----------

    # Separated from adminMode write function for callback in component manager
    def _admin_mode_perform_action(self: CbfDevice, action: str) -> None:
        """
        Callback provided to perform an action on the state model from
        component manager.

        :param action: an action, as given in the transitions table
        """
        self.admin_mode_model.perform_action(action)


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
