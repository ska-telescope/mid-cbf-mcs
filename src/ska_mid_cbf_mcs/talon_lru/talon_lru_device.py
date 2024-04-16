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
import tango
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import (
    FastCommand,
    ResultCode,
    SubmittedSlowCommand,
)
from ska_tango_base.control_model import PowerState, SimulationMode
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# Additional import
# PROTECTED REGION ID(TalonLRU.additionnal_import) ENABLED START #
from ska_mid_cbf_mcs.talon_lru.talon_lru_component_manager import (
    TalonLRUComponentManager,
)

# PROTECTED REGION END #    //  TalonLRU.additionnal_import

__all__ = ["TalonLRU", "main"]


class TalonLRU(SKABaseDevice):
    """
    TANGO device class for controlling and monitoring a Talon LRU.
    """

    # PROTECTED REGION ID(TalonLRU.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  TalonLRU.class_variable

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

    LRUPowerState = attribute(
        dtype="uint16",
        doc="Power mode of the Talon LRU",
    )

    # ---------------
    # General methods
    # ---------------

    def always_executed_hook(self: TalonLRU) -> None:
        """
        Hook to be executed before any attribute access or command.
        """

    def delete_device(self: TalonLRU) -> None:
        """
        Uninitialize the device.
        """

    def init_command_objects(self: TalonLRU) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object(
            "On", 
            SubmittedSlowCommand(
                command_name = "On",
                command_tracker = self._command_tracker,
                component_manager = self.create_component_manager,
                method_name = "on",
                logger = self.logger,
            ),
        )
        self.register_command_object(
            "Off", 
            SubmittedSlowCommand(
                command_name = "Off",
                command_tracker = self._command_tracker,
                component_manager = self.create_component_manager,
                method_name = "off",
                logger = self.logger,
            ),
        )

    # ------------------
    # Attributes methods
    # ------------------

    def read_LRUPowerState(self: TalonLRU) -> PowerState:
        """
        Read the power mode of the LRU by checking the power mode of the PDUs.

        :return: Power mode of the LRU.
        """
        self.component_manager.check_power_mode(self.get_state())
        if (
            self.component_manager.pdu1_power_mode == PowerState.ON
            or self.component_manager.pdu2_power_mode == PowerState.ON
        ):
            return PowerState.ON
        elif (
            self.component_manager.pdu1_power_mode == PowerState.OFF
            and self.component_manager.pdu2_power_mode == PowerState.OFF
        ):
            return PowerState.OFF
        else:
            return PowerState.UNKNOWN

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

    def _check_power_mode(
        self: TalonLRUComponentManager,
        fqdn: str = "",
        name: str = "",
        value: Any = None,
        quality: tango.AttrQuality = None,
    ) -> None:
        """
        Get the power mode of both PDUs and check that it is consistent with the
        current device state. This is a callback that gets called whenever simulationMode
        changes in the power switch devices.
        """
        with self._power_switch_lock:
            self.component_manager.check_power_mode(self.get_state())


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonLRU.main) ENABLED START #
    return run((TalonLRU,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonLRU.main


if __name__ == "__main__":
    main()
