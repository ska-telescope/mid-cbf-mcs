#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Slim."""

from __future__ import annotations

import gc
import os
from typing import Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevFailed, DevState

from ska_mid_cbf_mcs.slim.slim_device import Slim

from ... import test_utils

# Disable garbage collection to prevent tests hanging
gc.disable()

# Path
file_path = os.path.dirname(os.path.abspath(__file__))


class TestSlim:
    """
    Test class for SLIM.
    """

    @pytest.fixture(name="test_context")
    def slim_test_context(
        self: TestSlim,
        initial_mocks: dict[str, Mock],
        # initial_links: dict[str, Mock],
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that creates a test context for the Slim tests.

        :param initial_mocks: A dictionary of initial mocks to be added to the test context.
        :return: A test context for the Slim tests.
        """
        harness = context.ThreadedTestTangoContextManager()
        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/slim/001",
            device_class=Slim,
            Links=[
                "mid_csp_cbf/slim_link/001",
                "mid_csp_cbf/slim_link/002",
                "mid_csp_cbf/slim_link/003",
                "mid_csp_cbf/slim_link/004",
            ],
        )
        # This device uses SlimLink mocks that will return ResultCode.FAILED
        harness.add_device(
            device_name="mid_csp_cbf/slim_fail/001",
            device_class=Slim,
            Links=[
                "mid_csp_cbf/slim_link_fail/001",
                "mid_csp_cbf/slim_link_fail/002",
                "mid_csp_cbf/slim_link_fail/003",
                "mid_csp_cbf/slim_link_fail/004",
            ],
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock(name))

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the adminMode attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_On(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the On() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        """
        # prepare device
        device_under_test.adminMode = AdminMode.ONLINE
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=(DevState.OFF),
        )

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "On completed OK"]',
            ),
        )
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.ON,
        )

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [
            ("./tests/data/slim_test_config.yaml"),
            ("./tests/data/slim_test_config_inactive.yaml"),
        ],
    )
    def test_Configure(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """
        assert test_utils.device_online_and_on(device_under_test, event_tracer)

        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test.Configure(
                mesh_config.read()
            )
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "Configure completed OK"]',
            ),
        )

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_fail_config.yaml")],
    )
    def test_Configure_too_many_links(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command when the configuration contains more links than there are SlimLink mocks.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """
        device_under_test.simulationMode = SimulationMode.FALSE
        assert test_utils.device_online_and_on(device_under_test, event_tracer)

        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test.Configure(
                mesh_config.read()
            )

        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[3, "Too many links defined in the link configuration. Not enough SlimLink devices exist."]',
            ),
        )

    @pytest.mark.skip(reason="Skipping test involving nested LRC")
    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_Configure_slim_link_init_fails(
        self: TestSlim,
        device_under_test_fail: context.DeviceProxy,
        event_tracer_fail: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command using SlimLink mocks set to reject the nested ConnectTxRx call.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """
        assert test_utils.device_online_and_on(
            device_under_test_fail, event_tracer_fail
        )

        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test_fail.Configure(
                mesh_config.read()
            )

        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer_fail).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test_fail,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[3, "Nested LRC SlimLink.ConnectTxRx() rejected"]',
            ),
        )

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_Configure_not_allowed(
        self: TestSlim,
        device_under_test_fail: context.DeviceProxy,
        event_tracer_fail: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command before Slim has started up.

        :param device_under_test_fail: DeviceProxy to the device under test for failure conditions.
        :param event_tracer_fail: A TangoEventTracer used to receive subscribed change
                                  events from the device under test, for failure conditions.
        :param mesh_config_filename: A JSON file for the configuration.
        """
        device_under_test_fail.adminMode = AdminMode.OFFLINE

        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test_fail.Configure(
                mesh_config.read()
            )
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer_fail).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test_fail,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    @pytest.mark.skip(reason="Skipping test involving nested LRC")
    @pytest.mark.parametrize(
        "mesh_config_filename",
        [
            ("./tests/data/slim_test_config.yaml"),
            ("./tests/data/slim_test_config_inactive.yaml"),
        ],
    )
    def test_Off(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Off() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """

        self.test_Configure(
            device_under_test, event_tracer, mesh_config_filename
        )

        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "Off completed OK"]',
            ),
        )
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.OFF,
        )

    @pytest.mark.skip(reason="Skipping test involving nested LRC")
    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_Off_not_allowed(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Off() command when Slim has gone offline after configuring.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """

        self.test_Configure(
            device_under_test, event_tracer, mesh_config_filename
        )

        device_under_test.adminMode = AdminMode.OFFLINE
        with pytest.raises(
            DevFailed, match="Communication with component is not established"
        ):
            device_under_test.Off()

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_Off_already_off(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Off() command when it is already off.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """
        self.test_Configure(
            device_under_test, event_tracer, mesh_config_filename
        )

        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[0, "Off completed OK"]',
            ),
        )
        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="state",
            attribute_value=DevState.OFF,
        )

        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=device_under_test,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                '[6, "Command is not allowed"]',
            ),
        )

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_SlimTest(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the SlimTest() command's happy path.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """

        self.test_Configure(
            device_under_test, event_tracer, mesh_config_filename
        )

        result_code, message = device_under_test.SlimTest()
        assert result_code == ResultCode.OK, message

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config_inactive.yaml")],
    )
    def test_SlimTest_no_active_links(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the SlimTest() command when the configuration does not activate any links.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to receive subscribed change
                             events from the device under test.
        :param mesh_config_filename: A JSON file for the configuration.
        """

        self.test_Configure(
            device_under_test, event_tracer, mesh_config_filename
        )

        result_code, message = device_under_test.SlimTest()
        assert result_code == ResultCode.REJECTED, message

    def test_SlimTest_links_unconfigured(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test the SlimTest() command before Slim has been started up or configured.

        :param device_under_test: DeviceProxy to the device under test.
        """
        result_code, message = device_under_test.SlimTest()
        assert result_code == ResultCode.REJECTED, message
