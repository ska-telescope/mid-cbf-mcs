# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.


from __future__ import annotations

import logging

__all__ = ["TalonBoardSimulator"]


class TalonBoardSimulator:
    """
    Simulator for the Talon Board Device Class
    """

    def __init__(
        self: TalonBoardSimulator,
        logger: logging.Logger,
    ) -> None:
        """
        Initialize A Talon Board Component Manager Simulator

        Current usage is to retrieve simulated values for Talon Board Device attributes

        :param logger: a logger for this object to use
        """

        self.logger = logger

        # Init FPGA sensor attr
        self._fpga_die_voltages = [12.0, 2.5, 0.87, 1.8, 1.8, 0.9, 1.8]
        self._fpga_die_temperature = 50.0

        # Init TalonSysId attr
        self._sysid_version = "test"
        self._bitstream_version = 0xBEEFBABE

        # Init TalonStatus attr
        self._iopll_locked_fault = False
        self._fs_iopll_locked_fault = False
        self._comms_iopll_locked_fault = False
        self._system_clk_fault = False
        self._emif_bl_fault = False
        self._emif_br_fault = False
        self._emif_tr_fault = False
        self._e100g_0_pll_fault = False
        self._e100g_1_pll_fault = False
        self._slim_pll_fault = False

    @property
    def fpga_die_temperature(self: TalonBoardSimulator) -> float:
        """
        Simulates value for fpga_die_temperature in degrees celcius

        :return : a float value representing the temperature reading from the sensor
        """
        return self._fpga_die_temperature

    @property
    def fpga_die_voltages(self: TalonBoardSimulator) -> list[float]:
        """
        Simulates value for fpga_die_voltage in volts

        :return : a list of float values representing the various voltage readings from the sensor
        """
        return self._fpga_die_voltages

    @property
    def sysid_version(self: TalonBoardSimulator) -> str:
        """
        The bitsream version as a string.

        :return: the bitsream version.
        :rtype: str
        """
        return self._bitstream_version

    @property
    def sysid_bitstream(self: TalonBoardSimulator) -> int:
        """
        The bitsream checksum as a string.

        :return: the bitsream checksum.
        :rtype: int
        """
        return self._bitstream_version

    @property
    def status_iopll_locked_fault(self: TalonBoardSimulator) -> bool:
        """
        The iopll locked fault status.

        :return: iopll locked fault status.
        :rtype: bool
        """
        return self._iopll_locked_fault

    @property
    def status_fs_iopll_locked_fault(self: TalonBoardSimulator) -> bool:
        """
        The fs iopll locked fault status.

        :return: fs iopll locked fault status.
        :rtype: bool
        """
        return self._fs_iopll_locked_fault

    @property
    def status_comms_iopll_locked_fault(self: TalonBoardSimulator) -> bool:
        """
        The comms iopll locked fault status.

        :return: comms iopll locked fault status.
        :rtype: bool
        """
        return self._comms_iopll_locked_fault

    @property
    def status_system_clk_fault(self: TalonBoardSimulator) -> bool:
        """
        The system clock fault status.

        :return: system clock fault status.
        :rtype: bool
        """
        return self._system_clk_fault

    @property
    def status_emif_bl_fault(self: TalonBoardSimulator) -> bool:
        """
        The emif bl fault status.

        :return: emif bl fault status.
        :rtype: bool
        """
        return self._emif_bl_fault

    @property
    def status_emif_br_fault(self: TalonBoardSimulator) -> bool:
        """
        The emif br fault status.

        :return: emif br fault status.
        :rtype: bool
        """
        return self._emif_br_fault

    @property
    def status_emif_tr_fault(self: TalonBoardSimulator) -> bool:
        """
        The emif tr fault status.

        :return: emif tr fault status.
        :rtype: bool
        """
        return self._emif_tr_fault

    @property
    def status_e100g_0_pll_fault(self: TalonBoardSimulator) -> bool:
        """
        The ethernet100g_0 pll fault status.

        :return: e100g_0 pll fault status.
        :rtype: bool
        """
        return self._e100g_0_pll_fault

    @property
    def status_e100g_1_pll_fault(self: TalonBoardSimulator) -> bool:
        """
        The ethernet100g_1 pll fault status.

        :return: e100g_1 pll fault status.
        :rtype: bool
        """
        return self._e100g_1_pll_fault

    @property
    def status_slim_pll_fault(self: TalonBoardSimulator) -> bool:
        """
        The slim pll fault status.

        :return: slim pll fault status.
        :rtype: bool
        """
        return self._slim_pll_fault
