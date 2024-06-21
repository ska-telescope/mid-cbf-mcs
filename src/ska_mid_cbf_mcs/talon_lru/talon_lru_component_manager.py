# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import concurrent.futures
import threading
from typing import Any, Callable, Optional

import tango
from ska_control_model import TaskStatus
from ska_tango_base.base.base_component_manager import check_communicating
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, PowerState, SimulationMode
from ska_tango_testing import context

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


class TalonLRUComponentManager(CbfComponentManager):
    """A component manager for the TalonLRU device."""

    def __init__(
        self: TalonLRUComponentManager,
        *args: Any,
        talons: list[str],
        pdus: list[str],
        pdu_outlets: list[str],
        pdu_cmd_timeout: int,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param talons: FQDNs of the Talon DX board
        :param pdus: FQDNs of the power switch devices
        :param pdu_outlets: IDs of the PDU outlets
        :param pdu_cmd_timeout: timeout for PDU commands in seconds
        """
        super().__init__(*args, **kwargs)
        self.simulation_mode = SimulationMode.TRUE

        # Get the device proxies of all the devices we care about
        self._talons = talons
        self._pdus = pdus
        self._pdu_outlets = pdu_outlets
        self._pdu_cmd_timeout = pdu_cmd_timeout

        self._proxy_talondx_board1 = None
        self._proxy_talondx_board2 = None
        self._proxy_power_switch1 = None
        self._proxy_power_switch2 = None

        self._using_single_outlet = False

        self.pdu1_power_state = PowerState.UNKNOWN
        self.pdu2_power_state = PowerState.UNKNOWN

    # -------------
    # Communication
    # -------------

    def _get_device_proxy(
        self: TalonLRUComponentManager, fqdn: str
    ) -> context.DeviceProxy | None:
        """
        Attempt to get a device proxy of the specified device.

        :param fqdn: FQDN of the device to connect to
        :return: context.DeviceProxy to the device or None if no connection was made
        """
        try:
            self.logger.debug(f"Attempting connection to {fqdn} device")
            device_proxy = context.DeviceProxy(device_name=fqdn)
            return device_proxy
        except tango.DevFailed as df:
            for item in df.args:
                self.logger.error(
                    f"Failed connection to {fqdn} device: {item.reason}"
                )
            return None

    def _init_talon_proxies(self: TalonLRUComponentManager) -> None:
        """
        Get and initialize the 2 Talon Board proxies
        """
        if len(self._talons) < 2:
            self.logger.error("Expected two Talon board FQDNs")
            tango.Except.throw_exception(
                "TalonLRU_TalonBoardFailed",
                "Two FQDNs for Talon Boards are needed for the LRU",
                "_init_talon_proxies()",
            )

        try:
            self._proxy_talondx_board1 = self._get_device_proxy(
                "mid_csp_cbf/talon_board/" + self._talons[0]
            )
            self._proxy_talondx_board2 = self._get_device_proxy(
                "mid_csp_cbf/talon_board/" + self._talons[1]
            )

            # Needs Admin mode == ONLINE to run ON command
            if self._proxy_talondx_board1:
                self._proxy_talondx_board1.adminMode = AdminMode.ONLINE
            if self._proxy_talondx_board2:
                self._proxy_talondx_board2.adminMode = AdminMode.ONLINE
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to set AdminMode to ONLINE on Talon boards: {df}"
            )
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )

    def _init_power_switch(self, pdu, pdu_outlet) -> None:
        """
        Initialize power switch and get the power mode of the specified outlet.

        :param pdu: FQDN of the power switch device
        :param pdu_outlet: ID of the PDU outlet
        :return: the power switch proxy and the power mode of the outlet
        """
        power_switch_proxy = self._get_device_proxy(
            "mid_csp_cbf/power_switch/" + pdu
        )
        if power_switch_proxy is not None:
            # TODO: Refactor proxy simulation mode setting in controller instead.
            try:
                # Set the power switch's simulation mode and set admin mode to ONLINE
                power_switch_proxy.adminMode = AdminMode.OFFLINE
                power_switch_proxy.simulationMode = self.simulation_mode
                power_switch_proxy.adminMode = AdminMode.ONLINE
 
                power_state = power_switch_proxy.GetOutletPowerState(
                    pdu_outlet
                )
                if power_switch_proxy.numOutlets == 0:
                    power_state = PowerState.UNKNOWN
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to set AdminMode to ONLINE on Talon boards: {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
        return power_switch_proxy, power_state

    def _init_power_switch_proxies(self: TalonLRUComponentManager) -> None:
        """
        Get and initialize the 2 Power Switch proxies
        """
        (
            self._proxy_power_switch1,
            self.pdu1_power_state,
        ) = self._init_power_switch(self._pdus[0], self._pdu_outlets[0])
        if self._pdus[0] == self._pdus[1]:
            self._proxy_power_switch2 = self._proxy_power_switch1
            self.pdu2_power_state = self.pdu1_power_state
            if self._pdu_outlets[0] == self._pdu_outlets[1]:
                self._using_single_outlet = True
        else:
            (
                self._proxy_power_switch2,
                self.pdu2_power_state,
            ) = self._init_power_switch(self._pdus[1], self._pdu_outlets[1])

    def start_communicating(self: TalonLRUComponentManager) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager.start_communicating"
        )

        if self.is_communicating:
            self.logger.info("Already communicating.")
            return

        # Get and initialize the device proxies of all the devices we care about
        self._init_talon_proxies()
        self._init_power_switch_proxies()

        for dp in [
            self._proxy_power_switch1,
            self._proxy_power_switch2,
            self._proxy_talondx_board1,
            self._proxy_talondx_board2,
        ]:
            if dp is None:
                self.logger.error(
                    "One or more device properties are missing. Check charts."
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return
            else:
                self._subscribe_command_results(dp)
        self.logger.info(
            f"event_ids after subscribing = {self._event_ids_count}"
        )

        super().start_communicating()
        # This moves the op state model.
        self._update_component_state(power=self.get_lru_power_state())

    def stop_communicating(self: TalonLRUComponentManager) -> None:
        """
        Stop communication with the component.
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager.stop_communicating"
        )

        for dp in [
            self._proxy_power_switch1,
            self._proxy_power_switch2,
            self._proxy_talondx_board1,
            self._proxy_talondx_board2,
        ]:
            if dp in self._event_ids:
                device_events = self._event_ids.pop(dp)
                while len(device_events):
                    dp.unsubscribe_event(device_events.pop())
                    self._event_ids_count -= 1

        self._num_blocking_results = 0
        self.logger.info(
            f"event_ids after unsubscribing = {self._event_ids_count}"
        )

        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model.
        super().stop_communicating()

    # ---------------
    # General methods
    # ---------------

    def _get_outlet_power_state(
        self: TalonLRUComponentManager, proxy_power_switch, outlet
    ) -> PowerState:
        """
        Get the power mode of the specified outlet from the power switch.

        :params: proxy_power_switch: the power switch proxy
        :params: outlet: the outlet to get the power mode of
        """
        if (
            proxy_power_switch is not None
            and proxy_power_switch.numOutlets != 0
        ):
            return proxy_power_switch.GetOutletPowerState(outlet)
        else:
            return PowerState.UNKNOWN

    def _update_pdu_power_states(self: TalonLRUComponentManager) -> None:
        """
        Check and update current PowerState states of both PDUs.
        """
        self.pdu1_power_state = self._get_outlet_power_state(
            self._proxy_power_switch1, self._pdu_outlets[0]
        )

        if self._using_single_outlet:
            self.pdu2_power_state = self.pdu1_power_state
        else:
            self.pdu2_power_state = self._get_outlet_power_state(
                self._proxy_power_switch2, self._pdu_outlets[1]
            )

    def get_lru_power_state(self: TalonLRUComponentManager) -> PowerState:
        """
        Get the current PowerState of the TalonLRU based on the power mode of the PDUs.
        Also update the current LRU PowerState state to match.

        :return: the current TalonLRU PowerState
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager.get_lru_power_state"
        )

        self._update_pdu_power_states()
        lru_power_state = PowerState.UNKNOWN
        if (
            self.pdu1_power_state == PowerState.ON
            or self.pdu2_power_state == PowerState.ON
        ):
            lru_power_state = PowerState.ON
        elif (
            self.pdu1_power_state == PowerState.OFF
            and self.pdu2_power_state == PowerState.OFF
        ):
            lru_power_state = PowerState.OFF
        self._update_component_state(power=lru_power_state)
        return lru_power_state

    # ---------------------
    # Long Running Commands
    # ---------------------

    def _turn_on_pdus(
        self: TalonLRUComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, ResultCode]:
        """
        If not already on, turn on the two PDUs.

        :return: A tuple containing the 2 return codes of turning on the PDUs
        """
        # Turn on PDU 1
        result1 = ResultCode.FAILED
        if self.pdu1_power_state == PowerState.ON:
            self.logger.info("PDU 1 is already on.")
            result1 = ResultCode.OK
        elif self._proxy_power_switch1 is not None:
            self._num_blocking_results = 1
            [[result1], [command_id]] = self._proxy_power_switch1.TurnOnOutlet(
                self._pdu_outlets[0]
            )
            # Guard incase LRC was rejected.
            if result1 == ResultCode.REJECTED:
                message = f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} rejected"
                self.logger.error(message)
            else:
                lrc_status = self._wait_for_blocking_results(
                    timeout=10.0, task_abort_event=task_abort_event
                )
            
            if lrc_status != TaskStatus.COMPLETED:
                if result1 != ResultCode.REJECTED:
                    self.logger.error(
                        f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} timed out",
                    )
                    result1 = ResultCode.FAILED
            else:
                self.pdu1_power_state = PowerState.ON
                self.logger.info(
                    f"PDU 1 ({self._pdu_outlets[0]}) successfully turned on."
                )
                result1 = ResultCode.OK

        # Turn on PDU 2
        result2 = ResultCode.FAILED
        if self._using_single_outlet:
            self.logger.info("PDU 2 is not used.")
            result2 = result1
        elif self.pdu2_power_state == PowerState.ON:
            self.logger.info("PDU 2 is already on.")
            result2 = ResultCode.OK
        elif self._proxy_power_switch2 is not None:
            self._num_blocking_results = 1
            [[result2], [command_id]] = self._proxy_power_switch2.TurnOnOutlet(
                self._pdu_outlets[1]
            )
            # Guard incase LRC was rejected.
            if result2 == ResultCode.REJECTED:
                message = f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} rejected"
                self.logger.error(message)
                return result1, result2
            else:
                lrc_status = self._wait_for_blocking_results(
                    timeout=10.0, task_abort_event=task_abort_event
                )

            if lrc_status != TaskStatus.COMPLETED:
                self.logger.error(
                    f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} timed out",
                )
                result2 = ResultCode.FAILED
            else:
                self.pdu2_power_state = PowerState.ON
                self.logger.info(
                    f"PDU 2 (outlet {self._pdu_outlets[1]}) successfully turned on."
                )
                result2 = ResultCode.OK
        return result1, result2

    def _turn_on_talons(
        self: TalonLRUComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, str]:
        """
        Turn on the two Talon boards.
        """
        self._num_blocking_results = 2
        for i, board in enumerate(
            [self._proxy_talondx_board1, self._proxy_talondx_board2]
        ):
            try:
                [[result_code], [command_id]] = board.On()

                # Guard incase LRC was rejected.
                if result_code == ResultCode.REJECTED:
                    message =  f"Nested LRC TalonBoard.On() to {board.dev_name()} rejected"
                    self.logger.error(message)
            except tango.DevFailed as df:
                self.logger.error(
                    f"Nested LRC TalonBoard.On() failed: {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    f"Nested LRC TalonBoard.On() to {board.dev_name()} failed",
                )
                
        lrc_status = self._wait_for_blocking_results(
            timeout=10.0, task_abort_event=task_abort_event
        )
        if lrc_status != TaskStatus.COMPLETED:
            self.logger.error(
                f"One or more calls to nested LRC TalonBoard.On() timed out. Check TalonBoard logs."
            )
            return ResultCode.FAILED, "Nested LRC TalonBoard.On() timed out"
        return ResultCode.OK, "_turn_on_talons completed OK"

    def _determine_on_result_code(
        self: TalonLRUComponentManager,
        result1: ResultCode,
        result2: ResultCode,
    ) -> tuple[ResultCode, str]:
        """
        Determine the return code to return from the on command, given turning on PDUs' result codes.
        Also update the component power mode if successful.

        :param result1: the result code of turning on PDU 1
        :param result2: the result code of turning on PDU 2
        :return: A tuple containing a return code and a string
        """
        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            msg = f'LRU failed to turn on: {"single outlet failed to turn on" if self._using_single_outlet else "both outlets failed to turn on"}'

            self.logger.error(msg)
            return (
                ResultCode.FAILED,
                msg,
            )

        if result1 == ResultCode.OK and result2 == ResultCode.OK:
            msg = f'LRU succesfully turned on: {"single PDU successfully turned on" if self._using_single_outlet else "both outlets successfully turned on"}'
            self.logger.info(msg)

        else:
            self.logger.info(
                "LRU successfully turn on: one outlet turned on",
            )

        self._update_component_state(power=PowerState.ON)
        return (
            ResultCode.OK,
            "On completed OK",
        )

    def is_on_allowed(self: TalonLRUComponentManager) -> bool:
        self.logger.debug("Checking if on is allowed")
        if self._component_state["power"] == PowerState.OFF:
            return True
        self.logger.warning("LRU is already on, do not need to turn on.")
        return False

    def _on(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Turn on the TalonLRU and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering TalonLRUComponentManager.on")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        self._update_pdu_power_states()
        result1, result2 = self._turn_on_pdus(task_abort_event)

        # Start monitoring talon board telemetries and fault status
        # This can fail if HPS devices are not deployed to the
        # board, but it's okay to continue.
        talon_on_result, message = self._turn_on_talons(task_abort_event)
        
        if talon_on_result != ResultCode.OK:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    talon_on_result,
                    message,
                ),
            )
            return

        # _determine_on_result_code will update the component power state
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                self._determine_on_result_code(result1, result2),
                "On completed OK",
            )
        )

    @check_communicating
    def on(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit on operation method to task executor queue.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._on,
            is_cmd_allowed=self.is_on_allowed,
            task_callback=task_callback,
        )

    def _turn_off_pdus(
        self: TalonLRUComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, ResultCode]:
        """
        Turn off the two PDUs.

        :return: A tuple containing the 2 return codes of turning off the PDUs
        """
        # Power off PDU 1
        result1 = ResultCode.FAILED
        if self._proxy_power_switch1 is not None:
            self._num_blocking_results = 1
            [[result1],[command_id]] = self._proxy_power_switch1.TurnOffOutlet(
                self._pdu_outlets[0]
            )
            # Guard incase LRC was rejected.
            if result1 == ResultCode.REJECTED:
                message = f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} rejected"
                self.logger.error(message)

            lrc_status = self._wait_for_blocking_results(
                timeout=10.0, task_abort_event=task_abort_event
            )
            if lrc_status != TaskStatus.COMPLETED:
                self.logger.error(
                    f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} timed out"
                )
                result1 = ResultCode.FAILED
            else:
                self.pdu1_power_state = PowerState.OFF
                self.logger.info(
                    f"PDU 1 (outlet {self._pdu_outlets[0]}) successfully turned off."
                )
                result1 = ResultCode.OK

        # Power off PDU 2
        result2 = ResultCode.FAILED
        if self._proxy_power_switch2 is not None:
            if self._using_single_outlet:
                self.logger.info("PDU 2 is not used.")
                result2 = result1
            else:
                self._num_blocking_results = 1
                [[result2],[command_id]] = self._proxy_power_switch2.TurnOffOutlet(
                    self._pdu_outlets[1]
                )
                # Guard incase LRC was rejected.
                if result1 == ResultCode.REJECTED:
                    message = f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} rejected"
                    self.logger.error(message)

                lrc_status = self._wait_for_blocking_results(
                    timeout=10.0, task_abort_event=task_abort_event
                )
                if lrc_status != TaskStatus.COMPLETED:
                    self.logger.error(
                        f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} timed out"
                    )
                    result2 = ResultCode.FAILED
                else:
                    self.pdu1_power_state = PowerState.OFF
                    self.logger.info(
                        f"PDU 2 (outlet {self._pdu_outlets[1]}) successfully turned off."
                    )
                    result2 = ResultCode.OK
        return result1, result2

    def _turn_off_talon(
        self: TalonLRUComponentManager,
        talondx_board_proxy: context.DeviceProxy,
    ) ->  tuple[ResultCode, str]:
        """
        Turn off the specified Talon board.
        """
        try:
            talondx_board_proxy.Off()
        except tango.DevFailed as df:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return (
                ResultCode.FAILED,
                f"_turn_off_talon FAILED on {talondx_board_proxy.dev_name()}: {df}",
            )
        return (
            ResultCode.OK,
            f"_turn_off_talon completed OK"
        )

    def _turn_off_talons(
        self: TalonLRUComponentManager,
    ) -> None | tuple[ResultCode, str]:
        """
        Turn off the two Talon boards, threaded.

        :return: ResultCode.FAILED if one of the boards failed to turn off, None otherwise
        """
        group_talon_board = [
            self._proxy_talondx_board1,
            self._proxy_talondx_board2,
        ]
        
        # Turn off all the talons
        for result_code, msg in self._issue_group_command(
            command_name="Off", proxies=group_talon_board
        ):
            if result_code == ResultCode.FAILED:
                return (
                    ResultCode.FAILED,
                    f"Failed to turn off Talon board: {msg}",
                )
            elif result_code == ResultCode.OK:
                self.logger.info(f"Talon board successfully turned off: {msg}")
            else:
                self.logger.warn(
                    f"Talon board turned off with unexpected result code {result_code}: {msg}"
                )
        return None        

    def _determine_off_result_code(
        self: TalonLRUComponentManager,
        result1: ResultCode,
        result2: ResultCode,
    ) -> tuple[ResultCode, str]:
        """
        Determine the return code to return from the off command, given turning on PDUs' result codes.
        Also update the component power mode if successful.

        :param result1: the result code of turning off PDU 1
        :param result2: the result code of turning off PDU 2
        :return: A tuple containing a return code and a string
        """

        if result1 == ResultCode.OK and result2 == ResultCode.OK:
            msg = f'Off completed OK: {"single outlet turned off" if self._using_single_outlet else "both outlets turned off"}'
            self._update_component_state(power=PowerState.OFF)
            return (
                ResultCode.OK,
                msg,
            )

        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            msg = f'Unable to turn off LRU: {"single outlet failed to turn off" if self._using_single_outlet else "both outlets failed to turn off"}'
            self.logger.error(msg)
            return (
                ResultCode.FAILED,
                msg,
            )

        else:
            self.logger.error(
                "LRU failed to turn off: one outlet failed to turn off"
            )
            return (
                ResultCode.FAILED,
                "LRU failed to turn off: one outlet failed to turn off",
            )

    def is_off_allowed(self: TalonLRUComponentManager) -> bool:
        self.logger.debug("Checking if off is allowed")
        if self._component_state["power"] == PowerState.ON:
            return True
        self.logger.info("LRU is already off, do not need to turn off.")
        return False

    def _off(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Turn off the TalonLRU and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering TalonLRUComponentManager.off")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        # Power off both outlets
        result1, result2 = self._turn_off_pdus(task_abort_event)

        # Stop monitoring talon board telemetries and fault status
        talon_off_result = self._turn_off_talons()
        if talon_off_result:
            task_callback(
                result=talon_off_result,
                status=TaskStatus.FAILED,
            )
            return

        # _determine_off_result_code will update the component power state
        task_callback(
            result=self._determine_off_result_code(result1, result2),
            status=TaskStatus.COMPLETED,
        )

    @check_communicating
    def off(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit off operation method to task executor queue.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )
