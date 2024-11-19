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

# Additional import
from ska_control_model import HealthState

# tango imports
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from tango import DebugIt
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.device.base_device import (
    CbfDevice,
    CbfFastCommand,
    DevVarLongStringArrayType,
)
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

    LRCTimeout = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    @attribute(dtype=str)
    def txDeviceName(self: SlimLink) -> str:
        """
        Read the txDeviceName of the device.

        :return: txDeviceName of the device.
        """
        return self.component_manager.tx_device_name

    @txDeviceName.write
    def txDeviceName(self: SlimLink, value: str) -> None:
        """
        Set the txDeviceName of the device.

        :param value: str
        """
        self.logger.debug(f"Writing txDeviceName to {value}")
        self.component_manager.tx_device_name = value

    @attribute(dtype=str)
    def rxDeviceName(self: SlimLink) -> str:
        """
        Read the rxDeviceName of the device.

        :return: rxDeviceName of the device.
        """
        return self.component_manager.rx_device_name

    @rxDeviceName.write
    def rxDeviceName(self: SlimLink, value: str) -> None:
        """
        Set the rxDeviceName of the device.

        :param value: str
        """
        self.logger.debug(f"Writing txDeviceName to {value}")
        self.component_manager.rx_device_name = value

    @attribute(dtype=str)
    def linkName(self: SlimLink) -> str:
        """
        Read the linkName of the device.

        :return: linkName of the device.
        """
        return self.component_manager.link_name

    @attribute(dtype=int)
    def txIdleCtrlWord(self: SlimLink) -> int:
        """
        Read the txIdleCtrlWord of the device.

        :return: txIdleCtrlWord of the device.
        """
        return self.component_manager.tx_idle_ctrl_word

    @attribute(dtype=int)
    def rxIdleCtrlWord(self: SlimLink) -> int:
        """
        Read the rxIdleCtrlWord of the device.

        :return: rxIdleCtrlWord of the device.
        """
        return self.component_manager.rx_idle_ctrl_word

    @attribute(dtype=float)
    def bitErrorRate(self: SlimLink) -> float:
        """
        Read the bitErrorRate of the device.

        :return: bitErrorRate of the device.
        """
        return self.component_manager.bit_error_rate

    @attribute(dtype=[int], max_dim_x=9)
    def counters(self: SlimLink) -> list[int]:
        """
        Read the counters attribute.

        :return: the counters array.
        :rtype: list[int]
        """
        return self.component_manager.read_counters()

    @attribute(dtype=HealthState)
    def healthState(self: SlimLink) -> HealthState:
        """
        Read the Health State of the device. This overrides the ska-tango-base
        implementation.

        :return: Health State of the device.
        :rtype: HealthState
        """
        return self._health_state

    @attribute(dtype=[bool], max_dim_x=4)
    def rxDebugAlignmentAndLockStatus(self: SlimLink) -> list[bool]:
        """
        Alignment and lock status rollup attribute for debug

        [0]: 66b block alignment lost. Read '1' = alignment lost. Write '1' to clear.
        [1]: 66b block aligned. Read '1' = aligned. Read only.
        [2]: Clock data recovery lock lost. Read '1' = CDR lock lost. Write '1' to clear.
        [3]: Clock data recovery locked. Read '1' = CDR locked. Read only.

        :return Alignment and lock status rollup attribute of the Rx Device
        :rtype list[bool]
        """
        return self.component_manager.rx_debug_alignment_and_lock_status

    @attribute(dtype=float)
    def rxLinkOccupancy(self: SlimLink) -> float:
        """
        Read the Link Occupancy of the Rx Device

        :return: The Rx Link Occupancy as a percentage (0-1)
        :rtype: float
        """
        return self.component_manager.rx_link_occupancy

    @attribute(dtype=float)
    def txLinkOccupancy(self: SlimLink) -> float:
        """
        Read the Link Occupancy of the Tx Device

        :return: The Tx Link Occupancy as a percentage (0-1)
        :rtype: float
        """
        return self.component_manager.tx_link_occupancy

    # --------------
    # Initialization
    # --------------

    def create_component_manager(self: SlimLink) -> SlimLinkComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device
        :rtype: SlimLinkComponentManager
        """
        self.logger.debug("Entering create_component_manager()")
        return SlimLinkComponentManager(
            lrc_timeout=int(self.LRCTimeout),
            logger=self.logger,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )

    def init_command_objects(self: SlimLink) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

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
            "VerifyConnection",
            self.VerifyConnectionCommand(
                component_manager=self.component_manager,
                logger=self.logger,
            ),
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
            "ClearCounters",
            self.ClearCountersCommand(
                component_manager=self.component_manager,
                logger=self.logger,
            ),
        )

    # -------------
    # Fast Commands
    # -------------

    class VerifyConnectionCommand(CbfFastCommand):
        """
        The command class for the VerifyConnection command.

        Run several health checks on the SLIM Link.
        """

        def is_allowed(self: SlimLink.VerifyConnectionCommand) -> bool:
            if self.component_manager.is_communicating:
                return True
            return False

        def do(
            self: SlimLink.VerifyConnectionCommand,
        ) -> tuple[ResultCode, str]:
            """
            Implement VerifyConnection command functionality.

            :return: The HealthState enum describing the link's status.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                return self.component_manager.verify_connection()
            else:
                return (
                    ResultCode.REJECTED,
                    "Device is offline. Failed to issue VerifyConnection command.",
                )

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def VerifyConnection(self: SlimLink) -> DevVarLongStringArrayType:
        command_handler = self.get_command_object("VerifyConnection")
        return_code, message = command_handler()
        return [[return_code], [message]]

    class ClearCountersCommand(CbfFastCommand):
        """
        The command class for the ClearCounters command.

        Clear the read counters array on Tx and Rx sides of the SLIM Link.
        """

        def is_allowed(self: SlimLink.ClearCountersCommand) -> bool:
            if self.component_manager.is_communicating:
                return True
            return False

        def do(self: SlimLink.ClearCountersCommand) -> tuple[ResultCode, str]:
            """
            Implement ClearCounters command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                return self.component_manager.clear_counters()
            else:
                return (
                    ResultCode.REJECTED,
                    "Device is offline. Failed to issue ClearCounters command.",
                )

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ClearCounters(self: SlimLink) -> DevVarLongStringArrayType:
        command_handler = self.get_command_object("ClearCounters")
        return_code, message = command_handler()
        return [[return_code], [message]]

    # ---------------------
    # Long Running Commands
    # ---------------------

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConnectTxRx(self: SlimLink) -> DevVarLongStringArrayType:
        command_handler = self.get_command_object("ConnectTxRx")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def DisconnectTxRx(self: SlimLink) -> DevVarLongStringArrayType:
        command_handler = self.get_command_object("DisconnectTxRx")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    # ----------
    # Callbacks
    # ----------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return SlimLink.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
