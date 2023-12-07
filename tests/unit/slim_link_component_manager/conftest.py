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

"""This module contains pytest-specific test harness for FspPstSubarrayComponentManager unit tests."""

from __future__ import annotations

# Standard imports
import logging
import os
import unittest
from typing import Callable, Dict

import pytest
from ska_tango_base.control_model import SimulationMode

from ska_mid_cbf_mcs.slim.slim_link_component_manager import (
    SlimLinkComponentManager,
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
def slim_link_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> SlimLinkComponentManager:
    """
    Return a SlimLink component manager.

    :param logger: the logger fixture

    :return: a SlimLink component manager.
    """

    return SlimLinkComponentManager(
        logger,
        push_change_event_callback,
        communication_status_changed_callback,
        component_power_mode_changed_callback,
        component_fault_callback,
        SimulationMode.FALSE,
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
def mock_tx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()

    builder.add_attribute("idle_ctrl_word", 0x12345678)
    builder.add_command(
        "read_counters",
        [
            100000,
            200000,
            300000,
        ],
    )
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_rx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()

    builder.add_attribute("idle_ctrl_word", 0)
    builder.add_attribute("bit_error_rate", 3e-12)
    builder.add_command("initialize_connection", None)
    builder.add_command(
        "read_counters",
        [
            100000,
            200000,
            300000,
            0,
            0,
            0,
        ],
    )
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_tx: unittest.mock.Mock, mock_rx: unittest.mock.Mock
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_tx: a mock slim-tx that is powered off.
    :param mock_rx: a mock slim-rx that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/slim-tx-rx/tx-test": mock_tx,
        "mid_csp_cbf/slim-tx-rx/rx-test": mock_rx,
    }
