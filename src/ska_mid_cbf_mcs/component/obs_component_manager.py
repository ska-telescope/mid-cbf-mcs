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

from typing import Any

from ska_tango_base.control_model import ObsState

from .component_manager import CbfComponentManager

__all__ = ["CbfObsComponentManager"]


class CbfObsComponentManager(CbfComponentManager):
    """A stub for an observing device component manager."""

    # TODO - remove rely on TaskExecutor.__init__?
    def __init__(
        self: CbfObsComponentManager,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)

        self.obs_state = ObsState.IDLE
