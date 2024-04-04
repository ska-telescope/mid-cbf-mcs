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

from threading import Lock
from typing import Any, Callable, Optional, cast

from ska_tango_base.control_model import (
    AdminMode,
    CommunicationStatus,
    HealthState,
    PowerState,
)
from ska_tango_base.executor.executor_component_manager import (
    TaskExecutorComponentManager,
)
from tango import DevState

__all__ = ["CbfComponentManager"]


class CbfComponentManager(TaskExecutorComponentManager):

    """
    TODO
    A base component manager for SKA Mid.CBF MCS

    This class exists to modify the interface of the
    :py:class:`ska_tango_base.base.component_manager.TaskExecutorComponentManager`.
    The ``TaskExecutorComponentManager`` accepts an ``op_state_model`` argument,
    and is expected to interact directly with it. This is not a very
    good design decision. It is better to leave the ``op_state_model``
    behind in the device, and drive it indirectly through callbacks.

    Therefore this class accepts three callback arguments: one for when
    communication with the component changes, one for when the power
    mode of the component changes, and one for when the component fault
    status changes. In the last two cases, callback hooks are provided
    so that the component can indicate the change to this component
    manager.
    TODO
    """

    # TODO - remove rely on TaskExecutor.__init__?
    def __init__(
        self: CbfComponentManager,
        *args: Any,
        attr_callback: Callable[[str, Any], None] | None = None,
        state_callback: Callable[[DevState, str], None] | None = None,
        admin_mode_callback: Callable[[AdminMode], None] | None = None,
        health_state_callback: Callable[[HealthState], None] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        # Here we have statically defined the states useful in Mid.CBF component
        # management, allowing the use of the _update_component_state method in
        # the BaseComponentManager to execute the device state changes callback
        # any number of states
        self._component_state = {
            "fault": None,
            "power": None,
        }

        self._device_attr_callback = attr_callback
        self._attr_lock = Lock()

        self._device_state_callback = state_callback
        self._state_lock = Lock()
        self._state = DevState.UNKNOWN

        self._device_admin_mode_callback = admin_mode_callback
        self._admin_mode_lock = Lock()
        self._admin_mode = AdminMode.OFFLINE

        self._device_health_state_callback = health_state_callback
        self._health_state_lock = Lock()
        self._health_state = HealthState.UNKNOWN

    ###########
    # Callbacks
    ###########
    def _update_attribute(
        self: CbfComponentManager, attr_name: str, value: Any
    ):
        """
        Handle an attribute change pushed by the component manager.

        :param attr_name: the attribute name
        :param value: the new attribute value
        """

    def _update_device_state(
        self: CbfComponentManager,
        state: DevState,
    ) -> None:
        """
        Handle a state change.
        This is a helper method for use by subclasses.
        :param state: the new state of the
            component manager.
        """
        with self._state_lock:
            if self._state != state:
                self._state = state
                self._push_state_update(state)

    def _push_state_update(self: CbfComponentManager, state: DevState) -> None:
        if self._device_state_callback is not None:
            self._device_state_callback(state)

    def _update_device_admin_mode(
        self: CbfComponentManager,
        admin_mode: AdminMode,
    ) -> None:
        """
        Handle a admin mode change.
        This is a helper method for use by subclasses.
        :param state: the new admin mode of the
            component manager.
        """
        with self._admin_mode_lock:
            if self._admin_mode != admin_mode:
                self._admin_mode = admin_mode
                self._push_admin_mode_update(admin_mode)

    def _push_admin_mode_update(
        self: CbfComponentManager, admin_mode: AdminMode
    ) -> None:
        if self._device_admin_mode_callback is not None:
            self._device_admin_mode_callback(admin_mode)

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
        self._update_device_admin_mode(AdminMode.ONLINE)

    def stop_communicating(self: CbfComponentManager) -> None:
        """Break off communicating with the component."""
        self._update_communication_state(
            communication_state=CommunicationStatus.DISABLED
        )
        self._update_device_admin_mode(AdminMode.OFFLINE)

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
        Return the power mode of this component manager.

        :return: the power mode of this component manager.
        """
        return self._component_state["power_state"]

    @property
    def faulty(self: CbfComponentManager) -> Optional[bool]:
        """
        Return whether this component manager is currently experiencing a fault.

        :return: whether this component manager is currently
            experiencing a fault.
        """
        return cast(bool, self._component_state["fault"])
