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

# Standard imports
import os
import time
from typing import List

import pytest

# SKA imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DevState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# Tango imports


# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

CONST_WAIT_TIME = 4


#@pytest.mark.skip
class TestCbfSubarray:
    """
    Test class for TestCbfSubarray tests.
    """
    @pytest.mark.skip
    def test_State(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE
    @pytest.mark.skip
    def test_Status(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."
    @pytest.mark.skip
    def test_adminMode(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE
    @pytest.mark.skip
    @pytest.mark.parametrize("command", ["On", "Off"])
    def test_Power_Commands(
        self: TestCbfSubarray, device_under_test: CbfDeviceProxy, command: str
    ) -> None:
        """
        Test the On/Off Commands

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param command: the command to test (one of On/Off)
        """

        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.ON

        if command == "On":
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            expected_state = DevState.OFF
            result = device_under_test.Off()

        time.sleep(CONST_WAIT_TIME)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "receptor_ids, \
        receptors_to_remove",
        [([1, 3, 4, 2], [2, 1, 4]), ([4, 1, 2], [2, 1])],
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
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON

        # add all except last receptor
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids[:-1])
        time.sleep(0.1)
        assert (device_under_test.receptors == receptor_ids[:-1]).all()
        assert device_under_test.obsState == ObsState.IDLE

        # add the last receptor
        device_under_test.AddReceptors([receptor_ids[-1]])
        time.sleep(0.1)
        assert (device_under_test.receptors == receptor_ids).all()
        assert device_under_test.obsState == ObsState.IDLE

        # remove all except last receptor
        device_under_test.RemoveReceptors(receptors_to_remove)
        time.sleep(0.1)
        receptor_ids_after_remove = [
            r for r in receptor_ids if r not in receptors_to_remove
        ]
        assert (device_under_test.receptors == receptor_ids_after_remove).all()
        assert device_under_test.obsState == ObsState.IDLE

        # remove remaining receptor
        device_under_test.RemoveReceptors(receptor_ids_after_remove)
        time.sleep(0.1)
        assert (device_under_test.receptors == []).all()
        assert device_under_test.obsState == ObsState.EMPTY
    @pytest.mark.skip
    @pytest.mark.parametrize("receptor_ids", [([1, 3, 4, 2]), ([4, 1, 2])])
    def test_RemoveAllReceptors_valid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[int],
    ) -> None:
        """
        Test valid use of RemoveAllReceptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

        # remove all receptors
        device_under_test.RemoveAllReceptors()
        time.sleep(0.1)
        assert (device_under_test.receptors == []).all()
        assert device_under_test.obsState == ObsState.EMPTY
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "receptor_ids, \
        invalid_receptor_id",
        [([1, 3], [200]), ([4, 2], [0])],
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
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON

        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert (device_under_test.receptors == receptor_ids).all()
        assert device_under_test.obsState == ObsState.IDLE

        # try adding an invalid receptor ID
        device_under_test.AddReceptors(invalid_receptor_id)
        time.sleep(0.1)
        assert (device_under_test.receptors == receptor_ids).all()
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "receptor_ids, \
        invalid_receptors_to_remove",
        [([1, 3], [2]), ([4, 2], [1, 3])],
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
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

        # try removing a receptor not assigned to subarray 1
        device_under_test.RemoveReceptors(invalid_receptors_to_remove)
        time.sleep(0.1)
        assert (device_under_test.receptors == receptor_ids).all()
        assert device_under_test.obsState == ObsState.IDLE
    @pytest.mark.skip
    @pytest.mark.parametrize("receptor_ids", [([1, 3]), ([4, 2])])
    def test_RemoveAllReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # try removing all receptors
        result = device_under_test.RemoveAllReceptors()
        time.sleep(0.1)
        assert result[0][0] == ResultCode.FAILED

    @pytest.mark.parametrize(
        "config_file_name, \
        receptor_ids",
        [
            (
                "ConfigureScan_basic.json",
                ["MKT000", "MKT002", "MKT003", "MKT001"],
            )
        ],
    )
    def test_ConfigureScan_basic(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        receptor_ids: List[str],
    ) -> None:
        """
        Test a successful scan configuration
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.OFF
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        freq_offset_k = [0] * 197
        device_under_test.frequencyOffsetK = freq_offset_k
        freq_offset_deltaF = 1800
        device_under_test.frequencyOffsetDeltaF = freq_offset_deltaF
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

        # configure scan
        f = open(data_file_path + config_file_name)
        device_under_test.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.obsState == ObsState.READY
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptor_ids",
        [
            ("ConfigureScan_basic.json", "Scan1_basic.json", [1, 3, 4, 2]),
            ("Configure_TM-CSP_v2.json", "Scan2_basic.json", [4, 1, 2]),
        ],
    )
    def test_Scan(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        """
        Test the Scan command
        """
        self.test_ConfigureScan_basic(
            device_under_test, config_file_name, receptor_ids
        )

        # send the Scan command
        f = open(data_file_path + scan_file_name)
        device_under_test.Scan(f.read().replace("\n", ""))
        f.close()
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.SCANNING
    @pytest.mark.skip
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
            ),
        ],
    )
    @pytest.mark.skip
    def test_EndScan(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        """
        Test the EndScan command
        """
        self.test_Scan(
            device_under_test, config_file_name, scan_file_name, receptor_ids
        )

        # send the EndScan command
        device_under_test.EndScan()
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.READY
    @pytest.mark.skip
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
            ),
        ],
    )
    @pytest.mark.skip
    def test_Abort(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        """
        Test the Abort command
        """
        self.test_Scan(
            device_under_test, config_file_name, scan_file_name, receptor_ids
        )

        # send the Abort command
        device_under_test.Abort()
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.ABORTED
    @pytest.mark.skip
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
            ),
        ],
    )
    @pytest.mark.skip
    def test_Reset(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        """
        Test the ObsReset command
        """
        self.test_Abort(
            device_under_test, config_file_name, scan_file_name, receptor_ids
        )

        # send the Reset command
        device_under_test.ObsReset()
        time.sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.IDLE
    @pytest.mark.skip
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
            ),
        ],
    )
    @pytest.mark.skip
    def test_Restart(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        """
        Test the Restart command
        """
        self.test_Abort(
            device_under_test, config_file_name, scan_file_name, receptor_ids
        )

        # send the Reset command
        device_under_test.Restart()
        time.sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.EMPTY

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
            ),
        ],
    )
    @pytest.mark.skip
    def test_End(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        receptor_ids: List[int],
    ) -> None:
        self.test_ConfigureScan_basic(
            device_under_test, config_file_name, receptor_ids
        )

        device_under_test.End()
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.obsState == ObsState.IDLE
