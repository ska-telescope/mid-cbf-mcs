# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS Controller integration tests."""

from __future__ import annotations

import json
from typing import Generator

import pytest

# Tango imports
from ska_control_model import (
    AdminMode,
    LoggingLevel,
    ObsState,
    ResultCode,
    SimulationMode,
)
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils

from ... import test_utils


@pytest.fixture(name="device_under_test", scope="module", autouse=True)
def device_under_test_fixture() -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :return: the device under test
    """

    device_under_test = context.DeviceProxy(
        device_name="mid_csp_cbf/sub_elt/controller"
    )
    if device_under_test.State() != DevState.DISABLE:
        if device_under_test.State() != DevState.OFF:
            device_under_test.Off()
        device_under_test.adminMode = AdminMode.OFFLINE

    while True:
        yield device_under_test


@pytest.fixture(name="change_event_callbacks")
def change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    """
    Fixture that returns the device under test's change event callback group.

    :param device_under_test: the device whose change events will be subscribed to.
    :return: the change event callback object
    """
    change_event_attr_list = [
        "longRunningCommandResult",
        "state",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


# --- Sub Devices Initialization --- #


@pytest.fixture(name="subdevices", scope="module", autouse=True)
def subdevices() -> Generator[dict[any]]:
    """
    Initialize all device proxies needed for integration testing the DUT.

    Includes:
    - 1 CbfSubarray
    - 1 TalonBoard
    - 4 Fsp
    - 8 Vcc
    - 1 Slim
    - 4 SlimLink

    """
    subdevices = {}

    # TalonBoard : Single board is enough for integration testing
    subdevices["mid_csp_cbf/talon_board/001"] = context.DeviceProxy(
        device_name="mid_csp_cbf/talon_board/001",
    )

    # CbfSubarray
    subdevices["mid_csp_cbf/sub_elt/subarray_01"] = context.DeviceProxy(
        device_name=f"mid_csp_cbf/sub_elt/subarray_01",
    )

    # Fsp : index == fspID
    for i in range(1, 5):
        subdevices[f"mid_csp_cbf/fsp/{i:02}"] = context.DeviceProxy(
            device_name=f"mid_csp_cbf/fsp/{i:02}"
        )

    # Vcc : index == vccID
    for i in range(1, 5):
        subdevices[f"mid_csp_cbf/vcc/{i:03}"] = context.DeviceProxy(
            device_name=f"mid_csp_cbf/vcc/{i:03}"
        )

    # Talon LRU
    for i in range(1, 5):  # 4 Talon LRUs for now
        subdevices[f"mid_csp_cbf/talon_lru/{i:03}"] = context.DeviceProxy(
            device_name=f"mid_csp_cbf/talon_lru/{i:03}",
        )

    # Power switch
    for i in range(1, 4):  # 3 Power Switches
        subdevices[f"mid_csp_cbf/power_switch/{i:03}"] = context.DeviceProxy(
            device_name=f"mid_csp_cbf/power_switch/{i:03}",
        )

    # Slim
    subdevices["mid_csp_cbf/slim/slim-fs"] = context.DeviceProxy(
        device_name="mid_csp_cbf/slim/slim-fs",
    )

    # SlimLink
    for i in range(0, 3):  # 4 SlimLinks
        subdevices[f"mid_csp_cbf/fs_links/{i:03}"] = context.DeviceProxy(
            device_name=f"mid_csp_cbf/fs_links/{i:03}",
        )

    # Reset all proxys to OFFLINE
    for _, proxy in subdevices.items():
        if proxy.State() != DevState.DISABLE:
            if proxy.State() != DevState.OFF:
                proxy.Off()
            proxy.adminMode = AdminMode.OFFLINE

    while True:
        yield subdevices


@pytest.fixture(name="subdevices_change_event_callbacks")
def subdevices_change_event_callbacks(
    subdevices: pytest.fixture,
) -> MockTangoEventCallbackGroup:
    """
    Fixture that returns the PowerSwitch's change event callback group.

    :param test_proxies: the device proxies used in this scope.
    :return: the change event callback object for PowerSwitch devices
    """
    for subdevices in subdevices.items():
        print
    change_event_attr_list = ["state"]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    for fqdn, proxy in subdevices.items():
        if "mid_csp_cbf/power_switch/" in fqdn:
            test_utils.change_event_subscriber(
                proxy, change_event_attr_list, change_event_callbacks
            )
    return change_event_callbacks
