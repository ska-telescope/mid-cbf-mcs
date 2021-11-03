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
import threading
from ska_mid_cbf_mcs.power_switch.power_switch_driver import PowerSwitchDriver
from ska_mid_cbf_mcs.power_switch.power_switch_simulator import PowerSwitchSimulator
from ska_mid_cbf_mcs.commons.global_enum import PowerMode

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import SimulationMode

__all__ = [
    "PowerSwitchComponentManager"
]

class PowerSwitchComponentManager:
    """A component manager for the DLI web power switch. Calls either the power
       switch driver or the power switch simulator based on the simulation
       mode."""

    def __init__(
        self: PowerSwitchComponentManager,
        simulation_mode: SimulationMode,
        ip: str,
        logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.

        :simulation_mode: simulation mode identifies if the real power switch
                          driver or the simulator should be used
        :param ip: IP address of the power switch
        :param logger: a logger for this object to use
        """
        self._simulation_mode = simulation_mode
        self._power_switch_lock = threading.Lock()

        self.power_switch_driver = PowerSwitchDriver(ip, logger)
        self.power_switch_simulator = PowerSwitchSimulator(logger)
        self.start_communicating()

    def start_communicating(self: PowerSwitchComponentManager) -> None:
        """
        Establish connection with the component, then start monitoring.
        """
        with self._power_switch_lock:
            if not self._simulation_mode:
                self.power_switch_driver.initialize()

    @property
    def simulation_mode(self: PowerSwitchComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.
        """
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(self: PowerSwitchComponentManager, value: SimulationMode) -> None:
        """
        Set the simulation mode of the component manager.
        """
        self._simulation_mode = value

        threading.Thread(target=self.start_communicating).start()
        
    @property
    def num_outlets(self: PowerSwitchComponentManager) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        with self._power_switch_lock:
            if self.simulation_mode:
                return self.power_switch_simulator.num_outlets
            else:
                return self.power_switch_driver.num_outlets

    @property
    def is_communicating(self: PowerSwitchComponentManager) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        with self._power_switch_lock:
            if self.simulation_mode:
                return self.power_switch_simulator.is_communicating
            else:
                return self.power_switch_driver.is_communicating

    def get_outlet_power_mode(
        self: PowerSwitchComponentManager,
        outlet: int
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """
        with self._power_switch_lock:
            if self.simulation_mode:
                return self.power_switch_simulator.get_outlet_power_mode(outlet)
            else:
                return self.power_switch_driver.get_outlet_power_mode(outlet)

    def turn_on_outlet(
        self: PowerSwitchComponentManager,
        outlet: int
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        with self._power_switch_lock:
            if self.simulation_mode:
                return self.power_switch_simulator.turn_on_outlet(outlet)
            else:
                return self.power_switch_driver.turn_on_outlet(outlet)
        
    def turn_off_outlet(
        self: PowerSwitchComponentManager,
        outlet: int
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        with self._power_switch_lock:
            if self.simulation_mode:
                return self.power_switch_simulator.turn_off_outlet(outlet)
            else:
                return self.power_switch_driver.turn_off_outlet(outlet)
