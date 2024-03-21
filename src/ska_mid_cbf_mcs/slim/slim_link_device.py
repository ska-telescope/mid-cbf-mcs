# -*- coding: utf-8 -*-
#
# This file is part of the SlimLink project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

from typing import Optional, Tuple

# tango imports
import tango
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import FastCommand, ResultCode

# Additional import
# PROTECTED REGION ID(SlimLink.additional_import) ENABLED START #
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerState,
    SimulationMode,
)
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.slim.slim_link_component_manager import (
    SlimLinkComponentManager,
)

# PROTECTED REGION END #    //  SlimLink.additional_import

__all__ = ["SlimLink", "main"]


class SlimLink(SKABaseDevice):
    """
    TANGO device class for SLIM link device.
    """

    # PROTECTED REGION ID(SlimLink.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  SlimLink.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    txDeviceName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Tx Device FQDN",
        doc="FQDN of the link's Tx device",
    )

    rxDeviceName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Rx Device FQDN",
        doc="FQDN of the link's Rx device",
    )

    linkName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        label="Link Name",
        doc="Link name made up of the Tx and Rx FQDNs",
    )

    txIdleCtrlWord = attribute(
        dtype="DevULong64",
        access=AttrWriteType.READ,
        label="Tx Idle control word",
        doc="Idle control word read by the link's Tx device",
    )

    rxIdleCtrlWord = attribute(
        dtype="DevULong64",
        access=AttrWriteType.READ,
        label="Rx Idle control word",
        doc="Idle control word read by the link's Rx device",
    )

    bitErrorRate = attribute(
        dtype="DevFloat",
        access=AttrWriteType.READ,
        label="Bit Error Rate",
        doc="Bit Error Rate (BER) calculated by the link's Rx device",
    )

    counters = attribute(
        dtype=("DevULong64",),
        max_dim_x=9,
        access=AttrWriteType.READ,
        label="TxRx Counters",
        doc="""
            An array holding the counter values from the tx and rx devices in the order:
            [0] rx_word_count
            [1] rx_packet_count
            [2] rx_idle_word_count
            [3] rx_idle_error_count
            [4] rx_block_lost_count
            [5] rx_cdr_lost_count
            [6] tx_word_count
            [7] tx_packet_count
            [8] tx_idle_word_count
        """,
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

    def create_component_manager(self: SlimLink) -> SlimLinkComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device
        :rtype: SlimLinkComponentManager
        """
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerState] = None
        self._health_state = HealthState.UNKNOWN

        return SlimLinkComponentManager(
            update_health_state=self._update_health_state,
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )

    def init_command_objects(self: SlimLink) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.logger)
        self.register_command_object(
            "ConnectTxRx", self.ConnectTxRxCommand(*device_args)
        )
        self.register_command_object(
            "VerifyConnection", self.VerifyConnectionCommand(*device_args)
        )
        self.register_command_object(
            "DisconnectTxRx",
            self.DisconnectTxRxCommand(*device_args),
        )
        self.register_command_object(
            "ClearCounters", self.ClearCountersCommand(*device_args)
        )

    def always_executed_hook(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        # PROTECTED REGION END #    //  SlimLink.always_executed_hook

    def delete_device(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.delete_device) ENABLED START #
        """Hook to delete device."""
        # PROTECTED REGION END #    //  SlimLink.delete_device

    # ----------
    # Callbacks
    # ----------

    def _communication_status_changed(
        self: SlimLink, communication_status: CommunicationStatus
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
        self: SlimLink, power_mode: PowerState
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

    def _component_fault(self: SlimLink, faulty: bool) -> None:
        """
        Handle component fault

        :param faulty: True if component is faulty.
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")

    def _update_health_state(self: SlimLink, state: HealthState) -> None:
        """
        Update the device's health state

        :param state: HealthState describing the link's status.
        """
        if self._health_state != state:
            self.logger.info(f"Updating health state to {state}")
            self._health_state = state
            self.push_change_event("healthState", self._health_state)

    # -----------------
    # Attribute Methods
    # -----------------

    def read_txDeviceName(self: SlimLink) -> str:
        # PROTECTED REGION ID(SlimLink.txDeviceName_read) ENABLED START #
        """
        Read the txDeviceName attribute.

        :return: the txDeviceName FQDN.
        :rtype: str
        """
        return self.component_manager.tx_device_name
        # PROTECTED REGION END #    //  SlimLink.txDeviceName_read

    def write_txDeviceName(self: SlimLink, value: str) -> None:
        # PROTECTED REGION ID(SlimLink.txDeviceName_write) ENABLED START #
        """
        Write the txDeviceName attribute.

        :param value: the txDeviceName FQDN.
        """
        self.component_manager.tx_device_name = value
        # PROTECTED REGION END #    //  SlimLink.txDeviceName_write

    def read_rxDeviceName(self: SlimLink) -> str:
        # PROTECTED REGION ID(SlimLink.rxDeviceName_read) ENABLED START #
        """
        Read the rxDeviceName attribute.

        :return: the rxDeviceName FQDN.
        :rtype: str
        """
        return self.component_manager.rx_device_name
        # PROTECTED REGION END #    //  SlimLink.rxDeviceName_read

    def write_rxDeviceName(self: SlimLink, value: str) -> None:
        # PROTECTED REGION ID(SlimLink.rxDeviceName_write) ENABLED START #
        """
        Write the rxDeviceName attribute.

        :param value: the rxDeviceName FQDN.
        """
        self.component_manager.rx_device_name = value
        # PROTECTED REGION END #    //  SlimLink.rxDeviceName_write

    def read_linkName(self: SlimLink) -> str:
        # PROTECTED REGION ID(SlimLink.linkName_read) ENABLED START #
        """
        Read the linkName attribute.

        :return: the link name. Empty if not active.
        :rtype: str
        """
        return self.component_manager.link_name
        # PROTECTED REGION END #    //  SlimLink.linkName_read

    def read_txIdleCtrlWord(self: SlimLink) -> int:
        # PROTECTED REGION ID(SlimLink.txIdleCtrlWord_read) ENABLED START #
        """
        Read the txIdleCtrlWord attribute.

        :return: the HPS tx device's idle ctrl word.
        :rtype: int
        """
        return self.component_manager.tx_idle_ctrl_word
        # PROTECTED REGION END #    //  SlimLink.txIdleCtrlWord_read

    def read_rxIdleCtrlWord(self: SlimLink) -> int:
        # PROTECTED REGION ID(SlimLink.rxIdleCtrlWord_read) ENABLED START #
        """
        Read the rxIdleCtrlWord attribute.

        :return: the HPS rx device's idle ctrl word.
        :rtype: int
        """
        return self.component_manager.rx_idle_ctrl_word
        # PROTECTED REGION END #    //  SlimLink.rxIdleCtrlWord_read

    def read_bitErrorRate(self: SlimLink) -> float:
        # PROTECTED REGION ID(SlimLink.bitErrorRate_read) ENABLED START #
        """
        Read the bitErrorRate attribute.

        :return: the bitErrorRate value.
        :rtype: float
        """
        return self.component_manager.bit_error_rate
        # PROTECTED REGION END #    //  SlimLink.bitErrorRate_read

    def read_counters(self: SlimLink) -> list[int]:
        # PROTECTED REGION ID(SlimLink.counters_read) ENABLED START #
        """
        Read the counters attribute.

        :return: the counters array.
        :rtype: list[int]
        """
        return self.component_manager.read_counters()
        # PROTECTED REGION END #    //  SlimLink.counters_read

    def read_healthState(self: SlimLink):
        # PROTECTED REGION ID(SlimLink.healthState_read) ENABLED START #
        """
        Read the Health State of the device. This overrides the ska-tango-base
        implementation.

        :return: Health State of the device.
        :rtype: HealthState
        """
        return self._health_state
        # PROTECTED REGION END #    //  SlimLink.healthState_read

    def read_simulationMode(self: SlimLink) -> SimulationMode:
        """
        Get the simulation mode.

        :return: the current simulation mode
        """
        return self.component_manager.simulation_mode
    
    def write_simulationMode(self, value):
        # PROTECTED REGION ID(SlimLink.simulationMode_write) ENABLED START #
        """
        Set the Simulation Mode of the device. This overrides the ska-tango-base
        implementation.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulation mode: {value}")
        self.component_manager.simulation_mode = value
        # PROTECTED REGION END #    //  SlimLink.simulationMode_write

    # --------
    # Commands
    # --------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the SlimLink's init_device() "command".
        """

        def do(self: SlimLink.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, message) = super().do()

            device = self._device
            device.write_simulationMode(True)

            return (result_code, message)

    class ConnectTxRxCommand(FastCommand):
        """
        The command class for the ConnectTxRx command.

        Connect the SLIM Tx and Rx HPS devices to form the link.
        """

        def do(
            self: SlimLink.ConnectTxRxCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement ConnectTxRx command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.target.read_adminMode() == AdminMode.ONLINE:
                component_manager = self.target.component_manager
                return component_manager.connect_slim_tx_rx()
            else:
                return (
                    ResultCode.FAILED,
                    "Device is offline. Failed to issue ConnectTxRx command.",
                )

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConnectTxRx(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.ConnectTxRx) ENABLED START #
        handler = self.get_command_object("ConnectTxRx")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.ConnectTxRx

    class VerifyConnectionCommand(FastCommand):
        """
        The command class for the VerifyConnection command.

        Run several health checks on the SLIM Link.
        """

        def do(
            self: SlimLink.VerifyConnectionCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement VerifyConnection command functionality.

            :return: The HealthState enum describing the link's status.
            :rtype: (ResultCode, str)
            """
            if self.target.read_adminMode() == AdminMode.ONLINE:
                component_manager = self.target.component_manager
                return component_manager.verify_connection()
            else:
                return (
                    ResultCode.FAILED,
                    "Device is offline. Failed to issue VerifyConnection command.",
                )

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def VerifyConnection(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.VerifyConnection) ENABLED START #
        handler = self.get_command_object("VerifyConnection")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.VerifyConnection

    class DisconnectTxRxCommand(FastCommand):
        """
        The command class for the DisconnectTxRx command.

        Disconnect the Tx and Rx devices. Set Rx to serial loopback mode.
        """

        def do(
            self: SlimLink.DisconnectTxRxCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement DisconnectTxRx command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.target.read_adminMode() == AdminMode.ONLINE:
                component_manager = self.target.component_manager
                return component_manager.disconnect_slim_tx_rx()
            else:
                return (
                    ResultCode.FAILED,
                    "Device is offline. Failed to issue DisconnectTxRx command.",
                )

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def DisconnectTxRx(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.DisconnectTxRx) ENABLED START #
        handler = self.get_command_object("DisconnectTxRx")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.DisconnectTxRx

    class ClearCountersCommand(FastCommand):
        """
        The command class for the ClearCounters command.

        Clear the read counters array on Tx and Rx sides of the SLIM Link.
        """

        def do(self: SlimLink.ClearCountersCommand) -> Tuple[ResultCode, str]:
            """
            Implement ClearCounters command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.target.read_adminMode() == AdminMode.ONLINE:
                component_manager = self.target.component_manager
                return component_manager.clear_counters()
            else:
                return (
                    ResultCode.FAILED,
                    "Device is offline. Failed to issue ClearCounters command.",
                )

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ClearCounters(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.ClearCounters) ENABLED START #
        handler = self.get_command_object("ClearCounters")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.ClearCounters


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(SlimLink.main) ENABLED START #
    return run((SlimLink,), args=args, **kwargs)
    # PROTECTED REGION END #    //  SlimLink.main


if __name__ == "__main__":
    main()
