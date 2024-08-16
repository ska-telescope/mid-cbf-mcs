# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS VCC integration tests."""

from __future__ import annotations

import pytest

# Tango imports
from ska_control_model import SimulationMode
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ... import test_utils


@pytest.fixture(name="device_under_test")
def device_under_test_fixture() -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :return: the device under test
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/vcc/001")


@pytest.fixture(name="test_proxies")
def test_proxies_fixture() -> pytest.fixture:
    """
    Fixture that returns the device proxies required for this scope.

    :return: a TestProxies object containing device proxies to all devices required in this module's scope of integration testing
    """

    class TestProxies:
        def __init__(self: TestProxies) -> None:
            """
            Initialize all device proxies needed for integration testing the DUT.

            Includes:
            - 4 TalonLru
            - 2 PowerSwitch
            """

            # Talon LRU
            self.talon_lru = []
            for i in range(1, 5):  # 4 Talon LRUs for now
                self.talon_lru.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/talon_lru/{i:03}",
                    )
                )

            # Power switch
            self.power_switch = []
            for i in (1, 2):  # 2 Power Switches
                self.power_switch.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/power_switch/{i:03}",
                    )
                )

            # Set all proxies used in this test suite to simMode.TRUE
            for proxy in self.talon_lru + self.power_switch:
                proxy.simulationMode = SimulationMode.TRUE

    return TestProxies()


@pytest.fixture(name="change_event_callbacks")
def vcc_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    """
    Fixture that returns the device under test's change event callback group.

    :param device_under_test: the device whose change events will be subscribed to.
    :return: the change event callback object
    """
    change_event_attr_list = ["longRunningCommandResult", "obsState", "State"]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=60.0
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture(name="lru_change_event_callbacks")
def lru_change_event_callbacks(
    test_proxies: pytest.fixture,
) -> MockTangoEventCallbackGroup:
    """
    Fixture that returns the TalonLru's change event callback group.

    :param test_proxies: the device proxies used in this scope.
    :return: the change event callback object for TalonLru devices
    """
    change_event_attr_list = ["longRunningCommandResult", "State"]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    for lru in test_proxies.talon_lru:
        test_utils.change_event_subscriber(
            lru, change_event_attr_list, change_event_callbacks
        )
    return change_event_callbacks


@pytest.fixture(name="ps_change_event_callbacks")
def ps_change_event_callbacks(
    test_proxies: pytest.fixture,
) -> MockTangoEventCallbackGroup:
    """
    Fixture that returns the PowerSwitch's change event callback group.

    :param test_proxies: the device proxies used in this scope.
    :return: the change event callback object for PowerSwitch devices
    """
    change_event_attr_list = ["State"]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    for lru in test_proxies.power_switch:
        test_utils.change_event_subscriber(
            lru, change_event_attr_list, change_event_callbacks
        )
    return change_event_callbacks
