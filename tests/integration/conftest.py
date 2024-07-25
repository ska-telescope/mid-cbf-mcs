# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest fixtures for MCS integration tests."""

from __future__ import annotations

import pytest
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import const


@pytest.fixture(name="controller", scope="session", autouse=True)
def controller_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the controller device.

    :return: DeviceProxy to CbfController device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/sub_elt/controller")


@pytest.fixture(name="subarray", scope="session", autouse=True)
def subarray_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to subarray devices.

    :return: list of DeviceProxy to CbfSubarray devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/sub_elt/subarray_{i:02}")
        for i in range(1, const.DEFAULT_COUNT_SUBARRAY + 1)
    ]


# TODO: upgrade fsp corr fixture for multiple subarrays
@pytest.fixture(name="fsp_corr", scope="session", autouse=True)
def fsp_corr_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to FSP CORR subarray devices.

    :return: list of DeviceProxy to FspCorrSubarray devices
    """
    return [
        context.DeviceProxy(
            device_name=f"mid_csp_cbf/fspCorrSubarray/{i:02}_01"
        )
        for i in range(1, const.DEFAULT_COUNT_FSP + 1)
    ]


@pytest.fixture(name="fsp", scope="session", autouse=True)
def fsp_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to FSP devices.

    :return: list of DeviceProxy to Fsp devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/fsp/{i:02}")
        for i in range(1, const.DEFAULT_COUNT_FSP + 1)
    ]


@pytest.fixture(name="vcc", scope="session", autouse=True)
def vcc_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to VCC devices.

    :return: list of DeviceProxy to Vcc devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/vcc/{i:03}")
        for i in range(1, const.DEFAULT_COUNT_VCC + 1)
    ]


@pytest.fixture(name="talon_lru", scope="session", autouse=True)
def talon_lru_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to Talon LRU devices.

    :return: list of DeviceProxy to TalonLRU devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/talon_lru/{i:03}")
        for i in range(1, const.DEFAULT_COUNT_LRU + 1)
    ]


@pytest.fixture(name="talon_board", scope="session", autouse=True)
def talon_board_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to Talon board devices.

    :return: list of DeviceProxy to TalonBoard devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/talon_board/{i:03}")
        for i in range(1, const.DEFAULT_COUNT_BOARD + 1)
    ]


@pytest.fixture(name="power_switch", scope="session", autouse=True)
def power_switch_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to power switch devices.

    :return: list of DeviceProxy to PowerSwitch devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/power_switch/{i:03}")
        for i in range(1, const.DEFAULT_COUNT_PDU + 1)
    ]


@pytest.fixture(name="slim_fs", scope="session", autouse=True)
def slim_fs_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the frequency slice SLIM device.

    :return: DeviceProxy to Slim device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/slim/slim-fs")


@pytest.fixture(name="slim_vis", scope="session", autouse=True)
def slim_vis_proxy() -> context.DeviceProxy:
    """
    Fixture that returns a proxy to the visibility SLIM device.

    :return: DeviceProxy to Slim device
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/slim/slim-vis")


@pytest.fixture(name="slim_link_fs", scope="session", autouse=True)
def slim_link_fs_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to frequency slice SLIM link devices.

    :return: list of DeviceProxy to SlimLink devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/fs_links/{i:03}")
        for i in range(const.MAX_NUM_FS_LINKS)
    ]


@pytest.fixture(name="slim_link_vis", scope="session", autouse=True)
def slim_link_vis_proxies() -> list[context.DeviceProxy]:
    """
    Fixture that returns a list of proxies to visibility SLIM link devices.

    :return: list of DeviceProxy to SlimLink devices
    """
    return [
        context.DeviceProxy(device_name=f"mid_csp_cbf/vis_links/{i:03}")
        for i in range(const.MAX_NUM_VIS_LINKS)
    ]
