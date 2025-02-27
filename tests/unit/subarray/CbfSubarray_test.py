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

import gc
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, ObsState, ResultCode, SimulationMode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.subarray.subarray_device import CbfSubarray

from ... import test_utils

# Data file path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Disable garbage collection to prevent tests hanging
gc.disable()


class TestCbfSubarray:
    """
    Test class for CbfSubarray.
    """

    @pytest.fixture(name="test_context")
    def subarray_test_context(
        self: TestCbfSubarray, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that creates a test context for the CbfSubarray device.

        :param initial_mocks: A dictionary of initial mocks to be used in the test context.
        :return: A test context for the CbfSubarray device.
        """
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/sub_elt/subarray_01",
            device_class=CbfSubarray,
            CbfControllerAddress="mid_csp_cbf/sub_elt/controller",
            VCC=[
                "mid_csp_cbf/vcc/001",
                "mid_csp_cbf/vcc/002",
                "mid_csp_cbf/vcc/003",
                "mid_csp_cbf/vcc/004",
            ],
            FSP=[
                "mid_csp_cbf/fsp/01",
                "mid_csp_cbf/fsp/02",
                "mid_csp_cbf/fsp/03",
                "mid_csp_cbf/fsp/04",
            ],
            FspCorrSubarray=[
                "mid_csp_cbf/fspCorrSubarray/01_01",
                "mid_csp_cbf/fspCorrSubarray/02_01",
                "mid_csp_cbf/fspCorrSubarray/03_01",
                "mid_csp_cbf/fspCorrSubarray/04_01",
            ],
            TalonBoard=[
                "mid_csp_cbf/talon_board/001",
                "mid_csp_cbf/talon_board/002",
                "mid_csp_cbf/talon_board/003",
                "mid_csp_cbf/talon_board/004",
            ],
            VisSLIM=["mid_csp_cbf/slim/slim-vis"],
            DeviceID="1",
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock(name))

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestCbfSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestCbfSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestCbfSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def device_online_and_on(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test writing to the sysParam attribute. Also used to test startup of the DUT.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE

        device_under_test.adminMode = AdminMode.ONLINE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="adminMode",
            attribute_value=AdminMode.ONLINE,
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.ON,
        )

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param = f.read()
        device_under_test.sysParam = sys_param

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="sysParam",
            attribute_value=sys_param,
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="obsState",
            attribute_value=ObsState.EMPTY,
        )

    @pytest.mark.parametrize(
        "receptors, \
        remove_all, \
        receptors_to_remove",
        [
            (
                ["SKA001", "SKA063", "SKA100", "SKA036"],
                False,
                ["SKA063", "SKA036", "SKA001"],
            ),
            (["SKA100", "SKA036", "SKA001"], True, []),
        ],
    )
    def test_Add_Remove_Receptors(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        receptors: list[str],
        remove_all: bool,
        receptors_to_remove: list[str],
    ) -> None:
        """
        Test the AddReceptors(), RemoveReceptors(),
        and RemoveAllReceptors() commands' happy paths.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param receptors: list of DISH IDs to assign to subarray
        :param remove_all: False to use RemoveReceptors, True for RemoveAllReceptors
        :param receptors_to_remove: list of DISH IDs to remove from subarray
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        attr_values = [
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
        ]

        # Add receptors in 2 stages
        curr_rec = set()
        for i, input_rec in enumerate([receptors[:-1], receptors[-1:]]):
            (return_value, command_id) = device_under_test.AddReceptors(
                input_rec
            )
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{command_id[0]}",
                        f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
                    ),
                    None,
                    1,
                )
            )

            if i > 0:
                attr_values.append(
                    ("obsState", ObsState.RESOURCING, ObsState.IDLE, i)
                )
                attr_values.append(
                    ("obsState", ObsState.IDLE, ObsState.RESOURCING, i + 1)
                )

            # assert receptors attribute updated
            curr_rec.update(input_rec)
            receptors_push_val = list(curr_rec.copy())
            receptors_push_val.sort()
            attr_values.append(
                ("receptors", tuple(receptors_push_val), None, 1)
            )

        if remove_all:
            (return_value, command_id) = device_under_test.RemoveAllReceptors()

            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{command_id[0]}",
                        f'[{ResultCode.OK.value}, "RemoveAllReceptors completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        else:
            # Remove receptors in 2 stages
            for input_rec in [
                receptors_to_remove[:-1],
                receptors_to_remove[-1:],
            ]:
                (return_value, command_id) = device_under_test.RemoveReceptors(
                    input_rec
                )

                # Check that the command was successfully queued
                assert return_value[0] == ResultCode.QUEUED

                # Check that the queued command succeeded
                attr_values.append(
                    (
                        "longRunningCommandResult",
                        (
                            f"{command_id[0]}",
                            f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
                        ),
                        None,
                        1,
                    )
                )

                # Check obsState transitions
                attr_values.append(
                    ("obsState", ObsState.RESOURCING, ObsState.IDLE, i)
                )
                attr_values.append(
                    ("obsState", ObsState.IDLE, ObsState.RESOURCING, i + 1)
                )

                # Assert receptors attribute updated
                curr_rec.difference_update(input_rec)
                receptors_push_val = list(curr_rec.copy())
                receptors_push_val.sort()
                attr_values.append(
                    ("receptors", tuple(receptors_push_val), None, 1),
                )
                i += 1

            # Remove remaining receptor(s)
            (return_value, command_id) = device_under_test.RemoveReceptors(
                list(curr_rec)
            )

            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{command_id[0]}",
                        f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        # Check obsState transitions
        attr_values.append(("obsState", ObsState.RESOURCING, ObsState.IDLE, i))
        attr_values.append(
            ("obsState", ObsState.EMPTY, ObsState.RESOURCING, 1)
        )

        # Assert receptors attribute updated
        attr_values.append(("receptors", (), None, 1))

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "invalid_receptor",
        [["SKA200"], ["MKT100"]],
    )
    def test_AddReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        invalid_receptor: list[str],
    ) -> None:
        """
        Test the AddReceptors() command when a receptor ID is out of valid range.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param invalid_receptor: invalid DISH ID
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Add receptors
        (return_value, command_id) = device_under_test.AddReceptors(
            invalid_receptor
        )

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # Check that the queued command failed
        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f"[{ResultCode.FAILED.value}, "
                    f'"Invalid DISH ID {invalid_receptor[0]}"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.EMPTY, ObsState.RESOURCING, 1),
        ]

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "receptors, \
        unassigned_receptors",
        [
            (["SKA036", "SKA063"], ["SKA100"]),
            (["SKA100", "SKA001"], ["SKA063", "SKA036"]),
        ],
    )
    def test_RemoveReceptors_not_assigned(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        receptors: list[str],
        unassigned_receptors: list[int],
    ) -> None:
        """
        Test the RemoveReceptors() command when one of the receptors to remove
        was not assigned to the subarray.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param receptors: list of DISH IDs to assign to subarray
        :param unassigned_receptors: unassigned DISH IDs
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Add receptors
        (return_value, command_id) = device_under_test.AddReceptors(receptors)

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # Assert receptors attribute updated
        receptors.sort()

        # Check that the queued command succeeded
        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            ("receptors", tuple(receptors), None, 1),
        ]

        # Try removing a receptor not assigned to subarray
        (return_value, command_id) = device_under_test.RemoveReceptors(
            unassigned_receptors
        )
        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values.append(
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "RemoveReceptors completed OK"]',
                ),
                None,
                1,
            )
        )
        attr_values.append(("obsState", ObsState.RESOURCING, ObsState.IDLE, 1))
        attr_values.append(("obsState", ObsState.IDLE, ObsState.RESOURCING, 2))

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

        assert device_under_test.receptors == tuple(receptors)

    @pytest.mark.parametrize(
        "receptors, \
        invalid_receptor",
        [
            (["SKA036", "SKA063"], ["SKA000"]),
            (["SKA100", "SKA001"], [" MKT163"]),
        ],
    )
    def test_RemoveReceptors_invalid(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        receptors: list[str],
        invalid_receptor: list[int],
    ) -> None:
        """
        Test the RemoveReceptors() command when one of the receptor IDs to be
        removed is not in valid range.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param receptors: list of DISH IDs to assign to subarray
        :param invalid_receptor: invalid DISH ID
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Add receptors
        (return_value, command_id) = device_under_test.AddReceptors(receptors)

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # Assert receptors attribute updated
        receptors.sort()

        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            ("receptors", tuple(receptors), None, 1),
        ]

        # Try to remove invalid receptors
        (return_value, command_id) = device_under_test.RemoveReceptors(
            invalid_receptor
        )

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # Check that the queued command failed
        attr_values.append(
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f"[{ResultCode.FAILED.value}, "
                    + f'"DISH ID {invalid_receptor[0]} is not valid. '
                    + "It must be SKA001-SKA133 or MKT000-MKT063. "
                    + 'Spaces before, after, or in the middle of the ID are not accepted."]',
                ),
                None,
                1,
            )
        )
        attr_values.append(("obsState", ObsState.RESOURCING, ObsState.IDLE, 1))
        attr_values.append(("obsState", ObsState.IDLE, ObsState.RESOURCING, 2))

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "receptors",
        [["SKA036", "SKA063"], ["SKA100", "SKA001"]],
    )
    def test_RemoveAllReceptors_not_allowed(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        receptors: list[str],
    ) -> None:
        """
        Test the RemoveReceptors() and RemoveAllReceptors()
        commands when subarray is in ObsState.EMPTY.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param receptors: list of DISH IDs to remove from subarray
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Try to remove receptors
        (return_value, command_id) = device_under_test.RemoveReceptors(
            receptors
        )
        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        # Check that the queued command failed
        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
                None,
                1,
            )
        ]

        # Try to remove allreceptors
        (return_value, command_id) = device_under_test.RemoveAllReceptors()
        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values.append(
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
                None,
                1,
            )
        )

        # Check that the queued commands failed
        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors, scan_file_name",
        [
            ("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan1_basic.json"),
            ("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan_invalid.json"),
        ],
    )
    def test_Scan(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
        scan_file_name: str,
    ) -> None:
        """
        Test the Scan() command's happy path with a minimal successful scan configuration.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        :param scan_file_name: file name for the scan ID
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            config_str = f.read().replace("\n", "")
        with open(test_data_path + scan_file_name) as f:
            scan_str = f.read().replace("\n", "")

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        command_dict["AddReceptors"] = device_under_test.AddReceptors(
            receptors
        )
        receptors.sort()

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            config_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_str)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()
        command_dict["RemoveReceptors"] = device_under_test.RemoveReceptors(
            receptors
        )

        attr_values = [
            ("receptors", tuple(receptors), None, 1),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
        ]
        # Conditional for Scan/EndScan failure case testing
        if "invalid" not in scan_file_name:
            attr_values.extend(
                [
                    ("obsState", ObsState.SCANNING, ObsState.READY, 1),
                    ("obsState", ObsState.READY, ObsState.SCANNING, 1),
                ]
            )
        attr_values.extend(
            [
                ("obsState", ObsState.IDLE, ObsState.READY, 1),
                ("obsState", ObsState.RESOURCING, ObsState.IDLE, 1),
                ("obsState", ObsState.EMPTY, ObsState.RESOURCING, 1),
                ("receptors", (), None, 1),
            ]
        )

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Conditional for Scan/EndScan failure case testing
            if "Scan" in command_name and "invalid" in scan_file_name:
                if command_name == "Scan":
                    attr_values.append(
                        (
                            "longRunningCommandResult",
                            (
                                f"{return_value[1][0]}",
                                f'[{ResultCode.FAILED.value}, "Failed to validate Scan input JSON"]',
                            ),
                            None,
                            1,
                        )
                    )
                elif command_name == "EndScan":
                    attr_values.append(
                        (
                            "longRunningCommandResult",
                            (
                                f"{return_value[1][0]}",
                                f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                            ),
                            None,
                            1,
                        )
                    )
                continue

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors, scan_file_name",
        [("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan1_basic.json")],
    )
    def test_Scan_reconfigure(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
        scan_file_name: str,
    ) -> None:
        """
        Test subarrays's ability to reconfigure and run multiple scans.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        :param scan_file_name: file name for the scan ID
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            config_str = f.read().replace("\n", "")
        with open(test_data_path + scan_file_name) as f:
            scan_str = f.read().replace("\n", "")

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Add receptors
        command_dict["AddReceptors"] = device_under_test.AddReceptors(
            receptors
        )
        # Assert receptors attribute updated
        receptors.sort()

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            config_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_str)
        command_dict["EndScan"] = device_under_test.EndScan()

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # Check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
                min_n_events=1,
            )

        # Second round of observation
        command_dict = {}
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            config_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_str)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()
        command_dict["RemoveReceptors"] = device_under_test.RemoveReceptors(
            receptors
        )

        attr_values = [
            ("receptors", tuple(receptors), None, 1),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.SCANNING, ObsState.READY, 1),
            ("obsState", ObsState.READY, ObsState.SCANNING, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.READY, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 2),
            ("obsState", ObsState.SCANNING, ObsState.READY, 2),
            ("obsState", ObsState.READY, ObsState.SCANNING, 2),
            ("obsState", ObsState.IDLE, ObsState.READY, 1),
            ("obsState", ObsState.RESOURCING, ObsState.IDLE, 1),
            ("obsState", ObsState.EMPTY, ObsState.RESOURCING, 1),
            ("receptors", (), None, 1),
        ]

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors",
        [("ConfigureScan_basic_CORR.json", ["SKA001"])],
    )
    def test_Abort_from_ready(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
    ) -> None:
        """
        Test the Abort() command from ObsState.READY.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            config_str = f.read().replace("\n", "")

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Add receptors
        command_dict["AddReceptors"] = device_under_test.AddReceptors(
            receptors
        )
        # Assert receptors attribute updated
        receptors.sort()

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            config_str
        )
        command_dict["Abort"] = device_under_test.Abort()

        attr_values = [
            ("receptors", tuple(receptors), None, 1),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.ABORTING, ObsState.READY, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
        ]

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors, scan_file_name",
        [("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan1_basic.json")],
    )
    def test_Abort_from_scanning(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
        scan_file_name: str,
    ) -> None:
        """
        Test the Abort() command from ObsState.SCANNING.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        :param scan_file_name: file name for the scan ID
        """
        # Set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # Prepare input data
        with open(test_data_path + config_file_name) as f:
            config_str = f.read().replace("\n", "")
        with open(test_data_path + scan_file_name) as f:
            scan_str = f.read().replace("\n", "")

        # Dict to store return code and unique IDs of queued commands
        command_dict = {}

        # Add receptors
        command_dict["AddReceptors"] = device_under_test.AddReceptors(
            receptors
        )
        # Assert receptors attribute updated
        receptors.sort()

        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            config_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_str)
        command_dict["Abort"] = device_under_test.Abort()

        attr_values = [
            ("receptors", tuple(receptors), None, 1),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.SCANNING, ObsState.READY, 1),
            ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
        ]

        # Assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # Check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ),
                    None,
                    1,
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors",
        [("ConfigureScan_basic_CORR.json", ["SKA001"])],
    )
    def test_ObsReset_abort_from_ready(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
    ) -> None:
        """
        Test the ObsReset() command to ObsState.IDLE from ObsState.READY.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        """
        # Test ObsReset from READY
        self.test_Abort_from_ready(
            device_under_test,
            event_tracer,
            config_file_name,
            receptors,
        )

        (return_value, command_id) = device_under_test.ObsReset()

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "ObsReset completed OK"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
        ]

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors, scan_file_name",
        [("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan1_basic.json")],
    )
    def test_ObsReset_abort_from_scanning(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
        scan_file_name: str,
    ) -> None:
        """
        Test the ObsReset() command to ObsState.IDLE from ObsState.SCANNING.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        :param scan_file_name: file name for the scan ID
        """
        # Test ObsReset from SCANNING
        self.test_Abort_from_scanning(
            device_under_test,
            event_tracer,
            config_file_name,
            receptors,
            scan_file_name,
        )

        (return_value, command_id) = device_under_test.ObsReset()

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "ObsReset completed OK"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
        ]

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors",
        [("ConfigureScan_basic_CORR.json", ["SKA001"])],
    )
    def test_Abort_Restart_from_ready(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
    ) -> None:
        """
        Test the Restart() command to ObsState.EMPTY from ObsState.READY.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        """
        # Test Restart from READY
        self.test_Abort_from_ready(
            device_under_test,
            event_tracer,
            config_file_name,
            receptors,
        )

        (return_value, command_id) = device_under_test.Restart()

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "Restart completed OK"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESTARTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.EMPTY, ObsState.RESTARTING, 1),
            ("receptors", (), None, 1),
        ]

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, receptors, scan_file_name",
        [("ConfigureScan_basic_CORR.json", ["SKA001"], "Scan1_basic.json")],
    )
    def test_Abort_Restart_from_scanning(
        self: TestCbfSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        receptors: list[int],
        scan_file_name: str,
    ) -> None:
        """
        Test the Restart() command to ObsState.EMPTY from ObsState.SCANNING.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        :param config_file_name: file name for the configuration
        :param receptors: list of DISH IDs to assign to subarray
        :param scan_file_name: file name for the scan ID
        """

        # Test Restart from SCANNING
        self.test_Abort_from_scanning(
            device_under_test,
            event_tracer,
            config_file_name,
            receptors,
            scan_file_name,
        )

        (return_value, command_id) = device_under_test.Restart()

        # Check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "Restart completed OK"]',
                ),
                None,
                1,
            ),
            ("obsState", ObsState.RESTARTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.EMPTY, ObsState.RESTARTING, 1),
            ("receptors", (), None, 1),
        ]

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )
