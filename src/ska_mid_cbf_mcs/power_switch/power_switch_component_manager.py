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
from typing import Callable, Optional, Tuple, List

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.power_switch.power_switch_driver import PowerSwitchDriver
from ska_mid_cbf_mcs.power_switch.power_switch_simulator import (
    PowerSwitchSimulator,
)

__all__ = ["PowerSwitchComponentManager"]


class PowerSwitchComponentManager(CbfComponentManager):
    """
    A component manager for the DLI web power switch. Calls either the power
    switch driver or the power switch simulator based on the value of simulation
    mode.

    :param simulation_mode: simulation mode identifies if the real power switch
                          driver or the simulator should be used
    :param protocol: Connection protocol (HTTP or HTTPS) for the power switch
    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param model: Make and model name of the power switch
    :param content_type: The content type in the request header
    :param status_url_prefix: A portion of the URL to get the outlet status
    :param control_url_prefix: A portion of the URL to turn on/off outlet
    :param url_postfix: A portion of the URL after the outlet
    :param outlet_schema_file: File name for the schema for a list of outlets
    :param outlet_id_list: List of Outlet IDs
    :param logger: a logger for this object to use
    """

    def __init__(
        self: PowerSwitchComponentManager,
        protocol: str,
        ip: str,
        login: str,
        password: str,
        model: str,
        content_type: str,
        status_url_prefix: str,
        control_url_prefix: str,
        url_postfix: str,
        outlet_schema_file: str,
        outlet_id_list: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
    ) -> None:
        """
        Initialize a new instance.

        :param ip: IP address of the power switch
        :param login: Login username of the power switch
        :param password: Login password for the power switch
        :param model: Make and model name of the power switch
        :param content_type: The content type in the request header
        :param status_url_prefix: A portion of the URL to get the outlet status
        :param control_url_prefix: A portion of the URL to turn on/off outlet
        :param url_postfix: A portion of the URL after the outlet
        :param outlet_schema_file: File name for the schema for a list of outlets
        :param outlet_id_list: List of Outlet IDs
        :param logger: a logger for this object to use
        :param push_change_event: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be
            called when the component has faulted
        :param simulation_mode: simulation mode identifies if the real power switch
                driver or the simulator should be used

        """
        self.connected = False

        self._simulation_mode = simulation_mode

        self.power_switch_driver = PowerSwitchDriver(protocol, ip, login, password, model, content_type, status_url_prefix, control_url_prefix, url_postfix, outlet_schema_file, outlet_id_list, logger)
        self.power_switch_simulator = PowerSwitchSimulator(outlet_id_list, logger)

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    @property
    def num_outlets(self: PowerSwitchComponentManager) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
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
        # If we haven't started communicating yet, don't check power switch
        # communication status
        if self.connected is False:
            return False

        # If we have started communicating, check the actual communication
        # status of the power switch
        if self.simulation_mode:
            return self.power_switch_simulator.is_communicating
        else:
            return self.power_switch_driver.is_communicating

    @property
    def simulation_mode(self: PowerSwitchComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(
        self: PowerSwitchComponentManager, value: SimulationMode
    ) -> None:
        """
        Set the simulation mode of the component manager.

        :param value: value to set simulation mode to
        """
        self._simulation_mode = value

    def start_communicating(self: PowerSwitchComponentManager) -> None:
        """
        Perform any setup needed for communicating with the power switch.
        """
        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()

        if not self._simulation_mode:
            self.power_switch_driver.initialize()

        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.ON)
        self.connected = True

    def stop_communicating(self: PowerSwitchComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False

    def get_outlet_power_mode(
        self: PowerSwitchComponentManager, outlet: str
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """
        if self.simulation_mode:
            return self.power_switch_simulator.get_outlet_power_mode(outlet)
        else:
            return self.power_switch_driver.get_outlet_power_mode(outlet)

    def turn_on_outlet(
        self: PowerSwitchComponentManager, outlet: int
    ) -> Tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        if self.simulation_mode:
            return self.power_switch_simulator.turn_on_outlet(outlet)
        else:
            return self.power_switch_driver.turn_on_outlet(outlet)

    def turn_off_outlet(
        self: PowerSwitchComponentManager, outlet: int
    ) -> Tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        if self.simulation_mode:
            return self.power_switch_simulator.turn_off_outlet(outlet)
        else:
            return self.power_switch_driver.turn_off_outlet(outlet)
