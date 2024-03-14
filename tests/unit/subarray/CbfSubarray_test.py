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

CONST_WAIT_TIME = 2


class TestCbfSubarray:
    """
    Test class for TestCbfSubarray tests.
    """

    def test_State(
        self: TestCbfSubarray, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestCbfSubarray, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestCbfSubarray, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_Power_Commands(
        self: TestCbfSubarray, device_under_test: CbfDeviceProxy
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

        # DevState should be OFF. Turn it to ON
        assert device_under_test.State() == DevState.OFF

        # test ON command
        expected_state = DevState.ON
        result = device_under_test.On()
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state

        # test OFF command
        expected_state = DevState.OFF
        result = device_under_test.Off()
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state

    @pytest.mark.parametrize(
        "receptors, \
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
        receptors: List[str],
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

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON

        # add all except last receptor
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptors[:-1])

        # list of receptors from device_under_test is returned as a tuple
        # so need to cast to list
        assert sorted(list(device_under_test.receptors)) == sorted(
            receptors[:-1]
        )
        assert device_under_test.obsState == ObsState.IDLE

        # add the last receptor
        device_under_test.AddReceptors([receptors[-1]])

        assert sorted(list(device_under_test.receptors)) == sorted(receptors)
        assert device_under_test.obsState == ObsState.IDLE

        # remove all except last receptor
        device_under_test.RemoveReceptors(receptors_to_remove)

        receptors_after_remove = [
            r for r in receptors if r not in receptors_to_remove
        ]
        assert sorted(list(device_under_test.receptors)) == sorted(
            receptors_after_remove
        )
        assert device_under_test.obsState == ObsState.IDLE

        # remove remaining receptor
        device_under_test.RemoveReceptors(receptors_after_remove)

        assert list(device_under_test.receptors) == []

        # check for ObsState.EMPTY fails inconsistently
        # adding wait time allows consistent pass
        sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "receptors",
        [
            (["SKA001", "SKA063", "SKA100", "SKA036"]),
            (["SKA036", "SKA001", "SKA063"]),
        ],
    )
    def test_RemoveAllReceptors_valid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptors: List[str],
    ) -> None:
        """
        Test valid use of RemoveAllReceptors command.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        # DevState should be OFF. Turn it to ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptors)

        assert device_under_test.obsState == ObsState.IDLE

        # remove all receptors
        device_under_test.RemoveAllReceptors()

        assert list(device_under_test.receptors) == []

        # check for ObsState.EMPTY fails inconsistently
        # adding wait time allows consistent pass
        sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "receptors, \
        invalid_receptor_id",
        [
            (["SKA100", "SKA063"], ["SKA200"]),
            (["SKA036", "SKA001"], ["MKT100"]),
        ],
    )
    def test_AddReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptors: List[str],
        invalid_receptor_id: List[str],
    ) -> None:
        """
        Test invalid use of AddReceptors commands:
            - when a receptor ID is invalid (e.g. out of range)
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON

        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptors)

        assert sorted(list(device_under_test.receptors)) == sorted(receptors)
        assert device_under_test.obsState == ObsState.IDLE

        # Validation of input receptors will throw an
        # exception if there is an invalid receptor id
        with pytest.raises(Exception):
            device_under_test.AddReceptors(invalid_receptor_id)

        assert sorted(list(device_under_test.receptors)) == sorted(receptors)

    @pytest.mark.parametrize(
        "receptors, \
        not_assigned_receptors_to_remove",
        [
            (["SKA036", "SKA063"], ["SKA100"]),
            (["SKA100", "SKA001"], ["SKA063", "SKA036"]),
        ],
    )
    def test_RemoveReceptors_notAssigned(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptors: List[str],
        not_assigned_receptors_to_remove: List[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptors)

        assert device_under_test.obsState == ObsState.IDLE

        # try removing a receptor not assigned to subarray 1
        device_under_test.RemoveReceptors(not_assigned_receptors_to_remove)

        assert sorted(list(device_under_test.receptors)) == sorted(receptors)
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "receptors, \
        invalid_receptors_to_remove",
        [
            (["SKA036", "SKA063"], ["SKA000"]),
            (["SKA100", "SKA001"], [" SKA160", "MKT163"]),
        ],
    )
    def test_RemoveReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptors: List[str],
        invalid_receptors_to_remove: List[int],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor id to be removed is not a valid receptor id
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON
        # add some receptors
        assert device_under_test.obsState == ObsState.EMPTY
        device_under_test.AddReceptors(receptors)

        assert device_under_test.obsState == ObsState.IDLE

        # Validation of requested receptors will throw an
        # exception if there is an invalid receptor id
        with pytest.raises(Exception):
            device_under_test.RemoveReceptors(invalid_receptors_to_remove)

        assert sorted(list(device_under_test.receptors)) == sorted(receptors)
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "receptors", [(["SKA100", "SKA036"]), (["SKA063", "SKA001"])]
    )
    def test_RemoveAllReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        receptors: List[str],
    ) -> None:
        """
        Test invalid use of RemoveReceptors commands:
            - when a receptor to be removed is not assigned to the subarray
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        # DevState should be OFF. Turn it to ON
        device_under_test.On()

        assert device_under_test.State() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        # try removing all receptors
        result = device_under_test.RemoveAllReceptors()

        assert result[0][0] == ResultCode.FAILED

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            )
        ],
    )
    def test_ConfigureScan_basic(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        receptors: List[str],
    ) -> None:
        """
        Test a successful scan configuration
        """
        assert device_under_test.State() == DevState.DISABLE
        device_under_test.adminMode = AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF
        assert device_under_test.obsState == ObsState.EMPTY

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        device_under_test.AddReceptors(receptors)
        freq_offset_k = [0] * 197
        device_under_test.frequencyOffsetK = freq_offset_k

        assert device_under_test.obsState == ObsState.IDLE

        # configure_scan command is only allowed in op state ON
        device_under_test.On()
        sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON

        # configure scan
        f = open(data_file_path + config_file_name)
        device_under_test.ConfigureScan(f.read().replace("\n", ""))
        f.close()
        sleep(CONST_WAIT_TIME)

        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                "Scan1_basic.json",
                ["SKA001", "SKA063", "SKA100", "SKA036"],
            ),
            (
                "ConfigureScan_CORR_PSS_PST.json",
                "Scan2_basic.json",
                ["SKA100", "SKA001", "SKA036"],
            ),
        ],
    )
    def test_Scan(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[int],
    ) -> None:
        """
        Test the Scan command
        """
        self.test_ConfigureScan_basic(
            device_under_test, config_file_name, receptors
        )

        # scan command is only allowed in op state ON
        device_under_test.On()
        sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON

        # send the Scan command
        f = open(data_file_path + scan_file_name)
        device_under_test.Scan(f.read().replace("\n", ""))
        f.close()

        assert device_under_test.obsState == ObsState.SCANNING

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                "Scan1_basic.json",
                ["SKA001", "SKA063", "SKA100", "SKA036"],
            ),
            (
                "ConfigureScan_CORR_PSS_PST.json",
                "Scan2_basic.json",
                ["SKA100", "SKA001", "SKA036"],
            ),
        ],
    )
    def test_EndScan(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[int],
    ) -> None:
        """
        Test the EndScan command
        """
        self.test_Scan(
            device_under_test, config_file_name, scan_file_name, receptors
        )

        # send the EndScan command
        device_under_test.EndScan()

        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                "Scan1_basic.json",
                ["SKA001", "SKA063", "SKA100", "SKA036"],
            ),
            (
                "ConfigureScan_CORR_PSS_PST.json",
                "Scan2_basic.json",
                ["SKA100", "SKA001", "SKA036"],
            ),
        ],
    )
    def test_Abort(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[int],
    ) -> None:
        """
        Test the Abort command
        """
        self.test_Scan(
            device_under_test, config_file_name, scan_file_name, receptors
        )

        # send the Abort command
        device_under_test.Abort()

        assert device_under_test.obsState == ObsState.ABORTED

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                "Scan1_basic.json",
                ["SKA001", "SKA063", "SKA100", "SKA036"],
            ),
            (
                "ConfigureScan_CORR_PSS_PST.json",
                "Scan2_basic.json",
                ["SKA100", "SKA001", "SKA036"],
            ),
        ],
    )
    def test_ObsReset(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[int],
    ) -> None:
        """
        Test the ObsReset command
        """
        self.test_Abort(
            device_under_test, config_file_name, scan_file_name, receptors
        )

        # send the ObsReset command
        device_under_test.ObsReset()

        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                "Scan1_basic.json",
                ["SKA001", "SKA063", "SKA100", "SKA036"],
            ),
            (
                "ConfigureScan_CORR_PSS_PST.json",
                "Scan2_basic.json",
                ["SKA100", "SKA001", "SKA036"],
            ),
        ],
    )
    def test_Restart(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[int],
    ) -> None:
        """
        Test the Restart command
        """
        self.test_Abort(
            device_under_test, config_file_name, scan_file_name, receptors
        )

        # send the Restart command
        device_under_test.Restart()

        assert device_under_test.obsState == ObsState.EMPTY

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic_CORR.json",
                ["SKA001", "SKA063", "SKA100", "SKA036"],
            ),
            (
                "ConfigureScan_CORR_PSS_PST.json",
                ["SKA100", "SKA001", "SKA036"],
            ),
        ],
    )
    def test_End(
        self: TestCbfSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        receptors: List[int],
    ) -> None:
        # End the scan block.
        self.test_ConfigureScan_basic(
            device_under_test, config_file_name, receptors
        )

        # end command is only permitted in Op state ON
        device_under_test.On()
        assert device_under_test.State() == DevState.ON

        device_under_test.End()

        assert device_under_test.obsState == ObsState.IDLE
