# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

from __future__ import annotations

from functools import partial
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ObsState, TaskStatus

from .component_manager import CbfComponentManager

__all__ = ["CbfObsComponentManager"]


class CbfObsComponentManager(CbfComponentManager):
    """
    A base observing device component manager for SKA Mid.CBF MCS
    """

    def __init__(
        self: CbfObsComponentManager,
        *args: Any,
        obs_command_running_callback: Callable[[str, bool], None],
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new CbfObsComponentManager instance.

        :param obs_command_running_callback: Callback to perform observing state model invoked/completed actions
        """

        # supply observing state machine trigger keywords
        super().__init__(
            *args,
            configured=None,
            scanning=None,
            resourced=None,
            obsfault=None,
            **kwargs,
        )

        self._obs_command_running_callback = obs_command_running_callback

        self.obs_state = ObsState.IDLE
        self.config_id = None
        self.scan_id = None

    # ---------------
    # Command Methods
    # ---------------

    def _obs_command_with_callback(
        self: CbfObsComponentManager,
        *args,
        command_thread: Callable[[Any], None],
        hook: str,
        **kwargs,
    ):
        """
        Wrap command thread with ObsStateModel-driving callbacks.

        :param command_thread: actual command thread to be executed
        :param hook: hook for state machine action
        """
        self._obs_command_running_callback(hook=hook, running=True)
        command_thread(*args, **kwargs)
        return self._obs_command_running_callback(hook=hook, running=False)

    def is_configure_scan_allowed(self: CbfObsComponentManager) -> bool:
        """
        Check if ConfigureScan is allowed.

        :return: True if allowed, else False.
        """
        self.logger.debug("Checking if ConfigureScan is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [
            ObsState.IDLE,
            ObsState.READY,
        ]:
            self.logger.warning(
                f"ConfigureScan not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _configure_scan(
        self: CbfComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute configure scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def configure_scan(
        self: CbfObsComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit configure scan operation method to task executor queue.

        :param argin: JSON string with the configure scan parameters

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=partial(
                self._obs_command_with_callback,
                hook="configure",
                command_thread=self._configure_scan,
            ),
            args=[argin],
            is_cmd_allowed=self.is_configure_scan_allowed,
            task_callback=task_callback,
        )

    def is_scan_allowed(self: CbfObsComponentManager) -> bool:
        """
        Check if Scan is allowed.

        :return: True if allowed, False otherwise
        """
        self.logger.debug("Checking if Scan is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.READY]:
            self.logger.warning(
                f"Scan not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _scan(
        self: CbfComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Begin scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def scan(
        self: CbfObsComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit scan operation method to task executor queue.

        :param argin: Scan ID integer

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._scan,
            args=[argin],
            is_cmd_allowed=self.is_scan_allowed,
            task_callback=task_callback,
        )

    def is_end_scan_allowed(self: CbfObsComponentManager) -> bool:
        """
        Check if EndScan is allowed.

        :return: True if allowed, False otherwise
        """
        self.logger.debug("Checking if EndScan is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.SCANNING]:
            self.logger.warning(
                f"EndScan not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _end_scan(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        End scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def end_scan(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Transition observing state from SCANNING to READY

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._end_scan,
            is_cmd_allowed=self.is_end_scan_allowed,
            task_callback=task_callback,
        )

    def is_go_to_idle_allowed(self: CbfObsComponentManager) -> bool:
        """
        Check if GoToIdle is allowed.

        :return: True if allowed, False otherwise
        """
        self.logger.debug("Checking if GoToIdle is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.READY]:
            self.logger.warning(
                f"GoToIdle not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _go_to_idle(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def go_to_idle(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Transition observing state from READY to IDLE

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._go_to_idle,
            is_cmd_allowed=self.is_go_to_idle_allowed,
            task_callback=task_callback,
        )

    def is_abort_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if Abort is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state in [
            ObsState.EMPTY,
            ObsState.FAULT,
            ObsState.ABORTED,
            ObsState.ABORTING,
            ObsState.RESTARTING,
        ]:
            self.logger.warning(
                f"Abort not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _abort(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Abort the current scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def abort(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Abort the current scan operation

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=partial(
                self._obs_command_with_callback,
                hook="abort",
                command_thread=self._abort,
            ),
            is_cmd_allowed=self.is_abort_allowed,
            task_callback=task_callback,
        )

    def is_obs_reset_allowed(self: CbfObsComponentManager) -> bool:
        """
        Check if ObsReset is allowed.

        :return: True if allowed, False otherwise
        """
        self.logger.debug("Checking if ObsReset is allowed.")
        if not self.is_communicating:
            return False
        if self.obs_state not in [ObsState.ABORTED, ObsState.FAULT]:
            self.logger.warning(
                f"ObsReset not allowed in ObsState {self.obs_state}"
            )
            return False
        return True

    def _obs_reset(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset observing state from ABORTED or FAULT to IDLE.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def obs_reset(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Reset observing state from ABORTED or FAULT to IDLE.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=partial(
                self._obs_command_with_callback,
                hook="obsreset",
                command_thread=self._obs_reset,
            ),
            is_cmd_allowed=self.is_obs_reset_allowed,
            task_callback=task_callback,
        )
