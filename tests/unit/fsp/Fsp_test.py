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
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_control_model import AdminMode, ResultCode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevFailed, DevState

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.fsp.fsp_device import Fsp
from ska_mid_cbf_mcs.testing import context

# Disable garbage collection to prevent tests hanging
gc.disable()

file_path = os.path.dirname(os.path.abspath(__file__))


class TestFsp:
    """
    Test class for Fsp tests.
    """

    @pytest.fixture(name="test_context")
    def fsp_test_context(
        self: TestFsp, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        harness.add_device(
            device_name="mid_csp_cbf/fsp/01",
            device_class=Fsp,
            FspCorrSubarray=[
                "mid_csp_cbf/fspCorrSubarray/01_01",
                "mid_csp_cbf/fspCorrSubarray/01_02",
                "mid_csp_cbf/fspCorrSubarray/01_03",
            ],
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
        Test State

        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestFsp, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestFsp,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        command: str,
    ) -> None:
        """
        Test the On/Off/Standby commands

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param command: the command to test (one of On/Off/Standby)
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        change_event_callbacks["state"].assert_change_event(DevState.OFF)

        if command == "On":
            result = device_under_test.On()
            # assert state attribute was updated and command completed OK
            change_event_callbacks["state"].assert_change_event(DevState.ON)
            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{result[1][0]}",
                    f'[{ResultCode.OK.value}, "On completed OK"]',
                )
            )
        elif command == "Off":
            assert device_under_test.Off()[0][0] == ResultCode.REJECTED
        elif command == "Standby":
            assert device_under_test.Standby()[0][0] == ResultCode.REJECTED

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize("function_mode", [FspModes.CORR])
    def test_SetFunctionMode(
        self: TestFsp,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        function_mode: FspModes,
    ) -> None:
        """
        Test setting Fsp function mode.

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param function_mode: the function mode to be set
        """
        # SetFunctionMode not allowed if state is not ON
        with pytest.raises(
            DevFailed,
            match="Command SetFunctionMode not allowed when the device is in DISABLE state",
        ):
            device_under_test.SetFunctionMode(function_mode.name)

        # set device ONLINE and ON
        self.test_Power_Commands(
            change_event_callbacks, device_under_test, "On"
        )

        # test issuing SetFunctionMode from ON
        result = device_under_test.SetFunctionMode(function_mode.name)

        # check that the command was successfully queued
        assert result[0] == ResultCode.QUEUED
        # check that the queued command succeeded
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{result[1][0]}",
                f'[{ResultCode.OK.value}, "SetFunctionMode completed OK"]',
            )
        )
        # assert frequencyBand attribute updated
        change_event_callbacks["functionMode"].assert_change_event(
            function_mode.value
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

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
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        sub_ids: list[int],
    ) -> None:
        """
        Test adding subarray membership

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param sub_ids: list of subarray IDs to add
        """

        # set device ONLINE, ON and set function mode to CORR
        self.test_SetFunctionMode(
            change_event_callbacks, device_under_test, FspModes.CORR
        )

        sub_ids_added = []
        for sub_id in sub_ids:
            if len(device_under_test.subarrayMembership) == const.MAX_SUBARRAY:
                assert device_under_test.AddSubarrayMembership(sub_id) == [
                    [ResultCode.FAILED],
                    [
                        f"Fsp already assigned to the maximum number of subarrays ({const.MAX_SUBARRAY})"
                    ],
                ]
            elif sub_id - 1 not in range(const.MAX_SUBARRAY):
                assert device_under_test.AddSubarrayMembership(sub_id) == [
                    [ResultCode.FAILED],
                    [
                        f"Subarray {sub_id} invalid; must be in range [1, {const.MAX_SUBARRAY}]"
                    ],
                ]
            elif sub_id in device_under_test.subarrayMembership:
                assert device_under_test.AddSubarrayMembership(sub_id) == [
                    [ResultCode.FAILED],
                    [f"FSP already belongs to subarray {sub_id}"],
                ]
            else:
                assert device_under_test.AddSubarrayMembership(sub_id) == [
                    [ResultCode.OK],
                    ["AddSubarrayMembership completed OK"],
                ]
                # assert subarrayMembership attribute updated
                sub_ids_added.append(sub_id)
                change_event_callbacks[
                    "subarrayMembership"
                ].assert_change_event(sub_ids_added)

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    # @pytest.mark.parametrize("sub_ids", [[1, 2, 3]])
    # def test_RemoveSubarrayMembership(
    #     self: TestFsp,
    #     change_event_callbacks: MockTangoEventCallbackGroup,
    #     device_under_test: context.DeviceProxy,
    #     sub_ids: list[int],
    # ) -> None:
    #     """
    #     Test removing subarray membership

    #     :param change_event_callbacks: fixture that provides a
    #         :py:class:`MockTangoEventCallbackGroup` that is subscribed to
    #         pertinent attributes
    #     :param device_under_test: fixture that provides a proxy to the device
    #         under test, in a :py:class:`context.DeviceProxy`
    #     :param sub_ids: list of subarray IDs to remove
    #     """

    #     # set device ONLINE, ON, function mode to CORR and add subarray membership
    #     self.test_AddSubarrayMembership(
    #         change_event_callbacks, device_under_test, sub_ids
    #     )

    #     # test invalid subarray ID
    #     assert device_under_test.RemoveSubarrayMembership(0) == [
    #         [ResultCode.FAILED],
    #         ["FSP does not belong to subarray 0"],
    #     ]

    #     # test valid subarray IDs, assert subarrayMembership attribute updated
    #     sub_ids_remaining = sub_ids.copy()
    #     for sub_id in sub_ids:
    #         sub_ids_remaining.pop(0)
    #         result = device_under_test.RemoveSubarrayMembership(sub_id)
    #         assert result == [
    #             [ResultCode.OK],
    #             ["RemoveSubarrayMembership completed OK"],
    #         ]

    #         change_event_callbacks["subarrayMembership"].assert_change_event(
    #             sub_ids_remaining
    #         )

    #     # assert if any captured events have gone unaddressed
    #     change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "delay_model_file_name, \
        sub_id",
        [("/../../data/delaymodel_unit_test.json", 1)],
    )
    def test_UpdateDelayModel(
        self: TestFsp,
        change_event_callbacks: MockTangoEventCallbackGroup,
        device_under_test: context.DeviceProxy,
        delay_model_file_name: str,
        sub_id: int,
    ) -> None:
        """
        Test Fsp's UpdateDelayModel command

        :param change_event_callbacks: fixture that provides a
            :py:class:`MockTangoEventCallbackGroup` that is subscribed to
            pertinent attributes
        :param device_under_test: fixture that provides a proxy to the device
            under test, in a :py:class:`context.DeviceProxy`
        :param delay_model_file_name: JSON file for the delay model
        :param sub_id: the subarray id
        """
        # set device ONLINE, ON, function mode to CORR and add subarray membership
        self.test_AddSubarrayMembership(
            change_event_callbacks, device_under_test, [sub_id]
        )

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
