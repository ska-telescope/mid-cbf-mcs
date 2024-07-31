# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS Controller integration tests."""

from __future__ import annotations

from typing import Generator

import pytest
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer

@pytest.fixture(name="all_sub_devices", scope="module", autouse=True)
def all_sub_device_proxies(
    power_switch: list[context.DeviceProxy],
    talon_lru: list[context.DeviceProxy],
    talon_board: list[context.DeviceProxy],
    subarray: list[context.DeviceProxy],
    slim_fs: context.DeviceProxy,
    slim_vis: context.DeviceProxy,
) -> list[context.DeviceProxy]:
    return (
        power_switch + talon_lru + talon_board + subarray + [slim_fs, slim_vis]
    )


@pytest.fixture(name="powered_sub_devices", scope="module", autouse=True)
def powered_sub_device_proxies(
    talon_lru: list[context.DeviceProxy],
    talon_board: list[context.DeviceProxy],
    subarray: list[context.DeviceProxy],
    slim_fs: context.DeviceProxy,
    slim_vis: context.DeviceProxy,
) -> list[context.DeviceProxy]:
    return talon_lru + talon_board + [slim_fs, slim_vis]


@pytest.fixture(name="event_tracer", scope="module", autouse=True)
def tango_event_tracer(
    controller: context.DeviceProxy,
    all_sub_devices: list[context.DeviceProxy],
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    tracer.subscribe_event(controller, "longRunningCommandResult")

    for proxy in [controller] + all_sub_devices:
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")

        if (
            "mid_csp_cbf/vcc/" in proxy.dev_name()
            or "mid_csp_cbf/sub_elt/subarray" in proxy.dev_name()
            or "mid_csp_cbf/fspCorrSubarray" in proxy.dev_name()
        ):
            tracer.subscribe_event(proxy, "obsState")

    return tracer
