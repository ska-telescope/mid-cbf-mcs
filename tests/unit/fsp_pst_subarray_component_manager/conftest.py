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

from ska_mid_cbf_mcs.fsp.fsp_pst_subarray_component_manager import (
    FspPstSubarrayComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

file_path = os.path.dirname(os.path.abspath(__file__))


# Local imports


CONST_TEST_NUM_VCC = 8
CONST_TEST_NUM_FSP = 4
CONST_TEST_NUM_SUBARRAY = 1


@pytest.fixture()
def fsp_pst_subarray_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
    component_obs_fault_callback: MockCallable,
) -> FspPstSubarrayComponentManager:
    """
    Return a FspPstSubarray component manager.

    :param logger: the logger fixture

    :return: a FspPstSubarray component manager.
    """

    fsp_id = 1

    return FspPstSubarrayComponentManager(
        logger,
        fsp_id,
        push_change_event_callback,
        communication_status_changed_callback,
        component_power_mode_changed_callback,
        component_fault_callback,
        component_obs_fault_callback,
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
    Return a mock callback for component manager op fault.

    :param mock_callback_factory: fixture that provides a mock callback
        factory (i.e. an object that returns mock callbacks when
        called).

    :return: a mock callback to be called when the communication status
        of a component manager changed.
    """
    return mock_callback_factory()


@pytest.fixture()
def component_obs_fault_callback(
    mock_callback_factory: Callable[[], unittest.mock.Mock],
) -> unittest.mock.Mock:
    """
    Return a mock callback for component manager obs fault.

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
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    # Mock the Vcc subarrayMembership attribute
    # The subarray ID for this unit test is hardcoded to 1
    builder.add_attribute("subarrayMembership", 1)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_controller: unittest.mock.Mock, mock_vcc: unittest.mock.Mock
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_controller: a mock CbfController.
    :param mock_vcc: a mock Vcc that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/sub_elt/controller": mock_controller,
        "mid_csp_cbf/vcc/001": mock_vcc,
        "mid_csp_cbf/vcc/002": mock_vcc,
        "mid_csp_cbf/vcc/003": mock_vcc,
        "mid_csp_cbf/vcc/004": mock_vcc,
        "mid_csp_cbf/vcc/005": mock_vcc,
        "mid_csp_cbf/vcc/006": mock_vcc,
        "mid_csp_cbf/vcc/007": mock_vcc,
        "mid_csp_cbf/vcc/008": mock_vcc,
    }