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
        check_power_mode_callback: Callable,
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
        :param check_power_mode_callback: callback to be called in event of
            power switch simulationMode change
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

        self._check_power_mode_callback = check_power_mode_callback

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    # --------------
    #  Comunication
    # --------------

    def start_communicating(self: TalonLRUComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()

        if len(self._talons) < 2:
            self._logger.error("Expect two Talon board FQDNs")
            tango.Except.throw_exception(
                "TalonLRU_TalonBoardFailed",
                "Two FQDNs for Talon Boards are needed for the LRU",
                "start_communicating()",
            )

        self._proxy_talondx_board1 = self._get_device_proxy(
            "mid_csp_cbf/talon_board/" + self._talons[0]
        )
        self._proxy_talondx_board2 = self._get_device_proxy(
            "mid_csp_cbf/talon_board/" + self._talons[1]
        )

        # Needs Admin mode == ONLINE to run ON command
        self._proxy_talondx_board1.adminMode = AdminMode.ONLINE
        self._proxy_talondx_board2.adminMode = AdminMode.ONLINE

        self._proxy_power_switch1 = self._get_device_proxy(
            "mid_csp_cbf/power_switch/" + self._pdus[0]
        )
        if self._pdus[1] == self._pdus[0]:
            self._proxy_power_switch2 = self._proxy_power_switch1
        else:
            self._proxy_power_switch2 = self._get_device_proxy(
                "mid_csp_cbf/power_switch/" + self._pdus[1]
            )

        if (self._proxy_power_switch1 is None) and (
            self._proxy_power_switch2 is None
        ):
            self.update_communication_status(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.update_component_fault(True)
            self._logger.error("Both power switches failed to connect.")
            return
        # Subscribe to simulationMode change event and increase the access
        # timeout of the power switch proxies, since the HTTP connection
        # timeout must be >3s.
        if self._proxy_power_switch1 is not None:
            # TEMP: increase timeout to 30s until LRU2 is switched over to the ITF PDU
            # to handle the observed slowness in the PSI PDU
            self._proxy_power_switch1.set_timeout_millis(
                self._pdu_cmd_timeout * 1000
            )
            self._simulation_mode_events[
                0
            ] = self._proxy_power_switch1.add_change_event_callback(
                "simulationMode",
                self._check_power_mode_callback,
                stateless=True,
            )
            self.pdu1_power_mode = (
                self._proxy_power_switch1.GetOutletPowerMode(
                    self._pdu_outlets[0]
                )
            )
            if self._proxy_power_switch1.numOutlets == 0:
                self.pdu1_power_mode = PowerMode.UNKNOWN

            # Set the power switch 1's simulation mode
            self._proxy_power_switch1.adminMode = AdminMode.OFFLINE
            self._proxy_power_switch1.simulationMode = self.simulation_mode
            self._proxy_power_switch1.adminMode = AdminMode.ONLINE

        if self._proxy_power_switch2 is not None:
            if self._pdus[1] != self._pdus[0]:
                # TEMP: increase timeout to 30s until LRU2 is switched over to the ITF PDU
                # to handle the observed slowness in the PSI PDU
                self._proxy_power_switch2.set_timeout_millis(
                    self._pdu_cmd_timeout * 1000
                )
                self._simulation_mode_events[
                    1
                ] = self._proxy_power_switch2.add_change_event_callback(
                    "simulationMode",
                    self._check_power_mode_callback,
                    stateless=True,
                )
                self.pdu2_power_mode = (
                    self._proxy_power_switch2.GetOutletPowerMode(
                        self._pdu_outlets[1]
                    )
                )
                if self._proxy_power_switch2.numOutlets == 0:
                    self.pdu2_power_mode = PowerMode.UNKNOWN

                # Set the power switch 2's simulation mode
                self._proxy_power_switch2.adminMode = AdminMode.OFFLINE
                self._proxy_power_switch2.simulationMode = self.simulation_mode
                self._proxy_power_switch2.adminMode = AdminMode.ONLINE

        self.connected = True

        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: TalonLRUComponentManager) -> None:
        """Stop communication with the component."""
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

    def _get_device_proxy(
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

    # -----------------
    #  General methods
    # -----------------

    def check_power_mode(
        self: TalonLRUComponentManager, state: DevState
    ) -> None:
        """
        Get the power mode of both PDUs and check that it is consistent with the
        current device state.

        :param state: device operational state
        :return: None
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

    def _update_power_mode(self: TalonLRUComponentManager) -> None:
        """
        Check and update current PowerMode states of both PDUs.

        :return: None
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

        :param proxy_power_switch: the power switch proxy
        :param outlet: the outlet to get the power mode of
        :return: the PowerMode of the outlet
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

    # -----------------
    #  Command methods
    # -----------------

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
        # Check if the component is connected
        if not self.connected:
            return self._handle_not_connected()

        # Check and update the power mode of the PDUs
        self._update_power_mode()

        # Power on both outlets
        result1, self.pdu1_power_mode = self._turn_on_outlet(
            self.pdu1_power_mode,
            self._proxy_power_switch1,
            self._pdu_outlets[0],
            1,
        )

        if (
            self._pdus[1] == self._pdus[0]
            and self._pdu_outlets[1] == self._pdu_outlets[0]
        ):
            self._logger.info("PDU 2 is not used.")
            result2 = result1
        else:
            result2, self.pdu2_power_mode = self._turn_on_outlet(
                self.pdu2_power_mode,
                self._proxy_power_switch2,
                self._pdu_outlets[1],
                2,
            )

        # Start monitoring talon board telemetries and fault status
        # This can fail if HPS devices are not deployed to the
        # board, but it's okay to continue.
        self.turn_on_talon_board(self._proxy_talondx_board1, self._talons[0])
        self.turn_on_talon_board(self._proxy_talondx_board2, self._talons[1])

        # Determine what result code to return
        return self._determine_result_code(result1, result2, "on")

    def _handle_not_connected(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Handle case where the component is not connected by logging and updating component fault.

        :return: A tuple containing a return code and a string
        """
        log_msg = "Proxies not connected"
        self._logger.error(log_msg)
        self.update_component_fault(True)
        return (ResultCode.FAILED, log_msg)

    def _turn_on_outlet(
        self: TalonLRUComponentManager,
        pdu_power_mode: PowerMode,
        proxy_power_switch: CbfDeviceProxy,
        pdu_outlet: str,
        pdu_id: int,
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the specified PDU outlet.

        :param pdu_power_mode: the current power mode of the PDU
        :param proxy_power_switch: the power switch proxy
        :param pdu_outlet: the outlet to turn on
        :param pdu_id: the ID of the PDU
        :return: A tuple containing a return code and updated PDU power mode
        """
        if pdu_power_mode == PowerMode.ON:
            self._logger.info(f"PDU {pdu_id} is already on.")
            result = ResultCode.OK
        elif proxy_power_switch is not None:
            result = proxy_power_switch.TurnOnOutlet(pdu_outlet)[0][0]
            if result == ResultCode.OK:
                pdu_power_mode = PowerMode.ON
                self._logger.info(f"PDU {pdu_id} successfully turned on.")
        else:
            result = ResultCode.FAILED
        return result, pdu_power_mode

    def _turn_on_talon_board(
        self: TalonLRUComponentManager,
        proxy_talondx_board: CbfDeviceProxy,
        talon_id: int,
    ) -> None:
        """
        Turn on the specified Talon board.

        :param proxy_talondx_board: the Talon board proxy
        :param talon_id: the ID of the Talon board
        """
        try:
            proxy_talondx_board.On()
        except tango.DevFailed as df:
            self._logger.warn(
                f"Talon board {talon_id} ON command failed: {df}"
            )

    def _determine_result_code(
        self: TalonLRUComponentManager,
        result1: ResultCode,
        result2: ResultCode,
        action: str,
    ) -> Tuple[ResultCode, str]:
        """
        Determine the result code based on the results of the power switch commands.
        Also update the component fault status.

        :param result1: the result code of the first power switch command
        :param result2: the result code of the second power switch command
        :param action: the action that was performed (on/off)
        :return: A tuple containing a return code and a string message
        """
        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            self.update_component_fault(True)
            return (ResultCode.FAILED, f"Failed to turn {action} both outlets")
        elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
            self.update_component_fault(True)
            return (
                ResultCode.FAILED,
                f"Only one outlet successfully turned {action}",
            )
        else:
            power_mode = PowerMode.ON if action == "on" else PowerMode.OFF
            self.update_component_power_mode(power_mode)
            return (
                ResultCode.OK,
                f"Both outlets successfully turned {action}",
            )

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
            self._handle_not_connected()

        # Power off both outlets
        result1, self.pdu1_power_mode = self._turn_off_outlet(
            self.pdu1_power_mode,
            self._proxy_power_switch1,
            self._pdu_outlets[0],
            1,
        )

        if (
            self._pdus[1] == self._pdus[0]
            and self._pdu_outlets[1] == self._pdu_outlets[0]
        ):
            self._logger.info("PDU 2 is not used.")
            result2 = result1
        else:
            result2, self.pdu2_power_mode = self._turn_off_outlet(
                self.pdu2_power_mode,
                self._proxy_power_switch2,
                self._pdu_outlets[1],
                2,
            )

        # Stop monitoring talon board telemetries and fault status
        turn_off_result = self._turn_off_talon_boards()
        if turn_off_result is not None:
            return turn_off_result

        # Determine what result code to return
        return self._determine_result_code(result1, result2, "off")

    def _turn_off_outlet(
        self: TalonLRUComponentManager,
        pdu_power_mode: PowerMode,
        proxy_power_switch: CbfDeviceProxy,
        pdu_outlet: str,
        pdu_id: int,
    ) -> Tuple[ResultCode, str]:
        """
        Turn off the specified PDU outlet.

        :param pdu_power_mode: the current power mode of the PDU
        :param proxy_power_switch: the power switch proxy
        :param pdu_outlet: the outlet to turn off
        :param pdu_id: the ID of the PDU
        :return: A tuple containing a return code and updated PDU power mode
        """
        result = ResultCode.FAILED
        if proxy_power_switch is not None:
            result = proxy_power_switch.TurnOffOutlet(pdu_outlet)[0][0]
            if result == ResultCode.OK:
                pdu_power_mode = PowerMode.OFF
                self._logger.info(f"PDU {pdu_id} successfully turned off.")
        return result, pdu_power_mode

    def _turn_off_talon_boards(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, str] | None:
        """
        Turn off both Talon boards.

        :return: None if successful, otherwise a tuple containing a return code and a string message
        """
        # Stop monitoring talon board telemetries and fault status
        talondx_board_proxies_by_id = {
            1: self._proxy_talondx_board1,
            2: self._proxy_talondx_board2,
        }
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self._turn_off_talon_boards, board_id, proxy_talondx_board
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

    def _turn_off_board(
        self: TalonLRUComponentManager,
        board_id: int,
        talondx_board_proxy: CbfDeviceProxy,
    ) -> Tuple[ResultCode, str]:
        """
        Turn off the specified Talon board.

        :param board_id: the ID of the Talon board
        :param talondx_board_proxy: the Talon board proxy
        :return: A tuple containing a return code and a string message
        """
        try:
            talondx_board_proxy.Off()
        except tango.DevFailed as df:
            return (
                ResultCode.FAILED,
                f"_turn_off_board FAILED on Talon board {board_id}: {df}",
            )
        return (
            ResultCode.OK,
            f"_turn_off_board completed OK on Talon board {board_id}",
        )

    def standby(
        self: TalonLRUComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn the TalonLRU into low power standby mode

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        return (ResultCode.OK, "TalonLRU Standby command completed OK")
