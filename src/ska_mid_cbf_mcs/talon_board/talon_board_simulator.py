# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.


from __future__ import annotations

import logging
from datetime import datetime, timezone
from random import randint, uniform

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
    def simulated_telemetry_results(
        self: TalonBoardSimulator,
    ) -> list[list[tuple[str, datetime, any]]]:
        telemetry = [
            (field, datetime.now(timezone.utc), value)
            for field, value in [
                (
                    "temperature-sensors_fpga-die-temp",
                    round(uniform(20.0, 50.0), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-0",
                    round(uniform(11.2, 12.8), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-1",
                    round(uniform(2.404, 2.596), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-2",
                    round(uniform(0.77, 0.97), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-3",
                    round(uniform(1.71, 1.89), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-4",
                    round(uniform(1.71, 1.89), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-5",
                    round(uniform(0.87, 0.93), 3),
                ),
                (
                    "voltage-sensors_fpga-die-voltage-6",
                    round(uniform(1.71, 1.89), 3),
                ),
                (
                    "temperature-sensors_humidity-temp",
                    round(uniform(20.0, 50.0), 3),
                ),
            ]
        ]
        telemetry.extend(
            [
                (
                    f"MBOs_{i}_TX_temperature",
                    datetime.now(timezone.utc),
                    round(uniform(20.0, 50.0), 3),
                ),
                (
                    f"MBOs_{i}_TX_vcc-3.3-voltage",
                    datetime.now(timezone.utc),
                    round(uniform(3.19, 3.41), 3),
                ),
                (
                    f"MBOs_{i}_TX_tx-fault-status",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"MBOs_{i}_TX_tx-lol-status",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"MBOs_{i}_TX_tx-los-status",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"MBOs_{i}_RX_vcc-3.3-voltage",
                    datetime.now(timezone.utc),
                    round(uniform(3.19, 3.41), 3),
                ),
                (
                    f"MBOs_{i}_RX_rx-lol-status",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"MBOs_{i}_RX_rx-los-status",
                    datetime.now(timezone.utc),
                    False,
                ),
            ]
            for i in range(5)
        )
        telemetry.extend(
            [
                (
                    f"temperature-sensors_dimm-temps_{i}_temp",
                    datetime.now(timezone.utc),
                    round(uniform(20.0, 50.0), 3),
                ),
                (
                    f"fans_fan-input_{i}",
                    datetime.now(timezone.utc),
                    randint(1, 499),
                ),
                (
                    f"fans_pwm_{i}",
                    datetime.now(timezone.utc),
                    randint(0, 255),
                ),
                (
                    f"fans_pwm-enable_{i}",
                    datetime.now(timezone.utc),
                    randint(0, 2),
                ),
                (
                    f"fans_fan-fault_{i}",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_voltage-input",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_voltage-output-1",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_voltage-output-2",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_current-input",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_current-output-1",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_current-output-2",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_temperature-1",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_temperature-2",
                    datetime.now(timezone.utc),
                    round(uniform(0.0, 1.0), 3),
                ),
                (
                    f"LTMs_{i}_LTM_voltage-output-max-alarm-1",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_voltage-output-max-alarm-2",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_voltage-input-crit-alarm",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_current-output-max-alarm-1",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_current-output-max-alarm-2",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_current-input-max-alarm",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_temperature-max-alarm-1",
                    datetime.now(timezone.utc),
                    False,
                ),
                (
                    f"LTMs_{i}_LTM_temperature-max-alarm-2",
                    datetime.now(timezone.utc),
                    False,
                ),
            ]
            for i in range(4)
        )
        return [telemetry]

    @property
    def sysid_version(self: TalonBoardSimulator) -> str:
        """
        The bitstream version as a string.

        :return: the bitstream version.
        :rtype: str
        """
        return self._bitstream_version

    @property
    def sysid_bitstream(self: TalonBoardSimulator) -> int:
        """
        The bitstream checksum as a string.

        :return: the bitstream checksum.
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
