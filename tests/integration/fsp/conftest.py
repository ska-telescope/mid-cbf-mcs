#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.
"""Contain the tests for the FspSubarray."""

from __future__ import annotations

import random

# Standard imports
from typing import List

import pytest

# Tango imports
from tango import DeviceProxy, DevState


@pytest.fixture(scope="function")
def receptors_to_test() -> List[int]:
    # reserve receptor ID 4 to test unassigned/invalid receptor
    return random.sample(range(1, 4), 3)
