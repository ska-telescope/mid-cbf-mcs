#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the power switch device."""

from __future__ import annotations

import gc
from typing import Any, Iterator

import pytest
from ska_control_model import AdminMode, SimulationMode

# Standard imports
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevFailed, DevState

from ska_mid_cbf_mcs.commons.global_enum import Const
from ska_mid_cbf_mcs.power_switch.power_switch_device import PowerSwitch
from ska_mid_cbf_mcs.testing.mock.mock_dependency import MockDependency

# To prevent tests hanging during gc.
gc.disable()


# Local imports
class TestPowerSwitch:
    """
    Test class for PowerSwitch tests.
    """

    power_switch_driver_model = None

    @pytest.fixture(
        name="test_context",
        params=[
            {"power_switch_model": "DLI_PRO"},
            {"power_switch_model": "APC_SNMP"},
        ],
    )
    def power_switch_test_context(
        self: TestPowerSwitch,
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        harness = context.ThreadedTestTangoContextManager()

        def mock_patch(url: str, **kwargs: Any) -> MockDependency.Response:
            """
            Replace requests.request method with a mock method.

            :param url: the URL
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.Response(
                url,
                request.param["sim_patch_error"],
                request.param["sim_state"],
            )

        def mock_get(
            url: str, params: Any = None, **kwargs: Any
        ) -> MockDependency.Response:
            """
            Replace requests.get with mock method.

            :param url: the URL
            :param params: arguments to the GET
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.Response(
                url, request.param["sim_get_error"], request.param["sim_state"]
            )

        def mock_get_snmp(
            authData, transportTarget, *varNames, **kwargs
        ) -> tuple:
            """
            Replace pysnmp...CommandGenerator.getCmd with mock method.

            :param self, authData, transportTarget, *varNames: arguments to the GET
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.ResponseSNMP(
                request.param["sim_get_error"],
                request.param["sim_state"],
            )

        def mock_set_snmp(
            authData, transportTarget, *varNames, **kwargs
        ) -> tuple:
            """
            Replace pysnmp...CommandGenerator.getCmd with mock method.

            :param params: arguments to the GET
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.ResponseSNMP(
                request.param["sim_patch_error"],
                request.param["sim_state"],
            )

        # Monkeypatches for patch, get, and set commands
        monkeypatch.setattr("requests.patch", mock_patch)
        monkeypatch.setattr("requests.get", mock_get)
        monkeypatch.setattr(
            "pysnmp.entity.rfc3413.oneliner.cmdgen.CommandGenerator.getCmd",
            mock_get_snmp,
        )
        monkeypatch.setattr(
            "pysnmp.entity.rfc3413.oneliner.cmdgen.CommandGenerator.setCmd",
            mock_set_snmp,
        )

        if request.param["power_switch_model"] == "DLI_PRO":
            harness.add_device(
                device_name="mid_csp_cbf/power_switch/001",
                device_class=PowerSwitch,
                PowerSwitchIp="192.168.0.100",
                PowerSwitchLogin="admin",
                PowerSwitchModel="DLI LPC9",
                PowerSwitchPassword="1234",
            )
        elif request.param["power_switch_model"] == "APC_SNMP":
            harness.add_device(
                device_name="mid_csp_cbf/power_switch/001",
                device_class=PowerSwitch,
                PowerSwitchIp="192.168.1.253",
                PowerSwitchModel="APC AP8681 SNMP",
                PowerSwitchLogin="apc",
                PowerSwitchPassword="apc",
            )
        self.power_switch_driver_model = request.param["power_switch_model"]

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_adminModeOnline(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_isCommunicating(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Tests that the device can respond to requests when the power
        switch is communicating.
        """
        # Take device out of simulation mode
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE

        # Check that the device is communicating
        assert device_under_test.isCommunicating

        # Check that numOutlets is the same as the driver
        assert device_under_test.numOutlets == Const.POWER_SWITCH_OUTLETS

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": True,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": True,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_get_request_failure(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Tests that a GET request failure is appropriately handled.
        """
        # Take device out of simulation mode
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE

        # Check that the device is not communicating
        assert device_under_test.isCommunicating is False

        # Check that numOutlets is 0 since we cannot talk to the power switch
        assert device_under_test.numOutlets == 0

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": True,
                "sim_get_error": False,
                "sim_state": None,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": True,
                "sim_get_error": False,
                "sim_state": None,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_patch_request_failure(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests that a PATCH request failure is appropriately handled.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS
        if self.power_switch_driver_model == "DLI_PRO":
            msg = '[3, "HTTP response error"]'
        elif self.power_switch_driver_model == "APC_SNMP":
            msg = '[3, "Connection error: "]'
        # Attempt to turn outlets off
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOffOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event((f"{command_id[0]}", msg))

        # Attempt to turn outlets on
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOnOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event((f"{command_id[0]}", msg))

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOffOutlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests that the outlets can be turned off individually.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS

        # Turn outlets off and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOffOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "TurnOffOutlet completed OK"]')
            )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOffOutlet_not_allowed(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests that the outlets can not be turned off if power switch is not communicating.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.adminMode == AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE

        with pytest.raises(
            DevFailed, match="Communication with component is not established"
        ):
            device_under_test.TurnOffOutlet("0")

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOffOutlet_outlet_stays_on(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests the failure response when outlets are not turned off as instructed.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS

        # Turn outlets off and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOffOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[3, "Outlet {i} failed to power off after sleep."]',
                )
            )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOffOutlet_invalid_outlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests the failure response when an invalid outlet is requested to be turned off.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS

        result_code, command_id = device_under_test.TurnOffOutlet(
            f"{num_outlets + 1}"
        )
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f"Outlet ID {num_outlets+1} must be in the allowable outlet_id_list",
            )
        )

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[3, "TurnOffOutlet FAILED"]')
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests that the outlets can be turned on individually.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS

        # Turn outlets on and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOnOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (f"{command_id[0]}", '[0, "TurnOnOutlet completed OK"]')
            )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet_not_allowed(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests that the outlets can not be turned on if power switch is not communicating.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.adminMode == AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE

        with pytest.raises(
            DevFailed, match="Communication with component is not established"
        ):
            device_under_test.TurnOnOutlet("0")

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet_outlet_stays_off(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests the failure response when outlets are not turned on as instructed.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS

        # Turn outlets on and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOnOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            change_event_callbacks[
                "longRunningCommandResult"
            ].assert_change_event(
                (
                    f"{command_id[0]}",
                    f'[3, "Outlet {str(i)} failed to power on after sleep."]',
                )
            )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "DLI_PRO",
            },
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
                "power_switch_model": "APC_SNMP",
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet_invalid_outlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Tests the failure response when an invalid outlet is requested to be turned on.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.ON

        num_outlets = device_under_test.numOutlets
        assert num_outlets == Const.POWER_SWITCH_OUTLETS

        result_code, command_id = device_under_test.TurnOnOutlet(
            str(num_outlets + 1)
        )
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                f"Outlet ID {num_outlets+1} must be in the allowable outlet_id_list",
            )
        )

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (f"{command_id[0]}", '[3, "TurnOnOutlet FAILED"]')
        )

        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
