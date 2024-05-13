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

# Standard imports
import os
import time
from typing import Any, Iterator
from unittest.mock import Mock

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.talon_board.talon_board_device import TalonBoard
from ska_mid_cbf_mcs.testing import context

from ... import test_utils

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports

CONST_WAIT_TIME = 1


class TestTalonBoard:
    """
    Test class for TalonBoard tests.
    """

    @pytest.fixture(name="test_context")
    def talon_board_test_context(
        self: TestTalonBoard, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/talon_board/001",
            device_class=TalonBoard,
            TalonDxBoardAddress="192.168.8.1",
            InfluxDbPort="8086",
            InfluxDbOrg="ska",
            InfluxDbBucket="talon",
            InfluxDbAuthToken="ikIDRLicRaMxviUJRqyE8bKF1Y_sZnaHc9MkWZY92jxg1isNPIGCyLtaC8EjbOhsT_kTzjt12qenB4g7-UOrog==",
            Instance="talon1_test",       
            TalonDxSysIdAddress="talondx-001/ska-talondx-sysid-ds/sysid",
            TalonDx100GEthernetAddress="talondx-001/ska-talondx-100-gigabit-ethernet/100g_eth",      
            TalonStatusAddress="talondx-001/ska-talondx-status/status",
            HpsMasterAddress="talondx-001/hpsmaster/hps-1",
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestTalonBoard, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_StartupState(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

    def test_On(
        self: TestTalonBoard,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """
        Test the Off() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """

        self.test_StartupState(device_under_test)

        result_code, command_id = device_under_test.On()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "On completed OK"]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    # @pytest.mark.parametrize(
    #     "influx time too old",
    #     [
    #         ("subarrayID", "1"),
    #         (),
    #     ],
    # )
    def test_readWriteAttr(
        self: TestTalonBoard,
        # attr: Any,
        # expected_val: Any,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test the that all attr can be read/written correctly.
        """
        self.test_StartupState(device_under_test)
        
        # Private Attr 
        assert device_under_test.subarrayID == ""
        assert device_under_test.dishID == ""
        assert device_under_test.vccID == ""
        device_under_test.subarrayID = "1"
        device_under_test.dishID = "2"
        device_under_test.vccID = "3"
        assert device_under_test.subarrayID == "1"
        assert device_under_test.dishID == "2"
        assert device_under_test.vccID == "3"
        
        # All these values are read from mocked device attr
        # TalonStatus Attr
        assert device_under_test.ipAddr == "192.168.8.1"
        assert device_under_test.bitstreamVersion == "0.2.6"
        assert device_under_test.bitstreamChecksum == 0xBEEFBABE
        # TalonStatus Attr
        assert device_under_test.iopllLockedFault == False
        assert device_under_test.fsIopllLockedFault == False
        assert device_under_test.commsIopllLockedFault == False
        assert device_under_test.systemClkFault == False
        assert device_under_test.emifBlFault == False
        assert device_under_test.emifBrFault == False
        assert device_under_test.emifTrFault == False
        assert device_under_test.ethernet0PllFault == False
        assert device_under_test.ethernet1PllFault == False
        assert device_under_test.slimPllFault == False
        
        # All these values are read from InfluxDB
        assert device_under_test.fpgaDieTemperature == 32.0
        
        
        
        #     InfluxDbPort="8086",
        #     InfluxDbOrg="ska",
        #     InfluxDbBucket="talon",
        #     InfluxDbAuthToken="ikIDRLicRaMxviUJRqyE8bKF1Y_sZnaHc9MkWZY92jxg1isNPIGCyLtaC8EjbOhsT_kTzjt12qenB4g7-UOrog==",
        #     Instance="talon1_test",       
        #     TalonDxSysIdAddress="talondx-001/ska-talondx-sysid-ds/sysid",
        #     TalonDx100GEthernetAddress="talondx-001/ska-talondx-100-gigabit-ethernet/100g_eth",      
        #     TalonStatusAddress="talondx-001/ska-talondx-status/status",
        #     HpsMasterAddress="talondx-001/hpsmaster/hps-1",