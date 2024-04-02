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

from typing import Any, Optional, cast

from ska_tango_base.control_model import (
    AdminMode,
    CommunicationStatus,
    PowerState,
)
from ska_tango_base.executor.executor_component_manager import (
    TaskExecutorComponentManager,
)

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
        **kwargs: Any,
    ):
        super().__init__(None, *args, **kwargs)
        # Here we have statically defined the states useful in Mid.CBF component
        # management, allowing the use of the _update_component_state method in
        # the BaseComponentManager to execute the device state changes callback
        # any number of states
        self._component_state = {
            "admin_mode": None,
            "fault": None,
            "health_state": None,
            "obs_mode": None,
            "obs_state": None,
            "op_state": None,
            "power_state": None,
            "simulation_mode": None,
        }

    def start_communicating(self: CbfComponentManager) -> None:
        """Start communicating with the component."""
        self._update_communication_state(
            communication_state=CommunicationStatus.ESTABLISHED
        )
        self._update_component_state(admin_mode=AdminMode.ONLINE)

    def stop_communicating(self: CbfComponentManager) -> None:
        """Break off communicating with the component."""
        self._update_communication_state(
            communication_state=CommunicationStatus.DISABLED
        )
        self._update_component_state(admin_mode=AdminMode.OFFLINE)

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
