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

import random
import logging
from typing import List
from ska_mid_cbf_mcs.power_switch.power_switch_driver import Outlet
from ska_mid_cbf_mcs.commons.global_enum import PowerMode

from ska_tango_base.commands import ResultCode

__all__ = [
    "PowerSwitchSimulator"
]

class PowerSwitchSimulator:
    """A simulator of the power switch."""

    def __init__(
        self: PowerSwitchSimulator,
        logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        """
        self.logger = logger
        self.outlets: List(Outlet) = []
        random.seed()

    @property
    def num_outlets(self: PowerSwitchSimulator) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        self.outlets = self.get_outlet_list()
        return len(self.outlets)

    @property
    def is_communicating(self: PowerSwitchSimulator) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        return True

    def get_outlet_power_mode(
        self: PowerSwitchSimulator,
        outlet: int
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet < len(self.outlets) and outlet >= 0
        ), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)" 

        return self.outlets[outlet].power_mode

    def turn_on_outlet(
        self: PowerSwitchSimulator,
        outlet: int
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet < len(self.outlets) and outlet >= 0
        ), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        self.outlets[outlet].power_mode = PowerMode.ON
        return ResultCode.OK, f"Outlet {outlet} power on"
        
    def turn_off_outlet(
        self: PowerSwitchSimulator,
        outlet: int
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet < len(self.outlets) and outlet >= 0
        ), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        self.outlets[outlet].power_mode = PowerMode.OFF
        return ResultCode.OK, f"Outlet {outlet} power off"

    def get_outlet_list(
        self: PowerSwitchSimulator
    ) -> List(Outlet):
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch
        """
        outlets: List(Outlet) = []
        for i in range(0, 8):
            outlets.append(Outlet(
                outlet_ID = i,
                outlet_name = f"Outlet {i}",
                power_mode = PowerMode.ON if random.getrandbits(1) else PowerMode.OFF
            ))

        return outlets
 