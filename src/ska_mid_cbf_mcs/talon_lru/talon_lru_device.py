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
from typing import Any, Optional, Tuple

# tango imports
from ska_mid_cbf_mcs.device.base_device import CbfDevice
import tango
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import (
    ResultCode,
    SubmittedSlowCommand,
)
from ska_tango_base.control_model import PowerState, SimulationMode
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

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

    # TODO: Re-look into this, attribute is not changed; just used so read_LRUPowerState can be called
    LRUPowerState = attribute(
        dtype="uint16",
        access=tango.AttrWriteType.READ_WRITE,
        label="PowerState of the Talon LRU",
        doc="PowerState of the Talon LRU",
    )

    # ------------------
    # Attributes methods
    # ------------------

    def read_LRUPowerState(self: TalonLRU) -> PowerState:
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
        super(CbfDevice, self).init_command_objects()


    def create_component_manager(self: TalonLRU) -> TalonLRUComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerState] = None

        # TODO: Come back and update when component manager is updated
        return TalonLRUComponentManager(
            talons=[self.TalonDxBoard1, self.TalonDxBoard2],
            pdus=[self.PDU1, self.PDU2],
            pdu_outlets=[self.PDU1PowerOutlet, self.PDU2PowerOutlet],
            pdu_cmd_timeout=int(self.PDUCommandTimeout),
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
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
        ) -> Tuple[ResultCode, str]:
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
            self._device.simulation_mode(SimulationMode.TRUE)
            return (result_code, msg)

    # On Command
    def is_On_allowed (
            self: TalonLRU,
    ) -> bool:
        """
        Overwrite baseclass's is_On_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArrayType",
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

    # Off Command
    def is_Off_allowed (
            self: TalonLRU,
    ) -> bool:
        """
        Overwrite baseclass's is_Off_allowed method.
        """
        return True
    
    @command(
        dtype_out="DevVarLongStringArrayType",
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

    def _communication_status_changed(
        self: TalonLRU, communication_status: CommunicationStatus
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
        self: TalonLRU, power_mode: PowerState
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

    def _component_fault(self: TalonLRU, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status(
                "The device is in FAULT state - one or both PDU outlets have incorrect power state."
            )

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    return TalonLRU.run_server(args=args or None, **kwargs)

if __name__ == "__main__":
    main()
