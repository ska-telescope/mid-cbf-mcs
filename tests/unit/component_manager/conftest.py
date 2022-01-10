# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for CbfComponentManager unit tests."""

from __future__ import annotations

# Standard imports
import logging
import pytest
import unittest
from typing import Any, Dict

import tango

import os
file_path = os.path.dirname(os.path.abspath(__file__))
import json

# Local imports
from ska_mid_cbf_mcs.component.component_manager import CbfComponentManager
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

@pytest.fixture(scope="function")
def cbf_component_manager(
    tango_harness: TangoHarness, # sets the connection_factory
    logger: logging.Logger,
) -> CbfComponentManager:
    """
    Return a Cbf component manager.

    :param logger: the logger fixture

    :return: a Controller component manager.
    """

    pass
