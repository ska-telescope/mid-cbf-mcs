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
from ska_tango_base.commands import ResponseCommand, ResultCode

# Additional import
# PROTECTED REGION ID(SlimLink.additional_import) ENABLED START #
from ska_tango_base.control_model import PowerMode, SimulationMode
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
    TANGO device class for slim link device
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
        label="FQDN of the link's Tx device",
        doc="FQDN of the link's Tx device",
    )
    rxDeviceName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="FQDN of the link's Rx device",
        doc="FQDN of the link's Rx device",
    )
    debugTxIdleCtrlWord = attribute(
        dtype="DevULong64",
        access=AttrWriteType.READ,
        label="Idle control word read by the link's Tx device",
        doc="Idle control word read by the link's Tx device",
    )
    debugRxIdleCtrlWord = attribute(
        dtype="DevULong64",
        access=AttrWriteType.READ,
        label="Idle control word read by the link's Rx device",
        doc="Idle control word read by the link's Rx device",
    )
    bitErrorRate = attribute(
        dtype="DevFloat",
        access=AttrWriteType.READ,
        label="Bit Error Rate (BER) calculated by the link's Rx device",
        doc="Bit Error Rate (BER) calculated by the link's Rx device",
    )
    linkOccupancy = attribute(
        dtype="DevFloat",
        access=AttrWriteType.READ,
        label="Link occupancy calculated by the link's Rx device",
        doc="Link occupancy calculated by the link's Rx device",
    )
    readCounters = attribute(
        dtype="DevLong64Array",
        access=AttrWriteType.READ,
        label="Array holding counts from both Tx and Rx devices",
        doc="""
            An array holding the counter values from the tx and rx devices in the order:
            [0] rx_word_count
            [1] rx_packet_count
            [2] rx_idle_word_count
            [3] rx_idle_error_count
            [4] tx_word_count
            [5] tx_packet_count
            [6] tx_idle_word_count
        """,
    )
    linkHealthy = attribute(
        dtype="DevBoolean",
        access=AttrWriteType.READ_WRITE,
        label="The health of the link summarized as a boolean",
        doc="The health of the link summarized as a boolean",
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
        """
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return SlimLinkComponentManager(
            tx_device_name=self.TxDeviceName,
            rx_device_name=self.RxDeviceName,
            serial_loopback=self.SerialLoopback,
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

        device_args = (self.component_manager, self.logger)
        self.register_command_object(
            "ConnectToSlimRx", self.ConnectToSlimRxCommand(*device_args)
        )
        self.register_command_object(
            "ConnectToSlimTx", self.ConnectToSlimTxCommand(*device_args)
        )
        self.register_command_object(
            "CerifyConnection", self.VerifyConnectionCommand(*device_args)
        )
        self.register_command_object(
            "DisconnectFromSlimTx",
            self.DisconnectFromSlimTxCommand(*device_args),
        )
        self.register_command_object(
            "DisconnectFromSlimRx",
            self.DisconnectFromSlimRxCommand(*device_args),
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
        self: SlimLink, power_mode: PowerMode
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

    def _component_fault(self: SlimLink, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")

    # -----------------
    # Attribute Methods
    # -----------------

    def read_txDeviceName(self: SlimLink) -> str:
        # PROTECTED REGION ID(SlimLink.txDeviceName_read) ENABLED START #
        """
        Read the txDeviceName attribute.

        :return: the txDeviceName fqdn.
        :rtype: str
        """
        return self.component_manager.tx_device_name
        # PROTECTED REGION END #    //  SlimLink.txDeviceName_read

    def write_txDeviceName(self: SlimLink, value: str) -> None:
        # PROTECTED REGION ID(SlimLink.txDeviceName_write) ENABLED START #
        """
        Write the txDeviceName attribute.

        :param value: the txDeviceName fqdn.
        """
        self.component_manager.tx_device_name = value
        # PROTECTED REGION END #    //  SlimLink.txDeviceName_write

    def read_rxDeviceName(self: SlimLink) -> str:
        # PROTECTED REGION ID(SlimLink.rxDeviceName_read) ENABLED START #
        """
        Read the rxDeviceName attribute.

        :return: the rxDeviceName fqdn.
        :rtype: str
        """
        return self.component_manager.rx_device_name
        # PROTECTED REGION END #    //  SlimLink.rxDeviceName_read

    def write_rxDeviceName(self: SlimLink, value: str) -> None:
        # PROTECTED REGION ID(SlimLink.rxDeviceName_write) ENABLED START #
        """
        Write the rxDeviceName attribute.

        :param value: the rxDeviceName fqdn.
        """
        self.component_manager.rx_device_name = value
        # PROTECTED REGION END #    //  SlimLink.rxDeviceName_write

    def read_debugTxIdleCtrlWord(self: SlimLink) -> int:
        # PROTECTED REGION ID(SlimLink.debugTxIdleCtrlWord_read) ENABLED START #
        """
        Read the debugTxIdleCtrlWord attribute.

        :return: the tx device's idle ctrl word.
        :rtype: int
        """
        return self.component_manager.debug_tx_idle_ctrl_word
        # PROTECTED REGION END #    //  SlimLink.debugTxIdleCtrlWord_read

    def read_debugRxIdleCtrlWord(self: SlimLink) -> int:
        # PROTECTED REGION ID(SlimLink.debugRxIdleCtrlWord_read) ENABLED START #
        """
        Read the debugRxIdleCtrlWord attribute.

        :return: the rx device's idle ctrl word.
        :rtype: int
        """
        return self.component_manager.debug_rx_idle_ctrl_word
        # PROTECTED REGION END #    //  SlimLink.debugRxIdleCtrlWord_read

    def read_bitErrorRate(self: SlimLink) -> float:
        # PROTECTED REGION ID(SlimLink.bitErrorRate_read) ENABLED START #
        """
        Read the bitErrorRate attribute.

        :return: the bitErrorRate value.
        :rtype: float
        """
        return self.component_manager.bit_error_rate
        # PROTECTED REGION END #    //  SlimLink.bitErrorRate_read

    def read_linkOccupancy(self: SlimLink) -> float:
        # PROTECTED REGION ID(SlimLink.linkOccupancy_read) ENABLED START #
        """
        Read the linkOccupancy attribute.

        :return: the linkOccupancy value.
        :rtype: float
        """
        return self.component_manager.link_occupancy
        # PROTECTED REGION END #    //  SlimLink.linkOccupancy_read

    def read_readCounters(self: SlimLink) -> int[7]:
        # PROTECTED REGION ID(SlimLink.readCounters_read) ENABLED START #
        """
        Read the readCounters attribute.

        :return: the readCounters array.
        :rtype: int[7]
        """
        return self.component_manager.read_counters
        # PROTECTED REGION END #    //  SlimLink.readCounters_read

    def read_blockLostCdrLostCount(self: SlimLink) -> int[2]:
        # PROTECTED REGION ID(SlimLink.blockLostCdrLostCount_read) ENABLED START #
        """
        Read the blockLostCdrLostCount attribute.

        :return: the blockLostCdrLostCount array.
        :rtype: int[2]
        """
        return self.component_manager.block_lost_cdr_lost_count
        # PROTECTED REGION END #    //  SlimLink.blockLostCdrLostCount_read

    def read_linkHealthy(self: SlimLink) -> bool:
        # PROTECTED REGION ID(SlimLink.linkHealthy_read) ENABLED START #
        """
        Read the linkHealthy attribute.

        :return: the linkHealthy value.
        :rtype: bool
        """
        return self.component_manager.link_healthy
        # PROTECTED REGION END #    //  SlimLink.linkHealthy_read

    def write_linkHealthy(self: SlimLink, value: bool) -> None:
        # PROTECTED REGION ID(SlimLink.linkHealthy_write) ENABLED START #
        """
        Write the linkHealthy attribute.

        :param value: the linkHealthy value.
        """
        self.component_manager.link_healthy = value
        # PROTECTED REGION END #    //  SlimLink.linkHealthy_write

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
            """
            (result_code, message) = super().do()

            device = self.target
            device.write_simulationMode(True)

            return (result_code, message)

    class ConnectToSlimTxCommand(ResponseCommand):
        """
        The command class for the ConnectToSlimTx command.

        Connect to a SLIM Tx HPS device.
        """

        def do(
            self: SlimLink.ConnectToSlimTxCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement ConnectToSlimTx command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.connect_to_slim_tx()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConnectToSlimTx(self: SlimLink) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(SlimLink.ConnectToSlimTx) ENABLED START #
        handler = self.get_command_object("ConnectToSlimTx")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.ConnectToSlimTx

    class ConnectToSlimRxCommand(ResponseCommand):
        """
        The command class for the ConnectToSlimRx command.

        Connect to a SLIM Rx HPS device.
        """

        def do(
            self: SlimLink.ConnectToSlimRxCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement ConnectToSlimRx command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.connect_to_slim_rx()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConnectToSlimRx(self: SlimLink) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(SlimLink.ConnectToSlimRx) ENABLED START #
        handler = self.get_command_object("ConnectToSlimRx")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.ConnectToSlimRx

    class VerifyConnectionCommand(ResponseCommand):
        """
        The command class for the VerifyConnection command.

        Run several health checks on the SLIM Link.
        """

        def do(
            self: SlimLink.VerifyConnectionCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement VerifyConnection command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.verify_connection()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def VerifyConnection(self: SlimLink) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(SlimLink.VerifyConnection) ENABLED START #
        handler = self.get_command_object("VerifyConnection")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.VerifyConnection

    class DisconnectFromSlimTxCommand(ResponseCommand):
        """
        The command class for the DisconnectFromSlimTx command.

        Disconnect from a SLIM Tx HPS device.
        """

        def do(
            self: SlimLink.DisconnectFromSlimTxCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement DisconnectFromSlimTx command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.disconnect_from_slim_tx()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def DisconnectFromSlimTx(self: SlimLink) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(SlimLink.DisconnectFromSlimTx) ENABLED START #
        handler = self.get_command_object("DisconnectFromSlimTx")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.DisconnectFromSlimTx

    class DisconnectFromSlimRxCommand(ResponseCommand):
        """
        The command class for the DisconnectFromSlimRx command.

        Disconnect from a SLIM Rx HPS device.
        """

        def do(
            self: SlimLink.DisconnectFromSlimRxCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Implement DisconnectFromSlimRx command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.disconnect_from_slim_rx()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def DisconnectFromSlimRx(self: SlimLink) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(SlimLink.DisconnectFromSlimRx) ENABLED START #
        handler = self.get_command_object("DisconnectFromSlimRx")
        return_code, message = handler()
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  SlimLink.DisconnectFromSlimRx

    class ClearCountersCommand(ResponseCommand):
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
            """
            component_manager = self.target
            return component_manager.clear_counters()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ClearCounters(self: SlimLink) -> tango.DevVarLongStringArray:
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
