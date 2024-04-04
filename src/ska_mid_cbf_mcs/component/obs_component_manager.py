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

from ska_csp_lmc_base.obs.obs_state_model import ObsStateModel
from ska_tango_base.control_model import (
    AdminMode,
    CommunicationStatus,
    HealthState,
    ObsState,
    PowerState,
)
from ska_tango_base.executor.executor_component_manager import (
    TaskExecutorComponentManager,
)
from tango import DevState

from .component_manager import CbfComponentManager

__all__ = ["CbfObsComponentManager"]


class CbfObsComponentManager(CbfComponentManager):
    """A stub for an observing device component manager."""

    # TODO - remove rely on TaskExecutor.__init__?
    def __init__(
        self: CbfObsComponentManager,
        *args: Any,
        obs_state_callback: Callable[[ObsState, str], None] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)

        self._device_obs_state_callback = obs_state_callback
        self._obs_state_lock = Lock()
        self._obs_state = ObsState.IDLE
