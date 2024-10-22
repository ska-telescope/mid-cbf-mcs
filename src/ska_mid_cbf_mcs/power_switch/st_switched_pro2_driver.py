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
from ska_control_model import PowerState
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.power_switch.pdu_common import Outlet

__all__ = ["STSwitchedPRO2Driver"]


class STSwitchedPRO2Driver:
    """
    A driver for the Server Technology Switched PRO2 PDU.
    The PDU provides a restapi through https.
    Valid outlet IDs are AA1 to AA48


    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param logger: a logger for this object to use
    """

    query_timeout_s = 6
    """Timeout in seconds used when waiting for a reply from the power switch"""

    def __init__(
        self: STSwitchedPRO2Driver,
        ip: str,
        login: str,
        password: str,
        logger: logging.Logger,
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # Initialize the various URLs for monitoring/controlling the power switch
        self.base_url = f"https://{ip}"
        self.outlet_list_url = f"{self.base_url}/jaws/monitor/outlets"
        self.outlet_state_url = (
            f"{self.base_url}/jaws/monitor/outlets/REPLACE_OUTLET"
        )
        self.outlet_control_url = (
            f"{self.base_url}/jaws/control/outlets/REPLACE_OUTLET"
        )

        # Initialize the login credentials
        self.login = login
        self.password = password

        # Initialize the request header
        self.header = CaseInsensitiveDict()
        self.header["Accept"] = "application/json"
        self.header["X-CSRF"] = "x"
        self.header["Content-Type"] = "application/json"

        # Initialize the value of the payload data to pass to
        # the request to turn on/off an outlet
        self.turn_on_action = '{"control_action": "on"}'
        self.turn_off_action = '{"control_action": "off"}'

        # Initialize the expected on/off values of the response
        # to the request to turn on/off an outlet
        self.state_on = "On"
        self.state_off = "Off"

        # valid range AA1 to AA48
        self.outlet_id_list: list[str] = [f"AA{i}" for i in range(1, 49)]

        # Initialize outlets
        self.outlets: list[Outlet] = []

    def initialize(self: STSwitchedPRO2Driver) -> None:
        """
        Initializes any variables needed for further communication with the
        power switch. Should be called once before any of the other methods.
        """
        self.outlets = self.get_outlet_list()

    def stop(self: STSwitchedPRO2Driver) -> None:
        """
        Stops communicating with the PDU and cleans up.
        """
        pass

    @property
    def num_outlets(self: STSwitchedPRO2Driver) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        return len(self.outlets)

    @property
    def is_communicating(self: STSwitchedPRO2Driver) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        try:
            response = requests.get(
                url=self.base_url,
                verify=False,
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

    def get_outlet_power_state(
        self: STSwitchedPRO2Driver, outlet: str
    ) -> PowerState:
        """
        Get the power state of a specific outlet.

        :param outlet: outlet ID
        :return: power state of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        :raise AssertionError: if outlet power state is different than expected
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list {self.outlet_id_list}"

        url = self.outlet_state_url.replace("REPLACE_OUTLET", outlet)
        outlet_idx = self.outlet_id_list.index(outlet)

        self.logger.debug(f"Checking outlet state @ {url}")

        try:
            response = requests.get(
                url=url,
                verify=False,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                try:
                    resp = response.json()
                    # Add [outlet_idx] to access for test
                    state = str(resp["state"])

                    if state == self.state_on:
                        power_state = PowerState.ON
                    elif state == self.state_off:
                        power_state = PowerState.OFF
                    else:
                        power_state = PowerState.UNKNOWN

                except IndexError:
                    power_state = PowerState.UNKNOWN

                if power_state != self.outlets[outlet_idx].power_state:
                    # This error should be noticed in the component manager
                    self.logger.error(
                        f"Power state of outlet ID {outlet} ({power_state})"
                        f" is different than the expected mode {self.outlets[outlet_idx].power_state}"
                    )
                return power_state
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return PowerState.UNKNOWN
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return PowerState.UNKNOWN

    def turn_on_outlet(
        self: STSwitchedPRO2Driver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list {self.outlet_id_list}"

        url = self.outlet_control_url.replace("REPLACE_OUTLET", outlet)
        data = self.turn_on_action
        outlet_idx = self.outlet_id_list.index(outlet)

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
                self.outlets[outlet_idx].power_state = PowerState.ON
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
        self: STSwitchedPRO2Driver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list {self.outlet_id_list}"

        url = self.outlet_control_url.replace("REPLACE_OUTLET", outlet)
        data = self.turn_off_action
        outlet_idx = self.outlet_id_list.index(outlet)

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
                self.outlets[outlet_idx].power_state = PowerState.OFF
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

    def get_outlet_list(self: STSwitchedPRO2Driver) -> list[Outlet]:
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch,
                 or an empty list if there was an error
        """

        url = self.outlet_list_url

        try:
            response = requests.get(
                url=url,
                verify=False,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )

            if response.status_code == requests.codes.ok:
                # Extract the outlet list
                outlets: list[Outlet] = []
                resp_list = response.json()

                for idx, resp_dict in enumerate(resp_list):
                    try:
                        state = str(resp_dict["state"])

                        if state == self.state_on:
                            power_state = PowerState.ON
                        elif state == self.state_off:
                            power_state = PowerState.OFF
                        else:
                            power_state = PowerState.UNKNOWN

                    except IndexError:
                        power_state = PowerState.UNKNOWN

                    outlets.append(
                        Outlet(
                            outlet_ID=str(idx),
                            outlet_name=resp_dict["name"],
                            power_state=power_state,
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
