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

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event, Lock, Thread
from time import sleep
from typing import Callable, Optional, cast

import tango
from pydantic.utils import deep_update
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
    component_state_callback, each with an analogous callback method in the
    SKABaseDevice (namely _communication_state_changed and _component_state_changed)
    used to drive the operational state (opState) model from the component manager.
    """

    def __init__(
        self: CbfComponentManager,
        *args: any,
        lrc_timeout: int = 15,
        state_change_timeout: int = 15,
        attr_change_callback: Callable[[str, any], None] | None = None,
        attr_archive_callback: Callable[[str, any], None] | None = None,
        health_state_callback: Callable[[HealthState], None] | None = None,
        admin_mode_callback: Callable[[str], None] | None = None,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new CbfComponentManager instance.

        max_queue_size of the parent is set to match the MAX_QUEUED_COMMANDS
        of the base device class, as this constant is also used to limit the
        dimensions of the longRunningCommandsInQueue, longRunningCommandIDsInQueue,
        longRunningCommandStatus and longRunningCommandProgress attributes used
        to track LRCs, a current limitation of the SKABaseDevice class.

        :param lrc_timeout: timeout (in seconds) per LRC when waiting for blocking results;
            defaults to 15.0 seconds
        :param state_change_timeout: timeout (in seconds) when waiting for Devices state attribute change;
            defaults to 15.0 seconds
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

        self.device_attr_change_callback = attr_change_callback
        self.device_attr_archive_callback = attr_archive_callback
        self.device_admin_mode_callback = admin_mode_callback
        self._device_health_state_callback = health_state_callback
        self._health_state_lock = Lock()
        self._health_state = HealthState.UNKNOWN

        # Initialize a lock and a set of to track the blocking LRC command IDs
        # that an LRC thread may depend on
        # See docstring under wait_for_blocking_result for an example scenario
        self.event_ids = {}
        self._results_lock = Lock()
        self._received_lrc_results = {}
        self.blocking_command_ids = set()
        self._lrc_timeout = lrc_timeout

        # dict and lock to store latest sub-device state attribute values
        self._op_states = {}
        self._attr_event_lock = Lock()
        self._state_change_timeout = state_change_timeout

        # NOTE: currently all devices are using constructor default
        # simulation_mode == SimulationMode.TRUE
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
        self.device_admin_mode_callback("to_online")

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
        self.device_admin_mode_callback("to_offline")

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

    # -------------
    # Group Methods
    # -------------

    def create_group_proxies(
        self: CbfComponentManager, group_proxies: dict
    ) -> bool:
        """
        Create group proxies (list of DeviceProxy) from the list of FQDNs passed in.
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
        argin: any,
        command_name: str,
    ) -> any:
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

    def issue_group_command(
        self: CbfComponentManager,
        command_name: str,
        proxies: list[context.DeviceProxy],
        max_workers: int,
        argin: any = None,
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
    ) -> any:
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
        max_workers: int,
    ) -> list[any]:
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
        value: any,
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
        value: any,
        proxies: list[context.DeviceProxy],
        max_workers: int,
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

    def _push_health_state_update(
        self: CbfComponentManager, health_state: HealthState
    ) -> None:
        """
        Push a health state update to the device.

        :param health_state: the new health state of the component manager.
        """
        if self._device_health_state_callback is not None:
            self._device_health_state_callback(health_state)

    def update_device_health_state(
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
                self.logger.info(f"Updating healthState to {health_state}")
                self._health_state = health_state
                self._push_health_state_update(self._health_state)

    def _results_callback_thread(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Thread to decrement blocking LRC command results for change event callback.

        :param event_data: Tango attribute change event data
        """
        if event_data.attr_value is None:
            return
        value = event_data.attr_value.value
        if value is None or value == ("", ""):
            return
        self.logger.debug(
            f"{event_data.device.dev_name()} EventData attr_value: {value}"
        )

        try:
            command_id = value[0]
            result = value[1]
        except IndexError as ie:
            self.logger.error(f"IndexError in parsing EventData; {ie}")
            return

        with self._results_lock:
            self._received_lrc_results[command_id] = result

    def results_callback(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Callback for LRC command result events.
        All subdevices that may block our LRC thread with their own LRC execution
        have their `lrcFinished` attribute subscribed to with this method
        as the change event callback.

        :param event_data: Tango attribute change event data
        """
        Thread(
            target=self._results_callback_thread, args=(event_data,)
        ).start()

    def _op_state_callback_thread(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Thread to update latest state attribute events.

        :param event_data: Tango attribute change event data
        """
        if event_data.attr_value is None:
            return
        value = event_data.attr_value.value
        if value is None:
            return

        dev_name = event_data.device.dev_name()
        self.logger.debug(f"{dev_name} state EventData attr_value: {value}")

        with self._attr_event_lock:
            self._op_states[dev_name] = value

    def op_state_callback(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Callback for state attribute events.

        :param event_data: Tango attribute change event data
        """
        Thread(
            target=self._op_state_callback_thread, args=(event_data,)
        ).start()

    # -------------------------
    # Wait for Blocking Results
    # -------------------------

    def wait_for_blocking_results(
        self: CbfComponentManager,
        task_abort_event: Optional[Event] = None,
        partial_success: bool = False,
    ) -> TaskStatus:
        """
        Wait for the number of anticipated results to be pushed by subordinate devices.

        When issuing an LRC (or multiple) on subordinate devices from an LRC thread,
        command result events will be stored in self._received_lrc_results; use this
        method to wait for all blocking command ID `lrcFinished` events.

        All subdevices that may block our LRC thread with their own LRC execution
        have the `results_callback` method above provided as the change event callback
        for their `lrcFinished` attribute subscription, which will store
        command IDs and results as change events are received.


        # --- Nested LRC management example code inside LRC thread --- #

        # Collect all blocking command IDs from subdevices
        self.blocking_command_ids = set() # reset blocking command IDs to empty
        for proxy in self.proxies:
            [[result_code], [command_id]] = proxy.LongRunningCommand()
            if result_code == ResultCode.QUEUED:
                blocking_command_ids.add(command_id)
            else:
                # command rejection handling
        # ...
        # Continue until we must wait for nested LRCs to complete
        # ...
        # Then wait for all of their lrcFinished attributes to update
        lrc_status = self.wait_for_blocking_results()
        if lrc_status != TaskStatus.COMPLETED:
            # LRC timeout/abort handling

        # --- #

        :param task_abort_event: Check for abort, defaults to None
        :param partial_success: set to True if we only need at least 1 of the blocking
            LRCs to be successful; defaults to False, in which case all LRCs must succeed
        :return: TaskStatus.COMPLETED if status reached, TaskStatus.FAILED if timed out
            TaskStatus.ABORTED if aborted
        """
        timeout_sec = float(len(self.blocking_command_ids) * self._lrc_timeout)
        ticks_10ms = int(timeout_sec / TIMEOUT_RESOLUTION)

        # Loop is exited when no blocking command IDs remain
        successes = []
        self.logger.debug(
            f"wait_for_blocking_results invoked; current received events: {self._received_lrc_results}"
        )
        while len(self.blocking_command_ids):
            if task_abort_event and task_abort_event.is_set():
                self.logger.warning(
                    "Task aborted while waiting for blocking results."
                )
                with self._results_lock:
                    self._received_lrc_results = {}
                return TaskStatus.ABORTED

            # Remove any successfully parsed results from received events
            command_id_list = list(self.blocking_command_ids)
            for command_id in command_id_list:
                with self._results_lock:
                    result = self._received_lrc_results.pop(command_id, None)
                if result is None:
                    continue

                try:
                    result_code = int(result.split(",")[0].split("[")[1])
                except IndexError as ie:
                    self.logger.error(
                        f"IndexError in parsing {command_id} event result code; {ie}"
                    )
                    successes.append(False)
                    continue

                if result_code != ResultCode.OK:
                    self.logger.error(
                        f"Blocking command failure; {command_id}: {result}"
                    )
                    successes.append(False)
                    self.blocking_command_ids.remove(command_id)
                    continue

                self.logger.debug(
                    f"Received LRC event for command ID {command_id}"
                )
                successes.append(True)
                self.blocking_command_ids.remove(command_id)

            sleep(TIMEOUT_RESOLUTION)
            ticks_10ms -= 1
            if ticks_10ms <= 0:
                self.logger.error(
                    f"{len(self.blocking_command_ids)} blocking result(s) remain after {timeout_sec}s.\n"
                    f"Blocking commands remaining: {self.blocking_command_ids}"
                )
                with self._results_lock:
                    self._received_lrc_results = {}
                return TaskStatus.FAILED

        self.logger.debug(
            f"Waited for {timeout_sec - ticks_10ms * TIMEOUT_RESOLUTION:.3f} seconds"
        )
        with self._results_lock:
            self._received_lrc_results = {}

        if not partial_success and all(successes):
            self.logger.debug("All blocking commands succeeded.")
            return TaskStatus.COMPLETED

        if partial_success and any(successes):
            self.logger.debug("Partial/complete blocking command success.")
            return TaskStatus.COMPLETED

        self.logger.error("All blocking commands failed.")
        return TaskStatus.FAILED

    # -------------------------
    # Wait for Op State Change
    # -------------------------

    def wait_for_op_state_change(
        self: CbfComponentManager, desired_state: tango.DevState
    ) -> TaskStatus:
        """
        Wait for subordinate devices state attribute to change to the given desired_state.
        Only check for devices that are subscribed in self._op_state.

        :param desired_state: The desired_state that we want to observe with the devices of interest


        :return: TaskStatus.COMPLETED if status reached, TaskStatus.FAILED if timed out
            TaskStatus.ABORTED if aborted
        """

        ticks_10ms = int(self._state_change_timeout / TIMEOUT_RESOLUTION)

        # A queue to keep track of devices that have not changed to the
        # desired state.
        op_state_devices_fqdn = list(self._op_states.keys())
        op_state_queue = deque(op_state_devices_fqdn)

        self.logger.debug(
            f" Desired State Change: {desired_state} \nDevices Subscribed: {op_state_queue}"
        )

        while len(op_state_queue):
            # Remove any successful results from blocking command IDs
            curr_device_fqdn = op_state_queue.popleft()

            with self._attr_event_lock:
                state = self._op_states[curr_device_fqdn]

            # Add the devices back to the stack if the desired state has not been reached
            if state != desired_state:
                self.logger.debug(
                    f"{curr_device_fqdn} Current State: {state}  Desired State: {desired_state}"
                )
                op_state_queue.append(curr_device_fqdn)

            sleep(TIMEOUT_RESOLUTION)
            ticks_10ms -= 1
            if ticks_10ms <= 0:
                self.logger.error(
                    f"{len(op_state_queue)} device(s) have not changed to desired state after {self._state_change_timeout}s.\n"
                    f"Remaining Devices: {op_state_queue}\n"
                    f"Desired State: {desired_state}"
                )
                return TaskStatus.FAILED

        self.logger.debug(
            f"Waited for {self._state_change_timeout - ticks_10ms * TIMEOUT_RESOLUTION:.3f} seconds"
        )

        if len(op_state_queue) == 0:
            self.logger.debug(
                f"Device(s) successfully transitioned to {desired_state}."
            )
            return TaskStatus.COMPLETED
        else:
            self.logger.error(
                f"Some/all device(s) failed to transition to {desired_state}."
            )
            return TaskStatus.FAILED

    # -----------------------
    # Subscription Management
    # -----------------------

    def attr_event_subscribe(
        self: CbfComponentManager,
        proxy: context.DeviceProxy,
        attr_name: str,
        callback: Callable,
        stateless: bool = True,
    ) -> None:
        """
        Subscribe to a given proxy's attribute.

        :param proxy: DeviceProxy
        :param attr_name: name of attribute for change event subscription
        :param callback: change event callback
        :param stateless: If False, an exception will be thrown if the event subscription
            encounters a problem; if True, the event subscription will always succeed,
            even if the corresponding device server is not running
        """
        dev_name = proxy.dev_name()

        if dev_name in self.event_ids:
            if attr_name in self.event_ids[dev_name]:
                self.logger.debug(
                    f"Skipping repeated {attr_name} event subscription: {dev_name}"
                )
                return
        self.logger.debug(f"Subscribing to {dev_name}/{attr_name}")

        event_id = proxy.subscribe_event(
            attr_name=attr_name,
            event_type=tango.EventType.CHANGE_EVENT,
            cb_or_queuesize=callback,
            stateless=stateless,
        )

        self.event_ids = deep_update(
            self.event_ids, {dev_name: {attr_name: event_id}}
        )

        self.logger.debug(f"Event IDs: {self.event_ids}")

    def unsubscribe_all_events(
        self: CbfComponentManager, proxy: context.DeviceProxy
    ) -> None:
        """
        Unsubscribe from a proxy's lrcFinished attribute.

        :param proxy: DeviceProxy
        """
        self.logger.debug(f"Event IDs: {self.event_ids}")
        dev_name = proxy.dev_name()
        dev_events = self.event_ids.pop(dev_name, None)
        if dev_events is None:
            self.logger.debug(
                f"No lrcFinished event subscription for {dev_name}"
            )
            return
        for attr_name, event_id in dev_events.items():
            self.logger.debug(
                f"Unsubscribing from {dev_name}/{attr_name} event ID {event_id}"
            )
            proxy.unsubscribe_event(event_id)

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
