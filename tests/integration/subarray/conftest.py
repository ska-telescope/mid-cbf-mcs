# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.


from __future__ import annotations

from typing import Generator

import pytest
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_mcs.commons.global_enum import const


@pytest.fixture(
    name="subarray_params",
    scope="module",
    params=[
        {
            "sys_param_file": "sys_param_4_boards.json",
            "configure_scan_file": "ConfigureScan_basic_CORR.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": ["SKA001"],
            "vcc_ids": [1],  # must be VCC IDs equivalent to assigned DISH IDs
            "fsp_ids": [1],  # must be FSP IDs provided in ConfigureScan JSON
        },
        # {
        #     "sys_param_file": "sys_param_4_boards.json",
        #     "configure_scan_file": "ConfigureScan_CORR_4_receptor_1_FSP.json",
        #     "scan_file": "Scan1_basic.json",
        #     "sub_id": 1,
        #     "dish_ids": ["SKA001", "SKA036", "SKA063", "SKA100"],
        #     "vcc_ids": [
        #         1,
        #         2,
        #         3,
        #         4,
        #     ],  # must be VCC IDs equivalent to assigned DISH IDs
        #     "fsp_ids": [1],  # must be FSP IDs provided in ConfigureScan JSON
        # },
        # {
        #     "sys_param_file": "sys_param_4_boards.json",
        #     "configure_scan_file": "ConfigureScan_CORR_4_receptor_4_FSP.json",
        #     "scan_file": "Scan1_basic.json",
        #     "sub_id": 1,
        #     "dish_ids": ["SKA001", "SKA036", "SKA063", "SKA100"],
        #     "vcc_ids": [
        #         1,
        #         2,
        #         3,
        #         4,
        #     ],  # must be VCC IDs equivalent to assigned DISH IDs
        #     "fsp_ids": [
        #         1,
        #         2,
        #         3,
        #         4,
        #     ],  # must be FSP IDs provided in ConfigureScan JSON
        # },
    ],
)
def subarray_test_parameters(request: pytest.FixtureRequest) -> dict[any]:
    """
    Fixture that subarray test input parameters.

    :return: dict containing all subarray test input parameters
    """
    return request.param


@pytest.fixture(name="subarray", scope="session", autouse=True)
def subarray_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to subarray devices.

    :return: dict of DeviceProxy to CbfSubarray devices
    """
    return {
        sub_id: context.DeviceProxy(
            device_name=f"mid_csp_cbf/sub_elt/subarray_{sub_id:02}"
        )
        for sub_id in range(1, const.DEFAULT_COUNT_SUBARRAY + 1)
    }


# TODO: upgrade fsp corr fixture for multiple subarrays
@pytest.fixture(name="fsp_corr", scope="session", autouse=True)
def fsp_corr_proxies() -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to FSP CORR subarray devices.

    :return: dict of DeviceProxy to FspCorrSubarray devices
    """
    return {
        fsp_id: context.DeviceProxy(
            device_name=f"mid_csp_cbf/fspCorrSubarray/{fsp_id:02}_01"
        )
        for fsp_id in range(1, const.DEFAULT_COUNT_FSP + 1)
    }


@pytest.fixture(name="fsp", scope="session", autouse=True)
def fsp_proxies() -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to FSP devices.

    :return: dict of DeviceProxy to Fsp devices
    """
    return {
        fsp_id: context.DeviceProxy(device_name=f"mid_csp_cbf/fsp/{fsp_id:02}")
        for fsp_id in range(1, const.DEFAULT_COUNT_FSP + 1)
    }


@pytest.fixture(name="vcc", scope="session", autouse=True)
def vcc_proxies() -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to VCC devices.

    :return: dict of DeviceProxy to Vcc devices
    """
    return {
        vcc_id: context.DeviceProxy(device_name=f"mid_csp_cbf/vcc/{vcc_id:03}")
        for vcc_id in range(1, const.DEFAULT_COUNT_VCC + 1)
    }


# TODO: scope=test?
@pytest.fixture(name="event_tracer", scope="function", autouse=True)
def tango_event_tracer(
    subarray: dict[int, context.DeviceProxy],
    vcc: dict[int, context.DeviceProxy],
    fsp: dict[int, context.DeviceProxy],
    fsp_corr: dict[int, context.DeviceProxy],
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    for proxy in list(subarray.values()):
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "obsState")
        tracer.subscribe_event(proxy, "longRunningCommandResult")
        tracer.subscribe_event(proxy, "receptors")
        tracer.subscribe_event(proxy, "sysParam")

    for proxy in (
        list(vcc.values()) + list(fsp.values()) + list(fsp_corr.values())
    ):
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")

        # only FSP is not an obs device
        if "mid_csp_cbf/fsp/" not in proxy.dev_name():
            tracer.subscribe_event(proxy, "obsState")
            if "mid_csp_cbf/vcc/" in proxy.dev_name():
                tracer.subscribe_event(proxy, "subarrayMembership")
                tracer.subscribe_event(proxy, "frequencyBand")
        else:
            tracer.subscribe_event(proxy, "subarrayMembership")
            tracer.subscribe_event(proxy, "functionMode")

    return tracer
