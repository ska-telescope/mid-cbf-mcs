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
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

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
        """
        A fixture that creates a test context for the Fsp.

        :param initial_mocks: A dictionary of initial mocks for the Fsp.
        :return: A test context for the Fsp.
        """
        harness = context.ThreadedTestTangoContextManager()
        harness.add_device(
            device_name="mid_csp_cbf/fsp/01",
            device_class=Fsp,
            FspCorrSubarray=list(
                filter(
                    lambda item: "fspCorrSubarray" in item,
                    initial_mocks.keys(),
                )
            ),
            FspPstSubarray=list(
                filter(
                    lambda item: "fspPstSubarray" in item, initial_mocks.keys()
                )
            ),
            HpsFspControllerAddress="talondx-001/fsp-app/fsp-controller",
            HpsFspCorrControllerAddress="talondx-001/fsp-app/fsp-corr-controller",
            HpsFspPstControllerAddress="talondx-001/fsp-app/fsp-pst-controller",
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

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def device_online_and_on(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> bool:
        """
        Helper function to start up and turn on the DUT.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        """
        # Set a given device to AdminMode.ONLINE and DevState.ON
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

        return device_under_test.adminMode == AdminMode.ONLINE

    @pytest.mark.parametrize("function_mode", [FspModes.CORR, FspModes.PST_BF])
    def test_SetFunctionMode(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        function_mode: FspModes,
    ) -> None:
        """
        Test the SetFunctionMode() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param function_mode: the function mode to be set
        """
        # set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # test issuing SetFunctionMode from ON
        (return_value, command_id) = device_under_test.SetFunctionMode(
            function_mode.name
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        attr_values = [
            (
                "longRunningCommandResult",
                (
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "SetFunctionMode completed OK"]',
                ),
                None,
                1,
            ),
            ("functionMode", function_mode.value, None, 1),
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

    @pytest.mark.parametrize("function_mode", [FspModes.VLBI])
    def test_SetFunctionMode_invalid_function_mode(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        function_mode: FspModes,
    ) -> None:
        """
        Test the SetFunctionMode() with un-implemented function modes.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param function_mode: the function mode to be set
        """
        # set device ONLINE and ON
        self.device_online_and_on(device_under_test, event_tracer)

        # test issuing SetFunctionMode from ON
        (return_value, command_id) = device_under_test.SetFunctionMode(
            function_mode.name
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{ResultCode.FAILED.value}, "Failed to validate FSP function mode {function_mode.name}"]',
            ),
        )

    @pytest.mark.parametrize("function_mode", [FspModes.CORR, FspModes.PST_BF])
    def test_SetFunctionMode_not_allowed_from_off(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        function_mode: FspModes,
    ) -> None:
        """
        Test the SetFunctionMode() command before the DUT has been turned ON.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param function_mode: the function mode to be set
        """
        # SetFunctionMode not allowed if state is not ON
        (return_value, command_id) = device_under_test.SetFunctionMode(
            function_mode.name
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
            ),
        )

    @pytest.mark.parametrize("function_mode", [FspModes.CORR, FspModes.PST_BF])
    def test_SetFunctionMode_not_allowed_already_set(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        function_mode: FspModes,
    ) -> None:
        """
        Test the SetFunctionMode() command when the DUT's functionMode has already been set.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param function_mode: the function mode to be set
        """
        # Run test_AddSubarrayMembership() to call SetFunctionMode() the first time.
        self.test_AddSubarrayMembership(
            device_under_test=device_under_test,
            event_tracer=event_tracer,
            sub_ids=[1, 2, 3],
            fsp_mode=function_mode,
        )

        # test issuing SetFunctionMode on a previously set FSP
        (return_value, command_id) = device_under_test.SetFunctionMode(
            function_mode.name
        )

        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
            ),
        )

    @pytest.mark.parametrize(
        "fsp_mode",
        [FspModes.CORR, FspModes.PST_BF],
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
        fsp_mode: FspModes,
    ) -> None:
        """
        Test the AddSubarrayMembership() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param sub_ids: list of subarray IDs to add
        :param fsp_mode: FspMode to be set for the device
        """

        # set device ONLINE, ON and set function mode to CORR
        self.test_SetFunctionMode(device_under_test, event_tracer, fsp_mode)

        sub_ids_added = []
        for sub_id in sub_ids:
            if (
                (
                    len(device_under_test.subarrayMembership)
                    == const.MAX_SUBARRAY
                )
                or (sub_id - 1 not in range(const.MAX_SUBARRAY))
                or (sub_id in device_under_test.subarrayMembership)
            ):
                (
                    return_value,
                    command_id,
                ) = device_under_test.AddSubarrayMembership(sub_id)
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
                (
                    return_value,
                    command_id,
                ) = device_under_test.AddSubarrayMembership(sub_id)
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
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device_under_test,
                    attribute_name="subarrayMembership",
                    custom_matcher=lambda e: list(e.attribute_value)
                    == sub_ids_added,
                )

    def test_AddSubarrayMembership_not_allowed_from_idle_mode(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the AddSubarrayMembership() command before the functionMode has been set.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        """

        # set device ONLINE and ON, but do NOT set functionMode
        self.device_online_and_on(device_under_test, event_tracer)

        for sub_id in [1, 2, 3]:
            (
                return_value,
                command_id,
            ) = device_under_test.AddSubarrayMembership(sub_id)
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{command_id[0]}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
            )

    @pytest.mark.parametrize(
        "fsp_mode",
        [FspModes.CORR, FspModes.PST_BF],
    )
    @pytest.mark.parametrize("sub_ids", [[1, 2, 3]])
    def test_RemoveSubarrayMembership(
        self: TestFsp,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        sub_ids: list[int],
        fsp_mode: FspModes,
    ) -> None:
        """
        Test the RemoveSubarrayMembership() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param sub_ids: list of subarray IDs to remove
        :param fsp_mode: FspMode to be set for the device
        """

        # set device ONLINE, ON, function mode to CORR and add subarray membership
        self.test_AddSubarrayMembership(
            device_under_test, event_tracer, sub_ids, fsp_mode
        )

        # test invalid subarray ID
        (
            return_value,
            command_id,
        ) = device_under_test.RemoveSubarrayMembership(0)
        # check that the command was successfully queued
        assert return_value[0] == ResultCode.QUEUED

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{ResultCode.FAILED.value}, "FSP does not belong to subarray 0"]',
            ),
        )

        # test valid subarray IDs, assert subarrayMembership attribute updated
        sub_ids_remaining = sub_ids.copy()
        for sub_id in sub_ids:
            sub_ids_remaining.pop(0)
            (
                return_value,
                command_id,
            ) = device_under_test.RemoveSubarrayMembership(sub_id)
            # check that the command was successfully queued
            assert return_value[0] == ResultCode.QUEUED

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{command_id[0]}",
                    f'[{ResultCode.OK.value}, "RemoveSubarrayMembership completed OK"]',
                ),
            )

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="subarrayMembership",
                custom_matcher=lambda e: list(e.attribute_value)
                == sub_ids_remaining,
            )

        # assert functionMode attribute updated to IDLE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="functionMode",
            attribute_value=0,
        )
