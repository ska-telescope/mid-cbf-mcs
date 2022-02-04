#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the CbfSubarray component manager."""

from __future__ import annotations

from typing import List

# Standard imports
import os
import time
import json
import pytest

from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

class TestVccComponentManager:
    """
    Test class for VccComponentManager tests.
    """

    def test_init_start_communicating(
        self: TestVccComponentManager,
        vcc_component_manager: VccComponentManager,
        tango_harness: TangoHarness
    ) -> None:
        """
        Test component manager initialization and communication establishment 
        with subordinate devices.

        :param vcc_component_manager: vcc component manager under test.
        """
        vcc_component_manager.start_communicating()
        assert vcc_component_manager.connected