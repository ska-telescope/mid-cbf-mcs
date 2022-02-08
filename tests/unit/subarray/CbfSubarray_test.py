#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfSubarray."""

from __future__ import annotations

from typing import List

# Standard imports
import os
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
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState

# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

@pytest.mark.skip
class TestCbfSubarray:
    """
    Test class for TestCbfSubarray tests.
    """

    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Init(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test initialization

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        time.sleep(0.1)
        # check attributes after initialization
        assert device_under_test.State() == DevState.OFF
        # TODO: these asserts don't work
        # assert device_under_test.receptors == []
        # assert device_under_test.fspList == [[], [], [], []]
        # assert device_under_test.fspState == {}
        # assert device_under_test.fspHealthState == {}
        # assert device_under_test.vccState == {}
        # assert device_under_test.vccHealthState == {}
        # This is a bug in the tango library: 
        # https://gitlab.com/tango-controls/pytango/-/issues/230
        assert device_under_test.frequencyBand == 0
        assert device_under_test.configID == ""
        assert device_under_test.scanID == 0
        assert device_under_test.latestScanConfig == ""

    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_On_Off(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test On/Off commands.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.OFF
        result = device_under_test.On()
        time.sleep(3)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == DevState.ON
        result = device_under_test.Off()
        time.sleep(3)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize(
        "receptor_ids, \
        receptors_to_remove",
        [
            (
                [1, 3, 4, 2],
                [2, 1, 4]
            ),
            (
                [4, 1, 2],
                [2, 1]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Add_Remove_Receptors_valid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[int], 
        receptors_to_remove: List[int], 
    ) -> None:
        """
        Test valid use of Add/RemoveReceptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

         # add all except last receptor
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids[:-1])
        time.sleep(0.1)
        assert [device_under_test.receptors[i] 
            for i in range(len(receptor_ids[:-1]))] == receptor_ids[:-1]
        assert device_under_test.obsState == ObsState.IDLE

        # add the last receptor
        device_under_test.AddReceptors([receptor_ids[-1]])
        time.sleep(0.1)
        assert [device_under_test.receptors[i] 
            for i in range(len(receptor_ids))] == receptor_ids
        assert device_under_test.obsState == ObsState.IDLE

        # remove all except last receptor
        device_under_test.RemoveReceptors(receptors_to_remove)
        time.sleep(0.1)
        receptor_ids_after_remove = [r for r in receptor_ids if r not in receptors_to_remove]
        for idx, receptor in enumerate(receptor_ids_after_remove):
            assert device_under_test.receptors[idx] == receptor
        assert device_under_test.obsState == ObsState.IDLE

        # remove remaining receptor
        device_under_test.RemoveReceptors(receptor_ids_after_remove)
        time.sleep(0.1)
        assert len(device_under_test.receptors) == 0
        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "receptor_ids",
        [
            (
                [1, 3, 4, 2]
            ),
            (
                [4, 1, 2]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_RemoveAllReceptors_valid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[int]
    ) -> None:
        """
        Test valid use of RemoveAllReceptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

        # remove all receptors
        device_under_test.RemoveAllReceptors()
        time.sleep(0.1)
        assert len(device_under_test.receptors) == 0
        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "receptor_ids, \
        invalid_receptor_id", 
        [
            (
                [1, 3],
                [200]
            ),
            (
                [4, 2],
                [0]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_AddReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[int], 
        invalid_receptor_id: List[int],
    ) -> None:
        """
        Test invalid use of AddReceptors commands:
            - when a receptor ID is invalid (e.g. out of range)
        """
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert [device_under_test.receptors[i] for i in range(len(receptor_ids))] == receptor_ids
        assert device_under_test.obsState == ObsState.IDLE

        # try adding an invalid receptor ID
        result = device_under_test.AddReceptors(invalid_receptor_id)
        time.sleep(0.1)
        assert result[0][0] == ResultCode.FAILED
        assert device_under_test.obsState == ObsState.FAULT

    @pytest.mark.parametrize(
        "receptor_ids, \
        invalid_receptors_to_remove", 
        [
            (
                [1, 3],
                [2]
            ),
            (
                [4, 2],
                [1, 3]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_RemoveReceptors_invalid(
            self: TestCbfSubarray,
            device_under_test: CbfDeviceProxy,
            receptor_ids: List[int], 
            invalid_receptors_to_remove: List[int], 
        ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

        # try removing a receptor not assigned to subarray 1
        # doing this doesn't actually throw an error
        device_under_test.RemoveReceptors(invalid_receptors_to_remove)
    
    @pytest.mark.parametrize(
        "receptor_ids", 
        [
            (
                [1, 3]
            ),
            (
                [4, 2]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_RemoveAllReceptors_invalid(
            self: TestCbfSubarray,
            device_under_test: CbfDeviceProxy,
            receptor_ids: List[int] 
        ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

        # try removing all receptors
        # doing this doesn't actually throw an error
        device_under_test.RemoveAllReceptors()

    @pytest.mark.parametrize(
        "config_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                [1, 3, 4, 2]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_ConfigureScan_basic(
        self: TestCbfSubarray, 
        device_under_test: CbfDeviceProxy, 
        config_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test a successful scan configuration
        """
        f = open(data_file_path + config_file_name)
        config_string = f.read().replace("\n", "")
        f.close()
        config_json = json.loads(config_string)

        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        
        # configure scan
        device_under_test.ConfigureScan(config_string)
        time.sleep(3) # ConfigureScan takes a while
        assert device_under_test.configID == config_json["common"]["config_id"]
        band_index = freq_band_dict()[config_json["common"]["frequency_band"]]
        assert device_under_test.frequencyBand == band_index 
        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2]
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2]
            )

        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Scan(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the Scan command
        """
        f1 = open(data_file_path + config_file_name)
        config_string = f1.read().replace("\n", "")
        f1.close()
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.ConfigureScan(config_string)
        time.sleep(3)
        assert device_under_test.obsState == ObsState.READY

        # send the Scan command
        f2 = open(data_file_path + scan_file_name)
        json_string_scan = f2.read().replace("\n", "")
        device_under_test.Scan(json_string_scan)
        f2.close()
        scan_id = json.loads(json_string_scan)["scan_id"]
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.SCANNING
        assert device_under_test.scanID == scan_id

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2],
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_EndScan(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the EndScan command
        """
        f1 = open(data_file_path + config_file_name)
        config_string = f1.read().replace("\n", "")
        f1.close()
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.ConfigureScan(config_string)
        time.sleep(3)
        assert device_under_test.obsState == ObsState.READY
        f2 = open(data_file_path + scan_file_name)
        json_string_scan = f2.read().replace("\n", "")
        device_under_test.Scan(json_string_scan)
        f2.close()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.SCANNING

        # send the EndScan command
        device_under_test.EndScan()
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.READY
        assert device_under_test.scanID == 0

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2],
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Abort(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the Abort command
        """
        f1 = open(data_file_path + config_file_name)
        config_string = f1.read().replace("\n", "")
        f1.close()
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.ConfigureScan(config_string)
        time.sleep(3)
        assert device_under_test.obsState == ObsState.READY
        f2 = open(data_file_path + scan_file_name)
        json_string_scan = f2.read().replace("\n", "")
        device_under_test.Scan(json_string_scan)
        f2.close()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.SCANNING

        # send the Abort command
        device_under_test.Abort()
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.ABORTED

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2],
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Reset(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the ObsReset command
        """
        f1 = open(data_file_path + config_file_name)
        config_string = f1.read().replace("\n", "")
        f1.close()
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.ConfigureScan(config_string)
        time.sleep(3)
        assert device_under_test.obsState == ObsState.READY
        f2 = open(data_file_path + scan_file_name)
        json_string_scan = f2.read().replace("\n", "")
        device_under_test.Scan(json_string_scan)
        f2.close()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.SCANNING
        device_under_test.Abort()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.ABORTED

        # send the Reset command
        device_under_test.ObsReset()
        time.sleep(3)

        assert device_under_test.obsState == ObsState.IDLE
        assert device_under_test.configID == ""
        assert device_under_test.scanID == 0
        assert device_under_test.frequencyBand == 0

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2],
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Restart(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the Restart command
        """
        f1 = open(data_file_path + config_file_name)
        config_string = f1.read().replace("\n", "")
        f1.close()
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.ConfigureScan(config_string)
        time.sleep(3)
        assert device_under_test.obsState == ObsState.READY
        f2 = open(data_file_path + scan_file_name)
        json_string_scan = f2.read().replace("\n", "")
        device_under_test.Scan(json_string_scan)
        f2.close()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.SCANNING
        device_under_test.Abort()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.ABORTED

        # send the Reset command
        device_under_test.Restart()
        time.sleep(3)

        assert device_under_test.obsState == ObsState.EMPTY
        assert device_under_test.configID == ""
        assert device_under_test.scanID == 0
        assert device_under_test.frequencyBand == 0
        assert len(device_under_test.receptors) == 0

    @pytest.mark.parametrize(
        "config_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                [1, 3, 4, 2],
            ),
            (
                "Configure_TM-CSP_v2.json",
                [4, 1, 2],
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_GoToIdle(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        f1 = open(data_file_path + config_file_name)
        config_string = f1.read().replace("\n", "")
        f1.close()
        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE
        device_under_test.ConfigureScan(config_string)
        time.sleep(3)
        assert device_under_test.obsState == ObsState.READY

        device_under_test.GoToIdle()
        time.sleep(3)
        assert device_under_test.obsState == ObsState.IDLE
        assert device_under_test.frequencyBand == 0
        assert device_under_test.configID == ""
        assert device_under_test.scanID == 0
