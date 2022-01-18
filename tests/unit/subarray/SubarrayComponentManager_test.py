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
from ska_mid_cbf_mcs.subarray.subarray_component_manager import SubarrayComponentManager
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

class TestSubarrayComponentManager:
    """
    Test class for SubarrayComponentManager tests.
    """

    def test_communication(
        self: TestSubarrayComponentManager,
        subarray_component_manager: SubarrayComponentManager,
    ) -> None:
        """
        Test component manager communication with subordinate devices.

        :param subarray_component_manager: subarrray component manager under test.
        """
        subarray_component_manager.start_communicating()

