# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for FspComponentManager unit tests."""

from __future__ import annotations

# Standard imports
import logging
import os
import unittest
from typing import Callable, Dict

import pytest
import tango

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

file_path = os.path.dirname(os.path.abspath(__file__))
import functools
import json

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    ObsState,
    PowerMode,
    SimulationMode,
)

from ska_mid_cbf_mcs.fsp.fsp_component_manager import FspComponentManager
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness

# Local imports


CONST_TEST_NUM_VCC = 4
CONST_TEST_NUM_FSP = 4
CONST_TEST_NUM_SUBARRAY = 1


@pytest.fixture()
def fsp_component_manager(
    logger: logging.Logger,
    tango_harness: TangoHarness,  # sets the connection_factory
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> FspComponentManager:
    """
    Return an Fsp component manager.

    :param logger: the logger fixture

    :return: an Fsp component manager.
    """

    fsp_id = 1

    f = open(file_path + "/../../data/test_fqdns.json")
    json_string = f.read().replace("\n", "")
    f.close()
    configuration = json.loads(json_string)

    fsp_corr_subarray_fqdns_all = configuration["fqdn_fsp_corr_subarray"]
    fsp_pss_subarray_fqdns_all = configuration["fqdn_fsp_pss_subarray"]
    fsp_pst_subarray_fqdns_all = configuration["fqdn_fsp_pst_subarray"]

    fsp_corr_subarray_address = fsp_corr_subarray_fqdns_all[0]
    fsp_pss_subarray_address = fsp_pss_subarray_fqdns_all[0]
    fsp_pst_subarray_address = fsp_pst_subarray_fqdns_all[0]
    vlbi_address = configuration["fqdn_vlbi"][0]

    return FspComponentManager(
        logger,
        fsp_id,
        fsp_corr_subarray_fqdns_all,
        fsp_pss_subarray_fqdns_all,
        fsp_pst_subarray_fqdns_all,
        fsp_corr_subarray_address,
        fsp_pss_subarray_address,
        fsp_pst_subarray_address,
        vlbi_address,
        push_change_event_callback,
        communication_status_changed_callback,
        component_power_mode_changed_callback,
        component_fault_callback,
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
def mock_fsp_corr_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()


@pytest.fixture()
def mock_fsp_corr_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()


@pytest.fixture()
def mock_fsp_pss_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    # add receptors to the mock pss subarray
    # (this is required for test_UpdateJonesMatrix)
    builder.add_attribute("receptors", [1, 2, 3, 4])
    return builder()


@pytest.fixture()
def mock_fsp_pss_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()


@pytest.fixture()
def mock_fsp_pst_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    # add receptors to the mock pst subarray
    # (this is required for test_UpdateBeamWeights)
    builder.add_attribute("receptors", [1, 2, 3, 4])
    return builder()


@pytest.fixture()
def mock_fsp_pst_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()


@pytest.fixture()
def initial_mocks(
    mock_fsp_corr_subarray: unittest.mock.Mock,
    mock_fsp_corr_subarray_group: unittest.mock.Mock,
    mock_fsp_pss_subarray: unittest.mock.Mock,
    mock_fsp_pss_subarray_group: unittest.mock.Mock,
    mock_fsp_pst_subarray: unittest.mock.Mock,
    mock_fsp_pst_subarray_group: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_fsp_corr_subarray: a mock FspCorrSubarray.
    :param mock_fsp_corr_subarray_group: a mock FspCorrSubarray group.
    :param mock_fsp_pss_subarray: a mock FspPssSubarray.
    :param mock_fsp_pss_subarray_group: a mock FspPssSubarray group.
    :param mock_fsp_pst_subarray: a mock FspPstSubarray.
    :param mock_fsp_pst_subarray_group: a mock FspPstSubarray group.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspPssSubarray/01_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/03_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/04_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPstSubarray/01_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/02_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/03_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/04_01": mock_fsp_pst_subarray,
        "FSP Subarray Corr": mock_fsp_corr_subarray_group,
        "FSP Subarray Pss": mock_fsp_pss_subarray_group,
        "FSP Subarray Pst": mock_fsp_pst_subarray_group,
    }
