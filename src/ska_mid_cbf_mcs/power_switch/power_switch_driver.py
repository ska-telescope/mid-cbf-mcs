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

import json
import logging
from typing import List

import requests
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

    :param protocol: Connection protocol (HTTP or HTTPS) for the power switch
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

    power_mode_conversion = {
        "true": PowerMode.ON,
        "false": PowerMode.OFF,
        "on": PowerMode.ON,
        "off": PowerMode.OFF,
    }
    """Coversion between PowerMode and outlet state response"""

    query_timeout_s = 6
    """Timeout in seconds used when waiting for a reply from the power switch"""

    def __init__(
        self: PowerSwitchDriver,
        protocol: str,
        ip: str,
        login: str,
        password: str,
        model: str,
        content_type: str,
        status_url_prefix: str,
        control_url_prefix: str,
        url_postfix: str,
        outlet_schema_file: str,
        outlet_id_list: List[str],
        logger: logging.Logger,
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # Initialize the base HTTP URL
        self.base_url = f"{protocol}://{ip}"

        # Initialize the login credentials
        self.login = login
        self.password = password

        # Initialize outlet model
        self.model = model

        # Initialize the request header
        self.content_type = content_type
        self.header = CaseInsensitiveDict()
        self.header["Accept"] = "application/json"
        self.header["X-CSRF"] = "x"
        self.header["Content-Type"] = f"{self.content_type}"

        # Initialize and populate the outlet_id_list as a list
        # of strings, not DevStrings
        self.outlet_id_list: List(str) = []
        for item in outlet_id_list:
            self.outlet_id_list.append(item)
        print(
            " --- LINE 106 --- power_switch_driver::__init__() --- self.outlet_id_list == ",
            self.outlet_id_list,
        )

        # Initialize outlets
        self.outlets: List(Outlet) = []

        # Initialize schema file
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
        print(
            " --- LINE 129 --- power_switch_driver::num_outlets() --- num_outlets == ",
            len(self.outlets),
        )
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
                verify=False,
                # headers=self.header,
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

        print(
            " --- LINE 174 --- power_switch_driver::get_outlet_power_mode --- outlet == ",
            outlet,
        )
        print(" --- LINE 175 --- power_switch_driver::get_outlet_power_mode --- outlet_id_list == ", self.outlet_id_list)
        print(" --- LINE 176 --- power_switch_driver::get_outlet_power_mode --- type(outlet_id_list) == ", type(self.outlet_id_list))

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list read in from the Config File"

        if self.model == "DLI-PRO":
            url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
        elif self.model == "Switched PRO2":
            url = f"{self.base_url}/jaws/monitor/outlets/{outlet}"
        else:
            url = self.base_url

        # url = f"{self.base_url}{self.status_url_prefix}/{outlet}{self.url_postfix}"
        print(
            " --- LINE 189 --- power_switch_driver::get_outlet_power_mode --- url == ",
            url,
        )
        # print("headers = ", self.header)

        print(" --- LINE 190 --- power_switch_driver::get_outlet_power_mode --- type(outlet) == ", type(outlet) )

        outlet_idx = self.outlet_id_list.index(outlet)
        print(
            " --- LINE 195 --- power_switch_driver::get_outlet_power_mode --- outlet_idx == ",
            outlet_idx,
        )
        print(
            " --- LINE 196 --- power_switch_driver::get_outlet_power_mode --- self.outlet_id_list == ",
            self.outlet_id_list
        )

        # outlet_idx = self.outlet_id_list.index(outlet)
        print(" --- LINE 200 --- power_switch_driver::get_outlet_power_mode --- outlet_idx == ", outlet_idx)
        try:
            response = requests.get(
                url=url,
                verify=False,
                # headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                try:
                    if self.model == "DLI-PRO":
                        out = response.text == "true"
                    elif self.model == "Switched PRO2":
                        json = response.json()
                        out = json["state"]

                    print(
                        " --- LINE 212 --- power_switch_driver::get_outlet_power_mode --- out == ",
                        out,
                    )
                    power_mode = self.power_mode_conversion[str(out).lower()]
                    print(
                        f"power_mode for outlet {outlet} in get outlet power mode fn = ",
                        power_mode,
                    )

                except IndexError:
                    power_mode = PowerMode.UNKNOWN

                # print(f" --- LINE 219 --- power_switch_driver::get_outlet_power_mode --- self.outlets[{outlet_idx}] == {self.outlets[outlet_idx].__dict__}")
                if power_mode != self.outlets[outlet_idx].power_mode:
                    raise AssertionError(
                        f"Power mode of outlet ID {outlet} ({power_mode})"
                        f" is different than the expected mode {self.outlets[outlet_idx].power_mode}"
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
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list read in from the Config File"

        if self.model == "DLI-PRO":
            url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
            data = "value=true"
        elif self.model == "Switched PRO2":
            url = f"{self.base_url}/jaws/control/outlets/{outlet}"
            data = '{"control_action": "on"}'
        else:
            url = self.base_url
            data = ""

        # url = f"{self.base_url}{self.control_url_prefix}/{outlet}{self.url_postfix}"
        print(
            f" --- LINE 263 --- power_switch_driver::turn_on_outlet --- url == {url}"
        )

        outlet_idx = self.outlet_id_list.index(outlet)
        print(
            " --- LINE 273 --- power_switch_driver::turn_on_outlet --- outlet_idx == ",
            outlet_idx,
        )
        # print("header = ", self.header)
        try:
            response = requests.patch(
                url=url,
                verify=False,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )

            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                print(
                    f" --- LINE 289 --- power_switch_driver::turn_on_outlet --- self.outlets[{outlet}] == ",
                    self.outlets[outlet_idx].__dict__,
                )
                self.outlets[outlet_idx].power_mode = PowerMode.ON
                print(
                    f" --- LINE 291 --- power_switch_driver::turn_on_outlet --- self.outlets[{outlet_idx}].power_mode for outlet {outlet} == ",
                    self.outlets[outlet_idx].power_mode,
                )
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
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list read in from the Config File"

        # url = f"{self.base_url}{self.control_url_prefix}/{outlet}{self.url_postfix}"

        if self.model == "DLI-PRO":
            url = f"{self.base_url}/restapi/relay/outlets/{outlet}/state/"
            data = "value=false"
        elif self.model == "Switched PRO2":
            url = f"{self.base_url}/jaws/control/outlets/{outlet}"
            data = '{"control_action": "off"}'
        else:
            url = self.base_url
            data = ""

        print(
            f" --- LINE 334 --- power_switch_driver::turn_off_outlet ---  url == {url}"
        )
        outlet_idx = self.outlet_id_list.index(outlet)
        print(
            " --- LINE 336 --- power_switch_driver::turn_off_outlet --- outlet_idx == ",
            outlet_idx,
        )
        try:
            response = requests.patch(
                url=url,
                verify=False,
                data=data,
                # headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            # print(
            #     " --- LINE 346 --- power_switch_driver::turn_off_outlet --- response.text turning off outlet in line 346 == ",
            #     response.text,
            # )
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                print(
                    f" --- LINE 351 --- power_switch_driver::turn_off_outlet --- self.outlets[{outlet}] = ",
                    self.outlets[outlet_idx],
                )
                self.outlets[outlet_idx].power_mode = PowerMode.OFF
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

        if self.model == "DLI-PRO":
            url = f"{self.base_url}/restapi/relay/outlets/"
        elif self.model == "Switched PRO2":
            url = f"{self.base_url}/jaws/monitor/outlets"
        else:
            url = self.base_url
        # url = f"{self.base_url}{self.status_url_prefix}"

        print(
            f" --- LINE 386 --- power_switch_driver::get_outlet_list ---  url == {url}"
        )

        try:
            response = requests.get(
                url=url,
                verify=False,
                # headers=self.header,
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

                for idx, resp_dict in enumerate(resp_list):
                    try:
                        # power_mode = PowerMode.ON
                        print(
                            " --- LINE 414 ---  power_switch_driver::get_outlet_list --- idx == ",
                            idx,
                        )
                        print(
                            " --- LINE 415 ---  power_switch_driver::get_outlet_list --- resp_dict == ",
                            resp_dict,
                        )
                        out = resp_dict["state"]
                        print(
                            " --- LINE 416 ---  power_switch_driver::get_outlet_list --- out == ",
                            out,
                        )
                        power_mode = self.power_mode_conversion[
                            str(out).lower()
                        ]
                        print(
                            f' --- LINE 417 ---  power_switch_driver::get_outlet_list --- power_mode for {resp_dict["name"]} == ',
                            power_mode,
                        )
                    except IndexError:
                        power_mode = PowerMode.UNKNOWN

                    outlets.append(
                        Outlet(
                            outlet_ID=str(idx),
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

        except requests.exceptions.ConnectTimeout:
            print("CONNECTION TIMEOUT AFTER ", self.query_timeout_s)
            self.logger.error("CONNECTION TIMEOUT")
        except requests.exceptions.TooManyRedirects:
            print("TOO MANY REDIRECTS")
            self.logger.error("TOO MANY REDIRECTS")
        except requests.exceptions.ConnectionError:
            print("CONNECTION ERROR")
            self.logger.error("Failed to connect to power switch")
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
            return []
