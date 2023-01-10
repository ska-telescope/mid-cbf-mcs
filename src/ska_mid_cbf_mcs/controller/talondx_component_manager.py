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
import os

import backoff
import tango
from paramiko import AutoAddPolicy, SSHClient
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
from scp import SCPClient, SCPException
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import SimulationMode

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

__all__ = ["TalonDxComponentManager"]


class TalonDxComponentManager:
    """
    A component manager for the Talon-DX boards. Used to configure and start
    the Tango applications on the HPS of each board.
    """

    def __init__(
        self: TalonDxComponentManager,
        talondx_config_path: str,
        simulation_mode: SimulationMode,
        logger: logging.Logger,
    ) -> None:
        """
        Initialise a new instance.

        :param talondx_config_path: path to the directory containing configuration
                                    files and artifacts for the Talon boards
        :param simulation_mode: simulation mode identifies if the real Talon boards or
                                a simulator should be used; note that currently there
                                is no simulator for the Talon boards, so the component
                            manager does nothing when in simulation mode
        :param logger: a logger for this object to use
        :param logger: a logger for this object to use
        """
        self.talondx_config_path = talondx_config_path
        self.simulation_mode = simulation_mode
        self.logger = logger

    def configure_talons(self: TalonDxComponentManager) -> ResultCode:
        """
        Performs all actions to configure the Talon boards after power on and
        start the HPS device servers. This includes: copying the device server
        binaries and FPGA bitstream to the Talon boards, starting the HPS master
        device server and sending the configure command to each DsHpsMaster.

        :return: ResultCode.FAILED if any operations failed, else ResultCode.OK
        """
        # Simulation mode does not do anything yet
        if self.simulation_mode == SimulationMode.TRUE:
            return ResultCode.OK

        # Try to read in the configuration file
        try:
            config_path = f"{self.talondx_config_path}/talondx-config.json"
            with open(config_path) as json_fd:
                self.talondx_config = json.load(json_fd)
        except IOError:
            self.logger.error(f"Could not open {config_path} file")
            return ResultCode.FAILED

        if self._setup_tango_host_file() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._configure_talon_networking() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._copy_binaries_and_bitstream() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._start_hps_master() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._create_hps_master_device_proxies() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._configure_hps_master() == ResultCode.FAILED:
            return ResultCode.FAILED

        return ResultCode.OK

    def _setup_tango_host_file(
        self: TalonDxComponentManager,
    ) -> None:
        """
        Copy the hps_master_mcs.sh file from mnt into mnt/talondx-config

        :return: ResultCode.OK if all artifacts were copied successfully,
                 otherwise ResultCode.FAILED
        """
        with open("hps_master_mcs_tmp.sh") as hps_master_file_tmp:
            namespace = os.getenv("NAMESPACE")
            tango_host = os.getenv("TANGO_HOST").split(":")
            db_service_name = tango_host[0]
            port = tango_host[1]
            hostname = f"{db_service_name}.{namespace}.svc.cluster.local"
            print(f"HOSTNAME: {hostname}")
            replaced_text = hps_master_file_tmp.read().replace(
                "<hostname>:<port>", f"{hostname}:{port}"
            )
        with open("hps_master_mcs.sh", "w") as hps_master_file:
            hps_master_file.write(replaced_text)

    def _secure_copy(
        self: TalonDxComponentManager,
        ssh_client: SSHClient,
        src: str,
        dest: str,
    ) -> None:
        """
        Execute a secure file copy to the specified target address.

        :param ssh_client: SSH client for the Talon board we are trying to SCP to
        :param src: Source file path
        :param dest: Destination file path

        :raise SCPException: if the file copy fails
        """
        with SCPClient(ssh_client.get_transport()) as scp_client:
            scp_client.put(src, remote_path=dest)

    def _configure_talon_networking(
        self: TalonDxComponentManager,
    ) -> ResultCode:
        """
        Configure the networking of the boards including DNS nameserver
        and ifconfig for default gateway

        :return: ResultCode.OK if all artifacts were copied successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config["config_commands"]:
            try:
                ip = talon_cfg["ip_address"]
                target = talon_cfg["target"]
                # timeout for the first attempt at SSH connection
                # to the Talon boards after boot-up
                talon_first_connect_timeout = talon_cfg[
                    "talon_first_connect_timeout"
                ]
                self.logger.info(
                    f"Copying FPGA bitstream and HPS binaries to {target}"
                )
                with SSHClient() as ssh_client:

                    @backoff.on_exception(
                        backoff.expo,
                        NoValidConnectionsError,
                        max_time=talon_first_connect_timeout,
                    )
                    def make_first_connect(
                        ip: str, ssh_client: SSHClient
                    ) -> None:
                        """
                        Attempts to connect to the Talon board for the first time
                        after power-on.

                        :param ip: IP address of the board
                        :param ssh_client: SSH client to use for connection
                        """
                        ssh_client.connect(ip, username="root", password="")

                    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
                    make_first_connect(ip, ssh_client)

                    environment = os.getenv("ENVIRONMENT")
                    host_ip = os.getenv("MINIKUBE_HOST_IP")
                    print(f"HOST IP: {host_ip}")

                    if environment == "minikube":
                        ssh_chan = ssh_client.get_transport().open_session()
                        ssh_chan.exec_command(
                            "echo 'nameserver 172.17.0.95' > /etc/resolv.conf"
                        )
                        exit_status = ssh_chan.recv_exit_status()
                        if exit_status != 0:
                            self.logger.error(
                                f"Error configuring nameserver: {exit_status}"
                            )
                            ret = ResultCode.FAILED

                        ssh_chan = ssh_client.get_transport().open_session()
                        ssh_chan.exec_command(
                            f"ip route add default via {host_ip} dev eth0"
                        )
                        exit_status = ssh_chan.recv_exit_status()
                        if exit_status != 0:
                            self.logger.error(
                                f"Error configuring default ip gateway: {exit_status}"
                            )
                            ret = ResultCode.FAILED

                    else:
                        ssh_chan = ssh_client.get_transport().open_session()
                        ssh_chan.exec_command(
                            "echo 'nameserver 192.168.128.47' > /etc/resolv.conf"
                        )
                        exit_status = ssh_chan.recv_exit_status()
                        if exit_status != 0:
                            self.logger.error(
                                f"Error configuring nameserver: {exit_status}"
                            )
                            ret = ResultCode.FAILED

            except NoValidConnectionsError:
                self.logger.error(
                    f"NoValidConnectionsError while connecting to {target}"
                )
                ret = ResultCode.FAILED
            except SSHException:
                self.logger.error(f"SSHException while talking to {target}")
                ret = ResultCode.FAILED

        return ret

    def _copy_binaries_and_bitstream(
        self: TalonDxComponentManager,
    ) -> ResultCode:
        """
        Copy the relevant device server binaries and FPGA bitstream to each
        Talon board.

        :return: ResultCode.OK if all artifacts were copied successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config["config_commands"]:
            try:
                ip = talon_cfg["ip_address"]
                target = talon_cfg["target"]
                # timeout for the first attempt at SSH connection
                # to the Talon boards after boot-up
                talon_first_connect_timeout = talon_cfg[
                    "talon_first_connect_timeout"
                ]
                self.logger.info(
                    f"Copying FPGA bitstream and HPS binaries to {target}"
                )

                with SSHClient() as ssh_client:

                    @backoff.on_exception(
                        backoff.expo,
                        NoValidConnectionsError,
                        max_time=talon_first_connect_timeout,
                    )
                    def make_first_connect(
                        ip: str, ssh_client: SSHClient
                    ) -> None:
                        """
                        Attempts to connect to the Talon board for the first time
                        after power-on.

                        :param ip: IP address of the board
                        :param ssh_client: SSH client to use for connection
                        """
                        ssh_client.connect(ip, username="root", password="")

                    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
                    make_first_connect(ip, ssh_client)
                    ssh_chan = ssh_client.get_transport().open_session()

                    # Make the DS binaries directory
                    src_dir = f"{self.talondx_config_path}"
                    dest_dir = talon_cfg["ds_path"]
                    ssh_chan.exec_command(f"mkdir -p {dest_dir}")
                    exit_status = ssh_chan.recv_exit_status()
                    if exit_status != 0:
                        self.logger.error(
                            f"Error creating directory {dest_dir} on {target}: {exit_status}"
                        )
                        ret = ResultCode.FAILED
                        continue

                    # Copy the HPS master binary
                    self._secure_copy(
                        ssh_client=ssh_client,
                        src=f"{src_dir}/dshpsmaster/bin/dshpsmaster",
                        dest="/lib/firmware/hps_software",
                    )

                    # Copy HPS master run script
                    self._secure_copy(
                        ssh_client=ssh_client,
                        src="hps_master_mcs.sh",
                        dest="/lib/firmware/hps_software",
                    )

                    # Copy the remaining DS binaries
                    for binary_name in talon_cfg["devices"]:
                        self._secure_copy(
                            ssh_client=ssh_client,
                            src=f"{src_dir}/{binary_name}/bin/{binary_name}",
                            dest=dest_dir,
                        )

                    # Copy the FPGA bitstream
                    dest_dir = talon_cfg["fpga_path"]
                    ssh_chan = ssh_client.get_transport().open_session()
                    ssh_chan.exec_command(f"mkdir -p {dest_dir}")
                    exit_status = ssh_chan.recv_exit_status()
                    if exit_status != 0:
                        self.logger.error(
                            f"Error creating directory {dest_dir} on {target}: {exit_status}"
                        )
                        ret = ResultCode.FAILED
                        continue

                    fpga_dtb_name = talon_cfg["fpga_dtb_name"]
                    self._secure_copy(
                        ssh_client=ssh_client,
                        src=f"{src_dir}/fpga-talon/bin/{fpga_dtb_name}",
                        dest=dest_dir,
                    )

                    fpga_rbf_name = talon_cfg["fpga_rbf_name"]
                    self._secure_copy(
                        ssh_client=ssh_client,
                        src=f"{src_dir}/fpga-talon/bin/{fpga_rbf_name}",
                        dest=dest_dir,
                    )

            except NoValidConnectionsError as e:
                self.logger.error(f"{e}")
                self.logger.error(
                    f"NoValidConnectionsError while connecting to {target}"
                )
                ret = ResultCode.FAILED
            except SSHException as e:
                self.logger.error(f"{e}")
                self.logger.error(f"SSHException while talking to {target}")
                ret = ResultCode.FAILED
            except SCPException as e:
                self.logger.error(f"{e}")
                self.logger.error(f"Failed to copy file to {target}")
                ret = ResultCode.FAILED
            except FileNotFoundError as e:
                self.logger.error(f"{e}")
                self.logger.error(
                    f"Failed to copy file {e.filename}, file does not exist"
                )
                ret = ResultCode.FAILED

        return ret

    def _start_hps_master(self: TalonDxComponentManager) -> ResultCode:
        """
        Start the DsHpsMaster on each Talon board.

        :return: ResultCode.OK if all HPS masters were started successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config["config_commands"]:
            ip = talon_cfg["ip_address"]
            target = f"root@{ip}"
            inst = talon_cfg["server_instance"]

            try:
                with SSHClient() as ssh_client:
                    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
                    ssh_client.connect(ip, username="root", password="")
                    ssh_chan = ssh_client.get_transport().open_session()

                    ssh_chan.exec_command(
                        f"/lib/firmware/hps_software/hps_master_mcs.sh {inst}"
                    )
                    exit_status = ssh_chan.recv_exit_status()
                    if exit_status != 0:
                        self.logger.error(
                            f"Error starting HPS master on {target}: {exit_status}"
                        )
                        ret = ResultCode.FAILED

            except NoValidConnectionsError:
                self.logger.error(
                    f"NoValidConnectionsError while connecting to {target}"
                )
                ret = ResultCode.FAILED
            except SSHException:
                self.logger.error(f"SSHException while talking to {target}")
                ret = ResultCode.FAILED

        return ret

    def _create_hps_master_device_proxies(
        self: TalonDxComponentManager,
    ) -> ResultCode:
        """
        Attempt to create a device proxy to each DsHpsMaster device.

        :return: ResultCode.OK if all proxies were created successfully,
                 otherwise ResultCode.FAILED
        """
        # Create device proxies for the HPS master devices
        ret = ResultCode.OK
        self.proxies = {}
        for talon_cfg in self.talondx_config["config_commands"]:
            fqdn = talon_cfg["ds_hps_master_fqdn"]

            self.logger.info(f"Trying connection to {fqdn} device")
            try:
                self.proxies[fqdn] = CbfDeviceProxy(
                    fqdn=fqdn, logger=self.logger
                )
            except tango.DevFailed as df:
                for item in df.args:
                    self.logger.error(
                        f"Failed connection to {fqdn} device: {item.reason}"
                    )
                ret = ResultCode.FAILED

        return ret

    def _configure_hps_master(self: TalonDxComponentManager) -> ResultCode:
        """
        Send the configure command to all the DsHpsMaster devices.

        :return: ResultCode.OK if all configure commands were sent successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config["config_commands"]:
            hps_master_fqdn = talon_cfg["ds_hps_master_fqdn"]
            hps_master = self.proxies[hps_master_fqdn]

            self.logger.info(f"Sending configure command to {hps_master_fqdn}")
            try:
                cmd_ret = hps_master.configure(json.dumps(talon_cfg))
                if cmd_ret != 0:
                    self.logger.error(
                        f"Configure command for {hps_master_fqdn}"
                        f" device failed with error code {cmd_ret}"
                    )
                    ret = ResultCode.FAILED

            except tango.DevFailed as df:
                for item in df.args:
                    self.logger.error(
                        f"Exception while sending configure command"
                        f" to {hps_master_fqdn} device: {str(item.reason)}"
                    )
                ret = ResultCode.FAILED

        return ret
