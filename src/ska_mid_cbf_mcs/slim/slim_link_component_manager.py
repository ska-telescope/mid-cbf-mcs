# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import logging
from typing import Callable, Optional

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, PowerMode, SimulationMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.slim.slim_link_simulator import SlimLinkSimulator

BER_PASS_THRESHOLD = 8.000e-11


class SlimLinkComponentManager(CbfComponentManager):
    """
    A component manager for a SLIM link, which is made up of a Tx and Rx device
    from the ds-slim-tx-rx HPS device server.
    """

    def __init__(
        self: SlimLinkComponentManager,
        update_health_state: Callable[[HealthState], None],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
    ) -> None:
        """
        Initialize a new instance.

        :param logger: a logger for this object to use
        :param update_health_state: method to call when link health state changes
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        self.connected = False
        self._simulation_mode = simulation_mode

        self._link_name = ""

        self._tx_device_name = ""
        self._rx_device_name = ""
        self._tx_device_proxy = None
        self._rx_device_proxy = None

        self._link_enabled = False  # True when tx rx are connected

        self.slim_link_simulator = SlimLinkSimulator(logger=logger)

        self._update_health_state = update_health_state

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    @property
    def tx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the tx device the link is associated with.

        :return: the tx device name.
        """
        return self._tx_device_name

    @tx_device_name.setter
    def tx_device_name(
        self: SlimLinkComponentManager, tx_device_name: str
    ) -> None:
        """
        Set the tx device name value.

        :param tx_device_name: The tx device name.
        """
        if self._simulation_mode:
            self.slim_link_simulator.tx_device_name = tx_device_name
        self._tx_device_name = tx_device_name

    @property
    def rx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the rx device the link is associated with.

        :return: the rx device name.
        """
        return self._rx_device_name

    @rx_device_name.setter
    def rx_device_name(
        self: SlimLinkComponentManager, rx_device_name: str
    ) -> None:
        """
        Set the rx device name value.

        :param rx_device_name: The rx device name.
        """
        if self._simulation_mode:
            self.slim_link_simulator.rx_device_name = rx_device_name
        self._rx_device_name = rx_device_name

    @property
    def link_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the link

        :return: the link name
        """
        return self._link_name

    @property
    def tx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        The idle control word value tx generates by hashing the tx's fqdn.

        :return: the tx idle control word.
        """
        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.tx_idle_ctrl_word
        if self._tx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_tx_idle_ctrl_word",
                "Tx Rx are not yet connected",
                "tx_idle_ctrl_word()",
            )

        return self._tx_device_proxy.idle_ctrl_word

    @property
    def rx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        The last idle control word read by rx from the datastream.

        :return: the rx idle control word.
        """
        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.rx_idle_ctrl_word
        if self._rx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_rx_idle_ctrl_word",
                "Tx Rx are not yet connected",
                "rx_idle_ctrl_word()",
            )

        return self._rx_device_proxy.idle_ctrl_word

    @property
    def bit_error_rate(self: SlimLinkComponentManager) -> float:
        """
        The bit error rate in 66b-word-errors per second.

        :return: The bit error rate.
        """
        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.bit_error_rate

        if self._rx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_Bit_Error_Rate",
                "Tx Rx are not yet connected",
                "bit_error_rate()",
            )

        return self._rx_device_proxy.bit_error_rate

    @property
    def simulation_mode(self):
        """
        Get the simulation mode
        """
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(self, value) -> None:
        """
        Set the simulation mode value.

        :param value: The simulation mode.
        """
        self._simulation_mode = value

    def read_counters(
        self: SlimLinkComponentManager,
    ) -> list[tango.DevULong64]:
        """
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

        :return: The read_counters array.
        """
        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.read_counters()

        if (
            not self._link_enabled
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            tango.Except.throw_exception(
                "SlimLink_Read_Counters",
                "Tx Rx are not yet connected",
                "read_counters()",
            )

        tx_counts = self._tx_device_proxy.read_counters
        rx_counts = self._rx_device_proxy.read_counters
        self._logger.debug(f"tx_counts = {tx_counts}")
        self._logger.debug(f"rx_counts = {rx_counts}")
        return [
            rx_counts[0],
            rx_counts[1],
            rx_counts[2],
            rx_counts[3],
            rx_counts[4],
            rx_counts[5],
            tx_counts[0],
            tx_counts[1],
            tx_counts[2],
        ]

    def start_communicating(self: SlimLinkComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        self._logger.debug(
            "Entering SlimLinkComponentManager.start_communicating()"
        )

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()

        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.connected = True

    def stop_communicating(self: SlimLinkComponentManager) -> None:
        """Stop communication with the component."""
        self._logger.debug(
            "Entering SlimLinkComponentManager.stop_communicating()"
        )
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False

    def connect_slim_tx_rx(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Link the Tx and Rx by setting them to use the same idle control word,
        and disable serial loopback. Begin monitoring the Tx and Rx.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "Entering SlimLinkComponentManager.connect_slim_tx_rx()  -  "
            + self._link_name
        )

        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.connect_slim_tx_rx()

        if self._rx_device_name == "" or self._tx_device_name == "":
            msg = "Tx or Rx device FQDN have not been set."
            return (ResultCode.FAILED, msg)

        try:
            self._tx_device_proxy = CbfDeviceProxy(
                fqdn=self._tx_device_name, logger=self._logger
            )
            self._rx_device_proxy = CbfDeviceProxy(
                fqdn=self._rx_device_name, logger=self._logger
            )

            # Sync the idle ctrl word between Tx and Rx
            idle_ctrl_word = self.tx_idle_ctrl_word
            self._rx_device_proxy.idle_ctrl_word = idle_ctrl_word

            # Take SLIM Rx out of serial loopback
            self._rx_device_proxy.initialize_connection(False)

            self.clear_counters()

        except tango.DevFailed as df:
            msg = f"Failed to connect Tx Rx: {df.args[0].desc}"
            self._logger.error(msg)
            self.update_component_fault(True)
            return (ResultCode.FAILED, msg)

        self._link_enabled = True
        self._link_name = f"{self._tx_device_name}->{self._rx_device_name}"
        return ResultCode.OK, "Connected Tx Rx successfully"

    def verify_connection(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Performs a health check on the SLIM link. No check is done if the link
        is not active, and the health state UNKNOWN will be returned.

        :return: the link HealthState. UNKNOWN if link is inactive. OK if link
                 is healthy. FAILED if problem has been detected.
        """
        self._logger.debug(
            "Entering SlimLinkComponentManager.verify_connection()  -  "
            + self._link_name
        )

        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.verify_connection()

        if (
            (not self._link_enabled)
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            msg = "Tx and Rx devices have not been connected."
            self._logger.debug(msg)
            self._update_health_state(HealthState.UNKNOWN)
            return ResultCode.OK, msg

        error_msg = ""
        error_flag = False
        try:
            if self.rx_idle_ctrl_word != self.tx_idle_ctrl_word:
                error_flag = True
                error_msg += (
                    "Expected and received idle control word do not match. "
                )
            counters = self.read_counters()
            if counters[4] != 0:
                error_flag = True
                error_msg += "block_lost_count not zero. "
            if counters[5] != 0:
                error_flag = True
                error_msg += "cdr_lost_count not zero. "
            if self.bit_error_rate > BER_PASS_THRESHOLD:
                error_flag = True
                error_msg += (
                    f"bit-error-rate higher than {BER_PASS_THRESHOLD}. "
                )
        except tango.DevFailed as df:
            error_msg = f"verify_connection() failed: {df.args[0].desc}"
            self._logger.error(error_msg)
            self._update_health_state(HealthState.FAILED)
            return ResultCode.FAILED, error_msg
        if error_flag:
            self._logger.warn(f"Link failed health check: {error_msg}")
            self._update_health_state(HealthState.FAILED)
            return ResultCode.OK, error_msg
        self._update_health_state(HealthState.OK)
        return ResultCode.OK, "Link health check OK"

    def disconnect_slim_tx_rx(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Stops controlling and monitoring the Tx and Rx devices. The link
        becomes inactive.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "Entering SlimLinkComponentManager.disconnect_slim_tx_rx()  -  "
            + self._link_name
        )
        if self._simulation_mode == SimulationMode.TRUE:
            return (self.slim_link_simulator.disconnect_slim_tx_rx(),)

        try:
            if self._rx_device_proxy is not None:
                # Put SLIM Rx back in serial loopback
                self._rx_device_proxy.initialize_connection(True)
        except tango.DevFailed:
            result_msg = (
                f"Failed to enable Rx loopback: {self._rx_device_name}"
            )
            self._logger.warn(result_msg)
            return ResultCode.FAILED, result_msg
        finally:
            self._rx_device_proxy = None
            self._tx_device_proxy = None
            self._link_name = ""
            self._link_enabled = False

        return ResultCode.OK, "Disconnected Tx Rx"

    def clear_counters(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Clears the Tx and Rx counters.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "Entering SlimLinkComponentManager.clearCounters()  -  "
            + self._link_name
        )
        if self._simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.clear_counters()

        if (
            (not self._link_enabled)
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            msg = "Tx and Rx devices have not been connected."
            return ResultCode.OK, msg

        try:
            self._tx_device_proxy.clear_read_counters()
            self._rx_device_proxy.clear_read_counters()
        except tango.DevFailed:
            result_msg = "Clearing counters failed: " + self._link_name
            self._logger.error(result_msg)
            return ResultCode.FAILED, result_msg

        return ResultCode.OK, "Counters cleared!"
