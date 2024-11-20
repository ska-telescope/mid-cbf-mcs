# @pytest.fixture() - indicates helper for testing
# fixture for mock component manager
# fixture to patch fixture
# fixture to mock external proxies

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import unittest
from typing import Generator

import pytest
import tango
from ska_tango_testing import context
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the DeviceProxy for the device under test
    """
    return test_context.get_device("mid_csp_cbf/talon_board/001")


@pytest.fixture(name="event_tracer", autouse=True)
def tango_event_tracer(
    device_under_test: context.DeviceProxy,
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :param device_under_test: the DeviceProxy for the device under test
    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    change_event_attr_list = [
        "longRunningCommandResult",
        "subarrayID",
        "dishID",
        "vccID",
        "pingResult",
        "bitstreamVersion",
        "bitstreamChecksum",
        "adminMode",
        "state",
    ]
    for attr in change_event_attr_list:
        tracer.subscribe_event(device_under_test, attr)

    return tracer


@pytest.fixture()
def monkeymodule():
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture()
def mock_talon_sysid() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("version", "0.2.6")
    builder.add_attribute("Bitstream", 0xBEEFBABE)
    return builder


@pytest.fixture()
def mock_ethernet_100g() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    return builder


@pytest.fixture()
def mock_talon_status() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("iopll_locked_fault", False)
    builder.add_attribute("fs_iopll_locked_fault", False)
    builder.add_attribute("comms_iopll_locked_fault", False)
    builder.add_attribute("system_clk_fault", False)
    builder.add_attribute("emif_bl_fault", False)
    builder.add_attribute("emif_br_fault", False)
    builder.add_attribute("emif_tr_fault", False)
    builder.add_attribute("e100g_0_pll_fault", False)
    builder.add_attribute("e100g_1_pll_fault", False)
    builder.add_attribute("slim_pll_fault", False)
    return builder


@pytest.fixture()
def mock_hps_master() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    return builder


@pytest.fixture()
def initial_mocks(
    mock_talon_sysid: unittest.mock.Mock,
    mock_ethernet_100g: unittest.mock.Mock,
    mock_talon_status: unittest.mock.Mock,
    mock_hps_master: unittest.mock.Mock,
) -> dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_talon_sysid: mock for talon sysid device
    :param mock_ethernet_100g: mock for talon 100g ethernet device
    :param mock_talon_status: mock for talon status device
    :param mock_hps_master: mock for hps master device
    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "talondx-001/ska-talondx-sysid-ds/sysid": mock_talon_sysid,
        "talondx-001/ska-talondx-100-gigabit-ethernet/100g_eth_0": mock_ethernet_100g,
        "talondx-001/ska-talondx-100-gigabit-ethernet/100g_eth_1": mock_ethernet_100g,
        "talondx-001/ska-talondx-status/status": mock_talon_status,
        "talondx-001/hpsmaster/hps-1": mock_hps_master,
    }
