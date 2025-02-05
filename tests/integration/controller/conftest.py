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
import yaml
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer

from ska_mid_cbf_tdc_mcs.commons.global_enum import const

# TODO: Update constants for AA2+

DEFAULT_COUNT_SUBARRAY = 1
DEFAULT_COUNT_VCC = 8
DEFAULT_COUNT_FSP = 4
DEFAULT_COUNT_LRU = 2


@pytest.fixture(
    name="controller_params",
    scope="module",
    params=[
        {
            "sys_param_file": "sys_param_4_boards.json",
            "sys_param_from_file": True,
            "hw_config_file": "mnt/hw_config/hw_config.yaml",
            "num_board": DEFAULT_COUNT_LRU * 2,
            "num_lru": DEFAULT_COUNT_LRU,
        },
        {
            "sys_param_file": "source_init_sys_param.json",
            "sys_param_from_file": False,
            "hw_config_file": "mnt/hw_config/hw_config.yaml",
            "num_board": DEFAULT_COUNT_LRU * 2,
            "num_lru": DEFAULT_COUNT_LRU,
        },
        # TODO: this JSON causes the following exception:
        # "urllib.error.URLError: <urlopen error [Errno -5] No address associated with hostname>""
        # {
        #     "sys_param_file": "source_init_sys_param_retrieve_from_car.json",
        #     "sys_param_from_file": False,
        #     "hw_config_file": "mnt/hw_config/hw_config.yaml",
        # },
    ],
)
def controller_test_parameters(request: pytest.FixtureRequest) -> dict[any]:
    """
    Fixture that controller test input parameters.

    :return: A dictionary containing all the test input parameters for the controller.
             This includes the system parameter file path, a flag indicating whether to retrieve
             the system parameters from the file, and the hardware configuration file path.
             Format follows {"sys_param_file": str, "sys_param_from_file": bool, "hw_config_file": str}.
    """
    with open(request.param["hw_config_file"]) as f:
        hw_config_dict = yaml.safe_load(f)
    request.param["num_lru_total"] = len(hw_config_dict["talon_lru"])
    request.param["num_board_total"] = len(hw_config_dict["talon_board"])
    request.param["num_pdu"] = len(hw_config_dict["power_switch"])
    return request.param


@pytest.fixture(name="controller", scope="module", autouse=True)
def controller_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the controller device.

    :return: DeviceProxy to CbfController device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/sub_elt/controller")


@pytest.fixture(name="deployer", scope="module", autouse=True)
def deployer_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the EC deployer device.

    :return: DeviceProxy to CbfDeployer device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/ec/deployer")


@pytest.fixture(name="subarray", scope="module", autouse=True)
def subarray_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to subarray devices.

    :return: list of DeviceProxy to CbfSubarray devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/sub_elt/subarray_{i:02}")
        for i in range(1, DEFAULT_COUNT_SUBARRAY + 1)
    ]


@pytest.fixture(name="fsp", scope="module", autouse=True)
def fsp_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to FSP devices.

    :return: list of DeviceProxy to Fsp devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/fsp/{fsp_id:02}")
        for fsp_id in range(1, DEFAULT_COUNT_FSP + 1)
    ]


@pytest.fixture(name="vcc", scope="module", autouse=True)
def vcc_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to VCC devices.

    :return: list of DeviceProxy to Vcc devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/vcc/{i:03}")
        for i in range(1, DEFAULT_COUNT_VCC + 1)
    ]


@pytest.fixture(name="talon_lru", scope="module", autouse=True)
def talon_lru_proxies(
    controller_params: dict[any],
) -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to Talon LRU devices.

    :param controller_params: Input parameters for running different instances of the suite.
    :return: list of DeviceProxy to TalonLRU devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/talon_lru/{i:03}")
        for i in range(1, controller_params["num_lru"] + 1)
    ]


@pytest.fixture(name="talon_lru_not_fitted", scope="module", autouse=True)
def talon_lru_not_fitted_proxies(
    controller_params: dict[any],
) -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to Talon LRU devices that are NOT_FITTED.

    :param controller_params: Input parameters for running different instances of the suite.
    :return: list of DeviceProxy to TalonLRU devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/talon_lru/{i:03}")
        for i in range(
            controller_params["num_lru"] + 1,
            controller_params["num_lru_total"] + 1,
        )
    ]


@pytest.fixture(name="talon_board", scope="module", autouse=True)
def talon_board_proxies(
    controller_params: dict[any],
) -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to Talon board devices.

    :param controller_params: Input parameters for running different instances of the suite.
    :return: list of DeviceProxy to TalonBoard devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/talon_board/{i:03}")
        for i in range(1, controller_params["num_board"] + 1)
    ]


@pytest.fixture(name="talon_board_not_fitted", scope="module", autouse=True)
def talon_board_not_fitted_proxies(
    controller_params: dict[any],
) -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to Talon board devices that are NOT_FITTED.

    :param controller_params: Input parameters for running different instances of the suite.
    :return: list of DeviceProxy to TalonBoard devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/talon_board/{i:03}")
        for i in range(
            controller_params["num_board"] + 1,
            controller_params["num_board_total"] + 1,
        )
    ]


@pytest.fixture(name="power_switch", scope="module", autouse=True)
def power_switch_proxies(
    controller_params: dict[any],
) -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to power switch devices.

    :param controller_params: Input parameters for running different instances of the suite.
    :return: list of DeviceProxy to PowerSwitch devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/power_switch/{i:03}")
        for i in range(1, controller_params["num_pdu"] + 1)
    ]


@pytest.fixture(name="slim_fs", scope="module", autouse=True)
def slim_fs_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the frequency slice SLIM device.

    :return: DeviceProxy to Slim device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/slim/slim-fs")


@pytest.fixture(name="slim_vis", scope="module", autouse=True)
def slim_vis_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the visibility SLIM device.

    :return: DeviceProxy to Slim device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/slim/slim-vis")


@pytest.fixture(name="slim_link_fs", scope="module", autouse=True)
def slim_link_fs_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to frequency slice SLIM link devices.

    :return: list of DeviceProxy to SlimLink devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/fs_links/{i:03}")
        for i in range(const.MAX_NUM_FS_LINKS)
    ]


@pytest.fixture(name="slim_link_vis", scope="module", autouse=True)
def slim_link_vis_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to visibility SLIM link devices.

    :return: list of DeviceProxy to SlimLink devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/vis_links/{i:03}")
        for i in range(const.MAX_NUM_VIS_LINKS)
    ]


@pytest.fixture(name="event_tracer", scope="function", autouse=True)
def tango_event_tracer(
    controller: context.DeviceProxy,
    fsp: list[context.DeviceProxy],
    power_switch: list[context.DeviceProxy],
    slim_fs: context.DeviceProxy,
    slim_vis: context.DeviceProxy,
    subarray: list[context.DeviceProxy],
    talon_board: list[context.DeviceProxy],
    talon_board_not_fitted: list[context.DeviceProxy],
    talon_lru: list[context.DeviceProxy],
    talon_lru_not_fitted: list[context.DeviceProxy],
    vcc: list[context.DeviceProxy],
) -> Generator[TangoEventTracer, None, None]:
    """
    Fixture that returns a TangoEventTracer for pertinent devices.
    Takes as parameter all required device proxy fixtures for this test module.

    :return: TangoEventTracer
    """
    tracer = TangoEventTracer()

    tracer.subscribe_event(controller, "longRunningCommandResult")

    for proxy in [controller] + talon_lru + power_switch + [slim_fs, slim_vis]:
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")

    for proxy in subarray:
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "obsState")
        tracer.subscribe_event(proxy, "sysParam")

    for proxy in fsp:
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "functionMode")

    for proxy in vcc + talon_board:
        tracer.subscribe_event(proxy, "adminMode")
        tracer.subscribe_event(proxy, "state")
        tracer.subscribe_event(proxy, "dishID")

    for proxy in talon_board_not_fitted + talon_lru_not_fitted:
        tracer.subscribe_event(proxy, "adminMode")

    return tracer
