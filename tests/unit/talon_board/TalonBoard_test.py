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
        device_under_test.loggingLevel = 5
        # Device must be on in order to query InfluxDB
        self.test_Online(device_under_test, event_tracer)

        # Local Attr
        assert device_under_test.subarrayID == ""
        assert device_under_test.dishID == ""
        assert device_under_test.vccID == ""

        # This will generate change events for the locally defined attr.
        device_under_test.subarrayID = "1"
        device_under_test.dishID = "2"
        device_under_test.vccID = "3"

        # Since the device defaults to simulation mode, finding change events
        # with the values from the mocks (different from the simulator) will
        # confirm that change events are being generated properly.
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
            # From Ethernet Client
            (
                "eth100g0Counters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 4),
            ),
            (
                "eth100g0ErrorCounters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 6),
            ),
            (
                "eth100g0AllTxCounters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 27),
            ),
            (
                "eth100g0AllRxCounters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 27),
            ),
            ("eth100g0DataFlowActive", True, None),
            ("eth100g0HasDataError", True, None),
            (
                "eth100g1Counters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 4),
            ),
            (
                "eth100g1ErrorCounters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 6),
            ),
            (
                "eth100g1AllTxCounters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 27),
            ),
            (
                "eth100g1AllRxCounters",
                None,
                lambda e: (list(e.attribute_value) == [1] * 27),
            ),
            ("eth100g1DataFlowActive", True, None),
            ("eth100g1HasDataError", True, None),
            # From InfluxDB
            ("fpgaDieTemperature", 32.0, None),
            ("fpgaDieVoltage0", 12.1, None),
            ("fpgaDieVoltage1", 2.1, None),
            ("fpgaDieVoltage2", 0.7, None),
            ("fpgaDieVoltage3", 1.9, None),
            ("fpgaDieVoltage4", 1.9, None),
            ("fpgaDieVoltage5", 0.8, None),
            ("fpgaDieVoltage6", 1.9, None),
            ("humiditySensorTemperature", 32.0, None),
            (
                "dimmTemperatures",
                None,
                lambda e: (list(e.attribute_value) == [32.0] * 4),
            ),
            (
                "mboTxTemperatures",
                None,
                lambda e: (list(e.attribute_value) == [32.0] * 5),
            ),
            (
                "mboTxVccVoltages",
                None,
                lambda e: (list(e.attribute_value) == [3.1] * 5),
            ),
            (
                "mboTxFaultStatus",
                None,
                lambda e: (list(e.attribute_value) == [True] * 5),
            ),
            (
                "mboTxLolStatus",
                None,
                lambda e: (list(e.attribute_value) == [True] * 5),
            ),
            (
                "mboTxLosStatus",
                None,
                lambda e: (list(e.attribute_value) == [True] * 5),
            ),
            (
                "mboRxVccVoltages",
                None,
                lambda e: (list(e.attribute_value) == [3.1] * 5),
            ),
            (
                "mboRxLolStatus",
                None,
                lambda e: (list(e.attribute_value) == [True] * 5),
            ),
            (
                "mboRxLosStatus",
                None,
                lambda e: (list(e.attribute_value) == [True] * 5),
            ),
            ("hasFanControl", False, None),
            (
                "fansPwm",
                None,
                lambda e: (list(e.attribute_value) == [255] * 4),
            ),
            (
                "fansPwmEnable",
                None,
                lambda e: (list(e.attribute_value) == [0] * 4),
            ),
            (
                "fansRpm",
                None,
                lambda e: (list(e.attribute_value) == [0] * 4),
            ),
            (
                "fansFault",
                None,
                lambda e: (list(e.attribute_value) == [True] * 4),
            ),
            (
                "ltmInputVoltage",
                None,
                lambda e: (list(e.attribute_value) == [11.0] * 4),
            ),
            (
                "ltmOutputVoltage1",
                None,
                lambda e: (list(e.attribute_value) == [1.5] * 4),
            ),
            (
                "ltmOutputVoltage2",
                None,
                lambda e: (list(e.attribute_value) == [1.5] * 4),
            ),
            (
                "ltmInputCurrent",
                None,
                lambda e: (list(e.attribute_value) == [1.0] * 4),
            ),
            (
                "ltmOutputCurrent1",
                None,
                lambda e: (list(e.attribute_value) == [1.0] * 4),
            ),
            (
                "ltmOutputCurrent2",
                None,
                lambda e: (list(e.attribute_value) == [1.0] * 4),
            ),
            (
                "ltmTemperature1",
                None,
                lambda e: (list(e.attribute_value) == [32.0] * 4),
            ),
            (
                "ltmTemperature2",
                None,
                lambda e: (list(e.attribute_value) == [32.0] * 4),
            ),
            (
                "ltmVoltageWarning",
                None,
                lambda e: (list(e.attribute_value) == [True] * 4),
            ),
            (
                "ltmCurrentWarning",
                None,
                lambda e: (list(e.attribute_value) == [True] * 4),
            ),
            (
                "ltmTemperatureWarning",
                None,
                lambda e: (list(e.attribute_value) == [True] * 4),
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
