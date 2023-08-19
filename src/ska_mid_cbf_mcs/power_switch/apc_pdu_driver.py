#
# This file is part of the SKA Mid.CBF MCS project
#
# The driver to remotely control the outlets of APC PDUs
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging
import re
import socket

import paramiko
from ska_mid_cbf_mcs.power_switch.pdu_common import Outlet
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode


class ApcPduDriver:
    """
    A driver for the APC AP8681 PDU.
    The PDU is controlled by a command line interface through SSH.
    Valid outlet IDs are 1 to 24.


    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param logger: a logger for this object to use
    """

    def __init__(
        self: ApcPduDriver,
        ip: str,
        login: str,
        password: str,
        logger: logging.Logger,
    ) -> None:
        self.logger = logger
        self.ip = ip
        self.user = login  # todo: use kubernetes secrets
        self.password = password

        # valid range 1 to 24
        self.outlet_id_list: List(str) = [f"{i}" for i in range(1, 25)]

        self.outlets: List(Outlet) = []

    def initialize(self: ApcPduDriver) -> None:
        """
        Initializes any variables needed for further communication with the
        power switch. Should be called once before any of the other methods.
        """
        self.outlets = self.get_outlet_list()

    @property
    def num_outlets(self: ApcPduDriver) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        return len(self.outlet_id_list)

    @property
    def is_communicating(self: ApcPduDriver) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.user, password=self.password)
        except (
            paramiko.ssh_exception.AuthenticationException,
            paramiko.ssh_exception.SSHException,
        ) as e:
            self.logger.error(f"Failed to connect to PDU: {e}")
            return False
        finally:
            ssh.close()
        return True

    def get_outlet_list(self: ApcPduDriver) -> List(Outlet):
        out_list = []
        outlets = self._outlet_status(
            "all"
        )  # (outlet id, outlet name, On/Off)
        for o in outlets:
            if o[2] == "On":
                status = PowerMode.ON
            elif o[2] == "Off":
                status = PowerMode.OFF
            else:
                status = PowerMode.UNKNOWN
            out_list.append(Outlet(o[0], o[1], status))
        return out_list

    def get_outlet_power_mode(self: ApcPduDriver, outlet: str) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID ("all" is not supported)
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        :raise AssertionError: if outlet power mode is different than expected
        """
        assert outlet in self.outlet_id_list, "Valid outlet IDs are 1 to 24"

        status = self._outlet_status(outlet)[0]
        if status is None:
            self.logger.error(f"Failed to get the status of outlet {outlet}")
            return PowerMode.UNKNOWN
        if "On" in status[2]:
            return PowerMode.ON
        elif "Off" in status[2]:
            return PowerMode.OFF
        else:
            self.logger.error(f"Unexpected outlet {outlet} status")
            return PowerMode.UNKNOWN

    def turn_on_outlet(
        self: ApcPduDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert outlet in self.outlet_id_list, "Valid outlet IDs are 1 to 24"

        (retval, output) = self._outlet_on(outlet)
        if not retval:
            err = f"Failed to turn on PDU outlet {outlet}: {output}"
            self.logger.error(err)
            return (ResultCode.FAILED, err)
        return ResultCode.OK, f"Outlet {outlet} power on"

    def turn_off_outlet(
        self: ApcPduDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert outlet in self.outlet_id_list, "Valid outlet IDs are 1 to 24"

        (retval, output) = self._outlet_off(outlet)
        if not retval:
            err = f"Failed to turn off PDU outlet {outlet}: {output}"
            self.logger.error(err)
            return (ResultCode.FAILED, err)
        return ResultCode.OK, f"Outlet {outlet} power off"

    def _outlet_on(self: ApcPduDriver, outlet: str):
        return self._cmd_common(outlet, "olOn")

    def _outlet_off(self: ApcPduDriver, outlet: str):
        return self._cmd_common(outlet, "olOff")

    def _outlet_status(self: ApcPduDriver, outlet: str):
        # Note: if outlet == 'all', all outlets will return status
        (status, out) = self._cmd_common(outlet, "olStatus")
        if status:
            # returns list of (outlet id, outlet name, On/Off)
            matches = re.findall("([0-9]+): ([A-Za-z0-9 ]+): (O[nf]+)", out)
            return matches
        else:
            return None

    def _cmd_common(self: ApcPduDriver, outlet: str, cmd: str):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(self.ip, username=self.user, password=self.password)
            ch = ssh.invoke_shell()
            _ = ch.recv(4096).decode("utf-8")  # ignore the log in banner
            ch.send(f"{cmd} {outlet}\n")
            out = ch.recv(1024).decode("utf-8")
            if "E000: Success" in out:
                print(f"{cmd} {outlet} completed successfully")
                return (True, out)
            else:
                print(f"{cmd} {outlet} failed")
                return (False, out)
        except (
            paramiko.ssh_exception.AuthenticationException,
            paramiko.ssh_exception.SSHException,
        ) as e:
            self.logger.error(f"Failed to connect to PDU: {e}")
        except socket.timeout:
            self.logger.error("APC PDU - Socket timeout error")
            return (False, None)
        finally:
            ssh.close()
