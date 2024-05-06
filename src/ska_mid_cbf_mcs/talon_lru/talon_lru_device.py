# -*- coding: utf-8 -*-
#
# This file is part of the TalonLRU project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
TANGO device class for controlling and monitoring a Talon LRU.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

import tango
from ska_tango_base import SKABaseDevice
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tango_base.control_model import PowerState, SimulationMode
from tango.server import attribute, command, device_property

# tango imports
from ska_mid_cbf_mcs.device.base_device import CbfDevice

# Additional import
from ska_mid_cbf_mcs.talon_lru.talon_lru_component_manager import (
    TalonLRUComponentManager,
)

__all__ = ["TalonLRU", "main"]


class TalonLRU(CbfDevice):
    """
    TANGO device class for controlling and monitoring a Talon LRU.
    """

    # -----------------
    # Device Properties
    # -----------------

    TalonDxBoard1 = device_property(dtype="str")

    TalonDxBoard2 = device_property(dtype="str")

    PDU1 = device_property(dtype="str")

    PDU1PowerOutlet = device_property(dtype="str")

    PDU2 = device_property(dtype="str")

    PDU2PowerOutlet = device_property(dtype="str")

    PDUCommandTimeout = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: TalonLRU) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: TalonLRU, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.debug(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    @attribute(
        dtype="uint16",
        label="PowerState of the Talon LRU",
        doc="PowerState of the Talon LRU",
    )
    def LRUPowerState(self: TalonLRU) -> PowerState:
        """
        Read the LRU's PowerState.

        :return: PowerState of the LRU.
        """
        return self.component_manager.get_lru_power_state()

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: TalonLRU) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()

        self.register_command_object(
            "On",
            SubmittedSlowCommand(
                command_name="On",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="on",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "Off",
            SubmittedSlowCommand(
                command_name="Off",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="off",
                logger=self.logger,
            ),
        )

    def create_component_manager(self: TalonLRU) -> TalonLRUComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return TalonLRUComponentManager(
            talons=[self.TalonDxBoard1, self.TalonDxBoard2],
            pdus=[self.PDU1, self.PDU2],
            pdu_outlets=[self.PDU1PowerOutlet, self.PDU2PowerOutlet],
            pdu_cmd_timeout=int(self.PDUCommandTimeout),
            logger=self.logger,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    # --------
    # Commands
    # --------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TalonLRU's init_device() "command".
        """

        def do(
            self: TalonLRU.InitCommand,
            *args: Any,
            **kwargs: Any,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation. Creates the device proxies
            to the power switch devices.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            (result_code, msg) = super().do(*args, **kwargs)

            self._device._power_switch_lock = Lock()

            # Setting initial simulation mode to True
            self._device._simulation_mode = SimulationMode.TRUE
            return (result_code, msg)

    def is_On_allowed(
        self: TalonLRU,
    ) -> bool:
        """
        Overwrite baseclass's is_On_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @tango.DebugIt()
    def On(
        self: TalonLRU,
    ) -> DevVarLongStringArrayType:
        """
        Turn on the Talon LRU.

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: DevVarLongStringArrayType
        """
        command_handler = self.get_command_object(command_name="On")
        result_code_message, command_id = command_handler()
        return [[result_code_message], [command_id]]

    def is_Off_allowed(
        self: TalonLRU,
    ) -> bool:
        """
        Overwrite baseclass's is_Off_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @tango.DebugIt()
    def Off(
        self: TalonLRU,
    ) -> DevVarLongStringArrayType:
        """
        Turn off the Talon LRU.

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: DevVarLongStringArrayType
        """
        command_handler = self.get_command_object(command_name="Off")
        result_code_message, command_id = command_handler()
        return [[result_code_message], [command_id]]


# ----------
# Callbacks
# ----------

# No callbacks in this device

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return TalonLRU.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
