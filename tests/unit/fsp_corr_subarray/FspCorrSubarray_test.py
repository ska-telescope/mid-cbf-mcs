#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the FspCorrSubarray."""

from __future__ import annotations

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray tests.
    """

    def test_ConfigureScan_basic(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == tango.DevState.OFF
        # check initial values of attributes
        # TODO: why does device_under_test.receptors return None?
        # assert device_under_test.receptors == ()
        assert device_under_test.frequencyBand == 0
        assert (device_under_test.band5Tuning[0],
                device_under_test.band5Tuning[1]) == (0, 0)
        assert device_under_test.frequencySliceID == 0
        assert device_under_test.corrBandwidth == 0
        assert device_under_test.zoomWindowTuning == 0
        assert device_under_test.integrationTime == 0
        for i in range(20):
            assert device_under_test.channelAveragingMap[i][1] == 0

        device_under_test.On()
        time.sleep(5)
        assert device_under_test.State() == DevState.ON

        # configure search window
        f = open(file_path + "/../../data/FspCorrSubarray_ConfigureScan_basic.json")
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        device_under_test.ConfigureScan(json_str)
        f.close()

        # TODO: These asserts should pass
        # assert device_under_test.receptors == (10, 197)
        # assert device_under_test.frequencyBand == configuration["frequency_band"]
        assert device_under_test.frequencySliceID == configuration["frequency_slice_id"]
        if "band_5_tuning" in configuration:
            if device_under_test.frequencyBand in [4, 5]:
                band5Tuning_config = configuration["band_5_tuning"]
                for i in range(0, len(band5Tuning_config)):
                    assert device_under_test.band5Tuning[i] == band5Tuning_config[i]
        else:
            logging.info("Attribute band5Tuning not in configuration")
        
        assert device_under_test.zoomWindowTuning == configuration["zoom_window_tuning"]
        assert device_under_test.integrationTime == configuration["integration_factor"]
        channelAveragingMap_config = configuration["channel_averaging_map"]
        logging.info(channelAveragingMap_config)
        for i, chan in enumerate(channelAveragingMap_config):
            for j in range(0,len(chan)):
                assert device_under_test.channelAveragingMap[i][j] == channelAveragingMap_config[i][j]