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
from time import sleep
from typing import Any, Callable, Optional, Tuple

import tango
from ska_control_model import (PowerState, SimulationMode, TaskStatus, CommunicationStatus)
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CbfComponentManager
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

    :param simulation_mode: simulation mode identifies if the real power switch
                          driver or the simulator should be used
    :param protocol: Connection protocol (HTTP or HTTPS) for the power switch
    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param logger: a logger for this object to use
    """

    def __init__(
        self: PowerSwitchComponentManager,
        *args: Any,
        model: str,
        ip: str,
        login: str,
        password: str,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
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
        super().__init__(*args, **kwargs)
        self.simulation_mode = simulation_mode

        self.power_switch_driver = self.get_power_switch_driver(
            model=model,
            ip=ip,
            login=login,
            password=password,
            logger=self.logger,
        )

        self.power_switch_simulator = PowerSwitchSimulator(
            model=model, logger=self.logger
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
        # Check the communication status of the power switch
        if self.simulation_mode:
            return self.power_switch_simulator.is_communicating
        else:
            return self.power_switch_driver.is_communicating

    def start_communicating(self: PowerSwitchComponentManager) -> None:
        """
        Perform any setup needed for communicating with the power switch.
        """
        if not self.simulation_mode:
            self.power_switch_driver.initialize()
            
        # We only want CommunicationStatus.Established if 
        # the PDU responded with a valid list of outlets.
        if self.power_switch_driver.outlets:
            super().start_communicating()
            self._update_component_state(power=PowerState.ON)
        else:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )

    def stop_communicating(self: PowerSwitchComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()

        if not self.simulation_mode:
            self.power_switch_driver.stop()

    def get_outlet_power_mode(
        self: PowerSwitchComponentManager, outlet: str
    ) -> PowerState:
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

    def is_turn_outlet_on_allowed(self) -> bool:
        self.logger.info("Checking if TurnOnOutlet is allowed.")
        return True

    def _turn_on_outlet(
        self: PowerSwitchComponentManager,
        outlet: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """
        Tell the power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        try:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            if self.simulation_mode:
                (
                    result_code,
                    message,
                ) = self.power_switch_simulator.turn_on_outlet(outlet)
            else:
                result_code, message = self.power_switch_driver.turn_on_outlet(
                    outlet
                )

            if task_callback:
                task_callback(progress=10)
            if result_code != ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED, result=(result_code, message)
                )
                return
            power_mode = self.get_outlet_power_mode(outlet)
            if task_callback:
                task_callback(progress=20)
            if power_mode != PowerState.ON:
                # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async events
                self.logger.info(
                    "The outlet's power mode is not 'on' as expected. Waiting for 5 seconds before rechecking the power mode..."
                )
                if task_abort_event and task_abort_event.is_set():
                    message = f"Power on aborted, outlet is in power mode {power_mode}"
                    task_callback(
                        status=TaskStatus.ABORTED,
                        result=(ResultCode.ABORTED, message),
                    )
                    return
                sleep(5)
                power_mode = self.get_outlet_power_mode(outlet)
                if power_mode != PowerState.ON:
                    task_callback(
                        status=TaskStatus.FAILED, result=(result_code, message)
                    )
                    return
            task_callback(progress=100)
            task_callback(
                status=TaskStatus.COMPLETED, result=(result_code, message)
            )
        except AssertionError as e:
            self.logger.error(e)
            task_callback(exception=e, status=TaskStatus.FAILED)
            
    def turn_on_outlet(
        self: PowerSwitchComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[TaskStatus, str]:
        """
        Turn the device on.

        :param task_callback: callback to be called when the status of
            the command changes

        :return: a result code and message
        """
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._turn_on_outlet,
            args=[argin],
            is_cmd_allowed=self.is_turn_outlet_on_allowed,
            task_callback=task_callback,
        )

    def is_turn_outlet_off_allowed(self) -> bool:
        self.logger.info("Checking if TurnOffOutlet is allowed.")
        return True
    
    def _turn_off_outlet(
        self: PowerSwitchComponentManager,
        outlet: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """
        Tell the power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        try:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            if self.simulation_mode:
                (result_code,message,) = self.power_switch_simulator.turn_off_outlet(outlet)
            else:
                result_code, message = self.power_switch_driver.turn_off_outlet(outlet)
                
            if task_callback:
                task_callback(progress=10)
            if result_code != ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED, result=(result_code, message)
                )
                return
            power_mode = self.get_outlet_power_mode(outlet)
            if task_callback:
                task_callback(progress=20)
    
            if power_mode != PowerState.OFF:
                # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
                self.logger.info(
                    "The outlet's power mode is not 'off' as expected. Waiting for 5 seconds before rechecking the power mode..."
                )
                if task_abort_event and task_abort_event.is_set():
                    message = f"Power off aborted, outlet is in power mode {power_mode}"
                    task_callback(
                        status=TaskStatus.ABORTED,
                        result=(ResultCode.ABORTED, message),
                    )
                    return
                sleep(5)
                power_mode = self.get_outlet_power_mode(outlet)
                if power_mode != PowerState.OFF:
                    task_callback(
                        status=TaskStatus.FAILED, result=(result_code, message)
                    )
                    return
            task_callback(progress=100)
            task_callback(
                status=TaskStatus.COMPLETED, result=(result_code, message)
            )
        except AssertionError as e:
            self.logger.error(e)
            task_callback(exception=e, status=TaskStatus.FAILED)
        

    def turn_off_outlet(
        self: PowerSwitchComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[TaskStatus, str]:
        """
        Turn the device off.

        :param task_callback: callback to be called when the status of
            the command changes

        :return: a result code and message
        """
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._turn_off_outlet,
            args=[argin],
            is_cmd_allowed=self.is_turn_outlet_off_allowed,
            task_callback=task_callback,
        )
        
    def get_power_switch_driver(
        self: PowerSwitchComponentManager,
        model: str,
        ip: str,
        login: str,
        password: str,
        logger: logging.Logger,
    ):
        # The text must match the powerswitch.yaml
        if model == "DLI LPC9":
            return DLIProSwitchDriver(
                ip=ip, login=login, password=password, logger=logger
            )
        elif model == "Server Technology Switched PRO2":
            return STSwitchedPRO2Driver(
                ip=ip, login=login, password=password, logger=logger
            )
        elif model == "APC AP8681 SSH":
            return ApcPduDriver(
                ip=ip, login=login, password=password, logger=logger
            )
        elif model == "APC AP8681 SNMP":
            return ApcSnmpDriver(
                ip=ip, login=login, password=password, logger=logger
            )
        else:
            err = f"Model name {model} is not supported."
            logger.error(err)
            tango.Except.throw_exception(
                "PowerSwitch_CreateDriverFailed",
                err,
                "get_power_switch_driver()",
            )
