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

from ska_tango_base.base import BaseComponentManager
from ska_tango_base.control_model import PowerMode

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

class CbfComponentManager(BaseComponentManager):

    def __init__(
        self: CbfComponentManager,
        logger: logging.Logger,
    ):
        """
        Initialise a new instance.

        :param logger: a logger for this instance to use
        """

        self._logger = logger

        super().__init__(None)

    
