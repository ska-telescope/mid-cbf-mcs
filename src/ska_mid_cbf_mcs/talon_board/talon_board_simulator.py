# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.


from __future__ import annotations

import logging
from typing import Callable

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState

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

        self._logger = logger

    def fpga_die_voltage_0(self) -> float:
        return 12.0

    def fpga_die_voltage_1(self) -> float:
        return 2.5

    def fpga_die_voltage_2(self) -> float:
        return 0.87

    def fpga_die_voltage_3(self) -> float:
        return 1.8

    def fpga_die_voltage_4(self) -> float:
        return 1.8

    def fpga_die_voltage_5(self) -> float:
        return 0.9

    def fpga_die_voltage_6(self) -> float:
        return 1.8
