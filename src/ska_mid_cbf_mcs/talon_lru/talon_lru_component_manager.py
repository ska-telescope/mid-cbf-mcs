# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import tango
from ska_control_model import PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


# TODO: Refactor
class TalonLRUComponentManager(CbfComponentManager):
    """
    A component manager for the TalonLRU device.
    """

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

        self._talons = talons
        self._pdus = pdus
        self._pdu_outlets = pdu_outlets
        self._pdu_cmd_timeout = pdu_cmd_timeout

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
        self.logger.debug(f"Attempting connection to {fqdn} device")
        try:
            return context.DeviceProxy(device_name=fqdn)
        except tango.DevFailed as df:
            self.logger.error(f"Failed connection to {fqdn} device: {df}")
            return None

    def _init_power_switch(
        self: TalonLRUComponentManager, pdu: str
    ) -> context.DeviceProxy | None:
        """
        Initialize power switch and get the power mode of the specified outlet.

        :param pdu: partial FQDN of the power switch device
        :return: the power switch proxy
        """
        power_switch_proxy = self._get_device_proxy(
            "mid_csp_cbf/power_switch/" + pdu
        )
        if power_switch_proxy is not None:
            try:
                if power_switch_proxy.numOutlets == 0:
                    self.logger.error(
                        "PowerSwitch driver has not been initialized."
                    )
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                return None
        return power_switch_proxy

    def _init_power_switch_proxies(self: TalonLRUComponentManager) -> bool:
        """
        Get and initialize the 2 Power Switch proxies

        :return: True if both proxies were successfully initialized, False otherwise
        """
        self._proxy_power_switch1 = self._init_power_switch(self._pdus[0])
        if self._proxy_power_switch1 is None:
            return False

        # If PDU1 and PDU2 match, use same proxy
        if self._pdus[0] == self._pdus[1]:
            self.logger.info("LRU is using a single PDU")
            self._proxy_power_switch2 = self._proxy_power_switch1
            # If outlet1 and outlet2 match then use the same PowerState and set using_single_outlet flag
            if self._pdu_outlets[0] == self._pdu_outlets[1]:
                self.logger.info("LRU is using a single PDU outlet")
                self._using_single_outlet = True
        else:
            self._proxy_power_switch2 = self._init_power_switch(self._pdus[1])
            if self._proxy_power_switch2 is None:
                return False
        return True

    def _subscribe_to_subdevices(self: TalonLRUComponentManager) -> None:
        """
        Subscribe to command results of the subdevices. This is necessary to monitor the status of the commands.
        """
        device_proxies = [
            self._proxy_power_switch1,
        ]

        if self._proxy_power_switch1 != self._proxy_power_switch2:
            device_proxies.append(self._proxy_power_switch2)

        for dp in device_proxies:
            self.attr_event_subscribe(
                proxy=dp,
                attr_name="longRunningCommandResult",
                callback=self.results_callback,
            )

        self.logger.info(
            f"event_ids after subscribing = {len(self.event_ids)}"
        )

    def _start_communicating(
        self: TalonLRUComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager._start_communicating"
        )

        # Get and initialize the device proxies of the power switches
        if not self._init_power_switch_proxies():
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        # Subscribe to command results of the devices
        self._subscribe_to_subdevices()
        super()._start_communicating()
        self._update_component_state(power=PowerState.OFF)

    def _unsubscribe_from_subdevices(self: TalonLRUComponentManager) -> None:
        """
        Unsubscribe to command results of the subdevices (power switches).
        """
        device_proxies = [
            self._proxy_power_switch1,
        ]

        if self._proxy_power_switch1 != self._proxy_power_switch2:
            device_proxies.append(self._proxy_power_switch2)

        for dp in device_proxies:
            self.unsubscribe_all_events(dp)

    def _stop_communicating(
        self: TalonLRUComponentManager, *args, **kwargs
    ) -> None:
        """
        Stop communication with the component.
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager.stop_communicating"
        )

        self._unsubscribe_from_subdevices()
        self.blocking_commands = set()

        super()._stop_communicating()

    # -------------
    # Fast Commands
    # -------------

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
            try:
                outlet_state = proxy_power_switch.GetOutletPowerState(outlet)
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to read outlet {outlet}'s power state: {df}"
                )
                outlet_state = PowerState.UNKNOWN
        else:
            outlet_state = PowerState.UNKNOWN
        return outlet_state

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

    def _get_lru_power_state(self: TalonLRUComponentManager) -> PowerState:
        """
        Get the current PowerState of the TalonLRU based on the power mode of the PDUs.
        Also update the current LRU PowerState state to match.

        :return: the current TalonLRU PowerState
        """
        self.logger.debug(
            "Entering TalonLRUComponentManager._get_lru_power_state"
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

        return lru_power_state

    # ---------------------
    # Long Running Commands
    # ---------------------

    # --- On Command --- #

    def _turn_on_pdus(
        self: TalonLRUComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, ResultCode]:
        """
        If not already on, turn on the two PDUs.

        :param task_abort_event: Event to signal task abort
        :return: A tuple containing the 2 return codes of turning on the PDUs
        """
        # Turn on PDU 1
        pdu1_result = ResultCode.FAILED
        if self.pdu1_power_state == PowerState.ON:
            self.logger.info("PDU 1 is already on.")
            pdu1_result = ResultCode.OK
        elif self._proxy_power_switch1 is not None:
            [
                [result_code],
                [command_id],
            ] = self._proxy_power_switch1.TurnOnOutlet(self._pdu_outlets[0])

            # Guard incase LRC was rejected.
            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} rejected"
                )
            else:
                self.blocking_command_ids = set([command_id])
                lrc_status = self.wait_for_blocking_results(
                    task_abort_event=task_abort_event
                )

                if lrc_status != TaskStatus.COMPLETED:
                    self.logger.error(
                        f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} failed/timed out",
                    )
                else:
                    self.pdu1_power_state = PowerState.ON
                    self.logger.info(
                        f"PDU 1 ({self._pdu_outlets[0]}) successfully turned on."
                    )
                    pdu1_result = ResultCode.OK

        # Turn on PDU 2
        pdu2_result = ResultCode.FAILED
        if self._using_single_outlet:
            self.logger.info("PDU 2 is not used.")
            pdu2_result = pdu1_result
        elif self.pdu2_power_state == PowerState.ON:
            self.logger.info("PDU 2 is already on.")
            pdu2_result = ResultCode.OK
        elif self._proxy_power_switch2 is not None:
            [
                [result_code],
                [command_id],
            ] = self._proxy_power_switch2.TurnOnOutlet(self._pdu_outlets[1])

            # Guard incase LRC was rejected.
            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} rejected"
                )
                return pdu1_result, ResultCode.FAILED
            else:
                self.blocking_command_ids = set([command_id])
                lrc_status = self.wait_for_blocking_results(
                    task_abort_event=task_abort_event
                )

                if lrc_status != TaskStatus.COMPLETED:
                    self.logger.error(
                        f"Nested LRC PowerSwitch.TurnOnOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} failed/timed out",
                    )
                else:
                    self.pdu2_power_state = PowerState.ON
                    self.logger.info(
                        f"PDU 2 (outlet {self._pdu_outlets[1]}) successfully turned on."
                    )
                    pdu2_result = ResultCode.OK

        return pdu1_result, pdu2_result

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
            msg = (
                "single outlet failed to turn on"
                if self._using_single_outlet
                else "both outlets failed to turn on"
            )
            self.logger.error(f"LRU failed to turn on: {msg}")
            return (
                ResultCode.FAILED,
                msg,
            )

        if result1 == ResultCode.OK and result2 == ResultCode.OK:
            msg = (
                "single PDU successfully turned on"
                if self._using_single_outlet
                else "both outlets successfully turned on"
            )
            self.logger.info(f"LRU successfully turned on: {msg}")

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
        """
        Check if On operation is allowed.

        :return: True if allowed, False otherwise
        """
        if not self.is_communicating:
            return False
        return True

    def _on(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Turn on the TalonLRU and its subordinate devices

        :param task_callback: Callback function to update task status
        :param task_abort_event: Event to signal task abort
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering TalonLRUComponentManager.on")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        self._update_component_state(power=self._get_lru_power_state())
        result1, result2 = self._turn_on_pdus(task_abort_event)

        # _determine_on_result_code will update the component power state
        task_callback(
            status=TaskStatus.COMPLETED,
            result=self._determine_on_result_code(result1, result2),
        )

    def on(
        self: TalonLRUComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit on operation method to task executor queue.

        :param task_callback: Callback function to update task status
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

    # --- Off Command --- #

    def _turn_off_pdus(
        self: TalonLRUComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, ResultCode]:
        """
        Turn off the two PDUs.

        :param task_abort_event: Event to signal task abort
        :return: A tuple containing the 2 return codes of turning off the PDUs
        """
        # Power off PDU 1
        pdu1_result = ResultCode.FAILED
        if self._proxy_power_switch1 is not None:
            [
                [result_code],
                [command_id],
            ] = self._proxy_power_switch1.TurnOffOutlet(self._pdu_outlets[0])

            # Guard incase LRC was rejected.
            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} rejected"
                )
            else:
                self.blocking_command_ids = set([command_id])
                lrc_status = self.wait_for_blocking_results(
                    task_abort_event=task_abort_event
                )
                if lrc_status != TaskStatus.COMPLETED:
                    self.logger.error(
                        f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch1.dev_name()}, outlet {self._pdu_outlets[0]} failed/timed out"
                    )
                    pdu1_result = ResultCode.FAILED
                else:
                    self.pdu1_power_state = PowerState.OFF
                    self.logger.info(
                        f"PDU 1 (outlet {self._pdu_outlets[0]}) successfully turned off."
                    )
                    pdu1_result = ResultCode.OK

        # Power off PDU 2
        pdu2_result = ResultCode.FAILED
        if self._using_single_outlet:
            self.logger.info("PDU 2 is not used.")
            pdu2_result = pdu1_result
        elif self._proxy_power_switch2 is not None:
            [
                [result_code],
                [command_id],
            ] = self._proxy_power_switch2.TurnOffOutlet(self._pdu_outlets[1])

            # Guard incase LRC was rejected.
            if result_code == ResultCode.REJECTED:
                self.logger.error(
                    f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} rejected"
                )
            else:
                self.blocking_command_ids = set([command_id])
                lrc_status = self.wait_for_blocking_results(
                    task_abort_event=task_abort_event
                )
                if lrc_status != TaskStatus.COMPLETED:
                    self.logger.error(
                        f"Nested LRC PowerSwitch.TurnOffOutlet() to {self._proxy_power_switch2.dev_name()}, outlet {self._pdu_outlets[1]} failed/timed out"
                    )
                    pdu2_result = ResultCode.FAILED
                else:
                    self.pdu1_power_state = PowerState.OFF
                    self.logger.info(
                        f"PDU 2 (outlet {self._pdu_outlets[1]}) successfully turned off."
                    )
                    pdu2_result = ResultCode.OK

        return pdu1_result, pdu2_result

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
            self.logger.info(
                f'Off completed OK: {"single outlet turned off" if self._using_single_outlet else "both outlets turned off"}'
            )
            self._update_component_state(power=PowerState.OFF)
            return (
                ResultCode.OK,
                "Off completed OK",
            )

        if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
            msg = f'Unable to turn off LRU: {"single outlet failed to turn off" if self._using_single_outlet else "both outlets failed to turn off"}'
            self.logger.error(msg)
            return (
                ResultCode.FAILED,
                msg,
            )

        else:
            msg = "LRU failed to turn off: one outlet failed to turn off"
            self.logger.error(msg)
            return (
                ResultCode.FAILED,
                msg,
            )

    def is_off_allowed(self: TalonLRUComponentManager) -> bool:
        """
        Check if Off operation is allowed.

        :return: True if allowed, False otherwise
        """
        if not self.is_communicating:
            return False
        return True

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

        self._update_component_state(power=self._get_lru_power_state())
        # Power off both outlets
        result1, result2 = self._turn_off_pdus(task_abort_event)

        # _determine_off_result_code will update the component power state
        task_callback(
            status=TaskStatus.COMPLETED,
            result=self._determine_off_result_code(result1, result2),
        )

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
