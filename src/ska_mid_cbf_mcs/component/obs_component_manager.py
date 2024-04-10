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

from typing import Any

from ska_control_model import ObsState

from .component_manager import CbfComponentManager

__all__ = ["CbfObsComponentManager"]


class CbfObsComponentManager(CbfComponentManager):
    """
    A base observing device component manager for SKA Mid.CBF MCS
    """

    def __init__(
        self: CbfObsComponentManager,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new CbfObsComponentManager instance.
        """
        super().__init__(*args, **kwargs)
        # Here we have statically defined the observing state keywords useful in Mid.CBF
        # component management, allowing the use of the _update_component_state
        # method in the BaseComponentManager to issue the component state change
        # callback in the CspSubElementObsDevice to drive the observing state model
        self._component_state["configured"] = None
        self._component_state["scanning"] = None

        self.obs_state = ObsState.IDLE
