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
from typing import Any, Callable, Optional

import logging
import enum
import threading

from ska_tango_base.base import BaseComponentManager
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.utils import ThreadsafeCheckingMeta, threadsafe

__all__ = [
    "CommunicationStatus",
    "CbfComponentManager",
]

class CommunicationStatus(enum.Enum):
    """The status of a component manager's communication with its component."""

    DISABLED = 1
    """
    The component manager is not trying to establish/maintain a channel
    of communication with its component. For example:

    * if communication with the component is connection-oriented, then
      there is no connection, and the component manager is not trying to
      establish a connection.
    * if communication with the component is by event subscription, then
      the component manager is unsubscribed from events.
    * if communication with the component is by periodic connectionless
      polling, then the component manager is not performing that
      polling.
    """

    NOT_ESTABLISHED = 2
    """
    The component manager is trying to establish/maintain a channel of
    communication with its component, but that channel is not currently
    established. For example:

    * if communication with the component is connection-oriented, then
      the component manager has failed to establish/maintain the
      connection.
    """

    ESTABLISHED = 3
    """
    The component manager has established a channel of communication
    with its component. For example:

    * if communication with the component is connection-oriented, then
      the component manager has connected to its component.
    """

class CbfComponentManager(BaseComponentManager, metaclass=ThreadsafeCheckingMeta):

    def __init__(
        self: CbfComponentManager,
        logger: logging.Logger,
        push_change_event: Optional[Callable],
        communication_status_changed_callback: Optional[
            Callable[[CommunicationStatus], None]
        ],
        component_power_mode_changed_callback: Optional[Callable[[PowerMode], None]],
        component_fault_callback: Optional[Callable[[bool], None]],
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialise a new instance.

        :param logger: a logger for this instance to use
        """

        self._logger = logger

        assert push_change_event
        self._push_change_event = push_change_event

        self.__communication_lock = threading.Lock()
        self._communication_status = CommunicationStatus.DISABLED
        self._communication_status_changed_callback = (
            communication_status_changed_callback
        )

        self._power_mode_lock = threading.RLock()
        self._power_mode: Optional[PowerMode] = None
        self._component_power_mode_changed_callback = (
            component_power_mode_changed_callback
        )

        self._faulty: Optional[bool] = None
        self._component_fault_callback = component_fault_callback

        super().__init__(None, *args, **kwargs)
    
    def start_communicating(self: CbfComponentManager) -> None:
        """Start communicating with the component."""
        self._logger.info("Entering CbfComponentManager.start_communicating with status {}".format(self.communication_status))
        if self.communication_status == CommunicationStatus.ESTABLISHED:
            return
        if self.communication_status == CommunicationStatus.DISABLED:
            self.update_communication_status(CommunicationStatus.NOT_ESTABLISHED)

    def stop_communicating(self: CbfComponentManager) -> None:
        """Break off communicating with the component."""
        if self.communication_status == CommunicationStatus.DISABLED:
            return

        self.update_communication_status(CommunicationStatus.DISABLED)
        with self._power_mode_lock:
            self.update_component_power_mode(None)
        self.update_component_fault(None)

    @threadsafe
    def update_communication_status(
        self: CbfComponentManager,
        communication_status: CommunicationStatus,
    ) -> None:
        """
        Handle a change in communication status.

        This is a helper method for use by subclasses.

        :param communication_status: the new communication status of the
            component manager.
        """
        if self._communication_status != communication_status:
            with self.__communication_lock:
                self._communication_status = communication_status
                if self._communication_status_changed_callback is not None:
                    self._communication_status_changed_callback(communication_status)

    @property
    def is_communicating(self: CbfComponentManager) -> bool:
        """
        Return communication with the component is established.

        MCCS uses the more expressive :py:attr:`communication_status`
        for this, but this is still needed as a base classes hook.

        :return: whether communication with the component is
            established.
        """
        return self.communication_status == CommunicationStatus.ESTABLISHED

    @property
    def communication_status(self: CbfComponentManager) -> CommunicationStatus:
        """
        Return the communication status of this component manager.

        This is implemented as a replacement for the
        ``is_communicating`` property, which should be deprecated.

        :return: status of the communication channel with the component.
        """
        return self._communication_status

    @threadsafe
    def update_component_power_mode(
        self: CbfComponentManager, power_mode: Optional[PowerMode]
    ) -> None:
        """
        Update the power mode, calling callbacks as required.

        This is a helper method for use by subclasses.

        :param power_mode: the new power mode of the component. This can
            be None, in which case the internal value is updated but no
            callback is called. This is useful to ensure that the
            callback is called next time a real value is pushed.
        """
        if self._power_mode != power_mode:
            self._power_mode = power_mode
            if (
                self._component_power_mode_changed_callback is not None
                and power_mode is not None
            ):
                self._component_power_mode_changed_callback(power_mode)

    def component_power_mode_changed(
        self: CbfComponentManager, power_mode: PowerMode
    ) -> None:
        """
        Handle notification that the component's power mode has changed.

        This is a callback hook, to be passed to the managed component.

        :param power_mode: the new power mode of the component
        """
        with self._power_mode_lock:
            self.update_component_power_mode(power_mode)

    @property
    def power_mode(self: CbfComponentManager) -> Optional[PowerMode]:
        """
        Return the power mode of this component manager.

        :return: the power mode of this component manager.
        """
        return self._power_mode

    def update_component_fault(
        self: CbfComponentManager, faulty: Optional[bool]
    ) -> None:
        """
        Update the component fault status, calling callbacks as required.

        This is a helper method for use by subclasses.

        :param faulty: whether the component has faulted. If ``False``,
            then this is a notification that the component has
            *recovered* from a fault.
        """
        if self._faulty != faulty:
            self._faulty = faulty
            if self._component_fault_callback is not None and faulty is not None:
                self._component_fault_callback(faulty)

    def component_fault_changed(self: CbfComponentManager, faulty: bool) -> None:
        """
        Handle notification that the component's fault status has changed.

        This is a callback hook, to be passed to the managed component.

        :param faulty: whether the component has faulted. If ``False``,
            then this is a notification that the component has
            *recovered* from a fault.
        """
        self.update_component_fault(faulty)

    @property
    def faulty(self: CbfComponentManager) -> Optional[bool]:
        """
        Return whether this component manager is currently experiencing a fault.

        :return: whether this component manager is currently
            experiencing a fault.
        """
        return self._faulty