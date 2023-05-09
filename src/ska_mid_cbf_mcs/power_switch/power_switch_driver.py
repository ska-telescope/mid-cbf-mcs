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
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from requests.structures import CaseInsensitiveDict
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

__all__ = ["PowerSwitchDriver"]


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
    :param outlet_schema_file: File name for the schema for a list of outlets
    :param outlet_id_list: List of Outlet IDs
    :param logger: a logger for this object to use
    """

    power_mode_conversion = {'true': PowerMode.ON, 'false': PowerMode.OFF, 'on': PowerMode.ON, 'off': PowerMode.OFF}
    """Coversion between PowerMode and outlet state response"""

    query_timeout_s = 4
    """Timeout in seconds used when waiting for a reply from the power switch"""

    def __init__(
        self: PowerSwitchDriver, ip: str, login: str, password: str, model: str, content_type: str, status_url_prefix: str, control_url_prefix: str, url_postfix: str, outlet_schema_file: str, outlet_id_list: List[str], logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # Initialize the base HTTP URL
        self.base_url = f"http://{ip}"

        # Initialize the login credentials
        self.login = login
        self.password = password
        
        # Initialize outlet model
        self.model = model

        # Initialize the API endpoints
        self.status_url_prefix = status_url_prefix
        self.control_url_prefix = control_url_prefix
        self.url_postfix = url_postfix

        # Initialize the request header
        self.content_type = content_type
        self.header = CaseInsensitiveDict()
        self.header["Accept"] = "application/json"
        self.header["X-CSRF"] = "x"
        self.header["Content-Type"] = f"{self.content_type}"

        # Initialize outlets list
        self.outlet_id_list = outlet_id_list
        self.outlets: List(Outlet) = []
        self.outlet_schema_file = outlet_schema_file


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
        assert (
            str(outlet) in self.outlet_id_list
        ), "Outlet ID must be in the allowable outlet_id_list read in from the Config File"

        url = f"{self.base_url}{self.status_url_prefix}/{outlet}{self.url_postfix}"

        print("get_outlet_power_mode::url =", url)
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
                    out = response.text == "true"
                    power_mode = self.power_mode_conversion[str(out).lower()]
                    print(f"power_mode for outlet {outlet} in get outlet power mode fn = ", power_mode)

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
        assert (
            str(outlet) in self.outlet_id_list
        ), "Outlet ID must be in the allowable outlet_id_list read in from the Config File"

        url = f"{self.base_url}{self.control_url_prefix}/{outlet}{self.url_postfix}"
        print(f' turn on outlet url = {url}')
        # url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        # url = f"{self.base_url}/jaws/control/outlets/{outlet}/"

        if self.model == "DLI-PRO":
            data = "value=true"
        elif self.model == "Switched PRO2":
            data = '{"control_action": "on"}'
        else:
            data = ""

        try:
            response = requests.put(
                url=url,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )

            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                print(f"self.outlets[{outlet}] line 252 = ", self.outlets[outlet].__dict__)
                self.outlets[outlet].power_mode = PowerMode.ON
                print("self.outlets[outlet].power_mode == ", self.outlets[outlet].power_mode)
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
        assert (
            str(outlet) in self.outlet_id_list
        ), "Outlet ID must be in the allowable outlet_id_list read in from the Config File"

        url = f"{self.base_url}{self.control_url_prefix}/{outlet}{self.url_postfix}"
        print(f' turn off outlet url = {url}')
        #url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        #url = f"{self.base_url}/jaws/control/outlets/{outlet}/"

        if self.model == "DLI-PRO":
            data = "value=false"
        elif self.model == "Switched PRO2":
            data = '{"control_action": "off"}'
        else:
            data = ""

        try:
            response = requests.put(
                url=url,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            print('response.text turning off outlet in line 302 =', response.text)
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                print(f"self.outlets[{outlet}] = ", self.outlets[outlet])
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
        with open(self.outlet_schema_file, "r") as f:
            schema = json.loads(f.read())

        url = f"{self.base_url}{self.status_url_prefix}"
        print(f'get_outlet_list url = {url}')
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

                # print('resp_list in get outlet list=', resp_list)

                for idx, resp_dict in enumerate(resp_list):
                    try:
                        #print("   ")
                        #print("resp_dict = ", resp_dict)
                        #print("resp_dict[state] =", resp_dict["state"])
                        # power_mode = PowerMode.ON
                        out = resp_dict["state"]
                        power_mode = self.power_mode_conversion[str(out).lower()]
                        print(f'power_mode for {resp_dict["name"]} = ', power_mode)
                        #print("power_mode_conversion = " + self.power_mode_conversion[
                        #    resp_dict["state"]])
                        #print("power mode = " + power_mode)
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
