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
import time
from threading import Lock, Thread

import paramiko
from ska_control_model import PowerState
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_tdc_mcs.power_switch.pdu_common import Outlet


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
        self.outlet_id_list = [f"{i}" for i in range(1, 25)]

        self.mutex = Lock()
        self.list_outlets_thread = None
        self.end_thread = False
        self.num_failed_polls = 0

        # init outlet states to unknown first. The outlets can be polled
        # before initialize is called.
        self.outlets = [
            Outlet(
                outlet_ID=id, outlet_name="", power_state=PowerState.UNKNOWN
            )
            for id in self.outlet_id_list
        ]

    def initialize(self: ApcPduDriver) -> None:
        """
        Initializes any variables needed for further communication with the
        power switch. Should be called once before any of the other methods.
        """
        self.end_thread = False
        self.list_outlets_thread = Thread(target=self._poll_outlets)
        self.list_outlets_thread.start()

    def stop(self: ApcPduDriver) -> None:
        """
        Stops communicating with the PDU and cleans up.
        """
        self.end_thread = True
        if self.list_outlets_thread is not None:
            self.list_outlets_thread.join()

    def _poll_outlets(self: ApcPduDriver) -> None:
        n_fail_to_print_err = 3
        sleep_t = 20
        self.logger.info(f"Starting to poll the PDU every {sleep_t} seconds")
        while not self.end_thread:
            outlets_tmp = self.get_outlet_list()
            # this is not a critical failure. Log a warning
            # and hope it works next time.
            if outlets_tmp is None:
                self.num_failed_polls += 1
                warn = (
                    f"Failed to poll PDU outlets {self.num_failed_polls} times"
                )
                self.logger.warning(warn)
                if self.num_failed_polls == n_fail_to_print_err:
                    self.logger.error(
                        f"Failed to poll PDU outlets {n_fail_to_print_err} times consecutively. The PDU likely cannot be reached."
                    )
            else:
                self.num_failed_polls = 0
                with self.mutex:
                    self.outlets = outlets_tmp
            time.sleep(sleep_t)

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

    def get_outlet_list(self: ApcPduDriver) -> list[Outlet]:
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch,
                 or an empty list if there was an error.
        """
        out_list = []
        outlets = self._outlet_status(
            "all"
        )  # (outlet id, outlet name, On/Off)
        if outlets is None:
            return None
        for o in outlets:
            if o[2] == "On":
                status = PowerState.ON
            elif o[2] == "Off":
                status = PowerState.OFF
            else:
                status = PowerState.UNKNOWN
            out_list.append(Outlet(o[0], o[1], status))
        return out_list

    def get_outlet_power_state(self: ApcPduDriver, outlet: str) -> PowerState:
        """
        Get the power state of a specific outlet.

        :param outlet: outlet ID ("all" is not supported)
        :return: power state of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        :raise AssertionError: if outlet power state is different than expected
        """
        assert outlet in self.outlet_id_list, "Valid outlet IDs are 1 to 24"
        outlet_idx = self.outlet_id_list.index(outlet)
        with self.mutex:
            power_state = self.outlets[outlet_idx].power_state
        return power_state

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
        outlet_idx = self.outlet_id_list.index(outlet)
        with self.mutex:
            self.outlets[outlet_idx].power_state = PowerState.ON
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
        outlet_idx = self.outlet_id_list.index(outlet)
        with self.mutex:
            self.outlets[outlet_idx].power_state = PowerState.OFF
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
            self.logger.debug(f"PDU command output: {out}")
            if "E000: Success" in out:
                self.logger.info(f"{cmd} {outlet} completed successfully")
                return (True, out)
            else:
                self.logger.error(f"{cmd} {outlet} failed")
                return (False, out)
        except (
            paramiko.ssh_exception.AuthenticationException,
            paramiko.ssh_exception.SSHException,
            paramiko.ssh_exception.NoValidConnectionsError,
            paramiko.ssh_exception.BadAuthenticationType,
            paramiko.ssh_exception.BadHostKeyException,
        ) as e:
            self.logger.error(f"Failed to connect to PDU: {e}")
            return (False, None)
        except socket.timeout:
            self.logger.error("APC PDU - Socket timeout error")
            return (False, None)
        finally:
            ssh.close()
