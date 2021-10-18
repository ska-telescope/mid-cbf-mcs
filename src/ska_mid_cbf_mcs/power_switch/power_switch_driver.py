# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging
import requests
from requests.structures import CaseInsensitiveDict
from typing import List
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from ska_mid_cbf_mcs.commons.global_enum import PowerMode
from ska_tango_base.commands import ResultCode

__all__ = [
    "PowerSwitchDriver"
]

# TODO: replace these with Kubernetes secrets
user = "admin"
password = "1234"

class Outlet:
    """Represents a single outlet in the power switch."""
    def __init__(
        self: Outlet,
        outlet_ID: int,
        outlet_name: str,
        power_mode: PowerMode
    ) -> None:
        """
        Initialize a new instance.

        :param outlet_ID: ID of the outlet
        :param outlet_name: name of the outlet
        :param power_mode: current power mode of the outlet
        """
        self.outlet_ID = outlet_ID
        self.outlet_name = outlet_name
        self.power_mode = power_mode

class PowerSwitchDriver:
    """A driver for the DLI web power switch."""

    # Coversion between PowerMode and outlet state response
    power_mode_conversion = [PowerMode.OFF, PowerMode.ON]

    query_timeout_s = 4

    def __init__(
        self: PowerSwitchDriver,
        ip: str,
        logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.

        :param ip: IP address of the power switch
        :param logger: a logger for this object to use
        """
        self.logger = logger

        # Initialize the base HTTP URL
        self.base_url = f"http://{ip}"

        # Initialize the request header
        self.header = CaseInsensitiveDict()
        self.header['Accept'] = 'application/json'
        self.header['X-CSRF'] = 'x'
        self.header['Content-Type'] = "application/x-www-form-urlencoded"

        self.outlets: List(Outlet) = []

    @property
    def num_outlets(self: PowerSwitchDriver) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        self.outlets = self.get_outlet_list()
        return len(self.outlets)

    @property
    def is_communicating(self: PowerSwitchDriver) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        try:
            response = requests.get(url=self.base_url, headers=self.header,
                auth=(user, password), timeout=self.query_timeout_s)
            if response.status_code == requests.codes.ok:
                return True
            else:
                self.logger.error(f"HTTP response error: {response.status_code}")
                return False
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            self.logger.error("Failed to connect to power switch")
            return False

    def get_outlet_power_mode(
        self: PowerSwitchDriver,
        outlet: int
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet < len(self.outlets) and outlet >= 0
        ), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)" 

        return self.outlets[outlet].power_mode

    def turn_on_outlet(
        self: PowerSwitchDriver,
        outlet: int
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet < len(self.outlets) and outlet >= 0
        ), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        data = "value=true"

        try:
            response = requests.put(url=url, data=data, headers=self.header,
                auth=(user, password), timeout=self.query_timeout_s)
            if response.status_code in [requests.codes.ok, requests.codes.no_content]:
                self.outlets[outlet].power_mode = PowerMode.ON
                return ResultCode.OK, f"Outlet {outlet} power on"
            else:
                self.logger.error(f"HTTP response error: {response.status_code}")
                return ResultCode.FAILED, "HTTP response error"
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            self.logger.error("Failed to connect to power switch")
            return ResultCode.FAILED, "Connection error"
        
    def turn_off_outlet(
        self: PowerSwitchDriver,
        outlet: int
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet < len(self.outlets) and outlet >= 0
        ), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        data = "value=false"

        try:
            response = requests.put(url=url, data=data, headers=self.header,
                auth=(user, password), timeout=self.query_timeout_s)
            if response.status_code in [requests.codes.ok, requests.codes.no_content]:
                self.outlets[outlet].power_mode = PowerMode.OFF
                return ResultCode.OK, f"Outlet {outlet} power off"
            else:
                self.logger.error(f"HTTP response error: {response.status_code}")
                return ResultCode.FAILED, "HTTP response error"
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            self.logger.error("Failed to connect to power switch")
            return ResultCode.FAILED, "Connection error"

    def get_outlet_list(
        self: PowerSwitchDriver
    ) -> List(Outlet):
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch,
                 or an empty list if there was an error
        """
        # JSON schema of the response
        schema = {
            "name": "string",
            "locked": "boolean",
            "critical": "boolean",
            "cycle_delay": "integer",
            "state": "boolean",
            "physical_state": "boolean",
            "transient_state": "boolean"
        }

        url = f"{self.base_url}/restapi/relay/outlets/"
        try:
            response = requests.get(url=url, headers=self.header, auth=(user, password),
                timeout=self.query_timeout_s)
            if response.status_code == requests.codes.ok:
                # Validate the response has the expected format
                try:
                    validate(instance=response.text, schema=schema)
                except ValidationError as e:
                    self.logger.error(f"JSON validation error: {e}")
                    return []

                # Extract the outlet list
                outlets: List(Outlet) = []
                resp_list = response.json()
                for idx, resp_dict in enumerate(resp_list):
                    try:
                        power_mode = self.power_mode_conversion[resp_dict['state']]
                    except IndexError:
                        power_mode = PowerMode.UNKNOWN

                    outlets.append(Outlet(
                        outlet_ID = idx,
                        outlet_name = resp_dict['name'],
                        power_mode = power_mode
                    ))
                return outlets

            else:
                self.logger.error(f"HTTP response error: {response.status_code}")
                return []

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            self.logger.error("Failed to connect to power switch")
            return []