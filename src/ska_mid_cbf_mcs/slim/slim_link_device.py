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
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import (
    FastCommand,
    ResultCode,
    SubmittedSlowCommand,
)

# Additional import
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerState,
    SimulationMode,
)
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.device.base_device import CbfDevice
from ska_mid_cbf_mcs.slim.slim_link_component_manager import (
    SlimLinkComponentManager,
)

__all__ = ["SlimLink", "main"]


class SlimLink(CbfDevice):
    """
    TANGO device class for SLIM link device.
    """

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
            logger=self.logger,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self: SlimLink) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.logger)
        self.register_command_object(
            "ConnectTxRx",
            SubmittedSlowCommand(
                command_name="ConnectTxRx",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="connect_slim_tx_rx",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "VerifyConnection", self.VerifyConnectionCommand(*device_args)
        )
        self.register_command_object(
            "DisconnectTxRx",
            SubmittedSlowCommand(
                command_name="DisconnectTxRx",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="disconnect_slim_tx_rx",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "ClearCounters", self.ClearCountersCommand(*device_args)
        )

    def always_executed_hook(self: SlimLink) -> None:
        """Hook to be executed before any commands."""

    def delete_device(self: SlimLink) -> None:
        """Hook to delete device."""

    # ----------
    # Callbacks
    # ----------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.

    # -----------------
    # Attribute Methods
    # -----------------

    def read_txDeviceName(self: SlimLink) -> str:
        """
        Read the txDeviceName attribute.

        :return: the txDeviceName FQDN.
        :rtype: str
        """
        return self.component_manager.tx_device_name

    def write_txDeviceName(self: SlimLink, value: str) -> None:
        """
        Write the txDeviceName attribute.

        :param value: the txDeviceName FQDN.
        """
        self.component_manager.tx_device_name = value

    def read_rxDeviceName(self: SlimLink) -> str:
        """
        Read the rxDeviceName attribute.

        :return: the rxDeviceName FQDN.
        :rtype: str
        """
        return self.component_manager.rx_device_name

    def write_rxDeviceName(self: SlimLink, value: str) -> None:
        """
        Write the rxDeviceName attribute.

        :param value: the rxDeviceName FQDN.
        """
        self.component_manager.rx_device_name = value

    def read_linkName(self: SlimLink) -> str:
        """
        Read the linkName attribute.

        :return: the link name. Empty if not active.
        :rtype: str
        """
        return self.component_manager.link_name

    def read_txIdleCtrlWord(self: SlimLink) -> int:
        """
        Read the txIdleCtrlWord attribute.

        :return: the HPS tx device's idle ctrl word.
        :rtype: int
        """
        return self.component_manager.tx_idle_ctrl_word

    def read_rxIdleCtrlWord(self: SlimLink) -> int:
        """
        Read the rxIdleCtrlWord attribute.

        :return: the HPS rx device's idle ctrl word.
        :rtype: int
        """
        return self.component_manager.rx_idle_ctrl_word

    def read_bitErrorRate(self: SlimLink) -> float:
        """
        Read the bitErrorRate attribute.

        :return: the bitErrorRate value.
        :rtype: float
        """
        return self.component_manager.bit_error_rate

    def read_counters(self: SlimLink) -> list[int]:
        """
        Read the counters attribute.

        :return: the counters array.
        :rtype: list[int]
        """
        return self.component_manager.read_counters()

    def read_healthState(self: SlimLink):
        """
        Read the Health State of the device. This overrides the ska-tango-base
        implementation.

        :return: Health State of the device.
        :rtype: HealthState
        """
        return self._health_state

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: SlimLink) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: SlimLink, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

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
            self._device._simulation_mode = True

            return (result_code, message)

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConnectTxRx(self: SlimLink) -> None:
        command_handler = self.get_command_object("ConnectTxRx")
        result_code_message, command_id = command_handler()
        return [[result_code_message], [command_id]]

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
        handler = self.get_command_object("VerifyConnection")
        return_code, message = handler()
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def DisconnectTxRx(self: SlimLink) -> None:
        command_handler = self.get_command_object("DisconnectTxRx")
        result_code_message, command_id = command_handler()
        return [[result_code_message], [command_id]]

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
