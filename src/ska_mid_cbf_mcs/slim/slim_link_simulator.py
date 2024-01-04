# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState

__all__ = ["SlimLinkSimulator"]

BLOCK_LOST_COUNT_INDEX = 0
CDR_LOST_COUNT_INDEX = 1
BER_PASS_THRESHOLD = 8.000e-11


class SlimLinkSimulator:
    """
    A simulator for the SLIM Link.

    :param link_name: Name to describe the link.
    :param logger: a logger for this object to use
    """

    def __init__(self: SlimLinkSimulator, logger: logging.Logger) -> None:
        """
        Initialise a new instance.
        """
        self._logger = logger

        self._link_name = ""
        self._tx_device_name = ""
        self._rx_device_name = ""
        self._tx_idle_ctrl_word = 0x1B849FDE
        self._rx_idle_ctrl_word = 0xFFFFFFFF
        self._bit_error_rate = 0
        self._link_enabled = False
        self._read_counters = [0] * 9
        self._block_lost_cdr_lost_count = [0] * 2

    @property
    def tx_device_name(self: SlimLinkSimulator) -> str:
        """
        The name of the tx device the link is associated with.

        :return: the tx device name.
        """
        return self._tx_device_name

    @tx_device_name.setter
    def tx_device_name(self: SlimLinkSimulator, tx_device_name: str) -> None:
        """
        Set the tx device name value.

        :param tx_device_name: The tx device name.
        """
        self._tx_device_name = tx_device_name

    @property
    def rx_device_name(self: SlimLinkSimulator) -> str:
        """
        The name of the rx device the link is associated with.

        :return: the rx device name.
        """
        return self._rx_device_name

    @rx_device_name.setter
    def rx_device_name(self: SlimLinkSimulator, rx_device_name: str) -> None:
        """
        Set the rx device name value.

        :param rx_device_name: The rx device name.
        """
        self._rx_device_name = rx_device_name

    @property
    def tx_idle_ctrl_word(self: SlimLinkSimulator) -> int:
        """
        The idle control word value tx generates by hashing the tx's fqdn.

        :return: the tx idle control word.
        """
        return self._tx_idle_ctrl_word

    @property
    def rx_idle_ctrl_word(self: SlimLinkSimulator) -> int:
        """
        The last idle control word read by rx from the datastream.

        :return: the rx idle control word.
        """
        return self._rx_idle_ctrl_word

    @property
    def bit_error_rate(self: SlimLinkSimulator) -> float:
        """
        The bit error rate in 66b-word-errors per second.

        :return: A passing bit error rate.
        """
        return 8.000e-12

    def read_counters(self: SlimLinkSimulator) -> list[tango.DevULong64]:
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
        return self._read_counters

    def connect_slim_tx_rx(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        if self._tx_device_name == "" or self._rx_device_name == "":
            return ResultCode.FAILED, "Tx/Rx device name not set"
        self._rx_idle_ctrl_word = self._tx_idle_ctrl_word
        self._read_counters = [
            100000,
            200000,
            300000,
            0,
            0,
            0,
            100000,
            200000,
            300000,
        ]
        self._link_enabled = True
        return ResultCode.OK, "Connection to SLIM TX simulator successful"

    def verify_connection(
        self: SlimLinkSimulator,
    ) -> HealthState:
        if self._link_enabled:
            return ResultCode.OK, "link is healthy"
        return ResultCode.OK, "link is not active"

    def disconnect_slim_tx_rx(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        self.clear_counters()
        self._link_enabled = False
        result_msg = "Disconnected from SLIM Tx simulator."
        return ResultCode.OK, result_msg

    def clear_counters(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        self._read_counters = [0] * 9
        result_msg = "Cleared counters for SLIM Link simulator."
        return ResultCode.OK, result_msg
