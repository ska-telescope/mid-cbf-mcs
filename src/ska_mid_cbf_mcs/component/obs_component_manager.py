# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

from __future__ import annotations  # allow forward references in type hints

import functools
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
        """
        super().__init__(*args, **kwargs)

        # callback to perform observing state model invoked/completed actions
        self._obs_command_running_callback = obs_command_running_callback

        # Here we have statically defined the observing state keywords useful in Mid.CBF
        # component management, allowing the use of the _update_component_state
        # method in the BaseComponentManager to issue the component state change
        # callback in the CspSubElementObsDevice to drive the observing state model
        self._component_state["configured"] = None
        self._component_state["scanning"] = None

        self.obs_state = ObsState.IDLE

        self.config_id = None
        self.scan_id = None

    # ---------------
    # Command methods
    # ---------------

    def is_configure_scan_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if ConfigureScan is allowed.")
        if self.obs_state not in [
            ObsState.IDLE,
            ObsState.READY,
        ]:
            self.logger.warning(
                f"ConfigureScan not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.IDLE or READY"
            )
            return False
        return True

    def _configure_scan(
        self: CbfComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs,
    ) -> None:
        """
        Execute configure scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def _configure_scan_with_callback(
        self: CbfComponentManager,
        *args,
        hook: str,
        obs_callback: Callable[[str, bool], None],
        **kwargs,
    ):
        obs_callback(hook=hook, running=True)
        self._configure_scan(*args, **kwargs)
        return obs_callback(hook=hook, running=False)

    def configure_scan(
        self: CbfObsComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
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
            func=functools.partial(
                self._configure_scan_with_callback,
                hook="configure",
                obs_callback=self._obs_command_running_callback,
            ),
            args=[argin],
            is_cmd_allowed=self.is_configure_scan_allowed,
            task_callback=task_callback,
        )

    def is_scan_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if Scan is allowed.")
        if self.obs_state not in [ObsState.READY]:
            self.logger.warning(
                f"Scan not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.READY"
            )
            return False
        return True

    def _scan(
        self: CbfComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs,
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
        **kwargs: Any,
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
        self.logger.debug("Checking if EndScan is allowed.")
        if self.obs_state not in [ObsState.SCANNING]:
            self.logger.warning(
                f"EndScan not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.SCANNING"
            )
            return False
        return True

    def _end_scan(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs,
    ) -> None:
        """
        End scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def end_scan(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
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
        self.logger.debug("Checking if GoToIdle is allowed.")
        if self.obs_state not in [ObsState.READY]:
            self.logger.warning(
                f"GoToIdle not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.READY"
            )
            return False
        return True

    def _go_to_idle(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def go_to_idle(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
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

    def is_abort_scan_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if AbortScan is allowed.")
        if self.obs_state not in [
            ObsState.IDLE,
            ObsState.CONFIGURING,
            ObsState.READY,
            ObsState.SCANNING,
            ObsState.ABORTING,
            ObsState.RESETTING,
        ]:
            self.logger.warning(
                f"AbortScan not allowed in ObsState {self.obs_state};\
                    must be in ObsState.IDLE, READY or SCANNING."
            )
            return False
        return True

    def _abort_scan(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs,
    ) -> None:
        """
        Abort the current scan operation.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def _abort_scan_with_callback(
        self: CbfComponentManager,
        *args,
        hook: str,
        obs_callback: Callable[[str, bool], None],
        **kwargs,
    ):
        obs_callback(hook=hook, running=True)
        self._abort_scan(*args, **kwargs)
        return obs_callback(hook=hook, running=False)

    def abort_scan(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
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
            func=functools.partial(
                self._abort_scan_with_callback,
                hook="abort",
                obs_callback=self._obs_command_running_callback,
            ),
            is_cmd_allowed=self.is_abort_scan_allowed,
            task_callback=task_callback,
        )

    def is_obs_reset_allowed(self: CbfObsComponentManager) -> bool:
        self.logger.debug("Checking if ObsReset is allowed.")
        if self.obs_state not in [ObsState.FAULT, ObsState.ABORTED]:
            self.logger.warning(
                f"ObsReset not allowed in ObsState {self.obs_state};\
                    must be in ObsState.ABORTED or FAULT."
            )
            return False
        return True

    def _obs_reset(
        self: CbfComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs,
    ) -> None:
        """
        Reset observing state from ABORTED or FAULT to IDLE.

        :raises NotImplementedError: Not implemented in abstract class
        """
        raise NotImplementedError("CbfObsComponentManager is abstract.")

    def _obs_reset_with_callback(
        self: CbfComponentManager,
        *args,
        hook: str,
        obs_callback: Callable[[str, bool], None],
        **kwargs,
    ):
        obs_callback(hook=hook, running=True)
        self._obs_reset(*args, **kwargs)
        return obs_callback(hook=hook, running=False)

    def obs_reset(
        self: CbfObsComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
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
            func=functools.partial(
                self._obs_reset_with_callback,
                hook="obsreset",
                obs_callback=self._obs_command_running_callback,
            ),
            is_cmd_allowed=self.is_obs_reset_allowed,
            task_callback=task_callback,
        )
