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

    def __init__(
        self: SlimLinkSimulator, link_name: str, logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.
        """
        self._logger = logger

        self._link_name = link_name
        self._tx_device_name = link_name.split("->")[0]
        self._rx_device_name = link_name.split("->")[1]
        self._tx_idle_ctrl_word = 0
        self._rx_idle_ctrl_word = 0
        self._bit_error_rate = 0
        self._read_counters = [0] * 7
        self._block_lost_cdr_lost_count = [0] * 2

    @property
    def tx_device_name(self: SlimLinkSimulator) -> str:
        """
        The name of the tx device the link is associated with.

        :return: the tx device name.
        """
        return self._tx_device_name

    @property
    def rx_device_name(self: SlimLinkSimulator) -> str:
        """
        The name of the rx device the link is associated with.

        :return: the rx device name.
        """
        return self._rx_device_name

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

    @property
    def read_counters(self: SlimLinkSimulator) -> int[7]:
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
        # FIXME: This may need more appropriate values
        return [1, 2, 3, 4, 5, 6, 7]

    @property
    def block_lost_cdr_lost_count(self: SlimLinkSimulator) -> int[2]:
        """
        An array holding [0]: block lost count, and [1]: cdr lost count.

        :return: The block_lost_cdr_lost_count array.
        """
        return [0, 0]

    def connect_to_slim_tx(
        self: SlimLinkSimulator,
    ) -> str:
        self._tx_idle_ctrl_word = 0xDECAFBAD
        result_msg = (
            "Connection to SLIM TX simulator successful: "
            + self._tx_device_name
        )
        return result_msg

    def connect_to_slim_rx(
        self: SlimLinkSimulator,
    ) -> str:
        self._rx_idle_ctrl_word = 0xDECAFBAD
        result_msg = (
            "Connection to SLIM RX simulator successful: "
            + self._rx_device_name
        )
        return result_msg

    def verify_connection(
        self: SlimLinkSimulator,
    ) -> tuple[bool, str]:
        result_msg = (
            "Valid connection between TX and RX simulators: "
            + self._link_name
            + "! "
        )
        return True, result_msg

    def disconnect_from_slim_tx(
        self: SlimLinkSimulator,
    ) -> str:
        self._tx_device_name = None
        self.clear_counters()
        result_msg = "Disconnected from SLIM Tx simulator."
        return result_msg

    def disconnect_from_slim_rx(
        self: SlimLinkSimulator,
    ) -> str:
        self._rx_device_name = None
        self.clear_counters()
        result_msg = "Disconnected from SLIM Rx simulator."
        return result_msg

    def clear_counters(
        self: SlimLinkSimulator,
    ) -> str:
        self._read_counters = [0] * 7
        result_msg = "Cleared counters for SLIM Link simulator."
        return result_msg
