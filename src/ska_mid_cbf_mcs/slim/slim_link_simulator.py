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
from typing import List

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.power_switch.pdu_common import Outlet

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
        self._debug_tx_idle_ctrl_word = 0
        self._debug_rx_idle_ctrl_word = 0
        self._bit_error_rate = 0
        self._link_occupancy = 0
        self._read_counters = [0]*7
        self._block_lost_cdr_lost_count = [0]*2
        self._link_healthy = False

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
    def debug_tx_idle_ctrl_word(self: SlimLinkSimulator) -> int:
        """
        The idle control word value tx generates by hashing the tx's fqdn.

        :return: the tx idle control word.
        """
        return self._debug_tx_idle_ctrl_word
    
    @property
    def debug_rx_idle_ctrl_word(self: SlimLinkSimulator) -> int:
        """
        The last idle control word read by rx from the datastream.

        :return: the rx idle control word.
        """
        return self._debug_rx_idle_ctrl_word
    
    @property
    def bit_error_rate(self: SlimLinkSimulator) -> float:
        """
        The bit error rate in 66b-word-errors per second.

        :return: The bit error rate.
        """
        return self._bit_error_rate
    
    @property
    def link_occupancy(self: SlimLinkSimulator) -> float[2]:
        """
        An array holding the link occupancy percentages on [0] the tx side, [1] the rx side.
        Ideally they should be the same.

        :return: The link occupancy array.
        """
        return self._link_occupancy
    
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
        return self._read_counters

    @property
    def block_lost_cdr_lost_count(self: SlimLinkSimulator) -> int[2]:
        """
        An array holding [0]: block lost count, and [1]: cdr lost count.

        :return: The block_lost_cdr_lost_count array.
        """
        return self._block_lost_cdr_lost_count

    @property
    def link_healthy(self: SlimLinkSimulator) -> bool:
        """
        A boolean indicating the health of the link, based on:
        idle words match, block/cdr lost count = 0, bit-error-rate below threshold.

        :return: The link_healthy value.
        """
        return self._link_healthy

    def connect_to_slim_tx(
        self: SlimLinkSimulator,
    ) -> tuple[int, str]:
        self._tx_idle_ctrl_word = 0xDECAFBAD
        result_msg = (
            "Connection to SLIM TX simulator successful: "
            + self._tx_device_name
        )
        return self._tx_idle_ctrl_word, result_msg
    
    def connect_to_slim_rx(
        self: SlimLinkSimulator,
    ) -> tuple[int, str]:
        self._rx_idle_ctrl_word = 0xDECAFBAD
        result_msg = (
            "Connection to SLIM RX simulator successful: "
            + self._rx_device_name
        )
        return self._rx_idle_ctrl_word, result_msg
    
    def verify_connection(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        self._link_healthy = True
        result_msg = (
            "Valid connection between TX and RX simulators: "
            + self._link_name
            + "! "
        )
        return self._link_healthy, result_msg

    def disconnect_from_slim_tx(
        self: SlimLinkSimulator,
    ) -> str:
        self._tx_device_name = None
        self.clear_counters()
        self._link_healthy = False
        result_msg = result_msg = "Disconnected from SLIM Tx simulator."
        return result_msg


    def turn_on_outlet(
        self: PowerSwitchSimulator, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list read in from the Config File"

        outlet_idx = self.outlet_id_list.index(outlet)
        self.outlets[outlet_idx].power_mode = PowerMode.ON
        return ResultCode.OK, f"Outlet {outlet} power on"

    def turn_off_outlet(
        self: PowerSwitchSimulator, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list read in from the Config File"

        outlet_idx = self.outlet_id_list.index(outlet)
        self.outlets[outlet_idx].power_mode = PowerMode.OFF
        return ResultCode.OK, f"Outlet {outlet} power off"

    def get_outlet_list(self: PowerSwitchSimulator) -> List(Outlet):
        """
        Returns a list of 8 outlets, containing their name and current state.
        The current state is always set to OFF.

        :return: list of all the outlets available in this power switch
        """
        outlets: List(Outlet) = []
        for i in range(0, len(self.outlet_id_list)):
            outlets.append(
                Outlet(
                    outlet_ID=self.outlet_id_list[i],
                    outlet_name=f"Outlet {i}",
                    power_mode=PowerMode.OFF,
                )
            )

        return outlets
