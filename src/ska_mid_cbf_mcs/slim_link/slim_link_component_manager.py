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
from ska_tango_base.control_model import PowerMode

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
    A component manager for a SLIM link.
    """

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
        The idle control word value tx by hashing the link's tx fqdn.

        :return: the tx idle control word.
        """
        return self._debug_tx_idle_ctrl_word

    @debug_tx_idle_ctrl_word.setter
    def debug_tx_idle_ctrl_word(
        self: SlimLinkComponentManager, debug_tx_idle_ctrl_word: int
    ) -> None:
        """
        Set the tx idle control word value.

        :param debug_tx_idle_ctrl_word: The tx idle control word.
        """
        self._debug_tx_idle_ctrl_word = debug_tx_idle_ctrl_word

    @property
    def debug_rx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        Mirrors the SLIM Rx's idle_ctrl_word attr.
        Reading this register will return the last idle control word captured from the datastream.

        :return: the rx idle control word.
        """
        return self._debug_rx_idle_ctrl_word

    @debug_rx_idle_ctrl_word.setter
    def debug_rx_idle_ctrl_word(
        self: SlimLinkComponentManager, debug_rx_idle_ctrl_word: int
    ) -> None:
        """
        Mirrors the SLIM Rx's idle_ctrl_word attr.
        Writing this register will change the idle control word used for error comparison.

        :param debug_rx_idle_ctrl_word: The rx idle control word.
        """
        self._debug_rx_idle_ctrl_word = debug_rx_idle_ctrl_word

    @property
    def bit_error_rate(self: SlimLinkComponentManager) -> float:
        """
        The bit error rate in 66b-word-errors per second.

        :return: The bit error rate.
        """
        return self._bit_error_rate

    @bit_error_rate.setter
    def bit_error_rate(
        self: SlimLinkComponentManager, bit_error_rate: float
    ) -> None:
        """
        Sets the bit error rate in 66b-word-errors per second.

        :param bit_error_rate: The bit error rate.
        """
        self._bit_error_rate = bit_error_rate

    @property
    def link_occupancy(self: SlimLinkComponentManager) -> float[2]:
        """
        An array holding the link occupancy percentages on [0] the tx side, [1] the rx side.
        Ideally they should be the same.

        :return: The link occupancy array.
        """
        return self._link_occupancy

    @link_occupancy.setter
    def link_occupancy(
        self: SlimLinkComponentManager, link_occupancy: float[2]
    ) -> None:
        """
        Sets the link occupancy array. [0] the tx side, [1] the rx side
        Ideally they should be the same.

        :param link_occupancy: The link occupancy array.
        """
        self._link_occupancy = link_occupancy

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

    @read_counters.setter
    def read_counters(
        self: SlimLinkComponentManager, read_counters: int[7]
    ) -> None:
        """
        Sets the read_counters array in the order:
        [0] rx_word_count
        [1] rx_packet_count
        [2] rx_idle_word_count
        [3] rx_idle_error_count
        [4] tx_word_count
        [5] tx_packet_count
        [6] tx_idle_word_count

        :param read_counters: The read_counters array.
        """
        self._read_counters = read_counters

    @property
    def block_lost_cdr_lost_count(self: SlimLinkComponentManager) -> int[2]:
        """
        An array holding [0]: block lost count, and [1]: cdr lost count.

        :return: The block_lost_cdr_lost_count array.
        """
        return self._block_lost_cdr_lost_count

    @block_lost_cdr_lost_count.setter
    def block_lost_cdr_lost_count(
        self: SlimLinkComponentManager, block_lost_cdr_lost_count: int[2]
    ) -> None:
        """
        Sets the block_lost_cdr_lost_count array.
        [0] = block lost count, and [1] = cdr lost count.

        :param block_lost_cdr_lost_count: The block_lost_cdr_lost_count array.
        """
        self._block_lost_cdr_lost_count = block_lost_cdr_lost_count

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

        self._logger.debug(
            "SLIMLink  --  initDevice()  - " + self._device_name
        )

        self.connected = False

        self._tx_device_name = tx_device_name
        self._rx_device_name = rx_device_name

        self._serial_loopback = serial_loopback

        self._tx_device_proxy = None
        self._rx_device_proxy = None

        self._link_healthy = False

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )

        self._logger.info(
            f"SLIMLink  --  Linking {tx_device_name} to {rx_device_name}"
        )

    def start_communicating(self: SlimLinkComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        self._logger.debug("SLIMLink  --  startCommunicating()")

        if self.connected:
            self._logger.info("SLIMLink  --  Already communicating.")
            return

        super().start_communicating()

        try:
            self._tx_device_proxy = CbfDeviceProxy(
                fqdn=self._tx_device_name, logger=self._logger
            )
            self._rx_device_proxy = CbfDeviceProxy(
                fqdn=self._rx_device_name, logger=self._logger
            )
            self._logger.info("SLIMLink  --  Connection initialized.")
        except tango.DevFailed:
            self.update_component_fault(True)
            self._logger.error("SLIMLink  --  Error in proxy connection")
            # FIXME: throw?
            return

        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.ON)
        self.update_component_fault(False)

    def stop_communicating(self: SlimLinkComponentManager) -> None:
        """Stop communication with the component."""
        self._logger.debug("SLIMLink  --  stopCommunicating()")
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = False

    def connect_to_slim_tx(self: SlimLinkComponentManager) -> None:
        self._logger.debug(
            "SLIMLink  --  connectToSlimTx()  - " + self._tx_device_name
        )
        try:
            self.disconnect_from_slim_tx()
            ping = self._tx_device_proxy.ping()

            self._debug_tx_idle_ctrl_word = (
                self._tx_device_proxy.read_attribute("idle_ctrl_word")
            )

            self._logger.info(
                "SLIMLink  --  Connection to SLIM TX Tango DS successful. tx_device_name: "
                + self._tx_device_name
                + "; device ping took "
                + ping
                + " microseconds"
            )
        except tango.DevFailed:
            msg = (
                "connection to SLIM TX Tango DS failed: "
                + self._tx_device_name
            )
            self._logger.error(msg)
            # TODO: setstate()??
            self.update_component_fault(True)
            # TODO: Should throwing happen in device instead?
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "connectToSLIMTx execution",
                tango.ErrSeverity.ERR,
            )

    def connect_to_slim_rx(self: SlimLinkComponentManager) -> None:
        self._logger.debug(
            "SLIMLink  --  connectToSlimRx()  - " + self._rx_device_name
        )
        try:
            self.disconnect_from_slim_rx()
            ping = self._rx_device_proxy.ping()

            # Take SLIM Rx out of serial loopback
            serial_loopback_enable = False
            self._rx_device_proxy.initialize_connection(serial_loopback_enable)

            self._rx_device_proxy.write_attribute(
                "idle_ctrl_word", self._debug_rx_idle_ctrl_word
            )

            self._logger.info(
                "SLIMLink  --  Connection to SLIM RX Tango DS successful. rx_device_name: "
                + self._rx_device_name
                + "; device ping took "
                + ping
                + " microseconds"
            )
        except tango.DevFailed:
            msg = (
                "connection to SLIM RX Tango DS failed: "
                + self._rx_device_name
            )
            self._logger.error(msg)
            # TODO: setstate()??
            self.update_component_fault(True)
            # TODO: Should throwing happen in device instead?
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "connectToSLIMRx execution",
                tango.ErrSeverity.ERR,
            )

    def verify_connection(self: SlimLinkComponentManager) -> bool:
        self._link_healthy = False
        self._logger.debug(
            "SLIMLink  --  verifyConnection()  - " + self._device_name
        )

        if self._tx_device_proxy and self._rx_device_proxy:
            result_msg = "Valid connection between TX and RX devices! "
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
                check1, check2, check3, check4 = True

                if rx_idle_ctrl_word != expected_idle_ctrl_word:
                    check1 = False
                    result_msg = (
                        "Invalid connection between TX and RX device! "
                    )
                    error_msg += "Expected and received idle control word do not match. "
                if block_lost_count != 0:
                    check2 = False
                    result_msg = (
                        "Invalid connection between TX and RX device! "
                    )
                    error_msg += "block_lost_count not zero. "
                if cdr_lost_count != 0:
                    check3 = False
                    result_msg = (
                        "Invalid connection between TX and RX device! "
                    )
                    error_msg += "cdr_lost_count not zero. "
                if ber > BER_PASS_THRESHOLD:
                    check4 = False
                    result_msg = (
                        "Invalid connection between TX and RX device! "
                    )
                    error_msg += (
                        "bit-error-rate higher than "
                        + BER_PASS_THRESHOLD
                        + "! "
                    )
                if check1 and check2 and check3 and check4:
                    self._link_healthy = True

                self._logger.debug(
                    "SLIMLink  --  verifyConnection()  - "
                    + result_msg
                    + error_msg
                )
            except tango.DevFailed:
                msg = (
                    "verifying SLIM Link connection failed: "
                    + self._tx_device_name
                    + "->"
                    + self._rx_device_name
                )
                self._logger.error(msg)
                tango.Except.throw_exception(
                    "Command failed",
                    msg,
                    "verifyConnection execution",
                    tango.ErrSeverity.ERR,
                )
        else:
            self._logger.error("SLIMLink  --  Must connect Tx and Rx device!")
            # FIXME: throw?

        return self._link_healthy

    def disconnect_from_slim_tx(self: SlimLinkComponentManager) -> None:
        self._logger.debug(
            "SLIMLink  --  disconnectFromSlimTx()  - " + self._tx_device_name
        )
        try:
            if self._tx_device_proxy is not None:
                self._tx_device_proxy = None
                self._tx_device_name = None
                self._link_healthy = False
                self._logger.debug(
                    "SLIMLink  --  Disconnected from SLIM Tx device."
                )
            else:
                self._logger.debug(
                    "SLIMLink  --  Already disconnected from SLIM Tx device."
                )
        except tango.DevFailed:
            msg = (
                "disconnection from SLIM TX Tango DS failed: "
                + self._tx_device_name
            )
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "disconnectFromSLIMTx execution",
                tango.ErrSeverity.ERR,
            )

    def disconnect_from_slim_rx(self: SlimLinkComponentManager) -> None:
        self._logger.debug(
            "SLIMLink  --  disconnectFromSlimRx()  - " + self._rx_device_name
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
                self._logger.debug(
                    "SLIMLink  --  Disconnected from SLIM Rx device."
                )
            else:
                self._logger.debug(
                    "SLIMLink  --  Already disconnected from SLIM Rx device."
                )
        except tango.DevFailed:
            msg = (
                "disconnection from SLIM RX Tango DS failed: "
                + self._rx_device_name
            )
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "disconnectFromSLIMRx execution",
                tango.ErrSeverity.ERR,
            )

    def clear_counters(self: SlimLinkComponentManager) -> None:
        self._logger.debug(
            "SLIMLink  --  clearCounters()  - "
            + self._tx_device_name
            + "->"
            + self._rx_device_name
        )
        try:
            self._tx_device_proxy.clear_read_counters()
            self._rx_device_proxy.clear_read_counters()
            self._read_counters = [0, 0, 0, 0, 0, 0, 0]
            self._logger.debug("SLIMLink  --  counters cleared!")
        except tango.DevFailed:
            msg = "clearing counters failed "
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "disconnectFromSLIMRx execution",
                tango.ErrSeverity.ERR,
            )
