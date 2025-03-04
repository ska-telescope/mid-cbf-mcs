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

from ska_mid_cbf_tdc_mcs.commons.global_enum import FspModes

# TODO: Update constants for AA2+

DEFAULT_COUNT_VCC = 8
DEFAULT_COUNT_FSP = 8
DEFAULT_COUNT_SUBARRAY = 1


@pytest.fixture(
    name="subarray_params",
    scope="module",
    params=[
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_basic_CORR.json",
            "delay_model_file": "delay_model_1_receptor.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": ["SKA001"],
            "vcc_ids": [1],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                1: FspModes.CORR.value
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
            "alt_params": {
                "configure_scan_file": "ConfigureScan_basic_CORR_alt.json",
                "scan_file": "Scan2_basic.json",
                "dish_ids": ["SKA001"],
                "vcc_ids": [
                    1
                ],  # must be VCC IDs equivalent to assigned DISH IDs
                "freq_band": 1,  # must be index of frequency band in ConfigureScan JSON
                "fsp_modes": {
                    2: FspModes.CORR.value
                },  # must be FSP IDs and FspMode values in ConfigureScan JSON
            },
        },
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_CORR_4_receptor_1_FSP.json",
            "delay_model_file": "delay_model_4_receptor.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": ["SKA001", "SKA036", "SKA063", "SKA100"],
            "vcc_ids": [
                1,
                2,
                3,
                4,
            ],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                1: FspModes.CORR.value
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
        },
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_CORR_4_receptor_4_FSP.json",
            "delay_model_file": "delay_model_4_receptor.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": ["SKA001", "SKA036", "SKA063", "SKA100"],
            "vcc_ids": [
                1,
                2,
                3,
                4,
            ],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                1: FspModes.CORR.value,
                2: FspModes.CORR.value,
                3: FspModes.CORR.value,
                4: FspModes.CORR.value,
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
        },
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_basic_PST_band1.json",
            "delay_model_file": "delay_model_1_receptor_vcc_5.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": ["SKA081"],
            "vcc_ids": [5],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                5: FspModes.PST.value
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
            "alt_params": {
                "configure_scan_file": "ConfigureScan_basic_PST_band2_alt.json",
                "scan_file": "Scan2_basic.json",
                "dish_ids": ["SKA081"],
                "vcc_ids": [
                    5
                ],  # must be VCC IDs equivalent to assigned DISH IDs
                "freq_band": 1,  # must be index of frequency band in ConfigureScan JSON
                "fsp_modes": {
                    6: FspModes.PST.value
                },  # must be FSP IDs and FspMode values in ConfigureScan JSON
            },
        },
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_4_PR_PST.json",
            "delay_model_file": "delay_model_4_receptor_5_to_8.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": [
                "SKA081",
                "SKA046",
                "SKA077",
                "SKA048",
            ],
            "vcc_ids": [
                5,
                6,
                7,
                8,
            ],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                5: FspModes.PST.value,
                6: FspModes.PST.value,
                7: FspModes.PST.value,
                8: FspModes.PST.value,
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
        },
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_CORR_PST_8_receptor_5_FSP.json",
            "delay_model_file": "delay_model_8_receptor.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": [
                "SKA001",
                "SKA036",
                "SKA063",
                "SKA100",
                "SKA081",
                "SKA046",
                "SKA077",
                "SKA048",
            ],
            "vcc_ids": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
            ],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                1: FspModes.CORR.value,
                2: FspModes.CORR.value,
                3: FspModes.CORR.value,
                4: FspModes.CORR.value,
                8: FspModes.PST.value,
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
        },
        {
            "sys_param_file": "sys_param_8_boards.json",
            "configure_scan_file": "ConfigureScan_CORR_PST_8_receptor_8_FSP.json",
            "delay_model_file": "delay_model_8_receptor.json",
            "scan_file": "Scan1_basic.json",
            "sub_id": 1,
            "dish_ids": [
                "SKA001",
                "SKA036",
                "SKA063",
                "SKA100",
                "SKA081",
                "SKA046",
                "SKA077",
                "SKA048",
            ],
            "vcc_ids": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
            ],  # must be VCC IDs equivalent to assigned DISH IDs
            "freq_band": 0,  # must be index of frequency band in ConfigureScan JSON
            "fsp_modes": {
                1: FspModes.CORR.value,
                2: FspModes.CORR.value,
                3: FspModes.CORR.value,
                4: FspModes.CORR.value,
                5: FspModes.PST.value,
                6: FspModes.PST.value,
                7: FspModes.PST.value,
                8: FspModes.PST.value,
            },  # must be FSP IDs and FspMode values in ConfigureScan JSON
        },
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
        for sub_id in range(1, DEFAULT_COUNT_SUBARRAY + 1)
    }


@pytest.fixture(name="controller", scope="session", autouse=True)
def controller_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the controller device.

    :return: DeviceProxy to CbfController device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/sub_elt/controller")


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
        for fsp_id in range(1, (DEFAULT_COUNT_FSP) // 2 + 1)
    }


@pytest.fixture(name="fsp_pst", scope="session", autouse=True)
def fsp_pst_proxies() -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to FSP PST subarray devices.

    :return: dict of DeviceProxy to FspCorrSubarray devices
    """
    return {
        fsp_id: context.DeviceProxy(
            device_name=f"mid_csp_cbf/fspPstSubarray/{fsp_id:02}_01"
        )
        for fsp_id in range(
            (DEFAULT_COUNT_FSP) // 2 + 1, DEFAULT_COUNT_FSP + 1
        )
    }


@pytest.fixture(name="fsp_mode_all", scope="session", autouse=True)
def fsp_mode_proxies(
    fsp_corr: dict[int, context.DeviceProxy],
    fsp_pst: dict[int, context.DeviceProxy],
) -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to FSP Mode Subarray Devices.

    Combinations of all FSP Mode Subarray Devices under test.

    :return: dict of DeviceProxy to FspModeSubarray devices
    """
    # | operator to concatenate dictionaries is not in an in-place operation
    # TODO: Add new proxies as new FSP modes are added
    fsp_mode_proxies = {}
    fsp_mode_proxies = fsp_mode_proxies | fsp_corr
    fsp_mode_proxies = fsp_mode_proxies | fsp_pst
    return fsp_mode_proxies


@pytest.fixture(name="fsp", scope="session", autouse=True)
def fsp_proxies() -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to FSP devices.

    :return: dict of DeviceProxy to Fsp devices
    """
    return {
        fsp_id: context.DeviceProxy(device_name=f"mid_csp_cbf/fsp/{fsp_id:02}")
        for fsp_id in range(1, DEFAULT_COUNT_FSP + 1)
    }


@pytest.fixture(name="vcc", scope="session", autouse=True)
def vcc_proxies() -> dict[int, context.DeviceProxy]:
    """
    Fixture that returns a dict of proxies to VCC devices.

    :return: dict of DeviceProxy to Vcc devices
    """
    return {
        vcc_id: context.DeviceProxy(device_name=f"mid_csp_cbf/vcc/{vcc_id:03}")
        for vcc_id in range(1, DEFAULT_COUNT_VCC + 1)
    }


@pytest.fixture(name="tm", scope="session", autouse=True)
def tm_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the TM leaf node emulator device.

    :return: DeviceProxy to TmCspSubarrayLeafNodeTest device
    """
    return context.DeviceProxy(
        device_name="ska_mid/tm_leaf_node/csp_subarray_01"
    )


# TODO: scope=test?
@pytest.fixture(name="event_tracer", scope="function", autouse=True)
def tango_event_tracer(
    controller: context.DeviceProxy,
    subarray: dict[int, context.DeviceProxy],
    vcc: dict[int, context.DeviceProxy],
    fsp: dict[int, context.DeviceProxy],
    # fsp_corr: dict[int, context.DeviceProxy],
    # fsp_pst: dict[int, context.DeviceProxy],
    fsp_mode_all: dict[int, context.DeviceProxy],
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    tracer.subscribe_event(controller, "longRunningCommandResult")
    tracer.subscribe_event(controller, "adminMode")
    tracer.subscribe_event(controller, "state")

    for proxy in list(subarray.values()):
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "obsState")
        tracer.subscribe_event(proxy, "longRunningCommandResult")
        tracer.subscribe_event(proxy, "receptors")
        tracer.subscribe_event(proxy, "sysParam")

    for proxy in list(fsp.values()):
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "subarrayMembership")
        tracer.subscribe_event(proxy, "functionMode")

    # for proxy in list(fsp_corr.values()):
    #     tracer.subscribe_event(proxy, "adminMode")
    #     tracer.subscribe_event(proxy, "state")
    #     tracer.subscribe_event(proxy, "obsState")
    #     tracer.subscribe_event(proxy, "delayModel")

    for proxy in list(fsp_mode_all.values()):
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "obsState")
        tracer.subscribe_event(proxy, "delayModel")

    # for proxy in list(fsp_pst.values()):
    #     tracer.subscribe_event(proxy, "adminMode")
    #     tracer.subscribe_event(proxy, "state")
    #     tracer.subscribe_event(proxy, "obsState")
    #     tracer.subscribe_event(proxy, "delayModel")

    for proxy in list(vcc.values()):
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "obsState")
        tracer.subscribe_event(proxy, "subarrayMembership")
        tracer.subscribe_event(proxy, "frequencyBand")

    return tracer
