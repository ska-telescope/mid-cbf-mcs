#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for TalonBoard."""

from __future__ import annotations

import gc
import os
from typing import Any, Iterator
from unittest.mock import Mock

import pytest
from assertpy import assert_that
from ska_control_model import SimulationMode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.talon_board.talon_board_device import TalonBoard
from ska_mid_cbf_mcs.testing.mock.mock_dependency import MockDependency

from ... import test_utils

# Disable garbage collection to prevent tests hanging
gc.disable()

file_path = os.path.dirname(os.path.abspath(__file__))


class TestTalonBoard:
    """
    Test class for TalonBoard.
    """

    @pytest.fixture(name="test_context")
    def talon_board_test_context(
        self: TestTalonBoard,
        request: pytest.FixtureRequest,
        monkeymodule: pytest.MonkeyPatch,
        initial_mocks: dict[str, Mock],
    ) -> Iterator[context.ThreadedTestTangoContextManager._TangoContext]:
        """
        Fixture that creates a test context for the TalonBoard device.

        :param request: the pytest request object
        :param monkeymodule: the pytest monkeypatch object
        :param initial_mocks: A dictionary of device mocks to be added to the test context.
        :return: A test context for the TalonBoard device.
        """
        harness = context.ThreadedTestTangoContextManager()

        def mock_ping(self, **kwargs: Any) -> bool:
            """
            Replace requests.request method with a mock method.

            :param url: the URL
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.InfluxdbQueryClient(
                request.param["sim_ping_fault"],
            ).ping()

        def mock_do_queries(self) -> list[list]:
            """
            Replace requests.request method with a mock method.

            :param url: the URL
            :param kwargs: other keyword args

            :return: a response
            """
            return MockDependency.InfluxdbQueryClient().do_queries()

        monkeymodule.setattr(
            "ska_mid_cbf_mcs.talon_board.influxdb_query_client.InfluxdbQueryClient.ping",
            mock_ping,
        )
        monkeymodule.setattr(
            "ska_mid_cbf_mcs.talon_board.influxdb_query_client.InfluxdbQueryClient.do_queries",
            mock_do_queries,
        )

        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/talon_board/001",
            device_class=TalonBoard,
            TalonDxBoardAddress="192.168.8.1",
            InfluxDbPort="8086",
            InfluxDbOrg="ska",
            InfluxDbBucket="talon",
            InfluxDbAuthToken="test",
            Instance="talon1_test",
            TalonDxSysIdAddress=request.param["sim_sysid_property"],
            TalonDx100GEthernetAddress="talondx-001/ska-talondx-100-gigabit-ethernet/100g_eth",
            TalonStatusAddress="talondx-001/ska-talondx-status/status",
            HpsMasterAddress="talondx-001/hpsmaster/hps-1",
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock(name))

        with harness as test_context:
            yield test_context

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_State(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the State attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.State() == DevState.DISABLE

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_Status(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test the Status attribute just after device initialization.

        :param device_under_test: DeviceProxy to the device under test.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_adminMode(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
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
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            },
        ],
        indirect=True,
    )
    def test_Online(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test that the devState is appropriately set after device startup.

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

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_sysid_property": None,
            },
        ],
        indirect=True,
    )
    def test_Online_correct_state_when_missing_property(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test that the State attribute is appropriately set after device startup when there is a device property misisng form charts.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
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
            attribute_value=DevState.DISABLE,
        )

    @pytest.mark.parametrize(
        "test_context",
        [
            {
                "sim_ping_fault": False,
                "sim_sysid_property": "talondx-001/ska-talondx-sysid-ds/sysid",
            }
        ],
        indirect=True,
    )
    def test_ReadWriteAttributes(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the that all attributes can be read/written correctly.

        :param device_under_test: DeviceProxy to the device under test.
        :param event_tracer: A TangoEventTracer used to recieve subscribed change
                             events from the device under test.
        """
        # device_under_test.loggingLevel = 5
        # Device must be on in order to query InfluxDB
        self.test_Online(device_under_test, event_tracer)

        # Local Attr
        assert device_under_test.subarrayID == ""
        assert device_under_test.dishID == ""
        assert device_under_test.vccID == ""
        device_under_test.subarrayID = "1"
        device_under_test.dishID = "2"
        device_under_test.vccID = "3"

        attr_values = [
            # From device props
            ("subarrayID", "1", None),
            ("dishID", "2", None),
            ("vccID", "3", None),
            # From TalonSysId attr
            ("bitstreamVersion", "0.2.6", None),
            ("bitstreamChecksum", 0xBEEFBABE, None),
            # From TalonStatus attr
            ("iopllLockedFault", False, None),
            ("fsIopllLockedFault", False, None),
            ("commsIopllLockedFault", False, None),
            ("systemClkFault", False, None),
            ("emifBlFault", False, None),
            ("emifBrFault", False, None),
            ("emifTrFault", False, None),
            ("ethernet0PllFault", False, None),
            ("ethernet1PllFault", False, None),
            ("slimPllFault", False, None),
            # From InfluxDB
            ("fpgaDieTemperature", 32.0, None),
            ("fpgaDieVoltage0", 12.0, None),
            ("fpgaDieVoltage1", 2.5, None),
            ("fpgaDieVoltage2", 0.8, None),
            ("fpgaDieVoltage3", 1.8, None),
            ("fpgaDieVoltage4", 1.8, None),
            ("fpgaDieVoltage5", 0.9, None),
            ("fpgaDieVoltage6", 1.8, None),
            ("humiditySensorTemperature", 32.0, None),
            (
                "dimmTemperatures",
                None,
                lambda e: (idx == 32.0 for idx in e.attribute_value),
            ),
            (
                "mboTxTemperatures",
                None,
                lambda e: (idx == 32.0 for idx in e.attribute_value),
            ),
            (
                "mboTxVccVoltages",
                None,
                lambda e: (idx == 3.3 for idx in e.attribute_value),
            ),
            (
                "mboTxFaultStatus",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "mboTxLolStatus",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "mboTxLosStatus",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "mboRxVccVoltages",
                None,
                lambda e: (idx == 3.3 for idx in e.attribute_value),
            ),
            (
                "mboRxLolStatus",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "mboRxLosStatus",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            ("hasFanControl", True, None),
            (
                "fansPwm",
                None,
                lambda e: (idx == 255 for idx in e.attribute_value),
            ),
            (
                "fansPwmEnable",
                None,
                lambda e: (idx == 1 for idx in e.attribute_value),
            ),
            (
                "fansRpm",
                None,
                lambda e: (idx == 100 for idx in e.attribute_value),
            ),
            (
                "fansFault",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "ltmInputVoltage",
                None,
                lambda e: (idx == 12.0 for idx in e.attribute_value),
            ),
            (
                "ltmOutputVoltage1",
                None,
                lambda e: (idx == 1.5 for idx in e.attribute_value),
            ),
            (
                "ltmOutputVoltage2",
                None,
                lambda e: (idx == 1.5 for idx in e.attribute_value),
            ),
            (
                "ltmInputCurrent",
                None,
                lambda e: (idx == 1.0 for idx in e.attribute_value),
            ),
            (
                "ltmOutputCurrent1",
                None,
                lambda e: (idx == 1.0 for idx in e.attribute_value),
            ),
            (
                "ltmOutputCurrent2",
                None,
                lambda e: (idx == 1.0 for idx in e.attribute_value),
            ),
            (
                "ltmTemperature1",
                None,
                lambda e: (idx == 32.0 for idx in e.attribute_value),
            ),
            (
                "ltmTemperature2",
                None,
                lambda e: (idx == 32.0 for idx in e.attribute_value),
            ),
            (
                "ltmVoltageWarning",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "ltmCurrentWarning",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
            (
                "ltmTemperatureWarning",
                None,
                lambda e: (idx is False for idx in e.attribute_value),
            ),
        ]

        for name, value, custom in attr_values:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device_under_test,
                attribute_name=name,
                attribute_value=value,
                custom_matcher=custom,
            )
