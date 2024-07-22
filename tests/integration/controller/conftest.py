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
from ska_tango_testing.integration import TangoEventTracer
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils

from ... import test_utils


@pytest.fixture(name="sub_devices", scope="module", autouse=True)
def sub_device_proxies(
    power_switch: list[context.DeviceProxy],
    talon_lru: list[context.DeviceProxy],
    talon_board: list[context.DeviceProxy],
    subarray: list[context.DeviceProxy],
    fsp: list[context.DeviceProxy],
    vcc: list[context.DeviceProxy],
    slim_fs: context.DeviceProxy,
    slim_vis: context.DeviceProxy,
) -> list[context.DeviceProxy]:
    return (
        power_switch
        + talon_lru
        + talon_board
        + subarray
        + fsp
        + vcc
        + [slim_fs, slim_vis]
    )


@pytest.fixture(name="event_tracer", scope="module", autouse=True)
def tango_event_tracer(
    controller: context.DeviceProxy,
    sub_devices: list[context.DeviceProxy],
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    tracer.subscribe_event(controller, "longRunningCommandResult")

    for proxy in [controller] + sub_devices:
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")

    return tracer
