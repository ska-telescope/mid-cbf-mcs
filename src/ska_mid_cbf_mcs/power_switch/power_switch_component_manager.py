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
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.power_switch.apc_pdu_driver import ApcPduDriver
from ska_mid_cbf_mcs.power_switch.apc_snmp_driver import ApcSnmpDriver
from ska_mid_cbf_mcs.power_switch.dli_pro_switch_driver import (
    DLIProSwitchDriver,
)
from ska_mid_cbf_mcs.power_switch.power_switch_simulator import (
    PowerSwitchSimulator,
)
from ska_mid_cbf_mcs.power_switch.st_switched_pro2_driver import (
    STSwitchedPRO2Driver,
)

__all__ = ["PowerSwitchComponentManager"]


class PowerSwitchComponentManager(CbfComponentManager):
    """
    A component manager for the power switch. Calls either the power
    switch driver or the power switch simulator based on the value of simulation
    mode.
    """

    def __init__(
        self: PowerSwitchComponentManager,
        model: str,
        ip: str,
        login: str,
        password: str,
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

        :param model: Name of the power switch model
        :param ip: IP address of the power switch
        :param login: Login username of the power switch
        :param password: Login password for the power switch
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
        self._model = model
        self._ip = ip
        self._login = login
        self._password = password
        self._power_switch_driver = None
        self._power_switch_simulator = None
        self._simulation_mode = simulation_mode

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
        # If we haven't started communicating yet, don't check number of power
        # switch outlets
        if self._communication_status != CommunicationStatus.ESTABLISHED:
            self._logger.warning(
                "Power switch driver not yet configured, unable to determine number of outlets."
            )
            return 0

        if self._simulation_mode:
            return self._power_switch_simulator.num_outlets
        else:
            return self._power_switch_driver.num_outlets

    @property
    def is_communicating(self: PowerSwitchComponentManager) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        # If we haven't started communicating yet, don't check power switch
        # communication status
        if self._communication_status != CommunicationStatus.ESTABLISHED:
            return False

        # If we have started communicating, check the actual communication
        # status of the power switch
        if self._simulation_mode:
            return self._power_switch_simulator.is_communicating
        else:
            return self._power_switch_driver.is_communicating

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

    def _get_power_switch_driver(self: PowerSwitchComponentManager):
        self._logger.info(
            f"Configuring driver for {self._model} power switch."
        )
        driver = None

        # The text must match the hw_config.yaml
        match self._model:
            case "DLI LPC9":
                driver = DLIProSwitchDriver(
                    ip=self._ip,
                    login=self._login,
                    password=self._password,
                    logger=self._logger,
                )
            case "Server Technology Switched PRO2":
                driver = STSwitchedPRO2Driver(
                    ip=self._ip,
                    login=self._login,
                    password=self._password,
                    logger=self._logger,
                )
            case "APC AP8681 SSH":
                driver = ApcPduDriver(
                    ip=self._ip,
                    login=self._login,
                    password=self._password,
                    logger=self._logger,
                )
            case "APC AP8681 SNMP":
                driver = ApcSnmpDriver(
                    ip=self._ip,
                    login=self._login,
                    password=self._password,
                    logger=self._logger,
                )
            case _:
                self._logger.error(
                    f"Model name {self._model} is not supported."
                )
                self.update_communication_status(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                return None

        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        return driver

    def start_communicating(self: PowerSwitchComponentManager) -> None:
        """
        Perform any setup needed for communicating with the power switch.
        """
        if self.communication_status == CommunicationStatus.ESTABLISHED:
            self._logger.info(
                "start_communicating returning, already connected to component."
            )
            return

        if self._simulation_mode:
            self.update_communication_status(CommunicationStatus.ESTABLISHED)
            self._power_switch_simulator = PowerSwitchSimulator(
                model=self._model, logger=self._logger
            )
        else:
            self._power_switch_driver = self._get_power_switch_driver()
            if self._power_switch_driver is not None:
                self._power_switch_driver.initialize()

    def stop_communicating(self: PowerSwitchComponentManager) -> None:
        """Stop communication with the component."""
        if self.communication_status == CommunicationStatus.DISABLED:
            self._logger.info(
                "stop_communicating returning, not connected to component."
            )
            return

        if not self._simulation_mode and self._power_switch_driver is not None:
            self._power_switch_driver.stop()

        self.update_communication_status(CommunicationStatus.DISABLED)

    def get_outlet_power_mode(
        self: PowerSwitchComponentManager, outlet: str
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """
        self._logger.info(f"get_outlet_power_mode for outlet {outlet}")
        if self._simulation_mode:
            return self._power_switch_simulator.get_outlet_power_mode(outlet)
        else:
            return self._power_switch_driver.get_outlet_power_mode(outlet)

    def turn_on_outlet(
        self: PowerSwitchComponentManager, outlet: str
    ) -> Tuple[ResultCode, str]:
        """
        Tell the power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        self._logger.info(f"Turning on outlet {outlet}")
        if self._simulation_mode:
            return self._power_switch_simulator.turn_on_outlet(outlet)
        else:
            return self._power_switch_driver.turn_on_outlet(outlet)

    def turn_off_outlet(
        self: PowerSwitchComponentManager, outlet: str
    ) -> Tuple[ResultCode, str]:
        """
        Tell the power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        self._logger.info(f"Turning off outlet {outlet}")
        if self._simulation_mode:
            return self._power_switch_simulator.turn_off_outlet(outlet)
        else:
            return self._power_switch_driver.turn_off_outlet(outlet)
