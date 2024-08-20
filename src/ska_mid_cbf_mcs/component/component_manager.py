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

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event, Lock, Thread
from time import sleep
from typing import Any, Callable, Optional, cast

import tango
from ska_control_model import (
    CommunicationStatus,
    HealthState,
    PowerState,
    ResultCode,
    SimulationMode,
    TaskStatus,
)
from ska_tango_base.executor.executor_component_manager import (
    TaskExecutorComponentManager,
)
from ska_tango_testing import context

__all__ = ["CbfComponentManager"]

# Maximum number worker threads for group commands
MAX_GROUP_WORKERS = 8

# Default timeout per blocking command during _wait_for_blocking_results in seconds
DEFAULT_TIMEOUT_PER_COMMAND = 10

# 10 ms resolution
TIMEOUT_RESOLUTION = 0.01


class CbfComponentManager(TaskExecutorComponentManager):
    """
    A base component manager for SKA Mid.CBF MCS

    This class exists to modify the interface of the
    :py:class:`ska_tango_base.executor.executor_component_manager.TaskExecutorComponentManager`.
    The ``TaskExecutorComponentManager`` accepts ``max_queue_size`` keyword argument
    to determine limits on worker queue length, for the management of
    SubmittedSlowCommand (LRC) threads.

    Additionally, this provides optional arguments for attribute change event and
    HealthState updates, for a device to pass in its callbacks for push change events.

    Finally, the ``TaskExecutorComponentManager`` inherits from BaseComponentManager,
    which accepts the keyword arguments communication_state_callback and
    component_state_callback, each with an analoguous callback method in the
    SKABaseDevice (namely _communication_state_changed and _component_state_changed)
    used to drive the operational state (opState) model from the component manager.
    """

    def __init__(
        self: CbfComponentManager,
        *args: Any,
        attr_change_callback: Callable[[str, Any], None] | None = None,
        attr_archive_callback: Callable[[str, Any], None] | None = None,
        health_state_callback: Callable[[HealthState], None] | None = None,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new CbfComponentManager instance.

        max_queue_size of the parent is set to match the MAX_QUEUED_COMMANDS
        of the base device class, as this constant is also used to limit the
        dimensions of the longRunningCommandsInQueue, longRunningCommandIDsInQueue,
        longRunningCommandStatus and longRunningCommandProgress attributes used
        to track LRCs, a current limitation of the SKABaseDevice class.

        :param attr_change_callback: callback to be called when
            an attribute change event needs to be pushed from the component manager
        :param attr_archive_callback: callback to be called when
            an attribute archive event needs to be pushed from the component manager
        :param health_state_callback: callback to be called when the
            HealthState of the component changes
        :param simulation_mode: simulation mode identifies if the real component
            or a simulator should be monitored and controlled; defaults to
            SimulationMode.TRUE
        """

        # supply operating state machine trigger keywords
        super().__init__(
            *args,
            fault=None,
            power=None,
            **kwargs,
        )

        self._device_attr_change_callback = attr_change_callback
        self._device_attr_archive_callback = attr_archive_callback
        self._device_health_state_callback = health_state_callback
        self._health_state_lock = Lock()
        self._health_state = HealthState.UNKNOWN

        # initialize a lock and the set of of blocking resources
        # that an LRC thread may depend on
        self._event_ids = {}
        self._results_lock = Lock()
        self._blocking_commands: set["str"] = set()

        # NOTE: using component manager default of SimulationMode.TRUE,
        # as self._simulation_mode at this point during init_device()
        # SimulationMode.FALSE
        self.simulation_mode = simulation_mode

    # -------------
    # Communication
    # -------------

    def _start_communicating(
        self: CbfComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for start_communicating operation.
        """
        self.logger.debug("Entering CbfComponentManager._start_communicating")
        self._update_communication_state(
            communication_state=CommunicationStatus.ESTABLISHED
        )

    def start_communicating(
        self: CbfComponentManager,
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.info("Entering CbfComponentManager.start_communicating")

        if self.communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Already communicating")
            return

        task_status, message = self.submit_task(
            self._start_communicating,
        )

        if task_status == TaskStatus.REJECTED:
            self.logger.error(
                f"start_communicating thread rejected; {message}"
            )
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )

    def _stop_communicating(
        self: CbfComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for stop_communicating operation.
        """
        self.logger.debug("Entering CbfComponentManager._stop_communicating")
        self._update_component_state(power=PowerState.UNKNOWN)
        self._update_communication_state(
            communication_state=CommunicationStatus.DISABLED
        )

    def stop_communicating(
        self: CbfComponentManager,
    ) -> None:
        """
        Stop communication with the component
        """
        self.logger.info("Entering CbfComponentManager.stop_communicating")

        task_status, message = self.submit_task(self._stop_communicating)
        if task_status == TaskStatus.REJECTED:
            self.logger.error(f"stop_communicating thread rejected; {message}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )

    def task_abort_event_is_set(
        self: CbfComponentManager,
        command_name: str,
        task_callback: Callable,
        task_abort_event: Event,
    ) -> bool:
        """
        Helper method for checking task abort event during command thread.

        :param command_name: name of command for result message
        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort event

        :return: True if abort event is set, otherwise False
        """
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    f"{command_name} command aborted by task executor abort event.",
                ),
            )
            return True
        return False

    def _subscribe_command_results(
        self: CbfComponentManager, proxy: context.DeviceProxy
    ) -> None:
        dev_name = proxy.dev_name()
        self.logger.debug(f"Subscribing to {dev_name} LRC results")
        if dev_name in self._event_ids:
            self.logger.debug(
                f"Skipping repeated longRunningCommandResult event subscription: {dev_name}"
            )
            return

        self._event_ids.update(
            {
                dev_name: proxy.subscribe_event(
                    attr_name="longRunningCommandResult",
                    event_type=tango.EventType.CHANGE_EVENT,
                    cb_or_queuesize=self.results_callback,
                )
            }
        )

    def _unsubscribe_command_results(
        self: CbfComponentManager, proxy: context.DeviceProxy
    ) -> None:
        dev_name = proxy.dev_name()
        event_id = self._event_ids.pop(dev_name, None)
        if event_id is None:
            self.logger.debug(
                f"No longRunningCommandResult event subscription for {dev_name}"
            )
            return
        self.logger.debug(
            f"Unsubscribing from {dev_name} event ID {event_id}."
        )
        proxy.unsubscribe_event(event_id)

    # -------------
    # Group Methods
    # -------------

    def _create_group_proxies(
        self: CbfComponentManager, group_proxies: dict
    ) -> bool:
        """
        Create group proxies (list of DeviceProxy) from the list of fqdns passed in.
        Store as class attributes.
        :param
        :return: True if the group proxies are successfully created, False otherwise.
        """
        for group, fqdn in group_proxies.items():
            try:
                setattr(
                    self,
                    group,
                    [
                        context.DeviceProxy(device_name=device)
                        for device in fqdn
                    ],
                )
            except tango.DevFailed as df:
                self.logger.error(f"Failure in connection to {fqdn}: {df}")
                return False
        return True

    def _issue_command_thread(
        self: CbfComponentManager,
        proxy: context.DeviceProxy,
        argin: Any,
        command_name: str,
    ) -> Any:
        """
        Helper function to issue command to a DeviceProxy

        :param proxy: proxy target for command
        :param argin: optional command argument
        :param command_name: command to be issued
        :return: command result (if any)
        """
        try:
            return (
                proxy.command_inout(command_name, argin)
                if argin is not None
                else proxy.command_inout(command_name)
            )
        except tango.DevFailed as df:
            return (
                ResultCode.FAILED,
                f"Error issuing {command_name} command to {proxy.dev_name()}; {df}",
            )

    def _issue_group_command(
        self: CbfComponentManager,
        command_name: str,
        proxies: list[context.DeviceProxy],
        argin: Any = None,
        max_workers: int = MAX_GROUP_WORKERS,
    ) -> list[any]:
        """
        Helper function to perform tango.Group-like threaded command issuance.
        Returns list of command results in the same order as the input proxies list.
        If any command causes a tango.DevFailed exception, the result code for
        that device's return value will be ResultCode.FAILED.

        Important note: all proxies provided must be of the same device type.

        For fast commands, the return value will a list of ResultCode and message
        string tuples.
        For Long Running Commands, the return value will be a list of ResultCode
        and unique command ID tuples.

        :param command_name: name of command to be issued
        :param proxies: list of device proxies in group; determines ordering of
            return values
        :param argin: optional command argument, defaults to None
        :param max_workers: maximum number of ThreadPoolExecutor workers
        :return: list of proxy command returns
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for r in executor.map(
                partial(
                    self._issue_command_thread,
                    argin=argin,
                    command_name=command_name,
                ),
                proxies,
            ):
                results.append(r)
        return results

    def _read_attribute_thread(
        self: CbfComponentManager,
        proxy: context.DeviceProxy,
        attr_name: str,
    ) -> Any:
        """
        Helper function to read attribute from a DeviceProxy

        :param proxy: proxy target for read_attribute
        :param attr_name: name of attribute to be read
        :return: read attribute value
        """
        try:
            return proxy.read_attribute(attr_name)
        except tango.DevFailed as df:
            self.logger.error(
                f"Error reading {proxy.dev_name()}.{attr_name}; {df}"
            )
            return None

    def _read_group_attribute(
        self: CbfComponentManager,
        attr_name: str,
        proxies: list[context.DeviceProxy],
        max_workers: int = MAX_GROUP_WORKERS,
    ) -> list[Any]:
        """
        Helper function to perform tango.Group-like threaded read_attribute().
        Returns list of attribute values in the same order as the input proxies list.
        If any command causes a tango.DevFailed exception, the result code for
        that device's return value will be None.

        Important note: all proxies provided must be of the same device type.

        :param attr_name: name of attribute to be read
        :param proxies: list of device proxies in group; determines ordering of
            return values
        :param max_workers: maximum number of ThreadPoolExecutor workers
        :return: list of proxy attribute values
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for r in executor.map(
                partial(self._read_attribute_thread, attr_name=attr_name),
                proxies,
            ):
                results.append(r)
        return results

    def _write_attribute_thread(
        self: CbfComponentManager,
        proxy: context.DeviceProxy,
        attr_name: str,
        value: Any,
    ) -> bool:
        """
        Helper function to write attribute from a DeviceProxy

        :param proxy: proxy target for read_attribute
        :param attr_name: name of attribute to be read
        :param value: attribute value to be written
        :return: read attribute value
        """
        try:
            proxy.write_attribute(attr_name, value)
            return True
        except tango.DevFailed as df:
            self.logger.error(
                f"Error writing {value} to {proxy.dev_name()}.{attr_name}; {df}"
            )
            return False

    def _write_group_attribute(
        self: CbfComponentManager,
        attr_name: str,
        value: Any,
        proxies: list[context.DeviceProxy],
        max_workers: int = MAX_GROUP_WORKERS,
    ) -> bool:
        """
        Helper function to perform tango.Group-like threaded write_attribute().
        Returns a bool depending on each device's write_attribute success;
        True if all writes were successful, False otherwise.

        Important note: all proxies provided must be of the same device type.

        :param attr_name: name of attribute to be written
        :param value: attribute value to be written
        :param proxies: list of device proxies in group; determines ordering of
            return values
        :param max_workers: maximum number of ThreadPoolExecutor workers
        :return: list of proxy attribute values
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for r in executor.map(
                partial(
                    self._write_attribute_thread,
                    attr_name=attr_name,
                    value=value,
                ),
                proxies,
            ):
                results.append(r)
        return all(results)

    # ----------------
    # Callback Methods
    # ----------------

    def _update_device_health_state(
        self: CbfComponentManager,
        health_state: HealthState,
    ) -> None:
        """
        Handle a health state change.
        This is a helper method for use by subclasses.

        :param health_state: the new health state of the component manager.
        """
        with self._health_state_lock:
            if self._health_state != health_state:
                self._health_state = health_state
                self._push_health_state_update(health_state)

    def _push_health_state_update(
        self: CbfComponentManager, health_state: HealthState
    ) -> None:
        """
        Push a health state update to the device.

        :param health_state: the new health state of the component manager.
        """
        if self._device_health_state_callback is not None:
            self._device_health_state_callback(health_state)

    def _results_callback_thread(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Thread to decrement blocking LRC command results for change event callback.

        :param event_data: Tango attribute change event data
        """
        if (
            event_data.attr_value is not None
            and event_data.attr_value.value != ("", "")
        ):
            self.logger.info(
                f"EventData attr_value: {event_data.attr_value.value}"
            )
            # fetch the result code from the event_data tuple.
            try:
                result_code = int(
                    event_data.attr_value.value[1].split(",")[0].split("[")[1]
                )
                command_id = event_data.attr_value.value[0]
            except IndexError as ie:
                self.logger.error(f"{ie}")
                return

            # If the command ID not in blocking commands, we should wait a bit,
            # as the event may have occurred before we had the chance to add
            # it in the component manager.
            ticks = int(DEFAULT_TIMEOUT_PER_COMMAND / TIMEOUT_RESOLUTION)
            while command_id not in self._blocking_commands:
                sleep(TIMEOUT_RESOLUTION)
                ticks -= 1
                if ticks <= 0:
                    # If command ID was never added, we might have received an event
                    # triggered by a different device.
                    self.logger.warning(
                        f"Received event with command ID {command_id} that was not issued by this device."
                    )
                    return

            if result_code != ResultCode.OK:
                self.logger.error(
                    f"Command ID {command_id} result code: {result_code}"
                )
            with self._results_lock:
                self._blocking_commands.remove(command_id)

            self.logger.info(
                f"Blocking commands remaining: {self._blocking_commands}"
            )

    def results_callback(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Callback for LRC command result events

        :param event_data: Tango attribute change event data
        """
        Thread(
            target=self._results_callback_thread, args=(event_data,)
        ).start()

    def _wait_for_blocking_results(
        self: CbfComponentManager,
        timeout: float = 0.0,
        task_abort_event: Optional[Event] = None,
    ) -> TaskStatus:
        """
        Wait for the number of anticipated results to be pushed by subordinate devices.

        :param timeout: Time to wait, in seconds. If default value of 0.0 is set,
            timeout = current number of blocking commands * DEFAULT_TIMEOUT_PER_COMMAND
        :param task_abort_event: Check for abort, defaults to None

        :return: completed if status reached, FAILED if timed out, ABORTED if aborted
        """
        if timeout == 0.0:
            timeout = float(
                len(self._blocking_commands) * DEFAULT_TIMEOUT_PER_COMMAND
            )
        ticks = int(timeout / TIMEOUT_RESOLUTION)
        while len(self._blocking_commands):
            if task_abort_event and task_abort_event.is_set():
                self.logger.warning(
                    "Task aborted while waiting for blocking results."
                )
                return TaskStatus.ABORTED
            sleep(TIMEOUT_RESOLUTION)
            ticks -= 1
            if ticks <= 0:
                self.logger.error(
                    f"{len(self._blocking_commands)} blocking result(s) remain after {timeout}s.\n"
                    f"Blocking commands remaining: {self._blocking_commands}"
                )
                with self._results_lock:
                    self._blocking_commands = set()
                return TaskStatus.FAILED
        self.logger.debug(
            f"Waited for {timeout - ticks * TIMEOUT_RESOLUTION:.3f} seconds"
        )
        return TaskStatus.COMPLETED

    @property
    def is_communicating(self: CbfComponentManager) -> bool:
        """
        Return whether communication with the component is established.

        SKA Mid.CBF MCS uses the more expressive :py:attr:`communication_status`
        for this, but this is still needed as a base classes hook.

        :return: True if communication with the component is established, else False.
        """
        if self.communication_state == CommunicationStatus.ESTABLISHED:
            return True
        self.logger.warning(
            f"is_communicating() check failed; current communication_state: {self.communication_state}"
        )
        return False

    @property
    def power_state(self: CbfComponentManager) -> Optional[PowerState]:
        """
        Return the power state of this component manager.

        :return: the power state of this component manager, if known.
        """
        return self._component_state["power"]

    @property
    def faulty(self: CbfComponentManager) -> Optional[bool]:
        """
        Return whether this component manager is currently experiencing a fault.

        :return: True if this component manager is currently experiencing a fault, else False.
        """
        return cast(bool, self._component_state["fault"])
