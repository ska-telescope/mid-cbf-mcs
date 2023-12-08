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

"""This module contains pytest-specific test harness for Slim unit tests."""

from __future__ import annotations

# Standard imports
import logging
import os
import unittest
from typing import Callable, Dict, List

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import SimulationMode

from ska_mid_cbf_mcs.slim.slim_component_manager import (
    SlimComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

file_path = os.path.dirname(os.path.abspath(__file__))


# Local imports


@pytest.fixture()
def slim_component_manager(
    link_fqdns: List[str],
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> SlimComponentManager:
    """
    Return a Slim component manager.

    :param logger: the logger fixture

    :return: a Slim component manager.
    """

    return SlimComponentManager(
        link_fqdns=link_fqdns,
        logger=logger,
        push_change_event_callback=push_change_event_callback,
        communication_status_changed_callback=communication_status_changed_callback,
        component_power_mode_changed_callback=component_power_mode_changed_callback,
        component_fault_callback=component_fault_callback,
        simulation_mode=SimulationMode.FALSE,
    )


@pytest.fixture()
def communication_status_changed_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager communication status.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the communication status
        of a component manager changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def component_power_mode_changed_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component power mode change.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the component manager
        detects that the power mode of its component has changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def component_fault_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager fault.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the communication status
        of a component manager changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def push_change_event_callback_factory(
    mock_change_event_callback_factory: Callable[
        [str], MockChangeEventCallback
    ],
) -> Callable[[], MockChangeEventCallback]:
    """
    Return a mock change event callback factory

    :param mock_change_event_callback_factory: fixture that provides a
        mock change event callback factory (i.e. an object that returns
        mock callbacks when called).

    :return: a mock change event callback factory
    """

    def _factory() -> MockChangeEventCallback:
        return mock_change_event_callback_factory("adminMode")

    return _factory


@pytest.fixture()
def push_change_event_callback(
    push_change_event_callback_factory: Callable[[], MockChangeEventCallback],
) -> MockChangeEventCallback:
    """
    Return a mock change event callback

    :param push_change_event_callback_factory: fixture that provides a mock
        change event callback factory

    :return: a mock change event callback
    """
    return push_change_event_callback_factory()


@pytest.fixture()
def link_fqdns() -> unittest.mock.Mock:
    """
    Return a mock list of slim link fqdns

    :return: a mock list of slim link fqdns
    """
    return [
        "mid_csp_cbf/fs_links/000",
        "mid_csp_cbf/fs_links/001",
        "mid_csp_cbf/fs_links/002",
        "mid_csp_cbf/fs_links/003",
        "mid_csp_cbf/fs_links/004",
        "mid_csp_cbf/fs_links/005",
        "mid_csp_cbf/fs_links/006",
        "mid_csp_cbf/fs_links/007",
        "mid_csp_cbf/fs_links/008",
        "mid_csp_cbf/fs_links/009",
        "mid_csp_cbf/fs_links/010",
        "mid_csp_cbf/fs_links/011",
        "mid_csp_cbf/fs_links/012",
        "mid_csp_cbf/fs_links/013",
        "mid_csp_cbf/fs_links/014",
        "mid_csp_cbf/fs_links/015"
    ]


@pytest.fixture()
def mesh_config() -> unittest.mock.Mock:
    """
    Return a mock slim configuration string

    :return: a mock slim configuration
    """
    with open ("./mnt/slim/fs_slim_config.yaml", 'r') as mesh_config:
        return mesh_config.read()


@pytest.fixture()
def mock_link() -> unittest.mock.Mock:
    """
    Return a mock device proxy for a slim link

    :return: a mock slim-rx device
    """
    builder = MockDeviceBuilder()

    builder.add_command("ConnectTxRx", (ResultCode.OK, "Connected Tx Rx successfully"))
    builder.add_command("VerifyConnection", (ResultCode.OK, "Link health check OK"))
    builder.add_command("DisconnectTxRx", (ResultCode.OK, "Disconnected Tx Rx"))
    builder.add_command("ClearCounters", (ResultCode.OK, "Counters cleared!"))
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_link: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_link: a mock SlimLink.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/fs_links/000" : mock_link,
        "mid_csp_cbf/fs_links/001" : mock_link,
        "mid_csp_cbf/fs_links/002" : mock_link,
        "mid_csp_cbf/fs_links/003" : mock_link,
        "mid_csp_cbf/fs_links/004" : mock_link,
        "mid_csp_cbf/fs_links/005" : mock_link,
        "mid_csp_cbf/fs_links/006" : mock_link,
        "mid_csp_cbf/fs_links/007" : mock_link,
        "mid_csp_cbf/fs_links/008" : mock_link,
        "mid_csp_cbf/fs_links/009" : mock_link,
        "mid_csp_cbf/fs_links/010" : mock_link,
        "mid_csp_cbf/fs_links/011" : mock_link,
        "mid_csp_cbf/fs_links/012" : mock_link,
        "mid_csp_cbf/fs_links/013" : mock_link,
        "mid_csp_cbf/fs_links/014" : mock_link,
        "mid_csp_cbf/fs_links/015" : mock_link
    }