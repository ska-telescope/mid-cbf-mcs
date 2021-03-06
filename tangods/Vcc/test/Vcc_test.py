#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfMaster."""

# Standard imports
import sys
import os
import time
import json

# Path
file_path = os.path.dirname(os.path.abspath(__file__))
# insert base package directory to import global_enum 
# module in commons folder
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, os.path.abspath(path))

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports

from Vcc.Vcc import Vcc
from ska.base.control_model import HealthState, AdminMode, ObsState

@pytest.mark.usefixtures(
    "create_vcc_proxy",
    "create_band_12_proxy",
    "create_band_3_proxy",
    "create_band_4_proxy",
    "create_band_5_proxy",
    "create_sw_1_proxy"
)

class TestVcc:
    """
    @classmethod
    def mocking(cls):
    """#Mock external libraries.
    """
        # Example : Mock numpy
        # cls.numpy = CspMaster.numpy = MagicMock()
    """

    def test_SetFrequencyBand(
            self,
            create_vcc_proxy,
            create_band_12_proxy,
            create_band_3_proxy,
            create_band_4_proxy,
            create_band_5_proxy
    ):
        """
        Test SetFrequencyBand command state changes.
        """
        create_band_12_proxy.Init()
        create_band_3_proxy.Init()
        create_band_4_proxy.Init()
        create_band_5_proxy.Init()
        create_vcc_proxy.Init()
        time.sleep(3)

        # all bands should be disabled after initialization
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 1
        create_vcc_proxy.SetFrequencyBand("1")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.ON
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 3
        create_vcc_proxy.SetFrequencyBand("3")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.ON
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 2
        create_vcc_proxy.SetFrequencyBand("2")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.ON
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 5a
        create_vcc_proxy.SetFrequencyBand("5a")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.ON

        # set frequency band to 4
        create_vcc_proxy.SetFrequencyBand("4")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.ON
        assert create_band_5_proxy.State() == DevState.DISABLE

        # set frequency band to 5b
        create_vcc_proxy.SetFrequencyBand("5b")
        time.sleep(1)
        assert create_band_12_proxy.State() == DevState.DISABLE
        assert create_band_3_proxy.State() == DevState.DISABLE
        assert create_band_4_proxy.State() == DevState.DISABLE
        assert create_band_5_proxy.State() == DevState.ON

    def test_ConfigureSearchWindow_basic(self, create_vcc_proxy, create_tdc_1_proxy):
        """
        Test a minimal successful search window configuration.
        """
        create_sw_1_proxy.Init()
        create_vcc_proxy.Init()
        time.sleep(3)

        # check initial values of attributes
        assert create_sw_1_proxy.searchWindowTuning == 0
        assert create_sw_1_proxy.tdcEnable == False
        assert create_sw_1_proxy.tdcNumBits == 0
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 0
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 0
        assert create_sw_1_proxy.tdcDestinationAddress == ("", "", "")

        # check initial state
        assert create_sw_1_proxy.State() == DevState.DISABLE

        # set receptorID to 1 to correctly test tdcDestinationAddress
        create_vcc_proxy.receptorID = 1

        # configure search window
        f = open(file_path + "/test_json/test_ConfigureSearchWindow_basic.json")
        create_vcc_proxy.ConfigureSearchWindow(f.read().replace("\n", ""))
        f.close()
        time.sleep(1)

        # check configured values
        assert create_sw_1_proxy.searchWindowTuning == 1000000000
        assert create_sw_1_proxy.tdcEnable == True
        assert create_sw_1_proxy.tdcNumBits == 8
        assert create_sw_1_proxy.tdcPeriodBeforeEpoch == 5
        assert create_sw_1_proxy.tdcPeriodAfterEpoch == 25
        assert create_sw_1_proxy.tdcDestinationAddress == ("", "", "")

        # check state
        assert create_sw_1_proxy.State() == DevState.ON
