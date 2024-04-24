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
from typing import Any, Callable, List, Optional, Tuple

from ska_control_model import TaskStatus
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, PowerState, SimulationMode
from tango import DevState

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy


class TalonLRUComponentManager(CbfComponentManager):
    """A component manager for the TalonLRU device."""

    # TODO: Find out if we can remove check_power_mode_callback
    def __init__(
        *args: Any,
        self: TalonLRUComponentManager,
        talons: List[str],
        pdus: List[str],
        pdu_outlets: List[str],
        pdu_cmd_timeout: int,
        check_power_mode_callback: Callable,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param talons: FQDNs of the Talon DX board
        :param pdus: FQDNs of the power switch devices
        :param pdu_outlets: IDs of the PDU outlets
        :param pdu_cmd_timeout: timeout for PDU commands in seconds
        :param check_power_mode_callback: callback to be called in event of
            power switch simulationMode change
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
        self._check_power_mode_callback = check_power_mode_callback

        self._proxy_talondx_board1 = None
        self._proxy_talondx_board2 = None
        self._proxy_power_switch1 = None
        self._proxy_power_switch2 = None

        self.pdu1_power_mode = PowerState.UNKNOWN
        self.pdu2_power_mode = PowerState.UNKNOWN

        self._simulation_mode_events = [None, None]



    # -------------
    # Communication
    # -------------

    def start_communicating(self: TalonLRUComponentManager) -> None:
        """
        Establish communication with the component, then start monitoring.
        """

        super().start_communicating()

        if len(self._talons) < 2:
            self._logger.error("Expect two Talon board FQDNs")
            tango.Except.throw_exception(
                "TalonLRU_TalonBoardFailed",
                "Two FQDNs for Talon Boards are needed for the LRU",
                "start_communicating()",
            )

        # TODO: Refactor entire connection logic to helpers
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
                self._proxy_power_switch1.GetOutletPowerState(
                    self._pdu_outlets[0]
                )
            )
            if self._proxy_power_switch1.numOutlets == 0:
                self.pdu1_power_mode = PowerState.UNKNOWN

            # Set the power switch 1's simulation mode
            self._proxy_power_switch1.adminMode = AdminMode.OFFLINE
            self._proxy_power_switch1.simulationMode = self.simulation_mode
            self._proxy_power_switch1.adminMode = AdminMode.ONLINE

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
                    self._proxy_power_switch2.GetOutletPowerState(
                        self._pdu_outlets[1]
                    )
                )
                if self._proxy_power_switch2.numOutlets == 0:
                    self.pdu2_power_mode = PowerState.UNKNOWN

                # Set the power switch 2's simulation mode
                self._proxy_power_switch2.adminMode = AdminMode.OFFLINE
                self._proxy_power_switch2.simulationMode = self.simulation_mode
                self._proxy_power_switch2.adminMode = AdminMode.ONLINE

        self._update_component_state(power=PowerState.OFF)

    def stop_communicating(self: TalonLRUComponentManager) -> None:
        """Stop communication with the component."""

        # TODO: can I removed this???
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

        self._update_component_state(power=PowerState.UNKNOWN)
        super().stop_communicating()

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
            self.update_component_state(fault = True)
            return None

    # ---------------
    # General methods
    # ---------------

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

    # ---------------
    # Command methods
    # ---------------

    def _on(
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
            log_msg = "Attempted ON sequence without connected proxies"
            self._logger.error(log_msg)
            self.update_component_fault(True)
            return (ResultCode.FAILED, log_msg)

        self._update_power_mode()

        # Power on both outlets
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

        # Start monitoring talon board telemetries and fault status
        # This can fail if HPS devices are not deployed to the
        # board, but it's okay to continue.
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

        # Determine what result code to return
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
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            self.update_component_fault(True)
            return (ResultCode.FAILED, log_msg)

        # Power off both outlets
        result1 = ResultCode.FAILED
        if self._proxy_power_switch1 is not None:
            result1 = self._proxy_power_switch1.TurnOffOutlet(
                self._pdu_outlets[0]
            )[0][0]
            if result1 == ResultCode.OK:
                self.pdu1_power_mode = PowerMode.OFF
                self._logger.info("PDU 1 successfully turned off.")

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

        # Stop monitoring talon board telemetries and fault status
        talondx_board_proxies_by_id = {
            1: self._proxy_talondx_board1,
            2: self._proxy_talondx_board2,
        }
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self._turn_off_boards, board_id, proxy_talondx_board
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

        # Determine what result code to return
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

    def _turn_off_boards(
        self: TalonLRUComponentManager, board_id, talondx_board_proxy
    ):
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
