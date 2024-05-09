# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2023 National Research Council of Canada


from __future__ import annotations

import logging
import re
from typing import Callable, Optional

import tango
import yaml
from beautifultable import BeautifulTable
from pluggy import Result
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerMode,
    SimulationMode,
)

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# from ska_mid_cbf_mcs.slim.slim_link import SLIMLink

__all__ = ["SlimComponentManager"]


class SlimComponentManager(CbfComponentManager):
    """
    Manages a Serial Lightweight Interconnect Mesh (SLIM).
    """

    def __init__(
        self: SlimComponentManager,
        link_fqdns: list[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
    ) -> None:
        """
        Initialise a new instance.

        :param link_fqdns: a list of SLIM Link FQDNs
        :param logger: a logger for this object to use
        :param push_change_event_callback: callback used when the base classes want to send an event
        :param communication_status_changed_callback: callback used when the status of the communications channel between the component manager and its component changes
        :param component_power_mode_changed_callback: callback used when the component power mode changes
        :param component_fault_callback: callback used in event of component fault
        :param simulation_mode: simulation mode identifies if the real power switch
                driver or the simulator should be used
        """
        self.connected = False
        self._simulation_mode = simulation_mode
        self.mesh_configured = False
        self._config_str = ""

        # a list of [tx_fqdn, rx_fqdn] for active links.
        self._active_links = []

        # SLIM Link Device proxies
        self._link_fqdns = link_fqdns
        self._dp_links = []

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""
        self._logger.info("Entering SlimComponentManager.start_communicating")

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()

        self._logger.debug(f"Link FQDNs: {self._link_fqdns}")

        self._dp_links = []
        if len(self._dp_links) == 0 and self._link_fqdns is not None:
            for fqdn in self._link_fqdns:
                dp = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                dp.adminMode = AdminMode.ONLINE
                self._dp_links.append(dp)

        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = True

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self._logger.info("Entering SlimComponentManager.stop_communicating")
        super().stop_communicating()
        for dp in self._dp_links:
            dp.adminMode = AdminMode.OFFLINE
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False

    @property
    def is_communicating(self) -> bool:
        """
        Returns whether or not the SLIM can be communicated with.

        :return: whether the SLIM is communicating
        """
        return self.connected and self.mesh_configured

    def on(self) -> tuple[ResultCode, str]:
        """
        On command. Currently just returns OK. The device
        does nothing until mesh configuration is provided via
        the Configure command.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug("Entering SlimComponentManager.on")
        self.update_component_power_mode(PowerMode.ON)
        return (ResultCode.OK, "On command completed OK")

    def off(self) -> tuple[ResultCode, str]:
        """
        Off command. Disconnects SLIM Links if mesh is configured, else returns OK.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug("Entering SlimComponentManager.off")
        self.update_component_power_mode(PowerMode.OFF)
        if self.mesh_configured:
            self._disconnect_links()
        return (ResultCode.OK, "Off command completed OK")

    def configure(self, config_str) -> tuple[ResultCode, str]:
        """
        Configure command. Parses the mesh configuration.

        :param config_str: a string in YAML format describing the links to be created.
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        # each element is [tx_fqdn, rx_fqdn]
        self._config_str = config_str
        self._active_links = self._parse_links_yaml(self._config_str)

        self._logger.info(
            f"Setting simulation mode = {self._simulation_mode} to {len(self._dp_links)} links"
        )
        for dp in self._dp_links:
            dp.write_attribute("adminMode", AdminMode.OFFLINE)
            dp.write_attribute("simulationMode", self._simulation_mode)
            dp.write_attribute("adminMode", AdminMode.ONLINE)

        if self.mesh_configured:
            self._disconnect_links()

        rc, msg = self._initialize_links()

        if rc is not ResultCode.OK:
            self._logger.error("Failed to Parse the SLIM config.")
            return (rc, msg)

        return (rc, msg)

    def get_configuration_string(self) -> str:
        """
        Returns the configurations string used to configure the SLIM.

        :return: the SLIM configuration string
        :rtype: str
        """
        return self._config_str

    def get_link_fqdns(self) -> list[str]:
        """
        Returns a list of SLIM Link FQDNs.

        :return: the SLIM links assosiated with the mesh.
        :rtype: list[str]
        """
        fqdns = []
        for idx, txrx in enumerate(self._active_links):
            fqdn = self._link_fqdns[idx]
            fqdns.append(fqdn)
        return fqdns

    def get_link_names(self) -> list[str]:
        """
        Returns a list of SLIM Link names, formatted 'tx_device_name->rx_device_name'.

        :return: the names of SLIM links assosiated with the mesh.
        :rtype: list[str]
        """
        names = []
        for idx, txrx in enumerate(self._active_links):
            name = self._dp_links[idx].linkName
            names.append(name)
        return names

    def get_health_summary(self) -> list[HealthState]:
        """
        Returns a list of HealthState enums describing the status of each link.

        :return: the health state of each SLIM link in the mesh.
        :rtype: list[HealthState]
        """
        summary = []
        for idx, txrx in enumerate(self._active_links):
            link_health = self._dp_links[idx].healthState
            summary.append(link_health)
        return summary

    def get_bit_error_rate(self) -> list[float]:
        """
        Returns a list containing the bit-error rates for each link.

        :return: the bit-error rate (BER) of each SLIM link in the mesh.
        :rtype: list[float]
        """
        bers = []
        for idx, txrx in enumerate(self._active_links):
            ber = self._dp_links[idx].bitErrorRate
            bers.append(ber)
        return bers

    def get_device_counters(self) -> list[list[int]]:
        """
        Returns a list containing the counters array for each link

        :return: the counter array for each SLIM link in the mesh
        :rtype: List[List[int]]
        """

        counters = []
        for idx, txrx in enumerate(self._active_links):
            counter = self._dp_links[idx].counters
            counters.append(counter)

        return counters

    def _calculate_rx_idle_word_rate_float(
        self, rx_idle_word_count: int, rx_idle_error_count: int
    ) -> tuple[str, str]:
        """
        TODO
        Calculates and return a string the rate of Rx Idle Error Word Count over Rx Idle Word Count
        Along with a status that indicates if the Rate passes the Bit Error Rate Threshold
        Returns a tuple of the rate and the pass/fail BER status

        :return: A tuple of (rx_idle_word_error_rate,rx_ber_pass_status)
        :rtype: tuple[str,str]
        """
        if rx_idle_word_count == 0:
            rx_idle_word_error_rate = "NaN"
            rx_ber_pass_status = "Unknown"
        else:
            rx_idle_word_rate_float = rx_idle_error_count / rx_idle_word_count
            rx_idle_word_error_rate = f"{rx_idle_word_rate_float:.3e}"
            if rx_idle_word_rate_float < const.BER_PASS_THRESHOLD:
                rx_ber_pass_status = "Passed"
            else:
                rx_ber_pass_status = "Failed"
        return (rx_idle_word_error_rate, rx_ber_pass_status)

    def slim_test(self: SlimComponentManager) -> tuple[ResultCode, str]:
        counters: list[int] = []
        names: list[str] = []
        rx_idle_word_error_rate_and_ber_pass_status: list[tuple[str, str]] = []

        # grab the common values we need for the individual tests
        # to minimize device proxy access
        for idx, txrx in enumerate(self._active_links):
            dp_link = self._dp_links[idx]
            counter = dp_link.counters
            rx_idle_word_count = counter[2]
            rx_idle_error_count = counter[3]
            counters.append(counter)
            names.append(dp_link.linkName)
            rx_idle_word_error_rate_and_ber_pass_status.append(
                self._calculate_rx_idle_word_rate_float(
                    rx_idle_word_count, rx_idle_error_count
                )
            )

        # Summary check for SLIM Link Status and Bit Error Rate
        try:
            self._slim_links_ber_check_summary(
                counters, names, rx_idle_word_error_rate_and_ber_pass_status
            )
        except Exception as e:
            self._logger.error(
                f"Exception occur when running slim_test_slim_links_ber_check_summary: {e}"
            )
            return (
                ResultCode.FAILED,
                "Exception occur when running slim_test_slim_links_ber_check_summary. See log for detail",
            )

        # More detail table for the SLIM Link health
        try:
            self._slim_table(
                counters, names, rx_idle_word_error_rate_and_ber_pass_status
            )
        except Exception as e:
            self._logger.error(
                f"Exception occur when running slim_test_slim_table: {e}"
            )
            return (
                ResultCode.FAILED,
                "Exception occur when running slim_test_slim_table. See log for detail",
            )

        return (ResultCode.OK, f"SLIM Test Completed")

    def _slim_links_ber_check_summary(
        self: SlimComponentManager,
        all_counters: list[int],
        names: list[str],
        rx_idle_word_error_rate_and_ber_pass_status: list[tuple[str]],
    ):
        """
        Logs a summary status of the SLIM Link health for each device on the Mesh
        Specifically, this will calcualte the bit-error rate for a rx device in the mesh
        and compared to a threshold set in global_enum.py
        """

        res = "\nSLIM BER Check:\n\n"
        for idx in range(len(self._active_links)):
            counters = all_counters[idx]
            # tx rx fqdn link name
            name = names[idx]

            rx_word_count = counters[0]
            rx_idle_word_count = counters[2]

            # word error rate: a ratio of rx idle error count compared to the
            # count of rx idle word transmitted
            (
                rx_idle_word_error_rate,
                rx_ber_pass_status,
            ) = rx_idle_word_error_rate_and_ber_pass_status[idx]
            rx_words = rx_word_count + rx_idle_word_count

            res += f"Link Name: {name}\n"
            res += f"Slim Link status (rx_status): {rx_ber_pass_status}\n"
            res += f"rx_wer:{rx_idle_word_error_rate}\n"
            res += f"rx_rate_gbps:{rx_idle_word_count / rx_words * const.GBPS if rx_words != 0 else 'NaN'}\n"
            res += "\n"
        self._logger.info(res)

    def _slim_table(
        self: SlimComponentManager,
        all_counters: list[int],
        names: list[str],
        rx_idle_word_error_rate_and_ber_pass_status: list[tuple[str, str]],
    ):
        """
        Logs a summary for the rx and tx device on the Mesh
        """

        table = BeautifulTable(maxwidth=180)
        table.columns.header = [
            "Link",
            "CDR locked\n(lost)",
            "Block Aligned\n(lost)",
            "Tx Data (Gbps)\n(words)",
            "Tx Idle (Gbps)",
            "Rx Data\n(Gbps)\n(words)",
            "Rx Idle\n(Gbps)",
            "Idle Error\nCount",
            "Word\nError Rate",
        ]

        for idx in range(len(self._active_links)):
            dp_link = self._dp_links[idx]
            counters = all_counters[idx]
            # tx rx fqdn link name
            name = names[idx]
            (
                rx_idle_word_error_rate,
                _,
            ) = rx_idle_word_error_rate_and_ber_pass_status[idx]

            rx_debug_alignment_and_lock_statuses = (
                dp_link.rx_debug_alignment_and_lock_status
            )
            rx_link_occupancy = dp_link.rx_link_occupancy
            tx_link_occupancy = dp_link.tx_link_occupancy

            rx_word_count = counters[0]
            rx_idle_word_count = counters[2]
            rx_idle_error_count = counters[3]
            tx_word_count = counters[6]
            tx_idle_word_count = counters[8]
            tx_words = tx_word_count + tx_idle_word_count
            rx_words = rx_word_count + rx_idle_word_count

            # spliting up the tx rx name from the tx rx fqdn link name
            tx_name = (name.split("->"))[0]
            rx_name = (name.split("->"))[1]

            # Making the tx rx name shorter by keeping only the board name and the tx/rx port
            short_name_one = (
                (tx_name.split("/"))[0] + "/" + (tx_name.split("/"))[-1]
            )
            short_name_two = (
                (rx_name.split("/"))[0] + "/" + (rx_name.split("/"))[-1]
            )

            data_row = (
                f"{short_name_one}\n->{short_name_two}",
                f"{rx_debug_alignment_and_lock_statuses[3]}\n({rx_debug_alignment_and_lock_statuses[2]})",
                f"{rx_debug_alignment_and_lock_statuses[1]}\n({rx_debug_alignment_and_lock_statuses[0]})",
                f"{tx_link_occupancy * const.GBPS:.2f}\n({tx_word_count})",
                # Guard for divide by zero
                f"{tx_idle_word_count/tx_words * const.GBPS:.2f}"
                if tx_words != 0
                else "NaN",
                f"{rx_link_occupancy * const.GBPS:.2f}\n({rx_word_count})",
                # Guard for divide by zero
                f"{rx_idle_word_count/rx_words * const.GBPS:.2f}"
                if rx_words != 0
                else "NaN",
                f"{rx_idle_error_count} /\n{rx_words:.2e}",
                rx_idle_word_error_rate,
            )
            table.rows.append(data_row)

        self._logger.info(f"\nSLIM Health Summary Table\n{table}")

    def _parse_link(self, link: str):
        """
        Each link is in the format of "tx_fqdn -> rx_fqdn". If the
        link is disabled, then the text ends with [x].

        :param link: a string describing a singular SLIM link.

        :return: the pair of HPS tx and rx device FQDNs that make up a link.
        :rtype: list[str]
        """
        tmp = re.sub(r"[\s\t]", "", link)  # removes all whitespaces

        # ignore disabled links or lines without the expected format
        if tmp.endswith("[x]") or ("->" not in tmp):
            return None
        txrx = tmp.split("->")
        if len(txrx) != 2:
            return None
        return txrx

    def _validate_mesh_config(self, links: list) -> None:
        """
        Checks if the requested SLIM configuration is valid.

        :param links: a list of HPS tx and rx device pairs to be configured as SLIM links.
        :raise Tango exception: if SLIM configuration is not valid.
        """
        tx_set = set([x[0] for x in links])
        rx_set = set([y[1] for y in links])
        if len(tx_set) != len(rx_set) or len(tx_set) != len(links):
            msg = "Tx and Rx devices must be unique in the configuration."
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Slim_Validate_",
                msg,
                "_validate_mesh_config()",
            )
        return

    def _parse_links_yaml(self, yaml_str: str) -> list[list[str]]:
        """
        Parse a yaml string containing the mesh links.

        :param yaml_str: the string defining the mesh links
        :raise Tango exception: if the configuration is not valid yaml.
        :return: a list of HPS tx and rx device pairs as [Tx FQDN, Rx FQDN]
        :rtype: list[list[str]]
        """
        links = list()
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            self._logger.error(f"Failed to load YAML: {e}")
            tango.Except.throw_exception(
                "Slim_Parse_YAML",
                "Cannot parse SLIM configuration YAML",
                "_parse_links_yaml()",
            )
        for k, v in data.items():
            for line in v:
                txrx = self._parse_link(line)
                if txrx is not None:
                    links.append(txrx)
        self._validate_mesh_config(
            links
        )  # throws exception if validation fails
        return links

    def _initialize_links(self) -> tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to connect and starts polling each link's health state.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.info(
            f"Creating {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            msg = "No active links are defined in the mesh configuration"
            self._logger.warn(msg)
            return (ResultCode.OK, msg)
        try:
            for idx, txrx in enumerate(self._active_links):
                self._dp_links[idx].txDeviceName = txrx[0]
                self._dp_links[idx].rxDeviceName = txrx[1]

                # The SLIM link may need to wait for Tx/Rx to initialize
                self._dp_links[idx].set_timeout_millis(10000)
                rc, msg = self._dp_links[idx].command_inout("ConnectTxRx")

                self._dp_links[idx].set_timeout_millis(3000)
                # poll link health every 20 seconds
                self._dp_links[idx].poll_command("VerifyConnection", 20000)
        except tango.DevFailed as df:
            msg = f"Failed to initialize SLIM links: {df.args[0].desc}"
            self._logger.error(msg)
            return (ResultCode.FAILED, msg)
        msg = "Successfully set up SLIM links"
        self._logger.info(msg)
        self.mesh_configured = True
        return (ResultCode.OK, msg)

    def _disconnect_links(self) -> tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to disconnect and cease polling health states.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.info(
            f"Disconnecting {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            msg = "No active links are defined in the mesh configuration"
            self._logger.info(msg)
            return (ResultCode.OK, msg)
        try:
            for idx, txrx in enumerate(self._active_links):
                self._dp_links[idx].stop_poll_command("VerifyConnection")
                rc, msg = self._dp_links[idx].command_inout("DisconnectTxRx")
        except tango.DevFailed as df:
            msg = f"Failed to disconnect SLIM links: {df.args[0].desc}"
            self._logger.error(msg)
            return (ResultCode.FAILED, msg)
        msg = "Disconnected SLIM links"
        self._logger.info(msg)
        self.mesh_configured = False
        return (ResultCode.OK, msg)
