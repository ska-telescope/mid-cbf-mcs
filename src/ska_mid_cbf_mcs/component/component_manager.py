# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations  # allow forward references in type hints

from threading import Event, Lock
from time import sleep
from typing import Any, Callable, Optional, cast

from ska_control_model import (
    CommunicationStatus,
    HealthState,
    PowerState,
    TaskStatus,
)
from ska_tango_base.executor.executor_component_manager import (
    TaskExecutorComponentManager,
)

from ska_mid_cbf_mcs.device.base_device import MAX_QUEUED_COMMANDS

__all__ = ["CbfComponentManager"]


class CbfComponentManager(TaskExecutorComponentManager):
    """
    A base component manager for SKA Mid.CBF MCS

    This class exists to modify the interface of the
    :py:class:`ska_tango_base.base.component_manager.TaskExecutorComponentManager`.
    The ``TaskExecutorComponentManager`` accepts ``max_workers`` and ``max_queue_size``
    keyword arguments to determine limits on worker threads and queue length,
    respectively, for the management of SubmittedSlowCommand (LRC) threads.

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
        """

        super().__init__(*args, max_queue_size=MAX_QUEUED_COMMANDS, **kwargs)
        # Here we have statically defined the state keywords useful in Mid.CBF
        # component management, allowing the use of the _update_component_state
        # method in the BaseComponentManager to issue the component state change
        # callback to drive the operational state model
        self._component_state = {
            "fault": None,
            "power": None,
        }

        self._device_attr_change_callback = attr_change_callback
        self._device_attr_archive_callback = attr_archive_callback

        self._device_health_state_callback = health_state_callback
        self._health_state_lock = Lock()
        self._health_state = HealthState.UNKNOWN

        # initialize lock and set of of blocking resources an LRC thread may be
        # dependent on
        self._results_lock = Lock()
        self.blocking_devices: set["str"] = set(0)

    ###########
    # Callbacks
    ###########

    def _update_device_health_state(
        self: CbfComponentManager,
        health_state: HealthState,
    ) -> None:
        """
        Handle a health state change.
        This is a helper method for use by subclasses.
        :param state: the new health state of the
            component manager.
        """
        with self._health_state_lock:
            if self._health_state != health_state:
                self._health_state = health_state
                self._push_health_state_update(health_state)

    def _push_health_state_update(
        self: CbfComponentManager, health_state: HealthState
    ) -> None:
        if self._device_health_state_callback is not None:
            self._device_health_state_callback(health_state)

    def start_communicating(self: CbfComponentManager) -> None:
        """Start communicating with the component."""
        self._update_communication_state(
            communication_state=CommunicationStatus.ESTABLISHED
        )

    def stop_communicating(self: CbfComponentManager) -> None:
        """Break off communicating with the component."""
        self._update_communication_state(
            communication_state=CommunicationStatus.DISABLED
        )

    def results_callback(self: CbfComponentManager):
        """
        Locked callback to decrement number of blocking
        """
        with self._results_lock:
            self._num_blocking_results -= 1

    def _wait_for_blocking_results(
        self: CbfComponentManager,
        timeout: float,
        task_abort_event: Optional[Event] = None,
    ) -> TaskStatus:
        """
        Wait for the number of anticipated results to be pushed by subordinate devices.

        Example for submitted command method
        ------------------------------------
        def _command_thread(
            self: CbfComponentManager,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[threading.Event] = None,
            **kwargs,
        ):
            # thread begins
            # ...
            # call a bunch of commands, get back a list of command_ids
            command_ids = []
            # ...
            # continue until it the results of those commands are needed
            # ...
            # when we can no longer progress without the command results
            # first reset the number of blocking results
            self._num_blocking_results = len(command_ids)

            # subscribe to the LRC results of all blocking proxies, providing the
            # locked decrement counter method as the callback
            for proxy in proxies_to_wait_on:
            proxy.subscribe_event(
                attr_name="longRunningCommandResult",
                event_type=EventType.CHANGE_EVENT,
                callback=self.results_callback
            )

            # call wait method
            self._wait_for_blocking(timeout=10.0, task_abort_event=task_abort_event)

            # now we can continue

        :param timeout: Time to wait, in seconds.
        :param task_abort_event: Check for abort, defaults to None

        :return: completed if status reached, FAILED if timed out, ABORTED if aborted
        """

        ticks = int(timeout / 0.01)  # 10 ms resolution
        while self.num_blocking_events:
            if task_abort_event and task_abort_event.is_set():
                return TaskStatus.ABORTED
            sleep(0.01)
            ticks -= 1
            if ticks == 0:
                return TaskStatus.FAILED
        self.logger.debug(f"Waited for {timeout - ticks * 0.01} seconds")
        return TaskStatus.COMPLETED

    @property
    def is_communicating(self: CbfComponentManager) -> bool:
        """
        Return communication with the component is established.

        SKA Mid.CBF MCS uses the more expressive :py:attr:`communication_status`
        for this, but this is still needed as a base classes hook.

        :return: whether communication with the component is
            established.
        """
        return self.communication_state == CommunicationStatus.ESTABLISHED

    @property
    def power_state(self: CbfComponentManager) -> Optional[PowerState]:
        """
        Return the power state of this component manager.

        :return: the power state of this component manager.
        """
        return self._component_state["power"]

    @property
    def faulty(self: CbfComponentManager) -> Optional[bool]:
        """
        Return whether this component manager is currently experiencing a fault.

        :return: whether this component manager is currently
            experiencing a fault.
        """
        return cast(bool, self._component_state["fault"])
