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

from ska_mid_cbf_mcs.power_switch.power_switch_driver import Outlet

__all__ = ["PowerSwitchSimulator"]


class PowerSwitchSimulator:
    """
    A simulator for the power switch.

    :param logger: a logger for this object to use
    """

    def __init__(self: PowerSwitchSimulator, outlet_id_list: List[str], logger: logging.Logger) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger
        self.outlets = self.get_outlet_list()
        self.outlet_id_list = outlet_id_list


    @property
    def num_outlets(self: PowerSwitchSimulator) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        return len(self.outlets)

    @property
    def is_communicating(self: PowerSwitchSimulator) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: simulator always returns True
        """
        return True

    def get_outlet_power_mode(
        self: PowerSwitchSimulator, outlet: str
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            str(outlet) in self.outlet_id_list
        ), "Outlet ID must be in the allowable outlet_id_list read in from the Config File"

        return self.outlets[outlet].power_mode

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
            str(outlet) in self.outlet_id_list
        ), "Outlet ID must be in the allowable outlet_id_list read in from the Config File"

        self.outlets[outlet].power_mode = PowerMode.ON
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
            str(outlet) in self.outlet_id_list
        ), "Outlet ID must be in the allowable outlet_id_list read in from the Config File"

        self.outlets[outlet].power_mode = PowerMode.OFF
        return ResultCode.OK, f"Outlet {outlet} power off"

    def get_outlet_list(self: PowerSwitchSimulator) -> List(Outlet):
        """
        Returns a list of 8 outlets, containing their name and current state.
        The current state is always set to OFF.

        :return: list of all the outlets available in this power switch
        """
        outlets: List(Outlet) = []
        for i in range(0, 8):
            outlets.append(
                Outlet(
                    outlet_ID=str(i),
                    outlet_name=f"Outlet {i}",
                    power_mode=PowerMode.OFF,
                )
            )

        return outlets
