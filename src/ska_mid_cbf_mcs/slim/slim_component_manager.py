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
from typing import Callable, List, Optional, Tuple

import tango
import yaml
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerState,
    SimulationMode,
)

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
        link_fqdns: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerState], None],
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
        self._mesh_configured = False
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
        self.update_component_power_mode(PowerState.OFF)
        self.connected = True

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self._logger.info("Entering SlimComponentManager.stop_communicating")
        super().stop_communicating()
        for dp in self._dp_links:
            dp.adminMode = AdminMode.OFFLINE
        self.update_component_power_mode(PowerState.UNKNOWN)
        self.connected = False

    @property
    def is_communicating(self) -> bool:
        """
        Returns whether or not the SLIM can be communicated with.

        :return: whether the SLIM is communicating
        """
        return self.connected and self._mesh_configured

    def on(self) -> Tuple[ResultCode, str]:
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
        self.update_component_power_mode(PowerState.ON)
        return (ResultCode.OK, "On command completed OK")

    def off(self) -> Tuple[ResultCode, str]:
        """
        Off command. Disconnects SLIM Links if mesh is configured, else returns OK.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug("Entering SlimComponentManager.off")
        self.update_component_power_mode(PowerState.OFF)
        if self._mesh_configured:
            self._disconnect_links()
        return (ResultCode.OK, "Off command completed OK")

    def configure(self, config_str) -> Tuple[ResultCode, str]:
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

        if self._mesh_configured:
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

    def get_link_fqdns(self) -> List[str]:
        """
        Returns a list of SLIM Link FQDNs.

        :return: the SLIM links assosiated with the mesh.
        :rtype: List[str]
        """
        fqdns = []
        for idx, txrx in enumerate(self._active_links):
            fqdn = self._link_fqdns[idx]
            fqdns.append(fqdn)
        return fqdns

    def get_link_names(self) -> List[str]:
        """
        Returns a list of SLIM Link names, formatted 'tx_device_name->rx_device_name'.

        :return: the names of SLIM links assosiated with the mesh.
        :rtype: List[str]
        """
        names = []
        for idx, txrx in enumerate(self._active_links):
            name = self._dp_links[idx].linkName
            names.append(name)
        return names

    def get_health_summary(self) -> List[HealthState]:
        """
        Returns a list of HealthState enums describing the status of each link.

        :return: the health state of each SLIM link in the mesh.
        :rtype: List[HealthState]
        """
        summary = []
        for idx, txrx in enumerate(self._active_links):
            link_health = self._dp_links[idx].healthState
            summary.append(link_health)
        return summary

    def get_bit_error_rate(self) -> List[float]:
        """
        Returns a list containing the bit-error rates for each link.

        :return: the bit-error rate (BER) of each SLIM link in the mesh.
        :rtype: List[float]
        """
        bers = []
        for idx, txrx in enumerate(self._active_links):
            ber = self._dp_links[idx].bitErrorRate
            bers.append(ber)
        return bers

    def _parse_link(self, link: str):
        """
        Each link is in the format of "tx_fqdn -> rx_fqdn". If the
        link is disabled, then the text ends with [x].

        :param link: a string describing a singular SLIM link.

        :return: the pair of HPS tx and rx device FQDNs that make up a link.
        :rtype: List[str]
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

    def _initialize_links(self) -> Tuple[ResultCode, str]:
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
        self._mesh_configured = True
        return (ResultCode.OK, msg)

    def _disconnect_links(self) -> Tuple[ResultCode, str]:
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
        self._mesh_configured = False
        return (ResultCode.OK, msg)
