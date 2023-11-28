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
from ska_tango_base.control_model import PowerMode, SimulationMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

BLOCK_LOST_COUNT_INDEX = 0
CDR_LOST_COUNT_INDEX = 1
BER_PASS_THRESHOLD = 8.000e-11


class SlimLinkComponentManager(CbfComponentManager):
    """
    A component manager for a SLIM link, which is made up of a Tx and Rx device
    from the ds-slim-tx-rx HPS device server.
    """

    def __init__(
        self: SlimLinkComponentManager,
        tx_device_name: str,
        rx_device_name: str,
        serial_loopback: bool,
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

        :param tx_device_name: a string containing the tx device's fqdn
        :param rx_device_name: a string containing the rx device's fqdn
        :param serial_loopback: a bool indicating if serial loopback mode will be enabled
        :param logger: a logger for this object to use
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

        self._logger.debug("Entering SlimLinkComponentManager.initDevice()")

        self.connected = False
        self._simulation_mode = simulation_mode

        # Initialize device attributes.
        self._tx_device_name = tx_device_name
        self._rx_device_name = rx_device_name
        self._link_name = f"{tx_device_name} -> {rx_device_name}"

        self._serial_loopback = serial_loopback

        self._tx_device_proxy = None
        self._rx_device_proxy = None

        self._link_healthy = False

        # FIXME: Driver and.or simulator???

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

        self._logger.info(f"Attempting to link {self._link_name}")

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
        self._rx_device_name = rx_device_name

    @property
    def debug_tx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        The idle control word value tx generates by hashing the tx's fqdn.

        :return: the tx idle control word.
        """
        return self._debug_tx_idle_ctrl_word

    @property
    def debug_rx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        The last idle control word read by rx from the datastream.

        :return: the rx idle control word.
        """
        return self._debug_rx_idle_ctrl_word

    @property
    def bit_error_rate(self: SlimLinkComponentManager) -> float:
        """
        The bit error rate in 66b-word-errors per second.

        :return: The bit error rate.
        """
        return self._bit_error_rate

    @property
    def link_occupancy(self: SlimLinkComponentManager) -> float[2]:
        """
        An array holding the link occupancy percentages on [0] the tx side, [1] the rx side.
        Ideally they should be the same.

        :return: The link occupancy array.
        """
        return self._link_occupancy

    @property
    def read_counters(self: SlimLinkComponentManager) -> int[7]:
        """
        An array holding the counter values from the tx and rx devices in the order:
        [0] rx_word_count
        [1] rx_packet_count
        [2] rx_idle_word_count
        [3] rx_idle_error_count
        [4] tx_word_count
        [5] tx_packet_count
        [6] tx_idle_word_count

        :return: The read_counters array.
        """
        return self._read_counters

    @property
    def block_lost_cdr_lost_count(self: SlimLinkComponentManager) -> int[2]:
        """
        An array holding [0]: block lost count, and [1]: cdr lost count.

        :return: The block_lost_cdr_lost_count array.
        """
        return self._block_lost_cdr_lost_count

    @property
    def link_healthy(self: SlimLinkComponentManager) -> bool:
        """
        A boolean indicating the health of the link, based on:
        idle words match, block/cdr lost count = 0, bit-error-rate below threshold.

        :return: The link_healthy value.
        """
        return self._link_healthy

    @link_healthy.setter
    def link_healthy(
        self: SlimLinkComponentManager, link_healthy: bool
    ) -> None:
        """
        Sets the link_healthy attribute

        :param link_healthy: The link_healthy value.
        """
        self._link_healthy = link_healthy

    def start_communicating(self: SlimLinkComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        self._logger.debug(
            "Entering SlimLinkComponentManager.start_communicating()"
        )

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()

        # FIXME: if not self._simulation_mode

        try:
            self._tx_device_proxy = CbfDeviceProxy(
                fqdn=self._tx_device_name, logger=self._logger
            )
            self._rx_device_proxy = CbfDeviceProxy(
                fqdn=self._rx_device_name, logger=self._logger
            )
            self._logger.info("Tx and Rx proxies instantiated.")
        except tango.DevFailed as df:
            self._logger.error(df.args[0].desc)
            self.update_component_power_mode(PowerMode.UNKNOWN)
            self.update_communication_status(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.update_component_fault(True)
            raise ConnectionError("Error in proxy connection.") from df

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

        # FIXME: if not self._simulation_mode:

    def connect_to_slim_tx(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        self._logger.debug(
            "Entering SlimLinkComponentManager.connect_to_slim_tx()  -  "
            + self._link_name
        )
        try:
            self.disconnect_from_slim_tx()
            ping = self._tx_device_proxy.ping()

            self._debug_tx_idle_ctrl_word = (
                self._tx_device_proxy.read_attribute("idle_ctrl_word")
            )

            result_msg = (
                "Connection to SLIM TX HPS device successful: "
                + self._tx_device_name
                + "; device ping took "
                + ping
                + " microseconds"
            )
            self._logger.info(result_msg)
            return ResultCode.OK, result_msg
        except tango.DevFailed as df:
            self._logger.error(df.args[0].desc)
            self.update_component_fault(True)
            return ResultCode.FAILED, (
                "Connection to SLIM TX HPS device failed: "
                + self._tx_device_name
            )

    def connect_to_slim_rx(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        self._logger.debug(
            "Entering SlimLinkComponentManager.connect_to_slim_rx()  -  "
            + self._link_name
        )
        try:
            self.disconnect_from_slim_rx()
            ping = self._rx_device_proxy.ping()

            # Take SLIM Rx out of serial loopback
            serial_loopback_enable = False
            self._rx_device_proxy.initialize_connection(serial_loopback_enable)

            self._debug_rx_idle_ctrl_word = (
                self._rx_device_proxy.read_attribute("idle_ctrl_word")
            )

            result_msg = (
                "Connection to SLIM RX Tango DS successful: "
                + self._rx_device_name
                + "; device ping took "
                + ping
                + " microseconds"
            )
            self._logger.info(result_msg)
            return ResultCode.OK, result_msg
        except tango.DevFailed as df:
            self._logger.error(df.args[0].desc)
            self.update_component_fault(True)
            return ResultCode.FAILED, (
                "Connection to SLIM RX HPS device failed: "
                + self._rx_device_name
            )

    def verify_connection(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        self._logger.debug(
            "Entering SlimLinkComponentManager.verify_connection()  -  "
            + self._link_name
        )

        self._link_healthy = False
        if self._tx_device_proxy and self._rx_device_proxy:
            result_msg = (
                "Valid connection between TX and RX devices: "
                + self._link_name
                + "! "
            )
            error_msg = ""

            try:
                expected_idle_ctrl_word = self._debug_tx_idle_ctrl_word
                rx_idle_ctrl_word = self._debug_rx_idle_ctrl_word
                counters = self._rx_device_proxy.read_attribute(
                    "block_lost_cdr_lost_count"
                )
                ber = self._rx_device_proxy.read_attribute("bit_error_rate")
                block_lost_count = counters[BLOCK_LOST_COUNT_INDEX]
                cdr_lost_count = counters[CDR_LOST_COUNT_INDEX]
                error_flag = False

                if rx_idle_ctrl_word != expected_idle_ctrl_word:
                    error_flag = True
                    result_msg = (
                        "Invalid connection between TX and RX device: "
                        + self._link_name
                        + "! "
                    )
                    error_msg += "Expected and received idle control word do not match. "
                if block_lost_count != 0:
                    error_flag = True
                    result_msg = (
                        "Invalid connection between TX and RX device: "
                        + self._link_name
                        + "! "
                    )
                    error_msg += "block_lost_count not zero. "
                if cdr_lost_count != 0:
                    error_flag = True
                    result_msg = (
                        "Invalid connection between TX and RX device: "
                        + self._link_name
                        + "! "
                    )
                    error_msg += "cdr_lost_count not zero. "
                if ber > BER_PASS_THRESHOLD:
                    error_flag = True
                    result_msg = (
                        "Invalid connection between TX and RX device: "
                        + self._link_name
                        + "! "
                    )
                    error_msg += (
                        "bit-error-rate higher than "
                        + BER_PASS_THRESHOLD
                        + ". "
                    )
                if not error_flag:
                    self._link_healthy = True
                    return ResultCode.OK, result_msg
                else:
                    self._logger.error(result_msg + error_msg)
                    return ResultCode.FAILED, (result_msg + error_msg)
            except tango.DevFailed as df:
                self._logger.error(df.args[0].desc)
                return ResultCode.FAILED, (result_msg + error_msg)
        else:
            result_msg = "Could not reach Tx or Rx proxy: " + self._link_name
            self._logger.error(result_msg)
            return ResultCode.FAILED, result_msg

    def disconnect_from_slim_tx(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        self._logger.debug(
            "Entering SlimLinkComponentManager.disconnectFromSlimTx()  -  "
            + self._link_name
        )
        try:
            if self._tx_device_proxy is not None:
                self._tx_device_proxy = None
                self._tx_device_name = None
                self._link_healthy = False
                result_msg = "Disconnected from SLIM Tx device."
            else:
                result_msg = "No SLIM Tx device was connected."
            return ResultCode.OK, result_msg
        except tango.DevFailed:
            result_msg = (
                "Disconnection from SLIM TX Tango DS failed: "
                + self._tx_device_name
            )
            self._logger.error(result_msg)
            return ResultCode.FAILED, result_msg

    def disconnect_from_slim_rx(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        self._logger.debug(
            "Entering SlimLinkComponentManager.disconnectFromSlimRx()  -  "
            + self._link_name
        )
        try:
            if self._rx_device_proxy is not None:
                # Put SLIM Rx back in serial loopback
                self._serial_loopback = True
                self._rx_device_proxy.initialize_connection(
                    self._serial_loopback
                )

                self._rx_device_proxy = None
                self._rx_device_name = None
                self._link_healthy = False
                result_msg = "Disconnected from SLIM Rx device."
            else:
                result_msg = "No SLIM Rx device was connected."
            return ResultCode.OK, result_msg
        except tango.DevFailed:
            result_msg = (
                "Disconnection from SLIM RX Tango DS failed: "
                + self._rx_device_name
            )
            self._logger.error(result_msg)
            return ResultCode.FAILED, result_msg

    def clear_counters(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        self._logger.debug(
            "Entering SlimLinkComponentManager.clearCounters()  -  "
            + self._link_name
        )
        try:
            self._tx_device_proxy.clear_read_counters()
            self._rx_device_proxy.clear_read_counters()
            self._read_counters = [0] * 7
            result_msg = "Counters cleared!"
            return ResultCode.OK, result_msg
        except tango.DevFailed:
            result_msg = "Clearing counters failed: " + self._link_name
            self._logger.error(result_msg)
            return ResultCode.FAILED, result_msg
