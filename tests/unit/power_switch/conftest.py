# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for power switch unit tests."""

from __future__ import annotations

import json
import logging

# Standard imports
import re
import unittest
from typing import Any, Callable, List

import pytest
import requests
from ska_tango_base.control_model import SimulationMode

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import (
    PowerSwitchComponentManager,
)

# Local imports
from ska_mid_cbf_mcs.power_switch.power_switch_device import PowerSwitch
from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.tango_harness import (
    DevicesToLoadType,
    TangoHarness,
)


@pytest.fixture(scope="function")
def power_switch_component_manager(
    logger: logging.Logger,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    push_change_event_callback: MockChangeEventCallback,
    communication_status_changed_callback: MockCallable,
    component_power_mode_changed_callback: MockCallable,
    component_fault_callback: MockCallable,
) -> PowerSwitchComponentManager:
    """
    Return a power switch component manager (with HTTP connection monkey-patched).

    :param logger: the logger fixture
    :param request: the pytest request fixture, must be indirectly parametrized
                    by each test with a dict of the form:
                        {
                            "sim_patch_error": boolean,
                            "sim_get_error": boolean
                        }
    :param monkeypatch: the pytest monkey-patching fixture

    :return: a power switch component manager.
    """

    class MockResponse:
        """A mock class to replace requests.Response."""

        def __init__(
            self: MockResponse, url: str, simulate_response_error: bool
        ) -> None:
            """
            Initialise a new instance.

            :param url: URL of the request
            :param simulate_response_error: set to True to simulate error response
            """
            outlet_state_url = re.compile(
                r"http:\/\/[\d.]+\/restapi\/relay\/outlets\/\d+\/"
            )
            outlet_list_url = re.compile(
                r"http:\/\/[\d.]+\/restapi\/relay\/outlets\/"
            )

            self._json: List[dict[str, Any]] = []

            if simulate_response_error:
                self.status_code = 404
            else:
                self.status_code = requests.codes.ok

                for i in range(0, 8):
                    outlet_cfg = {
                        "name": f"Outlet {i}",
                        "locked": False,
                        "critical": False,
                        "cycle_delay": 0,
                        "state": True,
                        "physical_state": True,
                        "transient_state": True,
                    }

                    self._json.append(outlet_cfg)

                if outlet_list_url.fullmatch(url):
                    self.text = json.dumps(self._json)

                elif outlet_state_url.fullmatch(url):
                    url.split("/")
                    outlet = url[-2]

                    self._json = self._json[int(outlet)]
                    self.text = json.dumps(self._json)

        def json(self: MockResponse) -> dict[str, Any]:
            """
            Replace the patched :py:meth:`request.Response.json` with mock.

            This implementation always returns the same key-value pairs.

            :return: representative JSON reponse as the power switch when
                     querying the outlets page
            """

            return self._json

    def mock_patch(url: str, **kwargs: Any) -> MockResponse:
        """
        Replace requests.request method with a mock method.

        :param url: the URL
        :param kwargs: other keyword args

        :return: a response
        """
        return MockResponse(url, request.param["sim_patch_error"])

    def mock_get(url: str, params: Any = None, **kwargs: Any) -> MockResponse:
        """
        Replace requests.get with mock method.

        :param url: the URL
        :param params: arguments to the GET
        :param kwargs: other keyword args

        :return: a response
        """
        return MockResponse(url, request.param["sim_get_error"])

    monkeypatch.setattr(requests, "patch", mock_patch)
    monkeypatch.setattr(requests, "get", mock_get)

    return PowerSwitchComponentManager(
        simulation_mode=SimulationMode.FALSE,
        model="APC AP8681",
        ip="0.0.0.0",
        login="",
        password="",
        logger=logger,
        push_change_event_callback=push_change_event_callback,
        communication_status_changed_callback=communication_status_changed_callback,
        component_power_mode_changed_callback=component_power_mode_changed_callback,
        component_fault_callback=component_fault_callback,
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
def check_power_mode_callback(
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
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/power_switch/001")


@pytest.fixture()
def device_to_load() -> DevicesToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/power_switch/devicetoload.json",
        "package": "ska_mid_cbf_mcs.power_switch.power_switch_device",
        "device": "powerswitch-001",
        "device_class": "PowerSwitch",
        "proxy": CbfDeviceProxy,
        "patch": PowerSwitch,
    }
