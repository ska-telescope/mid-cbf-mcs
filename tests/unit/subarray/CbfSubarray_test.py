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
from time import sleep
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

        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.ON

        if command == "On":
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            expected_state = DevState.OFF
            result = device_under_test.Off()

        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state

    @pytest.mark.parametrize(
        "receptor_ids, \
        receptors_to_remove",
        [
            (
                ["SKA001", "SKA063", "SKA100", "SKA036"],
                ["SKA063", "SKA036", "SKA001"],
            ),
            (["SKA100", "SKA036", "SKA001"], ["SKA036", "SKA100"]),
        ],
    )
    def test_Add_Remove_Receptors_valid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[str],
        receptors_to_remove: List[str],
    ) -> None:
        """
        Test valid use of Add/RemoveReceptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON

        # add all except last receptor
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids[:-1])

        # list of receptors from device_under_test is returned as a tuple
        # so need to cast to list
        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids[:-1]
        )
        assert device_under_test.obsState == ObsState.IDLE

        # add the last receptor
        device_under_test.AddReceptors([receptor_ids[-1]])

        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids
        )
        assert device_under_test.obsState == ObsState.IDLE

        # remove all except last receptor
        device_under_test.RemoveReceptors(receptors_to_remove)

        receptor_ids_after_remove = [
            r for r in receptor_ids if r not in receptors_to_remove
        ]
        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids_after_remove
        )
        assert device_under_test.obsState == ObsState.IDLE

        # remove remaining receptor
        device_under_test.RemoveReceptors(receptor_ids_after_remove)

        assert list(device_under_test.receptors) == []

        # check for ObsState.EMPTY fails inconsistently
        # adding wait time allows consistent pass
        sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "receptor_ids",
        [
            (["SKA001", "SKA063", "SKA100", "SKA036"]),
            (["SKA036", "SKA001", "SKA063"]),
        ],
    )
    def test_RemoveAllReceptors_valid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[str],
    ) -> None:
        """
        Test valid use of RemoveAllReceptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)

        assert device_under_test.obsState == ObsState.IDLE

        # remove all receptors
        device_under_test.RemoveAllReceptors()

        assert list(device_under_test.receptors) == []

        # check for ObsState.EMPTY fails inconsistently
        # adding wait time allows consistent pass
        sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "receptor_ids, \
        invalid_receptor_id",
        [
            (["SKA100", "SKA063"], ["SKA200"]),
            (["SKA036", "SKA001"], ["MKT100"]),
        ],
    )
    def test_AddReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[str],
        invalid_receptor_id: List[str],
    ) -> None:
        """
        Test invalid use of AddReceptors commands:
            - when a receptor ID is invalid (e.g. out of range)
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON

        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)

        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids
        )
        assert device_under_test.obsState == ObsState.IDLE

        # Validation of input receptors will throw an
        # exception if there is an invalid receptor id
        with pytest.raises(Exception):
            device_under_test.AddReceptors(invalid_receptor_id)

        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids
        )

    @pytest.mark.parametrize(
        "receptor_ids, \
        not_assigned_receptors_to_remove",
        [
            (["SKA036", "SKA063"], ["SKA100"]),
            (["SKA100", "SKA001"], ["SKA063", "SKA036"]),
        ],
    )
    def test_RemoveReceptors_notAssigned(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[str],
        not_assigned_receptors_to_remove: List[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)

        assert device_under_test.obsState == ObsState.IDLE

        # try removing a receptor not assigned to subarray 1
        device_under_test.RemoveReceptors(not_assigned_receptors_to_remove)

        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids
        )
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "receptor_ids, \
        invalid_receptors_to_remove",
        [
            (["SKA036", "SKA063"], ["SKA000"]),
            (["SKA100", "SKA001"], [" SKA160", "MKT163"]),
        ],
    )
    def test_RemoveReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[str],
        invalid_receptors_to_remove: List[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor id to be removed is not a valid receptor id
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)

        assert device_under_test.obsState == ObsState.IDLE

        # Validation of requested receptors will throw an
        # exception if there is an invalid receptor id
        with pytest.raises(Exception):
            device_under_test.RemoveReceptors(invalid_receptors_to_remove)

        assert sorted(list(device_under_test.receptors)) == sorted(
            receptor_ids
        )
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "receptor_ids", [(["SKA100", "SKA036"]), (["SKA063", "SKA001"])]
    )
    def test_RemoveAllReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptor_ids: List[str],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # try removing all receptors
        result = device_under_test.RemoveAllReceptors()

        assert result[0][0] == ResultCode.FAILED

    @pytest.mark.parametrize(
        "config_file_name, \
        receptor_ids",
        [
            (
                "ConfigureScan_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
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

        assert device_under_test.State() == DevState.OFF
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptor_ids)
        freq_offset_k = [0] * 197
        device_under_test.frequencyOffsetK = freq_offset_k
        freq_offset_deltaF = 1800
        device_under_test.frequencyOffsetDeltaF = freq_offset_deltaF

        assert device_under_test.obsState == ObsState.IDLE

        # configure scan
        f = open(data_file_path + config_file_name)
        device_under_test.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        sleep(CONST_WAIT_TIME)

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
        sleep(CONST_WAIT_TIME)

        # send the Scan command
        f = open(data_file_path + scan_file_name)
        device_under_test.Scan(f.read().replace("\n", ""))
        f.close()

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

        assert device_under_test.obsState == ObsState.IDLE
