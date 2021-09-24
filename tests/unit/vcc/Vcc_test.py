#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Vcc."""

from __future__ import annotations

# Standard imports
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_mid_cbf_mcs.dev_factory import DevFactory
from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestVcc:
    """
    Test class for Vcc tests.
    """
    
    @pytest.mark.forked
    def test_On_ConfigureScan_Off(
        self: TestVcc,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test for Vcc device.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        # to get the mock devices, use tango_harness.get_device("fqdn")
        # mock_band12 = tango_harness.get_device("mid_csp_cbf/vcc_band12/001")
        # mock_band3 = tango_harness.get_device("mid_csp_cbf/vcc_band3/001")
        # mock_band4 = tango_harness.get_device("mid_csp_cbf/vcc_band4/001")
        # mock_band5 = tango_harness.get_device("mid_csp_cbf/vcc_band5/001")
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.On()

        json_str = json.dumps({
            "config_id": "vcc_unit_test",
            "frequency_band": "3",
        })
        device_under_test.ConfigureScan(json_str)
        assert device_under_test.obsState == ObsState.READY

        device_under_test.Off()
        assert device_under_test.State() == DevState.OFF
    

    @pytest.mark.forked
    def test_SetFrequencyBand(
        self: TestVcc,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test SetFrequencyBand command state changes.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        device_under_test.On()
        time.sleep(0.1)
        logging.info( ("vcc_proxy.State() AFTER VCC On() = {}".
        format( device_under_test.State())) )

        config_str = json.dumps({
            "config_id": "vcc_unit_test",
            "frequency_band": "3",
        })
        logging.info("json_str = {}".format(config_str))
        device_under_test.ConfigureScan(config_str)
        time.sleep(0.1)

        # TODO use the base class tango_change_event_helper() function
        # TODO -use the base class test  assert_calls()

        scan_id = '1'

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, scan_id)

        # Use callable 'Scan'  API
        device_under_test.Scan(scan_id_device_data)
        time.sleep(0.1)

        logging.info( (" vcc_proxy.scanID =  {}".
        format(device_under_test.scanID)) )

        logging.info( (" vcc_proxy.frequencyBand =  {}".
        format(device_under_test.frequencyBand)) )

        #TODO fix hardcoded value
        assert device_under_test.frequencyBand == 2 # index 2 == freq band 3
        
        assert device_under_test.scanID == int(scan_id)
        device_under_test.EndScan()
        time.sleep(0.1)

        device_under_test.GoToIdle()
        time.sleep(0.1)

        # VCC Off() command
        device_under_test.Off()
        time.sleep(0.1)
        logging.info( ("vcc_proxy.State() AFTER VCC Off() & sleep = {}".
        format( device_under_test.State())) )


        """
        # all bands should be OFF after initialization
        create_band_12_proxy.Init()
        create_band_3_proxy.Init()
        create_band_4_proxy.Init()
        create_band_5_proxy.Init()

        assert create_band_12_proxy.State() == DevState.OFF
        assert create_band_3_proxy.State() == DevState.OFF
        assert create_band_4_proxy.State() == DevState.OFF
        assert create_band_5_proxy.State() == DevState.OFF

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

        """

    @pytest.mark.skip
    def test_ConfigureSearchWindow_basic(
        self,
        tango_context
    ):
        """
        Test a minimal successful search window configuration.
        """
        if tango_context is None:
            dev_factory = DevFactory()
            logging.info("%s", dev_factory._test_context)
            vcc_proxy = dev_factory.get_device("mid_csp_cbf/vcc/001")
            sw_1_proxy = dev_factory.get_device("mid_csp_cbf/vcc_sw1/001")
            sw_1_proxy.Init()
            time.sleep(3)

            # check initial values of attributes
            assert sw_1_proxy.searchWindowTuning == 0
            assert sw_1_proxy.tdcEnable == False
            assert sw_1_proxy.tdcNumBits == 0
            assert sw_1_proxy.tdcPeriodBeforeEpoch == 0
            assert sw_1_proxy.tdcPeriodAfterEpoch == 0
            assert sw_1_proxy.tdcDestinationAddress == ("", "", "")

            # check initial state
            assert sw_1_proxy.State() == DevState.DISABLE

            # set receptorID to 1 to correctly test tdcDestinationAddress
            vcc_proxy.receptorID = 1

        
            # configure search window
            f = open(file_path + "/../data/test_ConfigureSearchWindow_basic.json")
            vcc_proxy.ConfigureSearchWindow(f.read().replace("\n", ""))
            f.close()
            time.sleep(1)

            # check configured values
            assert sw_1_proxy.searchWindowTuning == 1000000000
            assert sw_1_proxy.tdcEnable == True
            assert sw_1_proxy.tdcNumBits == 8
            assert sw_1_proxy.tdcPeriodBeforeEpoch == 5
            assert sw_1_proxy.tdcPeriodAfterEpoch == 25
            assert sw_1_proxy.tdcDestinationAddress == ("", "", "")

            # check state
            assert sw_1_proxy.State() == DevState.ON
