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
import logging
from typing import Iterator

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import (
    get_power_switch_driver,
)
from ska_mid_cbf_mcs.power_switch.power_switch_device import PowerSwitch
from ska_mid_cbf_mcs.testing.mock.mock_dependency import MockDependency

from ... import test_utils

# Disable garbage collection to prevent tests hanging
gc.disable()


class TestPowerSwitch:
    """
    Test class for PowerSwitch.
    """

    power_switch_driver_model = None
    power_switch_outlets = 0

    @pytest.fixture(name="test_context")
    def power_switch_test_context(
        self: TestPowerSwitch,
        request: pytest.FixtureRequest,
        power_switch_model: str,
        monkeymodule: pytest.MonkeyPatch,
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that provides a test context for the PowerSwitch device.

        :param request: the pytest request object
        :param power_switch_model: the power switch model
        :param monkeymodule: the monkeypatch fixture
        :return: a test context for the PowerSwitch device
        """
        harness = context.ThreadedTestTangoContextManager()

        def mock_patch(url: str, **kwargs: any) -> MockDependency.Response:
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
            url: str, params: any = None, **kwargs: any
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
            return MockDependency.ResponseSNMP.do(
                self,
                request.param["sim_get_error"],
                request.param["sim_state"],
            )

        def mock_set_snmp(
            authData, transportTarget, *varNames, **kwargs
        ) -> tuple:
            """
            Replace pysnmp...CommandGenerator.setCmd with mock method.

            :param params: arguments to the SET
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.ResponseSNMP.do(
                self,
                request.param["sim_patch_error"],
                request.param["sim_state"],
            )

        # Monkeypatches for patch, get, and set commands
        monkeymodule.setattr("requests.patch", mock_patch)
        monkeymodule.setattr("requests.get", mock_get)
        monkeymodule.setattr(
            "pysnmp.entity.rfc3413.oneliner.cmdgen.CommandGenerator.getCmd",
            mock_get_snmp,
        )
        monkeymodule.setattr(
            "pysnmp.entity.rfc3413.oneliner.cmdgen.CommandGenerator.setCmd",
            mock_set_snmp,
        )

        # TODO: test other drivers
        if power_switch_model == "DLI_PRO":
            self.power_switch_outlets = get_power_switch_driver(
                model="DLI LPC9",
                ip="192.168.0.100",
                login="admin",
                password="1234",
                logger=logging.getLogger(),
            ).power_switch_outlets

            harness.add_device(
                device_name="mid_csp_cbf/power_switch/001",
                device_class=PowerSwitch,
                PowerSwitchIp="192.168.0.100",
                PowerSwitchLogin="admin",
                PowerSwitchModel="DLI LPC9",
                PowerSwitchPassword="1234",
            )

        elif power_switch_model == "APC_SNMP":
            self.power_switch_outlets = get_power_switch_driver(
                model="APC AP8681 SNMP",
                ip="192.168.1.253",
                login="apc",
                password="apc",
                logger=logging.getLogger(),
            ).power_switch_outlets

            harness.add_device(
                device_name="mid_csp_cbf/power_switch/001",
                device_class=PowerSwitch,
                PowerSwitchIp="192.168.1.253",
                PowerSwitchModel="APC AP8681 SNMP",
                PowerSwitchLogin="apc",
                PowerSwitchPassword="apc",
            )
        self.power_switch_driver_model = power_switch_model

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestPowerSwitch, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
            },
        ],
        indirect=True,
    )
    def test_Online(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test that the device is in the proper state after startup,
        and that the power switch driver has been initialized
        (indicated by the numOutlets value).

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE

        # Set device to AdminMode.ONLINE and DevState.ON
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

        assert device_under_test.adminMode == AdminMode.ONLINE

        # Check that numOutlets is the same as the driver
        return device_under_test.numOutlets == self.power_switch_outlets

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
            },
        ],
        indirect=True,
    )
    def test_isCommunicating(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the PowerSwitch's isCommunicating attr, which
        makes an API call to the PDU to verify connection.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        # Check that the device is communicating
        assert device_under_test.isCommunicating

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": True,
                "sim_state": False,
            },
        ],
        indirect=True,
    )
    def test_get_request_failure(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests that a GET request failure is appropriately handled.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE

        # Set device to AdminMode.ONLINE and DevState.ON
        device_under_test.adminMode = AdminMode.ONLINE

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.UNKNOWN,
        )

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
            },
        ],
        indirect=True,
    )
    def test_patch_request_failure(
        self: TestPowerSwitch,
        power_switch_model: str,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests that a PATCH request failure is appropriately handled.

        :param power_switch_model: Informs the test for which driver's responses to expect.
        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.power_switch_driver_model = power_switch_model
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets
        if self.power_switch_driver_model == "DLI_PRO":
            msg = '[3, "HTTP response error"]'
        elif self.power_switch_driver_model == "APC_SNMP":
            msg = '[3, "Connection error: "]'
        # Attempt to turn outlets off
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOffOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="lrcFinished",
                attribute_value=(f"{command_id[0]}", msg),
            )

        # Attempt to turn outlets on
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOnOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="lrcFinished",
                attribute_value=(f"{command_id[0]}", msg),
            )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
            }
        ],
        indirect=True,
    )
    def test_TurnOffOutlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOffOutlet() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets

        # Turn outlets off and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOffOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="lrcFinished",
                attribute_value=(
                    f"{command_id[0]}",
                    '[0, "TurnOffOutlet completed OK"]',
                ),
            )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
            },
        ],
        indirect=True,
    )
    def test_TurnOffOutlet_not_allowed(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOffOutlet() command when the power switch is not communicating.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.adminMode == AdminMode.OFFLINE

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.DISABLE,
        )

        result_code, command_id = device_under_test.TurnOffOutlet("0")
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="lrcFinished",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
            }
        ],
        indirect=True,
    )
    def test_TurnOffOutlet_outlet_stays_on(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOffOutlet() command when outlets do not turn off as instructed.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets

        # Turn outlets off and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOffOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="lrcFinished",
                attribute_value=(
                    f"{command_id[0]}",
                    f'[3, "Outlet {i} failed to power off after sleep."]',
                ),
            )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
            },
        ],
        indirect=True,
    )
    def test_TurnOffOutlet_invalid_outlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOffOutlet() command when an invalid outlet is provided.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets

        result_code, command_id = device_under_test.TurnOffOutlet(
            f"{num_outlets + 1}"
        )
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="lrcFinished",
            attribute_value=(
                f"{command_id[0]}",
                '[3, "TurnOffOutlet FAILED"]',
            ),
        )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": True,
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOnOutlet() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets

        # Turn outlets on and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOnOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="lrcFinished",
                attribute_value=(
                    f"{command_id[0]}",
                    '[0, "TurnOnOutlet completed OK"]',
                ),
            )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet_not_allowed(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOnOutlet() command when the power switch is not communicating.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        device_under_test.simulationMode = SimulationMode.FALSE

        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.adminMode == AdminMode.OFFLINE

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.DISABLE,
        )

        result_code, command_id = device_under_test.TurnOnOutlet("0")

        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="lrcFinished",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet_outlet_stays_off(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOnOutlet() command when outlets do not turn on as instructed.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets

        # Turn outlets on and check the state again
        for i in range(1, 8):
            result_code, command_id = device_under_test.TurnOnOutlet(f"{i}")
            assert result_code == [ResultCode.QUEUED]

            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name="lrcFinished",
                attribute_value=(
                    f"{command_id[0]}",
                    f'[3, "Outlet {str(i)} failed to power on after sleep."]',
                ),
            )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_patch_error": False,
                "sim_get_error": False,
                "sim_state": False,
            },
        ],
        indirect=True,
    )
    def test_TurnOnOutlet_invalid_outlet(
        self: TestPowerSwitch,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Tests the TurnOnOutlet() command when an invalid outlet is provided.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        self.test_Online(device_under_test, event_tracer)

        num_outlets = device_under_test.numOutlets
        assert num_outlets == self.power_switch_outlets

        result_code, command_id = device_under_test.TurnOnOutlet(
            str(num_outlets + 1)
        )
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="lrcFinished",
            attribute_value=(
                f"{command_id[0]}",
                '[3, "TurnOnOutlet FAILED"]',
            ),
        )
