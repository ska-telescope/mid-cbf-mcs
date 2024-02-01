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

from pysnmp import error as snmp_error
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.hlapi import (  # noqa: F401
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    getCmd,
    setCmd,
    usmHMACMD5AuthProtocol,
    usmNoPrivProtocol,
)
from pysnmp.proto import rfc1902
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.power_switch.pdu_common import Outlet

__all__ = ["ApcSnmpDriver"]


class ApcSnmpDriver:
    """
    A driver for the APC power switch.
    The PDU provides an interface through SNMP.
    Valid outlet IDs are 1 to 24.

    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param logger: a logger for this object to use
    """

    query_timeout_s = 6
    """Timeout in seconds used when waiting for a reply from the power switch"""

    def __init__(
        self: ApcSnmpDriver,
        ip: str,
        login: str,
        password: str,
        logger: logging.Logger,
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # Initialize the IP for monitoring/controlling the power switch
        self.ip = ip

        # valid range 1 to 24
        self.outlet_id_list: List(str) = [str(i) for i in range(1, 25)]

        # Initialize outlets
        self.outlets: List(Outlet) = []

        # Snmp Auth
        self.auth = UsmUserData(
            userName=login,
            authKey=password,
        )

        # Initialize outlet on and off states
        self.state_on = 1
        self.state_off = 2

        # Initialize the on/off inputs
        self.action_on = 1
        self.action_off = 2

    def initialize(self: ApcSnmpDriver) -> None:
        """
        Initializes any variables needed for further communication with the
        power switch. Should be called once before any of the other methods.
        """
        self.outlets = self.get_outlet_list()

    def stop(self: ApcSnmpDriver) -> None:
        """
        Stops communicating with the PDU and cleans up.
        """
        pass

    @property
    def num_outlets(self: ApcSnmpDriver) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        return len(self.outlets)

    @property
    def is_communicating(self: ApcSnmpDriver) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """

        # The system description OID must be returnable and non-empty. If this OID is not returned via SNMP
        # then the communication is unavailable
        sys_description_oid = "1.3.6.1.2.1.1.1.0"

        try:
            cmdGen = cmdgen.CommandGenerator()
            errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
                self.auth,
                cmdgen.UdpTransportTarget((self.ip, 161)),
                cmdgen.MibVariable(sys_description_oid),
                lookupMib=False,
            )
            for oid, val in varBinds:
                sys_description = val

            if sys_description is None or sys_description == "":
                return False
            else:
                return True
        except snmp_error.PySnmpError as e:
            self.logger.error(f"Failed to connect to power switch: {e}")
            return False

    def get_outlet_power_mode(self: ApcSnmpDriver, outlet: str) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        :raise AssertionError: if outlet power mode is different than expected
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list"

        outlet_status_oid = f"1.3.6.1.4.1.318.1.1.4.4.2.1.3.{outlet}"

        try:
            cmdGen = cmdgen.CommandGenerator()
            errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
                self.auth,
                cmdgen.UdpTransportTarget((self.ip, 161)),
                cmdgen.MibVariable(outlet_status_oid),
                lookupMib=False,
            )
            if errorIndication:
                self.logger.info(
                    f"Outlet {outlet} get power mode error: {errorIndication}, status: {errorStatus}, index: {errorIndex}"
                )

            for oid, val in varBinds:
                state = val
            if state == self.state_on:
                power_mode = PowerMode.ON
            elif state == self.state_off:
                power_mode = PowerMode.OFF
            else:
                power_mode = PowerMode.UNKNOWN

            if power_mode != self.outlets[int(outlet) - 1].power_mode:
                self.logger.warning(
                    f"Power mode of outlet ID {outlet} is {power_mode} ({PowerMode(power_mode).name}), "
                    f"which is different than the expected mode {self.outlets[int(outlet) - 1].power_mode} "
                    f"({PowerMode(self.outlets[int(outlet) - 1].power_mode).name})"
                )
            return power_mode
        except snmp_error.PySnmpError as e:
            self.logger.error(f"Failed to connect to power switch: {e}")
            return PowerMode.UNKNOWN

    def turn_on_outlet(
        self: ApcSnmpDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the APC power switch to turn on a specific outlet via SNMP.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list"

        outlet_status_oid = f"1.3.6.1.4.1.318.1.1.4.4.2.1.3.{outlet}"

        try:
            cmdGen = cmdgen.CommandGenerator()
            errorIndication, errorStatus, errorIndex, varBinds = cmdGen.setCmd(
                self.auth,
                cmdgen.UdpTransportTarget((self.ip, 161)),
                (outlet_status_oid, rfc1902.Integer32(self.action_on)),
            )
            if errorIndication:
                self.logger.info(
                    f"Outlet {outlet} powering on error: {errorIndication}, status: {errorStatus}, index: {errorIndex}"
                )
            self.outlets[int(outlet) - 1].power_mode = PowerMode.ON
            return ResultCode.OK, f"Outlet {outlet} power on"
        except snmp_error.PySnmpError as e:
            return ResultCode.FAILED, f"Connection error: {e}"

    def turn_off_outlet(
        self: ApcSnmpDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the APC power switch to turn off a specific outlet via SNMP.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list"

        outlet_status_oid = f"1.3.6.1.4.1.318.1.1.4.4.2.1.3.{outlet}"

        try:
            cmdGen = cmdgen.CommandGenerator()

            errorIndication, errorStatus, errorIndex, varBinds = cmdGen.setCmd(
                self.auth,
                cmdgen.UdpTransportTarget((self.ip, 161)),
                (outlet_status_oid, rfc1902.Integer32(self.action_off)),
            )
            if errorIndication:
                self.logger.info(
                    f"Outlet {outlet} powering off error: {errorIndication}, status: {errorStatus}, index: {errorIndex}"
                )
            self.outlets[int(outlet) - 1].power_mode = PowerMode.OFF
            return ResultCode.OK, f"Outlet {outlet} power off"
        except snmp_error.PySnmpError as e:
            return ResultCode.FAILED, f"Connection error: {e}"

    def get_outlet_list(self: ApcSnmpDriver) -> List(Outlet):
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch,
                 or an empty list if there was an error
        """

        # Extract the outlet list
        outlets: List(Outlet) = []

        # Create cmdgen for snmp requests
        cmdGen = cmdgen.CommandGenerator()

        for idx in self.outlet_id_list:
            outlet_status_oid = f"1.3.6.1.4.1.318.1.1.4.4.2.1.3.{idx}"
            try:
                (
                    errorIndication,
                    errorStatus,
                    errorIndex,
                    varBinds,
                ) = cmdGen.getCmd(
                    self.auth,
                    cmdgen.UdpTransportTarget((self.ip, 161)),
                    cmdgen.MibVariable(outlet_status_oid),
                    lookupMib=False,
                )
                for oid, val in varBinds:
                    state = val
                if state == self.state_on:
                    power_mode = PowerMode.ON
                elif state == self.state_off:
                    power_mode = PowerMode.OFF
                else:
                    power_mode = PowerMode.UNKNOWN
                outlets.append(
                    Outlet(
                        outlet_ID=str(idx),
                        outlet_name=f"outlet_{idx}",
                        power_mode=power_mode,
                    )
                )
            except snmp_error.PySnmpError as e:
                self.logger.error(f"Failed to connect to power switch: {e}")
                return []
        return outlets
