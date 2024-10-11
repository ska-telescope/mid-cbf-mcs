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

import concurrent.futures
import json
import os
import time

import backoff
import tango
import yaml
from paramiko import AutoAddPolicy, SSHClient
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
from scp import SCPClient, SCPException
from ska_control_model import SimulationMode
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import CbfComponentManager

__all__ = ["TalonDxComponentManager"]


class TalonDxComponentManager(CbfComponentManager):
    """
    A component manager for the Talon-DX boards. Used to configure and start
    the Tango applications on the HPS of each board.
    """

    def __init__(
        self: TalonDxComponentManager,
        *args: any,
        talondx_config_path: str,
        hw_config_path: str,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param talondx_config_path: path to the directory containing configuration
                                    files and artifacts for the Talon boards
        :param hw_config_path: path to the directory containing the hardware
                               configuration file
        :param simulation_mode: simulation mode identifies if the real Talon boards or
                                a simulator should be used; note that currently there
                                is no simulator for the Talon boards, so the component
                            manager does nothing when in simulation mode
        :param logger: a logger for this object to use
        """
        super().__init__(*args, **kwargs)
        self.talondx_config_path = talondx_config_path
        self._hw_config_path = hw_config_path

        self._hw_config = {}
        self.talondx_config = {}
        self.proxies = {}

    # --- Configure Talons --- #

    def _configure_hps_master(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> ResultCode:
        """
        Send the configure command to all the DsHpsMaster devices.

        :param talon_cfg: the configuration for the Talon board
        :return: ResultCode.OK if all configure commands were sent successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK

        hps_master_fqdn = talon_cfg["ds_hps_master_fqdn"]
        hps_master = self.proxies[hps_master_fqdn]

        # Wait for HPS Master
        ping_ok = False
        for i in range(6):
            try:
                hps_master.ping()
                ping_ok = True
                break
            except tango.DevFailed:  # TODO handle unstarted HPS master
                time.sleep(5)

        if not ping_ok:
            self.logger.error(f"Timeout trying to ping {hps_master_fqdn}.")
            return ResultCode.FAILED

        self.logger.info(f"Sending configure command to {hps_master_fqdn}")
        try:
            hps_master.set_timeout_millis(self._lrc_timeout * 1000)
            cmd_ret = hps_master.configure(json.dumps(talon_cfg))
            if cmd_ret != 0:
                self.logger.error(
                    f"Configure command for {hps_master_fqdn}"
                    f" device failed with error code {cmd_ret}"
                )
                ret = ResultCode.FAILED

        except tango.DevFailed as df:
            self.logger.error(
                f"Exception while sending configure command to {hps_master_fqdn} device: {df}"
            )
            ret = ResultCode.FAILED

        return ret

    def _create_hps_master_device_proxies(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> ResultCode:
        """
        Attempt to create a device proxy to each DsHpsMaster device.

        :param talon_cfg: the configuration for the Talon board
        :return: ResultCode.OK if all proxies were created successfully,
                 otherwise ResultCode.FAILED
        """
        # Create device proxies for the HPS master devices
        ret = ResultCode.OK

        fqdn = talon_cfg["ds_hps_master_fqdn"]

        self.logger.info(f"Trying connection to {fqdn} device")
        try:
            self.proxies[fqdn] = context.DeviceProxy(device_name=fqdn)
        except tango.DevFailed as df:
            self.logger.error(f"Failed connection to {fqdn} device: {df}")
            ret = ResultCode.FAILED

        return ret

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

    def _start_hps_master(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> ResultCode:
        """
        Start the DsHpsMaster on each Talon board.

        :param talon_cfg: the configuration for the Talon board
        :return: ResultCode.OK if all HPS masters were started successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK

        talon = talon_cfg["target"]
        ip = self._hw_config["talon_board"][talon]
        target = f"root@{ip}"
        inst = talon_cfg["server_instance"]

        self.logger.info(f"Starting HPS Master on talon board {talon}")

        try:
            with SSHClient() as ssh_client:
                ssh_client.set_missing_host_key_policy(AutoAddPolicy())
                ssh_client.connect(ip, username="root", password="")
                ssh_chan = ssh_client.get_transport().open_session()

                ssh_chan.exec_command(
                    f"sh /lib/firmware/hps_software/hps_master_mcs.sh {inst}"
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

    def _copy_binaries_and_bitstream(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> ResultCode:
        """
        Copy the relevant device server binaries and FPGA bitstream to each
        Talon board.

        :param talon_cfg: the configuration for the Talon board
        :return: ResultCode.OK if all artifacts were copied successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK

        try:
            target = talon_cfg["target"]
            ip = self._hw_config["talon_board"][target]
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
                def make_first_connect(ip: str, ssh_client: SSHClient) -> None:
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
                    return ResultCode.FAILED

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

                # Clear the existing DS binaries from dest dir
                ssh_chan = ssh_client.get_transport().open_session()
                ssh_chan.exec_command(f"rm -f {dest_dir}/*")
                exit_status = ssh_chan.recv_exit_status()
                if exit_status != 0:
                    self.logger.error(
                        f"Error deleting ds binaries from {dest_dir}: {exit_status}"
                    )
                    return ResultCode.FAILED

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
                    return ResultCode.FAILED

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
            self.logger.error(
                f"NoValidConnectionsError while connecting to {target}: {e}"
            )
            ret = ResultCode.FAILED
        except SSHException as e:
            self.logger.error(f"SSHException while talking to {target}: {e}")
            ret = ResultCode.FAILED
        except SCPException as e:
            self.logger.error(f"Failed to copy file to {target}: {e}")
            ret = ResultCode.FAILED
        except FileNotFoundError as e:
            self.logger.error(
                f"Failed to copy file {e.filename}, file does not exist: {e}"
            )
            ret = ResultCode.FAILED
        except yaml.YAMLError as e:
            self.logger.error(f"YAMLError with target {target}: {e}")
            ret = ResultCode.FAILED

        return ret

    def _configure_talon_networking(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> ResultCode:
        """
        Configure the networking of the boards including DNS nameserver
        and ifconfig for default gateway

        :param talon_cfg: the configuration for the Talon board
        :return: ResultCode.OK if all artifacts were copied successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        try:
            target = talon_cfg["target"]
            ip = self._hw_config["talon_board"][target]
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
                    backoff.constant,
                    NoValidConnectionsError,
                    max_tries=3,
                    max_time=talon_first_connect_timeout,
                )
                def make_first_connect(ip: str, ssh_client: SSHClient) -> None:
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

                if environment == "minikube":
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

        except NoValidConnectionsError as e:
            self.logger.error(
                f"NoValidConnectionsError while connecting to {target}: {e}"
            )
            ret = ResultCode.FAILED
        except SSHException as e:
            self.logger.error(f"SSHException while talking to {target}: {e}")
            ret = ResultCode.FAILED
        except yaml.YAMLError as e:
            self.logger.error(f"YAMLError with target {target}: {e}")
            ret = ResultCode.FAILED

        return ret

    def _generate_kill_script(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> str:
        """
        Generate a script to kill all device processes on the Talon board

        :param talon_cfg: the configuration for the Talon board
        :return: the script to kill all device processes
        """
        talon_devices = talon_cfg["devices"] + ["dshpsmaster"]
        kill_script = "#!/bin/sh\n"

        for talon_device in talon_devices:
            kill_script += f"""
            pid=$(ps alx | grep {talon_device} | grep -v grep | awk '{{print $3}}')
            if [ $pid -gt 0 ]
            then kill -9 $pid
            fi
            """

        return kill_script

    def _clear_talon(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> ResultCode:
        """
        Clear the Talon board by sending a script to the Talon
        that kills all device processes

        :param talon_cfg: the configuration for the Talon board
        :return: ResultCode.OK if script was sent successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        target = talon_cfg["target"]
        ip = self._hw_config["talon_board"][target]
        talon_first_connect_timeout = talon_cfg["talon_first_connect_timeout"]
        kill_script = self._generate_kill_script(talon_cfg)

        try:
            with SSHClient() as ssh_client:

                @backoff.on_exception(
                    backoff.expo,
                    (NoValidConnectionsError, SSHException),
                    max_value=3,
                    max_time=talon_first_connect_timeout,
                )
                def make_first_connect(ip: str, ssh_client: SSHClient) -> None:
                    """
                    Attempts to connect to the Talon board for the first time
                    after power-on or reboot.

                    :param ip: IP address of the board
                    :param ssh_client: SSH client to use for connection
                    """
                    ssh_client.connect(ip, username="root", password="")

                self.logger.info(f"Clearing Talon board {target}")
                ssh_client.set_missing_host_key_policy(AutoAddPolicy())
                make_first_connect(ip, ssh_client)

                ssh_chan = ssh_client.get_transport().open_session()
                ssh_chan.exec_command(kill_script)
                time.sleep(const.DEFAULT_TIMEOUT)

        except NoValidConnectionsError as e:
            self.logger.error(
                f"NoValidConnectionsError while initially connecting to {target}: {e}"
            )
            ret = ResultCode.FAILED
        except SSHException as e:
            self.logger.error(f"SSHException while talking to {target}: {e}")
            ret = ResultCode.FAILED

        return ret

    def _configure_talon_thread(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> tuple[ResultCode, str]:
        """
        A thread to configure a single Talon board. This includes clearing the
        board, configuring the networking, copying the binaries and bitstream,
        starting the HPS master and sending the configure command to the DsHpsMaster.

        :param talon_cfg: the configuration for the Talon board
        :return: a tuple containing the result code and a message
        """
        if self._clear_talon(talon_cfg) == ResultCode.FAILED:
            return (ResultCode.FAILED, "_clear_talon FAILED")

        if self._configure_talon_networking(talon_cfg) == ResultCode.FAILED:
            return (ResultCode.FAILED, "_configure_talon_networking FAILED")

        if self._copy_binaries_and_bitstream(talon_cfg) == ResultCode.FAILED:
            return (ResultCode.FAILED, "_copy_binaries_and_bitstream FAILED")

        if self._start_hps_master(talon_cfg) == ResultCode.FAILED:
            return (ResultCode.FAILED, "_start_hps_master FAILED")

        if (
            self._create_hps_master_device_proxies(talon_cfg)
            == ResultCode.FAILED
        ):
            return (
                ResultCode.FAILED,
                "_create_hps_master_device_proxies FAILED",
            )

        if self._configure_hps_master(talon_cfg) == ResultCode.FAILED:
            return (ResultCode.FAILED, "_configure_hps_master FAILED")

        target = talon_cfg["target"]

        self.logger.info(f"Completed configuring talon board {target}")
        return (ResultCode.OK, "_configure_talon_thread completed OK")

    def _setup_tango_host_file(
        self: TalonDxComponentManager,
    ) -> None:
        """
        Copy the hps_master_mcs.sh file from mnt into mnt/talondx-config

        :return: ResultCode.OK if all artifacts were copied successfully,
                 else ResultCode.FAILED
        """
        with open("hps_master_mcs_tmp.sh") as hps_master_file_tmp:
            namespace = os.getenv("NAMESPACE")
            tango_host = os.getenv("TANGO_HOST").split(":")
            cluster_domain = os.getenv("CLUSTER_DOMAIN")
            db_service_name = tango_host[0].split(".")[0]
            port = tango_host[1]
            hostname = f"{db_service_name}.{namespace}.svc.{cluster_domain}"
            replaced_text = hps_master_file_tmp.read().replace(
                "<hostname>:<port>", f"{hostname}:{port}"
            )
        with open("hps_master_mcs.sh", "w") as hps_master_file:
            hps_master_file.write(replaced_text)

    def _read_config(self: TalonDxComponentManager) -> ResultCode:
        """
        Read in the configuration files for the Talon boards and the hardware

        :return: ResultCode.FAILED if any operations failed, else ResultCode.OK
        """
        try:
            talondx_config_path = (
                f"{self.talondx_config_path}/talondx-config.json"
            )
            with open(talondx_config_path) as json_fd:
                self.talondx_config = json.load(json_fd)
            with open(self._hw_config_path) as yaml_fd:
                self._hw_config = yaml.safe_load(yaml_fd)
            return ResultCode.OK
        except IOError as e:
            self.logger.error(e)
            return ResultCode.FAILED

    def configure_talons(self: TalonDxComponentManager) -> ResultCode:
        """
        Performs all actions to configure the Talon boards after power on. This includes: copying the device server
        binaries and FPGA bitstream to the Talon boards, starting the HPS master
        device server, and sending the configure command to each DsHpsMaster, which starts the HPS device servers.

        :return: ResultCode.FAILED if any operations failed, else ResultCode.OK
        """
        if self.simulation_mode == SimulationMode.TRUE:
            return ResultCode.OK

        if self._read_config() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._setup_tango_host_file() == ResultCode.FAILED:
            return ResultCode.FAILED

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._configure_talon_thread, talon_cfg)
                for talon_cfg in self.talondx_config["config_commands"]
            ]
            results = [f.result() for f in futures]

        if any(r[0] == ResultCode.FAILED for r in results):
            self.logger.error(f"Talon configure thread results: {results}")
            return ResultCode.FAILED

        return ResultCode.OK

    # --- Shutdown Talons --- #

    def _shutdown_talon_thread(
        self: TalonDxComponentManager, talon_cfg: dict
    ) -> tuple[ResultCode, str]:
        """
        A thread to shutdown a single Talon board. This includes sending the
        shutdown command to the DsHpsMaster.

        :param talon_cfg: the configuration for the Talon board
        :return: a tuple containing the result code and a message
        """
        # HPS master shutdown with code 3 to gracefully shut down linux host (HPS)
        hps_master_fqdn = talon_cfg["ds_hps_master_fqdn"]
        hps_master = self.proxies[hps_master_fqdn]
        try:
            hps_master.shutdown(3)
        except tango.DevFailed as df:
            self.logger.warning(
                f"Exception while sending shutdown command to {hps_master_fqdn} device: {df}"
            )
            # TODO: determine behaviour here; the shutdown command will
            # inevitably throw an exception, as the device is shut off
            # there may be a more elegant way to handle the expected shutdown
            # for CIP-1673 just logging a warning here

        # wait for linux shutdown
        time.sleep(const.DEFAULT_TIMEOUT)

        return (
            ResultCode.OK,
            f"_shutdown_talon_thread for {talon_cfg['target']} completed OK",
        )

    def shutdown(
        self: TalonDxComponentManager,
    ) -> ResultCode:
        """
        Shutdown the DsHpsMaster device with shutdown code 3.
        For reference, shutdown command codes:
            0. Child Tango DSs only
            1. Child and HPS Master Tango DSs
            2. Child and HPS Master Tango DSs, reboot Talon DX board
            3. Child and HPS Master Tango DSs, shut down Talon DX board
        :return: ResultCode.OK if all shutdown commands were sent successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        if self.simulation_mode == SimulationMode.TRUE:
            return ret

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._shutdown_talon_thread, talon_cfg)
                for talon_cfg in self.talondx_config["config_commands"]
            ]
            results = [f.result() for f in futures]

        if any(r[0] == ResultCode.FAILED for r in results):
            self.logger.error(f"Talon shutdown thread results: {results}")
            ret = ResultCode.FAILED

        return ret
