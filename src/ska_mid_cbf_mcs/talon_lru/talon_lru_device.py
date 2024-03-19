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
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerState, SimulationMode
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

    PDU1PowerState = attribute(
        dtype="uint16", doc="Power mode of the Talon LRU PDU 1"
    )

    PDU2PowerState = attribute(
        dtype="uint16", doc="Power mode of the Talon LRU PDU 2"
    )

    # ---------------
    # General methods
    # ---------------

    def always_executed_hook(self: TalonLRU) -> None:
        """
        Hook to be executed before any attribute access or command.
        """
        # PROTECTED REGION ID(TalonLRU.always_executed_hook) ENABLED START #
        # PROTECTED REGION END #    //  TalonLRU.always_executed_hook

    def delete_device(self: TalonLRU) -> None:
        """
        Uninitialize the device.
        """
        # PROTECTED REGION ID(TalonLRU.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  TalonLRU.delete_device

    def init_command_objects(self: TalonLRU) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)
        self.register_command_object("On", self.OnCommand(*device_args))
        self.register_command_object("Off", self.OffCommand(*device_args))

    # ------------------
    # Attributes methods
    # ------------------

    def read_PDU1PowerState(self: TalonLRU) -> PowerState:
        """
        Read the power mode of the outlet specified by PDU 1.

        :return: Power mode of PDU 1
        """
        return self.component_manager.pdu1_power_mode

    def read_PDU2PowerState(self: TalonLRU) -> PowerState:
        """
        Read the power mode of the outlet specified by PDU 2.

        :return: Power mode of PDU 2
        """
        return self.component_manager.pdu2_power_mode

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

    # --------
    # Commands
    # --------

    def create_component_manager(self: TalonLRU) -> TalonLRUComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerState] = None

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
            check_power_mode_callback=self._check_power_mode,
        )

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TalonLRU's init_device() "command".
        """

        def do(self: TalonLRU.InitCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation. Creates the device proxies
            to the power switch devices.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            (result_code, msg) = super().do()

            device = self.target
            device._power_switch_lock = Lock()

            # Setting initial simulation mode to True
            device.write_simulationMode(SimulationMode.TRUE)

            # check power mode in case of fault during communication establishment
            # device.component_manager.check_power_mode(device.get_state())

            return (result_code, msg)

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.

        Turn on both outlets that provide power to the LRU. Device is put into
        ON state if at least one outlet was successfully turned on.
        """

        def do(self: TalonLRU.OnCommand) -> Tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            device = self.target
            with device._power_switch_lock:
                # Check that this command is still allowed since the
                # _check_power_mode_callback could have changed the state
                self.is_allowed()
                return device.component_manager.on(
                    simulation_mode=device.read_simulationMode()
                )

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.

        Turn off both outlets that provide power to the LRU. Device is put in
        the OFF state if both outlets were successfully turned off.
        """

        def do(self: TalonLRU.OffCommand) -> Tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            device = self.target

            with device._power_switch_lock:
                # Check that this command is still allowed since the
                # _check_power_mode_callback could have changed the state
                self.is_allowed()
                return device.component_manager.off()


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonLRU.main) ENABLED START #
    return run((TalonLRU,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonLRU.main


if __name__ == "__main__":
    main()
