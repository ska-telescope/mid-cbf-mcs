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
from typing import List

import requests
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from requests.structures import CaseInsensitiveDict
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

__all__ = ["PowerSwitchDriver"]

# TODO: replace these with Kubernetes secrets
# user = "admin"
# password = "1234"


class Outlet:
    """Represents a single outlet in the power switch."""

    def __init__(
        self: Outlet, outlet_ID: str, outlet_name: str, power_mode: PowerMode
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
    """
    A driver for the DLI web power switch.

    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param model: Make and model name of the power switch
    :param content_type: The content type in the request header
    :param status_url_prefix: A portion of the URL to get the outlet status
    :param control_url_prefix: A portion of the URL to turn on/off outlet
    :param url_postfix: A portion of the URL after the outlet
    :param outlets_schema_file: File name for the schema for a list of outlets
    :param outlets_list: List of Outlet IDs
    :param logger: a logger for this object to use
    """

    power_mode_conversion = [PowerMode.OFF, PowerMode.ON]
    """Coversion between PowerMode and outlet state response"""

    query_timeout_s = 4
    """Timeout in seconds used when waiting for a reply from the power switch"""

    def __init__(
        self: PowerSwitchDriver, ip: str, login: str, password: str, model: str, content_type: str, status_url_prefix: str, control_url_prefix: str, url_postfix: str, outlets_schema_file: str, outlets_list: List[str], logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # Initialize the base HTTP URL
        self.base_url = f"http://{ip}"

        # Initialize the API endpoints
        self.status_url_prefix = status_url_prefix
        self.control_url_prefix = control_url_prefix
        self.url_postfix = url_postfix

        # Initialize the request header
        self.header = CaseInsensitiveDict()
        self.header["Accept"] = "application/json"
        self.header["X-CSRF"] = "x"
        self.header["Content-Type"] = "{content_type}"

        # Initialize the login credentials
        self.login = login
        self.password = password
        
        # Initialize outlets list
        self.outlets_list = outlets_list
        self.outlets: List(Outlet) = []
        self.outlets_schema_file = outlets_schema_file

        # Initialize outlet model
        self.model = model

    def initialize(self: PowerSwitchDriver) -> None:
        """
        Initializes any variables needed for further communication with the
        power switch. Should be called once before any of the other methods.
        """
        self.outlets = self.get_outlet_list()

    @property
    def num_outlets(self: PowerSwitchDriver) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        return len(self.outlets)

    @property
    def is_communicating(self: PowerSwitchDriver) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        try:
            response = requests.get(
                url=self.base_url,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            if response.status_code == requests.codes.ok:
                return True
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return False
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return False

    def get_outlet_power_mode(
        self: PowerSwitchDriver, outlet: str
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        :raise AssertionError: if outlet power mode is different than expected
        """
        # !!! FIX THE ASSERT because outlet ID for PSI is a str, not an int
        #assert (
        #    outlet < len(self.outlets) and outlet >= 0
        #), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        url = f"{self.base_url}{self.status_url_prefix}/{outlet}{self.url_postfix}"
        print(f' get outlet power mode url = {url}')
        # url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        # url = f"{self.base_url}/jaws/monitor/outlets/{outlet}/"
        try:
            response = requests.get(
                url=url,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                try:
                    print('response.text =' + response.text)
                    power_mode = self.power_mode_conversion[
                        response.text == "true"
                    ]
                except IndexError:
                    power_mode = PowerMode.UNKNOWN

                if power_mode != self.outlets[outlet].power_mode:
                    raise AssertionError(
                        f"Power mode of outlet {outlet} ({power_mode})"
                        f" is different than the expected mode {self.outlets[outlet].power_mode}"
                    )
                return power_mode
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return PowerMode.UNKNOWN
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return PowerMode.UNKNOWN

    def turn_on_outlet(
        self: PowerSwitchDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        # !!! FIX ASSERT
        #assert (
        #    outlet < len(self.outlets) and outlet >= 0
        #), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        url = f"{self.base_url}{self.control_url_prefix}/{outlet}{self.url_postfix}"
        print(f' turn on outlet url = {url}')
        # url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"

        #data = "value=true"
        # url = f"{self.base_url}/jaws/control/outlets/{outlet}/"
        data = '{"control_action": "off"}'

        try:
            response = requests.put(
                url=url,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            print('response.text turning on outlet=' + response.text)

            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                self.outlets[outlet].power_mode = PowerMode.ON
                return ResultCode.OK, f"Outlet {outlet} power on"
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return ResultCode.FAILED, "HTTP response error"
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return ResultCode.FAILED, "Connection error"

    def turn_off_outlet(
        self: PowerSwitchDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        # !!! FIX ASSERT
        #assert (
        #    outlet < len(self.outlets) and outlet >= 0
        #), f"Outlet ID must be >= 0 and < {len(self.outlets)} (number of outlets in this power switch)"

        url = f"{self.base_url}{self.control_url_prefix}/{outlet}{self.url_postfix}"
        print(f' turn off outlet url = {url}')
        #url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        #data = "value=false"
        #url = f"{self.base_url}/jaws/control/outlets/{outlet}/"
        data = '{"control_action": "off"}'

        try:
            response = requests.put(
                url=url,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            print('response.text turning off outlet=' + response.text)
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                self.outlets[outlet].power_mode = PowerMode.OFF
                return ResultCode.OK, f"Outlet {outlet} power off"
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return ResultCode.FAILED, "HTTP response error"
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return ResultCode.FAILED, "Connection error"

    def get_outlet_list(self: PowerSwitchDriver) -> List(Outlet):
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch,
                 or an empty list if there was an error
        """
        # JSON schema of the response

        with open(self.outlets_schema_file, "r") as f:
            schema = json.loads(f.read())

        print(f"schema = \n {schema}")

        url = f"{self.base_url}{self.status_url_prefix}"
        #url = f"{self.base_url}/restapi/relay/outlets/"
        #url = f"{self.base_url}/jaws/monitor/outlets"
        try:
            response = requests.get(
                url=url,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
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

                print('resp_list t=' + resp_list)

                for idx, resp_dict in enumerate(resp_list):
                    try:
                        print("resp_dict = " + resp_dict)
                        print("resp_dict[state] =" + resp_dict["state"])
                        power_mode = self.power_mode_conversion[
                            resp_dict["state"]
                        ]
                        print("power_mode_conversion = " + self.power_mode_conversion[
                            resp_dict["state"]])
                        print("power mode = " + power_mode)
                    except IndexError:
                        power_mode = PowerMode.UNKNOWN

                    outlets.append(
                        Outlet(
                            outlet_ID=idx,
                            outlet_name=resp_dict["name"],
                            power_mode=power_mode,
                        )
                    )
                return outlets

            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return []

        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return []
