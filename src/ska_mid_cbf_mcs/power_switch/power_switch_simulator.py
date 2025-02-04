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

from ska_control_model import PowerState
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.power_switch.pdu_common import Outlet

__all__ = ["PowerSwitchSimulator"]


class PowerSwitchSimulator:
    """
    A simulator for the power switch.

    :param model: Name of the power switch model
    :param logger: a logger for this object to use
    """

    def __init__(
        self: PowerSwitchSimulator, model: str, logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # The text must match the powerswitch.yaml
        if model == "DLI LPC9":
            self.outlet_id_list = [str(i) for i in range(0, 8)]
        elif model == "Server Technology Switched PRO2":
            self.outlet_id_list = [f"AA{i}" for i in range(1, 49)]
        elif model == "APC AP8681 SSH":
            self.outlet_id_list = [f"{i}" for i in range(1, 25)]
        elif model == "APC AP8681 SNMP":
            self.outlet_id_list = [f"{i}" for i in range(1, 25)]
        else:
            raise AssertionError(f"Invalid PDU model: {model}")

        self.outlets = self.get_outlet_list()

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

    def get_outlet_power_state(
        self: PowerSwitchSimulator, outlet: str
    ) -> PowerState:
        """
        Get the power state of a specific outlet.

        :param outlet: outlet ID
        :return: power state of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list read in from the Config File"

        outlet_idx = self.outlet_id_list.index(outlet)

        return self.outlets[outlet_idx].power_state

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
        self.outlets[outlet_idx].power_state = PowerState.ON
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
        self.outlets[outlet_idx].power_state = PowerState.OFF
        return ResultCode.OK, f"Outlet {outlet} power off"

    def get_outlet_list(self: PowerSwitchSimulator) -> list[Outlet]:
        """
        Returns a list of 8 outlets, containing their name and current state.
        The current state is always set to OFF.

        :return: list of all the outlets available in this power switch
        """
        outlets = []
        for i in range(0, len(self.outlet_id_list)):
            outlets.append(
                Outlet(
                    outlet_ID=self.outlet_id_list[i],
                    outlet_name=f"Outlet {i}",
                    power_state=PowerState.OFF,
                )
            )

        return outlets
