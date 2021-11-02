# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for power switch unit tests."""

from __future__ import annotations

# Standard imports
import re
import json
import logging
import pytest
import requests
from typing import List, Any

# Local imports
from ska_mid_cbf_mcs.power_switch.power_switch_device import PowerSwitch
from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import PowerSwitchComponentManager
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness, DevicesToLoadType
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import SimulationMode

@pytest.fixture(scope="function")
def power_switch_component_manager(
    logger: logging.Logger,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> PowerSwitchComponentManager:
    """
    Return a power switch component manager (with HTTP connection monkey-patched).

    :param logger: the logger fixture
    :param request: the pytest request fixture, must be indirectly parametrized 
                    by each test with a dict of the form:
                        { 
                            "sim_put_error": boolean,
                            "sim_get_error": boolean
                        }
    :param monkeypatch: the pytest monkey-patching fixture

    :return: a power switch component manager.
    """

    class MockResponse:
        """A mock class to replace requests.Response."""

        def __init__(
            self: MockResponse,
            url: str,
            simulate_response_error: bool
        ) -> None:
            """
            Initialise a new instance.

            :param url: URL of the request
            :param simulate_response_error: set to True to simulate error response
            """
            outlet_state_url = re.compile(r"http:\/\/[\d.]+\/restapi\/relay\/outlets\/\d+\/state\/")
            outlet_list_url = re.compile(r"http:\/\/[\d.]+\/restapi\/relay\/outlets\/")

            if simulate_response_error:
                self.status_code = 404
            else:
                self.status_code = requests.codes.ok

                if outlet_list_url.fullmatch(url):
                    self._json: List[dict[str, Any]] = []

                    for i in range(0, 8):
                        outlet_cfg = {
                            "name": f"Outlet {i}",
                            "locked": False,
                            "critical": False,
                            "cycle_delay": 0,
                            "state": True,
                            "physical_state": True,
                            "transient_state": True
                        }

                        self._json.append(outlet_cfg)

                    self.text = json.dumps(self._json)
                elif outlet_state_url.fullmatch(url):
                    self.text = "true"

        def json(self: MockResponse) -> dict[str, str]:
            """
            Replace the patched :py:meth:`request.Response.json` with mock.

            This implementation always returns the same key-value pairs.

            :return: representative JSON reponse as the power switch when
                     querying the outlets page
            """
            return self._json

    def mock_put(url: str, **kwargs: Any) -> MockResponse:
        """
        Replace requests.request method with a mock method.

        :param url: the URL
        :param kwargs: other keyword args

        :return: a response
        """
        return MockResponse(url, request.param["sim_put_error"])

    def mock_get(url: str, params: Any = None, **kwargs: Any) -> MockResponse:
        """
        Replace requests.get with mock method.

        :param url: the URL
        :param params: arguments to the GET
        :param kwargs: other keyword args

        :return: a response
        """
        return MockResponse(url, request.param["sim_get_error"])

    monkeypatch.setattr(requests, "put", mock_put)
    monkeypatch.setattr(requests, "get", mock_get)

    return PowerSwitchComponentManager(
        SimulationMode.FALSE,
        "0.0.0.0",
        logger
    )

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
        "proxy": CbfDeviceProxy,
        "patch": PowerSwitch
    }
