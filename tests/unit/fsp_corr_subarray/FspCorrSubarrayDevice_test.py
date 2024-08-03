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

from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_device import FspCorrSubarray

from ... import test_utils

# Path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Disable garbage collection to prevent tests hanging
gc.disable()

file_path = os.path.dirname(os.path.abspath(__file__))


class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray.
    """

    @pytest.fixture(name="test_context")
    def fsp_corr_test_context(
        self: TestFspCorrSubarray, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/fspCorrSubarray/01_01",
            device_class=FspCorrSubarray,
            HpsFspCorrControllerAddress="mid_csp_cbf/talon_lru/001",
            DeviceID="1",
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestFspCorrSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: A fixture that provides a
        :py:class: `CbfDeviceProxy` to the device under test, in a
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestFspCorrSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestFspCorrSubarray, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: A fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def device_online_and_on(
        self: TestFspCorrSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> bool:
        """
        Helper function to start up and turn on the DUT.

        :param device_under_test: A fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to recieve subscribed change events from the device under test.
        """
        # Set the DUT to AdminMode.ONLINE and DevState.ON
        device_under_test.simulationMode == SimulationMode.FALSE
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

        return device_under_test.adminMode == AdminMode.ONLINE

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("FspCorrSubarray_ConfigureScan_basic.json", 1)],
    )
    def test_Scan(
        self: TestFspCorrSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param config_file_name: JSON file for the configuration
        """
        # prepare device for observation
        assert self.device_online_and_on(device_under_test, event_tracer)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test happy path observing command sequence
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()
        
        attr_values = [
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.SCANNING, ObsState.READY, 1),
            ("obsState", ObsState.READY, ObsState.SCANNING, 1),
            ("obsState", ObsState.IDLE, ObsState.READY, 1),
        ]

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
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
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("FspCorrSubarray_ConfigureScan_basic.json", 1)],
    )
    def test_Scan_reconfigure(
        self: TestFspCorrSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test FspCorrSubarray's ability to reconfigure and run multiple scans.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param config_file_name: JSON file for the configuration
        :param scan_id: the scan id
        """
        # prepare device for observation
        assert self.device_online_and_on(device_under_test, event_tracer)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test happy path observing command sequence
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            # check that the queued command succeeded
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{return_value[1][0]}",
                    f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                ),
            )

        # second round of observation
        command_dict = {}
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["EndScan"] = device_under_test.EndScan()
        command_dict["GoToIdle"] = device_under_test.GoToIdle()
        
        attr_values = [
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.SCANNING, ObsState.READY, 1),
            ("obsState", ObsState.READY, ObsState.SCANNING, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.READY, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.SCANNING, ObsState.READY, 2),
            ("obsState", ObsState.READY, ObsState.SCANNING, 2),
            ("obsState", ObsState.IDLE, ObsState.READY, 1),
        ]

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ), None, 1
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )


    @pytest.mark.parametrize(
        "config_file_name",
        ["FspCorrSubarray_ConfigureScan_basic.json"],
    )
    def test_Abort_from_ready(
        self: TestFspCorrSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
    ) -> None:
        """
        Test a Abort from ObsState.READY.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param config_file_name: JSON file for the configuration
        """
        # prepare device for observation
        assert self.device_online_and_on(device_under_test, event_tracer)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test issuing Abort and ObsReset from READY
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Abort"] = device_under_test.Abort()
        command_dict["ObsReset"] = device_under_test.ObsReset()

        attr_values = [
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.ABORTING, ObsState.READY, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
        ]
        
        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ), None, 1
                )
            )
            
        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )


    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [("FspCorrSubarray_ConfigureScan_basic.json", 1)],
    )
    def test_Abort_from_scanning(
        self: TestFspCorrSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test a Abort from ObsState.SCANNING.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param config_file_name: JSON file for the configuration
        """
        # prepare device for observation
        assert self.device_online_and_on(device_under_test, event_tracer)

        # prepare input data
        with open(test_data_path + config_file_name) as f:
            json_str = f.read().replace("\n", "")

        # dict to store return code and unique IDs of queued commands
        command_dict = {}

        # test issuing Abort and ObsReset from SCANNING
        command_dict["ConfigureScan"] = device_under_test.ConfigureScan(
            json_str
        )
        command_dict["Scan"] = device_under_test.Scan(scan_id)
        command_dict["Abort"] = device_under_test.Abort()
        command_dict["ObsReset"] = device_under_test.ObsReset()
        
        attr_values = [
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ("obsState", ObsState.SCANNING, ObsState.READY, 1),
            ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
        ]

        # assertions for all issued LRC
        for command_name, return_value in command_dict.items():
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            attr_values.append(
                (
                    "longRunningCommandResult",
                    (
                        f"{return_value[1][0]}",
                        f'[{ResultCode.OK.value}, "{command_name} completed OK"]',
                    ), None, 1
                )
            )

        for name, value, previous, n in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.parametrize(
        "delay_model_file_name",
        ["/../../data/delaymodel_unit_test.json"],
    )
    def test_UpdateDelayModel(
        self: TestFspCorrSubarray,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        delay_model_file_name: str,
    ) -> None:
        """
        Test Fsp's UpdateDelayModel command

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param delay_model_file_name: JSON file for the delay model
        :param sub_id: the subarray id
        """
        assert self.device_online_and_on(device_under_test, event_tracer)

        # prepare input data
        with open(file_path + delay_model_file_name) as f:
            delay_model = f.read().replace("\n", "")

        # delay model should be empty string after initialization
        assert device_under_test.delayModel == ""

        result = device_under_test.UpdateDelayModel(delay_model)
        assert result == [
            [ResultCode.OK.value],
            ["UpdateDelayModel completed OK"],
        ]
        assert device_under_test.delayModel == delay_model
