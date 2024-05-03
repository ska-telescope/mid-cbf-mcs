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
from typing import Any, Callable, List, Optional, Tuple

import tango
from ska_control_model import TaskStatus
from ska_tango_base.base.component_manager import check_communicating
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
        talons: List[str],
        pdus: List[str],
        pdu_outlets: List[str],
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
        # TODO: the talondx_board proxies are not currently used for anything
        #       as the mirroring device on the HPS has not yet been created
        self._talons = talons
        self._pdus = pdus
        self._pdu_outlets = pdu_outlets
        self._pdu_cmd_timeout = pdu_cmd_timeout

        self._proxy_talondx_board1 = None
        self._proxy_talondx_board2 = None
        self._proxy_power_switch1 = None
        self._proxy_power_switch2 = None

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
            self.logger.info(f"Attempting connection to {fqdn} device")
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

    def _init_power_switch(self, pdu, pdu_outlet) -> None:
        """
        Initialize power switch and get the power mode of the specified outlet.

        :param pdu: FQDN of the power switch device
        :param pdu_outlet: ID of the PDU outlet
        :return: the power switch proxy and the power mode of the outlet
        """
        proxy = self._get_device_proxy("mid_csp_cbf/power_switch/" + pdu)
        if proxy is not None:
            proxy.set_timeout_millis(self._pdu_cmd_timeout * 1000)
            power_state = proxy.GetOutletPowerState(pdu_outlet)
            if proxy.numOutlets == 0:
                power_state = PowerState.UNKNOWN

            # Set the power switch's simulation mode
            proxy.adminMode = AdminMode.OFFLINE
            proxy.simulationMode = self.simulation_mode
            proxy.adminMode = AdminMode.ONLINE
        return proxy, power_state

    def _init_power_switch_proxies(self: TalonLRUComponentManager) -> None:
        """
        Get and initialize the 2 Power Switch proxies
        """
        (
            self._proxy_power_switch1,
            self.pdu1_power_state,
        ) = self._init_power_switch(self._pdus[0], self._pdu_outlets[0])
        if self._pdus[1] == self._pdus[0]:
            self._proxy_power_switch2 = self._proxy_power_switch1
            self.pdu2_power_state = self.pdu1_power_state
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

        if self._communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Communication already established")
            return

        # Get and initialize the device proxies of all the devices we care about
        self._init_talon_proxies()
        self._init_power_switch_proxies()

        if None in [
            self._proxy_power_switch1,
            self._proxy_power_switch2,
            self._proxy_talondx_board1,
            self._proxy_talondx_board2,
        ]:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
        else:
            super().start_communicating()
            self._update_component_state(power=self.get_lru_power_state())

    def stop_communicating(self: TalonLRUComponentManager) -> None:
        """
        Stop communication with the component.
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager.stop_communicating"
        )
        self._update_component_state(power=PowerState.UNKNOWN)
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

        if (self._pdus[1] == self._pdus[0]) and (
            self._pdu_outlets[1] == self._pdu_outlets[0]
        ):
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
    ) -> Tuple[ResultCode, ResultCode]:
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
            # TODO: Handle LRC in LRC
            result1 = self._proxy_power_switch1.TurnOnOutlet(
                self._pdu_outlets[0]
            )[0][0]
            if result1 == ResultCode.OK:
                self.pdu1_power_state = PowerState.ON
                self.logger.info("PDU 1 successfully turned on.")

        # Turn on PDU 2
        result2 = ResultCode.FAILED
        if (
            self._pdus[1] == self._pdus[0]
            and self._pdu_outlets[1] == self._pdu_outlets[0]
        ):
            self.logger.info("PDU 2 is not used.")
            result2 = result1
        elif self.pdu2_power_state == PowerState.ON:
            self.logger.info("PDU 2 is already on.")
            result2 = ResultCode.OK
        elif self._proxy_power_switch2 is not None:
            result2 = self._proxy_power_switch2.TurnOnOutlet(
                self._pdu_outlets[1]
            )[0][0]
            if result2 == ResultCode.OK:
                self.pdu2_power_state = PowerState.ON
                self.logger.info("PDU 2 successfully turned on.")

        return result1, result2

    def _turn_on_talons(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, ResultCode]:
        """
        Turn on the two Talon boards.
        """
        try:
            self._proxy_talondx_board1.On()
        except tango.DevFailed as df:
            self.logger.warn(
                f"Talon board {self._talons[0]} ON command failed: {df}"
            )

        try:
            self._proxy_talondx_board2.On()
        except tango.DevFailed as df:
            self.logger.warn(
                f"Talon board {self._talons[1]} ON command failed: {df}"
            )

    def _determine_on_result_code(
        self: TalonLRUComponentManager,
        result1: ResultCode,
        result2: ResultCode,
    ) -> Tuple[ResultCode, str]:
        """
        Determine the return code to return from the on command, given turning on PDUs' result codes.
        Also update the component power mode if successful.

        :param result1: the result code of turning on PDU 1
        :param result2: the result code of turning on PDU 2
        :return: A tuple containing a return code and a string
        """
        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            self.logger.error(
                "Unable to turn on LRU as both power switch outlets failed to power on"
            )
            return (
                ResultCode.FAILED,
                "LRU failed to turned on: both outlets failed to turn on",
            )
        elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
            self._update_component_state(power=PowerState.ON)
            return (
                ResultCode.OK,
                "LRU successfully turn on: one outlet successfully turned on",
            )
        else:
            self._update_component_state(power=PowerState.ON)
            return (
                ResultCode.OK,
                "LRU successfully turn on: both outlets successfully turned on",
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

        result1, result2 = self._turn_on_pdus()

        # Start monitoring talon board telemetries and fault status
        # This can fail if HPS devices are not deployed to the
        # board, but it's okay to continue.
        self._turn_on_talons()

        # _determine_on_result_code will update the component power state
        task_callback(
            result=self._determine_on_result_code(result1, result2),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def on(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[ResultCode, str]:
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
    ) -> Tuple[ResultCode, ResultCode]:
        """
        Turn off the two PDUs.

        :return: A tuple containing the 2 return codes of turning off the PDUs
        """
        # Power off PDU 1
        result1 = ResultCode.FAILED
        if self._proxy_power_switch1 is not None:
            # TODO: Handle LRC in LRC
            result1 = self._proxy_power_switch1.TurnOffOutlet(
                self._pdu_outlets[0]
            )[0][0]
            if result1 == ResultCode.OK:
                self.pdu1_power_state = PowerState.OFF
                self.logger.info("PDU 1 successfully turned off.")

        # Power off PDU 2
        result2 = ResultCode.FAILED
        if self._proxy_power_switch2 is not None:
            if (
                self._pdus[1] == self._pdus[0]
                and self._pdu_outlets[1] == self._pdu_outlets[0]
            ):
                self.logger.info("PDU 2 is not used.")
                result2 = result1
            else:
                result2 = self._proxy_power_switch2.TurnOffOutlet(
                    self._pdu_outlets[1]
                )[0][0]
                if result2 == ResultCode.OK:
                    self.pdu2_power_state = PowerState.OFF
                    self.logger.info("PDU 2 successfully turned off.")
        return result1, result2

    def _turn_off_talon(
        self: TalonLRUComponentManager,
        board_id: int,
        talondx_board_proxy: context.DeviceProxy,
    ):
        """
        Turn off the specified Talon board.
        """
        try:
            talondx_board_proxy.Off()
        except tango.DevFailed as df:
            return (
                ResultCode.FAILED,
                f"_turn_off_boards FAILED on Talon board {board_id}: {df}",
            )
        return (
            ResultCode.OK,
            f"_turn_off_boards completed OK on Talon board {board_id}",
        )

    def _turn_off_talons(
        self: TalonLRUComponentManager,
    ) -> None | Tuple[ResultCode, str]:
        """
        Turn off the two Talon boards, threaded.

        :return: ResultCode.FAILED if one of the boards failed to turn off, None otherwise
        """
        talondx_board_proxies_by_id = {
            1: self._proxy_talondx_board1,
            2: self._proxy_talondx_board2,
        }

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self._turn_off_talon, board_id, proxy_talondx_board
                )
                for board_id, proxy_talondx_board in talondx_board_proxies_by_id.items()
            ]
            results = [f.result() for f in futures]
        for result_code, msg in results:
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
    ) -> Tuple[ResultCode, str]:
        """
        Determine the return code to return from the off command, given turning on PDUs' result codes.
        Also update the component power mode if successful.

        :param result1: the result code of turning off PDU 1
        :param result2: the result code of turning off PDU 2
        :return: A tuple containing a return code and a string
        """
        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            self.logger.error(
                "Unable to turn off LRU as both power switch outlets failed to power off"
            )
            return (
                ResultCode.FAILED,
                "LRU failed to turn off: failed to turn off both outlets",
            )
        elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
            self.logger.error(
                "Unable to turn off LRU as a power switch outlet failed to power off"
            )
            return (
                ResultCode.FAILED,
                "LRU failed to turn off: only one outlet turned off",
            )
        else:
            self._update_component_state(power=PowerState.OFF)
            return (
                ResultCode.OK,
                "LRU successfully turned off: both outlets turned off",
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
        result1, result2 = self._turn_off_pdus()

        # Stop monitoring talon board telemetries and fault status
        talon_off_result = self._turn_off_talons()
        if talon_off_result:
            task_callback(
                result=talon_off_result,
                status=TaskStatus.COMPLETED,
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
    ) -> Tuple[ResultCode, str]:
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
