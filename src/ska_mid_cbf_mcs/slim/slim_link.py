# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2023 National Research Council of Canada


from __future__ import annotations

import logging

import tango

__all__ = ["SLIMLink"]


class SLIMLink:
    """
    Manages a link between a SLIM Tx and Rx

    :param tx_fqdn: FQDN of the Tx device
    :param rx_fqdn: FQDN of the Rx device
    """

    def __init__(
        self: SLIMLink,
        tx_fqdn: str,
        rx_fqdn: str,
        logger: logging.Logger,
    ) -> None:
        self.tx_fqdn = tx_fqdn
        self.rx_fqdn = rx_fqdn
        self.tx_proxy = None
        self.rx_proxy = None
        self.link_name = f"{tx_fqdn} -> {rx_fqdn}"
        self.idle_ctrl_word = (
            hash(self.link_name) & 0x0FFF_FFFF_FFFF_FFFF
        )  # 56 bits
        self.is_connected = False
        self.logger = logger

    def __del__(self: SLIMLink):
        self.disconnect()

    def connect(self: SLIMLink):
        try:
            self.tx_proxy = tango.DeviceProxy(self.tx_fqdn)
            self.rx_proxy = tango.DeviceProxy(self.rx_fqdn)

            self.tx_proxy.write_attribute(
                "idle_ctrl_word", self.idle_ctrl_word
            )
            self.tx_proxy.command_inout("phy_reset")

            loopback = False
            self.rx_proxy.command_inout("initialize_connection", loopback)
        except tango.DevFailed as df:
            tango.Except.re_throw_exception(
                df,
                "SLIM Link connect failed",
                f"Link {self.link_name} failed to connect to SLIM Tx/Rx",
            )

        if not self.verify_connection():
            tango.Except.throw_exception(
                "SLIM Link connect failed",
                f"SLIM Link {self.link_name} connection failed",
                "connect execution",
            )
        self.is_connected = True
        self.logger.info(f"Connected SLIM Link {self.link_name}")

    def disconnect(self: SLIMLink):
        if self.is_connected:
            loopback = True
            self.rx_proxy.command_inout("initialize_connection", loopback)
        self.is_connected = False
        self.rx_proxy = None
        self.tx_proxy = None
        self.logger.info(f"Disconnected SLIM Link {self.link_name}")

    def verify_connection(self: SLIMLink):
        if not self.is_connected:
            return False
        status = True
        icw = self.rx_proxy.read_attribute("idle_ctrl_word")
        if icw != self.idle_ctrl_word:
            self.logger.error(
                f"SLIM Link {self.link_name} - idle_ctrl_word does not match the expected value"
            )
            status = False

        """
        SLIM Rx counters attribute is
        [0]: word count
        [1]: packet count
        [2]: idle count
        [3]: idle error count
        [4]: block lost count
        [5]: CDR lost count
        """
        rx_counters = self.rx_proxy.read_attribute("read_counters")
        if rx_counters[4] != 0:
            self.logger.error(
                f"SLIM Link {self.link_name} - block lost count > 0"
            )
            status = False
        if rx_counters[5] != 0:
            self.logger.error(
                f"SLIM Link {self.link_name} - CDR lost count > 0"
            )
            status = False
        status_txt = "OK" if status else "Failed"
        self.logger.info(
            f"SLIM Link {self.link_name} - Verify Connection - {status_txt}"
        )
        return status

    def bit_error_rate(self: SLIMLink) -> int:
        """
        Returns the word error rate

        :return: word error rate
        """
        ber = self.rx_proxy.read_attribute("bit_error_rate")
        return ber
