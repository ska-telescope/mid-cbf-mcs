#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Fsp."""

from __future__ import annotations

import gc
from typing import Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, ResultCode, SimulationMode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from ska_tango_testing.integration import TangoEventTracer
from tango import DevFailed, DevState

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.fsp.fsp_device import Fsp

from ... import test_utils

# Disable garbage collection to prevent tests hanging
gc.disable()


class TestFsp:
    """
    Test class for FSP.
    """

    @pytest.fixture(name="test_context")
    def fsp_test_context(
        self: TestFsp, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/fsp/01",
            device_class=Fsp,
            FspCorrSubarray=list(initial_mocks.keys()),
            HpsFspControllerAddress="talondx-001/fsp-app/fsp-controller",
            HpsFspCorrControllerAddress="talondx-001/fsp-app/fsp-corr-controller",
            DeviceID="1",
        )
        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: A fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE


    def device_online_and_on(
        self: TestFsp,
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
        # Set a given device to AdminMode.ONLINE and DevState.ON
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

    @pytest.mark.parametrize("function_mode", [FspModes.CORR])
    def test_SetFunctionMode(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        function_mode: FspModes,
    ) -> None:
        """
        Test the SetFunctionMode() command's happy path.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param function_mode: the function mode to be set
        """
        # set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # test issuing SetFunctionMode from ON
        (return_value, command_id) = device_under_test.SetFunctionMode(function_mode.name)

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED
        
        attr_values = [
            ("longRunningCommandResult", 
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "SetFunctionMode completed OK"]',
                ), None, 1
            ),
            ("functionMode", function_mode.value, None, 1),

        ]

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
    
    @pytest.mark.parametrize("function_mode", [FspModes.CORR])
    def test_SetFunctionMode_not_allowed(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        function_mode: FspModes,
    ) -> None:
        """
        Test the SetFunctionMode() command's happy path.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param function_mode: the function mode to be set
        """
        # SetFunctionMode not allowed if state is not ON
        (return_value, command_id) = device_under_test.SetFunctionMode(function_mode.name)
        
        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).cbf_has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                    f"{command_id[0]}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
        )

    # parameterized with all possible subarray IDs, a duplicate ID and IDs below and above range
    @pytest.mark.parametrize(
        "sub_ids",
        [
            list(range(1, const.MAX_SUBARRAY + 1)),
            list(range(1, const.MAX_SUBARRAY + 1)) + [1],
            [0, 100, 1, 1],
        ],
    )
    def test_AddSubarrayMembership(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        sub_ids: list[int],
    ) -> None:
        """
        Test the AddSubarrayMembership() command's happy path.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param sub_ids: list of subarray IDs to add
        """

        # set device ONLINE, ON and set function mode to CORR
        self.test_SetFunctionMode(device_under_test, event_tracer, FspModes.CORR)

        sub_ids_added = []
        print(f"All SUB IDs: {sub_ids}")
        for sub_id in sub_ids:
            if ( 
                (len(device_under_test.subarrayMembership) == const.MAX_SUBARRAY) or
                (sub_id - 1 not in range(const.MAX_SUBARRAY)) or
                (sub_id in device_under_test.subarrayMembership)
            ):
                (return_value, command_id) = device_under_test.AddSubarrayMembership(sub_id)
                # check that the command was successfully queued
                assert return_value[0] == ResultCode.QUEUED
                
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device_under_test,
                    attribute_name="longRunningCommandResult",
                    attribute_value=(
                        f"{command_id[0]}",
                        f'[{ResultCode.FAILED.value}, "Unable to add subarray membership for subarray ID {sub_id}"]',
                    ),
                )
            else:
                (return_value, command_id) = device_under_test.AddSubarrayMembership(sub_id)
                # check that the command was successfully queued
                assert return_value[0] == ResultCode.QUEUED
                
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device_under_test,
                    attribute_name="longRunningCommandResult",
                    attribute_value=(
                        f"{command_id[0]}",
                        f'[{ResultCode.OK.value}, "AddSubarrayMembership completed OK"]',
                    ),
                )
                
                # assert subarrayMembership attribute updated
                sub_ids_added.append(sub_id)
                print(f"SUB IDs: {sub_ids_added}")
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device_under_test,
                    attribute_name="subarrayMembership",
                    attribute_value=sub_ids_added,
                )


    @pytest.mark.parametrize("sub_ids", [[1, 2, 3]])
    def test_RemoveSubarrayMembership(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        sub_ids: list[int],
    ) -> None:
        """
        Test the RemoveSubarryMembership() command's happy path.

        :param device_under_test: A fixture that provides a
            :py:class: `CbfDeviceProxy` to the device under test, in a
            :py:class:`context.DeviceProxy`.
        :param event_tracer: A :py:class:`TangoEventTracer` used to
            recieve subscribed change events from the device under test.
        :param sub_ids: list of subarray IDs to remove
        """

        # set device ONLINE, ON, function mode to CORR and add subarray membership
        self.test_AddSubarrayMembership(
            change_event_callbacks, device_under_test, sub_ids
        )

        # test invalid subarray ID
        assert device_under_test.RemoveSubarrayMembership(0) == [
            [ResultCode.FAILED],
            ["FSP does not belong to subarray 0"],
        ]

        # test valid subarray IDs, assert subarrayMembership attribute updated
        sub_ids_remaining = sub_ids.copy()
        for sub_id in sub_ids:
            sub_ids_remaining.pop(0)
            result = device_under_test.RemoveSubarrayMembership(sub_id)
            assert result == [
                [ResultCode.OK],
                ["RemoveSubarrayMembership completed OK"],
            ]

            change_event_callbacks["subarrayMembership"].assert_change_event(
                sub_ids_remaining
            )

        # assert functionMode attribute updated to IDLE
        change_event_callbacks["functionMode"].assert_change_event(0)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
