# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import concurrent.futures
import logging
from typing import Callable, List, Optional, Tuple

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, PowerMode, SimulationMode
from tango import DevState

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy


class TalonLRUComponentManager(CbfComponentManager):
    """A component manager for the TalonLRU device."""

    def __init__(
        self: TalonLRUComponentManager,
        talons: List[str],
        pdus: List[str],
        pdu_outlets: List[str],
        pdu_cmd_timeout: int,
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new instance.

        :param talons: FQDNs of the Talon DX board
        :param pdus: FQDNs of the power switch devices
        :param pdu_outlets: IDs of the PDU outlets
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        self.connected = False

        # Get the device proxies of all the devices we care about
        # TODO: the talondx_board proxies are not currently used for anything
        # as the mirroring device on the HPS has not yet been created
        self._talons = talons
        self._pdus = pdus
        self._pdu_outlets = pdu_outlets
        self._pdu_cmd_timeout = pdu_cmd_timeout

        self.pdu1_power_mode = PowerMode.UNKNOWN
        self.pdu2_power_mode = PowerMode.UNKNOWN

        self._proxy_talondx_board1 = None
        self._proxy_talondx_board2 = None
        self._proxy_power_switch1 = None
        self._proxy_power_switch2 = None

        self.simulation_mode = SimulationMode.TRUE
        self._simulation_mode_events = [None, None]

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    # -------------
    # Communication
    # -------------

    def get_device_proxy(
        self: TalonLRUComponentManager, fqdn: str
    ) -> CbfDeviceProxy | None:
        """
        Attempt to get a device proxy of the specified device.

        :param fqdn: FQDN of the device to connect to
        :return: CbfDeviceProxy to the device or None if no connection was made
        """
        try:
            self._logger.info(f"Attempting connection to {fqdn} device")
            device_proxy = CbfDeviceProxy(
                fqdn=fqdn, logger=self._logger, connect=False
            )
            device_proxy.connect(max_time=0)  # Make one attempt at connecting
            return device_proxy
        except tango.DevFailed as df:
            for item in df.args:
                self._logger.error(
                    f"Failed connection to {fqdn} device: {item.reason}"
                )
            self.update_component_fault(True)
            return None

    def _init_talon_proxies(self: TalonLRUComponentManager) -> None:
        """
        Get and initialize the 2 Talon Board proxies
        """
        if len(self._talons) < 2:
            self._logger.error("Expected two Talon board FQDNs")
            tango.Except.throw_exception(
                "TalonLRU_TalonBoardFailed",
                "Two FQDNs for Talon Boards are needed for the LRU",
                "start_communicating()",
            )

        self._proxy_talondx_board1 = self.get_device_proxy(
            "mid_csp_cbf/talon_board/" + self._talons[0]
        )

        self._proxy_talondx_board2 = self.get_device_proxy(
            "mid_csp_cbf/talon_board/" + self._talons[1]
        )

        # Needs Admin mode == ONLINE to run ON command
        self._proxy_talondx_board1.adminMode = AdminMode.ONLINE
        self._proxy_talondx_board2.adminMode = AdminMode.ONLINE

    def _init_power_switch(self, pdu, pdu_outlet) -> None:
        """
        Initialize power switch and get the power mode of the specified outlet.

        :param pdu: FQDN of the power switch device
        :param pdu_outlet: ID of the PDU outlet
        :return: the power switch proxy and the power mode of the outlet
        """
        proxy = self.get_device_proxy("mid_csp_cbf/power_switch/" + pdu)
        if proxy is not None:
            proxy.set_timeout_millis(self._pdu_cmd_timeout * 1000)
            power_mode = proxy.GetOutletPowerMode(pdu_outlet)
            if proxy.numOutlets == 0:
                power_mode = PowerMode.UNKNOWN

            # Set the power switch's simulation mode
            proxy.adminMode = AdminMode.OFFLINE
            proxy.simulationMode = self.simulation_mode
            proxy.adminMode = AdminMode.ONLINE
        return proxy, power_mode

    def _init_power_switch_proxies(self: TalonLRUComponentManager) -> None:
        """
        Get and initialize the 2 Power Switch proxies
        """
        (
            self._proxy_power_switch1,
            self.pdu1_power_mode,
        ) = self._init_power_switch(self._pdus[0], self._pdu_outlets[0])
        if self._pdus[1] == self._pdus[0]:
            self._proxy_power_switch2 = self._proxy_power_switch1
            self.pdu2_power_mode = self.pdu1_power_mode
        else:
            (
                self._proxy_power_switch2,
                self.pdu2_power_mode,
            ) = self._init_power_switch(self._pdus[1], self._pdu_outlets[1])

        if (self._proxy_power_switch1 is None) and (
            self._proxy_power_switch2 is None
        ):
            self.update_communication_status(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.update_component_fault(True)
            self._logger.error("Both power switches failed to connect.")

    def start_communicating(self: TalonLRUComponentManager) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()

        # Get and initialize the device proxies of all the devices we care about
        self._init_talon_proxies()
        self._init_power_switch_proxies()

        # Update status
        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: TalonLRUComponentManager) -> None:
        """
        Stop communication with the component.
        """
        super().stop_communicating()
        if self._simulation_mode_events[0]:
            self._proxy_power_switch1.remove_event(
                "simulationMode", self._simulation_mode_events[0]
            )
            self._simulation_mode_events[0] = None
        if self._simulation_mode_events[1]:
            self._proxy_power_switch2.remove_event(
                "simulationMode", self._simulation_mode_events[1]
            )
            self._simulation_mode_events[1] = None
        self.connected = False

    # ---------------
    # General methods
    # ---------------

    def _update_power_mode(self: TalonLRUComponentManager) -> None:
        """
        Check and update current PowerMode states of both PDUs.
        """
        self.pdu1_power_mode = self._get_power_mode(
            self._proxy_power_switch1, self._pdu_outlets[0]
        )
        self.pdu2_power_mode = self._get_power_mode(
            self._proxy_power_switch2, self._pdu_outlets[1]
        )

        if (self._pdus[1] == self._pdus[0]) and (
            self._pdu_outlets[1] == self._pdu_outlets[0]
        ):
            self.pdu2_power_mode = self.pdu1_power_mode

    def _get_power_mode(
        self: TalonLRUComponentManager, proxy_power_switch, outlet
    ) -> PowerMode:
        """
        Get the power mode of the specified outlet from the power switch.

        :params: proxy_power_switch: the power switch proxy
        :params: outlet: the outlet to get the power mode of
        """
        if (
            proxy_power_switch is not None
            and proxy_power_switch.numOutlets != 0
        ):
            return proxy_power_switch.GetOutletPowerMode(outlet)
        else:
            return PowerMode.UNKNOWN

    def _get_expected_power_mode(
        self: TalonLRUComponentManager, state: DevState
    ):
        """
        Get the expected power mode based on given device state.

        :param state: device operational state
        :return: the expected PowerMode
        """
        if state in [DevState.INIT, DevState.OFF]:
            return PowerMode.OFF
        elif state == DevState.ON:
            return PowerMode.ON
        else:
            # In other device states, we don't know what the expected power
            # mode should be. Don't check it.
            return None

    def check_power_mode(
        self: TalonLRUComponentManager, state: DevState
    ) -> None:
        """
        Get the power mode of both PDUs and check that it is consistent with the
        current device state.

        :param state: device operational state
        """
        self._update_power_mode()

        expected_power_mode = self._get_expected_power_mode(state)
        if expected_power_mode is None:
            return

        # Check the power mode of each outlet matches expected
        for i, power_mode in enumerate(
            [self.pdu1_power_mode, self.pdu2_power_mode], start=1
        ):
            if power_mode != expected_power_mode:
                self._logger.error(
                    f"Power connection {i} expected power mode: ({expected_power_mode}),"
                    f" actual power mode: ({power_mode})"
                )

        # Temporary fix to avoid redeploying MCS (CIP-1561)
        # PDU outlet state mismatch is logged but fault is not triggered
        # self.update_component_fault(True)

    def get_lru_power_mode(self: TalonLRUComponentManager) -> PowerMode:
        """
        Get the current power mode of the TalonLRU based on the power mode of the PDUs.

        :return: the current power mode
        """
        self._update_power_mode()
        if (
            self.pdu1_power_mode == PowerMode.ON
            or self.pdu2_power_mode == PowerMode.ON
        ):
            return PowerMode.ON
        elif (
            self.pdu1_power_mode == PowerMode.OFF
            and self.pdu2_power_mode == PowerMode.OFF
        ):
            return PowerMode.OFF
        else:
            return PowerMode.UNKNOWN

    # ---------------
    # Command methods
    # ---------------

    def _handle_not_connected(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Handle the case where command called when the component manager is not connected.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        log_msg = "Attempted LRU command without connected proxies"
        self._logger.error(log_msg)
        self.update_component_fault(True)
        return (ResultCode.FAILED, log_msg)

    def _turn_on_pdus(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, ResultCode]:
        """
        If not already on, turn on the two PDUs.

        :return: A tuple containing the 2 return codes of turning on the PDUs
        """
        # Turn on PDU 1
        result1 = ResultCode.FAILED
        if self.pdu1_power_mode == PowerMode.ON:
            self._logger.info("PDU 1 is already on.")
            result1 = ResultCode.OK
        elif self._proxy_power_switch1 is not None:
            result1 = self._proxy_power_switch1.TurnOnOutlet(
                self._pdu_outlets[0]
            )[0][0]
            if result1 == ResultCode.OK:
                self.pdu1_power_mode = PowerMode.ON
                self._logger.info("PDU 1 successfully turned on.")

        # Turn on PDU 2
        result2 = ResultCode.FAILED
        if (
            self._pdus[1] == self._pdus[0]
            and self._pdu_outlets[1] == self._pdu_outlets[0]
        ):
            self._logger.info("PDU 2 is not used.")
            result2 = result1
        elif self.pdu2_power_mode == PowerMode.ON:
            self._logger.info("PDU 2 is already on.")
            result2 = ResultCode.OK
        elif self._proxy_power_switch2 is not None:
            result2 = self._proxy_power_switch2.TurnOnOutlet(
                self._pdu_outlets[1]
            )[0][0]
            if result2 == ResultCode.OK:
                self.pdu2_power_mode = PowerMode.ON
                self._logger.info("PDU 2 successfully turned on.")

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
            self._logger.warn(
                f"Talon board {self._talons[0]} ON command failed: {df}"
            )

        try:
            self._proxy_talondx_board2.On()
        except tango.DevFailed as df:
            self._logger.warn(
                f"Talon board {self._talons[1]} ON command failed: {df}"
            )

    def _determine_on_result_code(
        self: TalonLRUComponentManager,
        result1: ResultCode,
        result2: ResultCode,
    ) -> Tuple[ResultCode, str]:
        """
        Determine the return code to return from the on command, given turning on PDUs' result codes.
        Also update the component power mode and fault status.

        :param result1: the result code of turning on PDU 1
        :param result2: the result code of turning on PDU 2
        :return: A tuple containing a return code and a string
        """
        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            self.update_component_fault(True)
            return (ResultCode.FAILED, "Failed to turn on both outlets")
        elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
            self.update_component_power_mode(PowerMode.ON)
            return (
                ResultCode.OK,
                "Only one outlet successfully turned on",
            )
        else:
            self.update_component_power_mode(PowerMode.ON)
            return (ResultCode.OK, "Both outlets successfully turned on")

    def on(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the TalonLRU and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if not self.connected:
            return self._handle_not_connected()

        self._update_power_mode()

        # Power on both outlets
        result1, result2 = self._turn_on_pdus()

        # Start monitoring talon board telemetries and fault status
        # This can fail if HPS devices are not deployed to the
        # board, but it's okay to continue.
        self._turn_on_talons()

        # Determine what result code to return
        return self._determine_on_result_code(result1, result2)

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
            result1 = self._proxy_power_switch1.TurnOffOutlet(
                self._pdu_outlets[0]
            )[0][0]
            if result1 == ResultCode.OK:
                self.pdu1_power_mode = PowerMode.OFF
                self._logger.info("PDU 1 successfully turned off.")

        # Power off PDU 2
        result2 = ResultCode.FAILED
        if self._proxy_power_switch2 is not None:
            if (
                self._pdus[1] == self._pdus[0]
                and self._pdu_outlets[1] == self._pdu_outlets[0]
            ):
                self._logger.info("PDU 2 is not used.")
                result2 = result1
            else:
                result2 = self._proxy_power_switch2.TurnOffOutlet(
                    self._pdu_outlets[1]
                )[0][0]
                if result2 == ResultCode.OK:
                    self.pdu2_power_mode = PowerMode.OFF
                    self._logger.info("PDU 2 successfully turned off.")
        return result1, result2

    def _turn_off_talon(
        self: TalonLRUComponentManager, board_id, talondx_board_proxy
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
                self._logger.info(
                    f"Talon board successfully turned off: {msg}"
                )
            else:
                self._logger.warn(
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
        Also update the component fault status if necessary.

        :param result1: the result code of turning off PDU 1
        :param result2: the result code of turning off PDU 2
        :return: A tuple containing a return code and a string
        """
        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            self.update_component_fault(True)
            return (ResultCode.FAILED, "Failed to turn off both outlets")
        elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
            self.update_component_fault(True)
            return (
                ResultCode.FAILED,
                "Only one outlet successfully turned off",
            )
        else:
            self.update_component_power_mode(PowerMode.OFF)
            return (ResultCode.OK, "Both outlets successfully turned off")

    def off(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn off the TalonLRU and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if not self.connected:
            return self._handle_not_connected()

        # Power off both outlets
        result1, result2 = self._turn_off_pdus()

        # Stop monitoring talon board telemetries and fault status
        talon_off_result = self._turn_off_talons()
        if talon_off_result:
            return talon_off_result

        # Determine what result code to return
        return self._determine_off_result_code(result1, result2)
