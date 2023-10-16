# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

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

        self._simulation_mode_events = [None, None]

        self._check_power_mode_callback = check_power_mode_callback

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

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

        self._proxy_talondx_board1 = self.get_device_proxy(
            "mid_csp_cbf/talon_board/" + self._talons[0]
        )
        self._proxy_talondx_board2 = self.get_device_proxy(
            "mid_csp_cbf/talon_board/" + self._talons[1]
        )

        # Needs Admin mode == ONLINE to run ON command
        self._proxy_talondx_board1.adminMode = AdminMode.ONLINE
        self._proxy_talondx_board2.adminMode = AdminMode.ONLINE

        self._proxy_power_switch1 = self.get_device_proxy(
            "mid_csp_cbf/power_switch/" + self._pdus[0]
        )
        if self._pdus[1] == self._pdus[0]:
            self._proxy_power_switch2 = self._proxy_power_switch1
        else:
            self._proxy_power_switch2 = self.get_device_proxy(
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
            self.pdu1_power_mode = self._proxy_power_switch1.GetOutletPowerMode(
                self._pdu_outlets[0]
            )
            if self._proxy_power_switch1.numOutlets == 0:
                self.pdu1_power_mode = PowerMode.UNKNOWN

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
                self.pdu2_power_mode = self._proxy_power_switch2.GetOutletPowerMode(
                    self._pdu_outlets[1]
                )
                if self._proxy_power_switch2.numOutlets == 0:
                    self.pdu2_power_mode = PowerMode.UNKNOWN

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

    def check_power_mode(
        self: TalonLRUComponentManager, state: DevState
    ) -> None:
        """
        Get the power mode of both PDUs and check that it is consistent with the
        current device state.

        :param state: device operational state
        """
        if self._proxy_power_switch1 is not None:
            if self._proxy_power_switch1.numOutlets != 0:
                self.pdu1_power_mode = self._proxy_power_switch1.GetOutletPowerMode(
                    self._pdu_outlets[0]
                )
            else:
                self.pdu1_power_mode = PowerMode.UNKNOWN
        else:
            self.pdu1_power_mode = PowerMode.UNKNOWN

        if self._proxy_power_switch2 is not None:
            if self._proxy_power_switch2.numOutlets != 0:
                if (self._pdus[1] == self._pdus[0]) and (
                    self._pdu_outlets[1] == self._pdu_outlets[0]
                ):
                    self.pdu2_power_mode = self.pdu1_power_mode
                else:
                    self.pdu2_power_mode = self._proxy_power_switch2.GetOutletPowerMode(
                        self._pdu_outlets[1]
                    )
            else:
                self.pdu2_power_mode = PowerMode.UNKNOWN
        else:
            self.pdu2_power_mode = PowerMode.UNKNOWN

        # Check the expected power mode
        if state == DevState.INIT or state == DevState.OFF:
            expected_power_mode = PowerMode.OFF
        elif state == DevState.ON:
            expected_power_mode = PowerMode.ON
        else:
            # In other device states, we don't know what the expected power
            # mode should be. Don't check it.
            return

        if (
            self.pdu1_power_mode == expected_power_mode
            and self.pdu2_power_mode == expected_power_mode
        ):
            return

        if self.pdu1_power_mode != expected_power_mode:
            self._logger.error(
                f"PDU outlet 1 expected power mode: ({expected_power_mode}),"
                f" actual power mode: ({self.pdu1_power_mode})"
            )

        if self.pdu2_power_mode != expected_power_mode:
            self._logger.error(
                f"PDU outlet 2 expected power mode: ({expected_power_mode}),"
                f" actual power mode: ({self.pdu2_power_mode})"
            )

        # Temporary fix to avoid redeploying MCS (CIP-1561)
        # PDU outlet state mismatch is logged but fault is not triggered
        # self.update_component_fault(True)
        return

    def on(
        self: TalonLRUComponentManager, simulation_mode: SimulationMode
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the TalonLRU and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self.connected:
            # Power on both outlets
            result1 = ResultCode.FAILED
            if self._proxy_power_switch1 is not None:
                # set PDU 1 simulation mode
                self._proxy_power_switch1.adminMode = AdminMode.OFFLINE
                self._proxy_power_switch1.simulationMode = simulation_mode
                self._proxy_power_switch1.adminMode = AdminMode.ONLINE

                result1 = self._proxy_power_switch1.TurnOnOutlet(
                    self._pdu_outlets[0]
                )[0][0]
                if result1 == ResultCode.OK:
                    self.pdu1_power_mode = PowerMode.ON
                    self._logger.info("PDU 1 successfully turned on.")

            result2 = ResultCode.FAILED
            if self._proxy_power_switch2 is not None:
                if (
                    self._pdus[1] == self._pdus[0]
                    and self._pdu_outlets[1] == self._pdu_outlets[0]
                ):
                    self._logger.info("PDU 2 is not used.")
                    result2 = result1
                else:
                    # set PDU 2 simulation mode
                    self._proxy_power_switch2.adminMode = AdminMode.OFFLINE
                    self._proxy_power_switch2.simulationMode = simulation_mode
                    self._proxy_power_switch2.adminMode = AdminMode.ONLINE

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
        else:
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            self.update_component_fault(True)
            return (ResultCode.FAILED, log_msg)

    def off(self: TalonLRUComponentManager,) -> Tuple[ResultCode, str]:
        """
        Turn off the TalonLRU and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self.connected:
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
            try:
                self._proxy_talondx_board1.Off()
            except tango.DevFailed as df:
                self._logger.warn(
                    f"Talon board {self._talons[0]} OFF command failed: {df}"
                )

            try:
                self._proxy_talondx_board2.Off()
            except tango.DevFailed as df:
                self._logger.warn(
                    f"Talon board {self._talons[1]} OFF command failed: {df}"
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

        else:
            log_msg = "Proxies not connected"
            self._logger.error(log_msg)
            self.update_component_fault(True)
            return (ResultCode.FAILED, log_msg)

    def standby(self: TalonLRUComponentManager,) -> Tuple[ResultCode, str]:
        """
        Turn the TalonLRU into low power standby mode

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        return (ResultCode.OK, "TalonLRU Standby command completed OK")
