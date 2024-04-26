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

import re
import threading
from typing import Any, Callable, List, Optional, Tuple

import tango
import yaml
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerState,
    SimulationMode,
)
from ska_tango_testing import context

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)

__all__ = ["SlimComponentManager"]


class SlimComponentManager(CbfComponentManager):
    """
    Manages a Serial Lightweight Interconnect Mesh (SLIM).
    """

    def __init__(
        self: SlimComponentManager,
        *args: Any,
        link_fqdns: List[str],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param link_fqdns: a list of SLIM Link FQDNs
        :param simulation_mode: Enum that identifies if the simulator should be used
        """
        super().__init__(*args, **kwargs)
        self.simulation_mode = simulation_mode

        self._mesh_configured = False
        self._config_str = ""

        # a list of [tx_fqdn, rx_fqdn] for active links.
        self._active_links = []

        # SLIM Link Device proxies
        self._link_fqdns = link_fqdns
        self._dp_links = []

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""
        self.logger.debug("Entering SlimComponentManager.start_communicating")

        if self.communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Already communicating.")
            return

        super().start_communicating()

        self._dp_links = []
        self.logger.debug(f"Link FQDNs: {self._link_fqdns}")
        if self._link_fqdns is not None:
            for fqdn in self._link_fqdns:
                try:
                    dp = context.DeviceProxy(device_name=fqdn)
                    dp.adminMode = AdminMode.ONLINE
                    self._dp_links.append(dp)
                except AttributeError as ae:
                    # Thrown if the device exists in the db but the executable is not running.
                    self._update_communication_state(
                        CommunicationStatus.NOT_ESTABLISHED
                    )
                    self.logger.error(
                        f"Attribute error {ae}. Ensure SlimLink devices are running."
                    )
                    return
                except tango.DevFailed as df:
                    # Thrown if the device doesn't exist in the db.
                    self._update_communication_state(
                        CommunicationStatus.NOT_ESTABLISHED
                    )
                    self.logger.error(
                        f"Failed to set AdminMode of {fqdn} to ONLINE: {df.args[0].desc}"
                    )
                    return
            # This moves the op state model.
            self._update_component_state(power=PowerState.OFF)
        else:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.logger.error(
                "'Links' device property is unpopulated. Check charts."
            )

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self.logger.debug("Entering SlimComponentManager.stop_communicating")

        for dp in self._dp_links:
            dp.adminMode = AdminMode.OFFLINE
        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model.
        super().stop_communicating()

    @property
    def is_communicating(self) -> bool:
        """
        Returns whether or not the SLIM can be communicated with.

        :return: whether the SLIM is communicating
        """
        return (
            self.communication_state == CommunicationStatus.ESTABLISHED
        ) and self._mesh_configured

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
        self.logger.debug("Entering SlimComponentManager.on")

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    def is_off_allowed(self) -> bool:
        self.logger.debug("Checking if Off is allowed.")
        return self.power_state == PowerState.ON

    def _off(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """
        Off command. Disconnects SLIM Links if mesh is configured, else returns OK.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering SlimComponentManager.off")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        self._update_component_state(power=PowerState.OFF)

        try:
            rc, msg = self._disconnect_links()
            if rc is not ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(rc, msg),
                )
                return
        except tango.DevFailed as df:
            task_callback(
                exception=df,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    df.args[0].desc,
                ),
            )
            return

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Off completed OK",
            ),
        )

    def off(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> Tuple[ResultCode, str]:
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )

    def is_configure_allowed(self) -> bool:
        self.logger.debug("Checking if Configure is allowed.")
        return self.communication_state == CommunicationStatus.ESTABLISHED

    def _configure(
        self: SlimComponentManager,
        config_str: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Configure command. Parses the mesh configuration.

        :param config_str: a string in YAML format describing the links to be created.
        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        """
        self.logger.debug("Entering SlimComponentManager.configure()")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "Configure", task_callback, task_abort_event
        ):
            return
        # Each element in the config is [tx_fqdn, rx_fqdn]
        self._config_str = config_str

        try:
            self._active_links = self._parse_links_yaml(self._config_str)

            self.logger.debug(
                f"Configuring {len(self._dp_links)} links with simulationMode = {self.simulation_mode}"
            )
            for dp in self._dp_links:
                dp.adminMode = AdminMode.OFFLINE
                dp.simulationMode = self.simulation_mode
                dp.adminMode = AdminMode.ONLINE

            if self._mesh_configured:
                self.logger.debug(
                    "SLIM was previously configured. Disconnecting links before re-initializing."
                )
                rc, msg = self._disconnect_links()
                if rc is not ResultCode.OK:
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            rc,
                            msg,
                        ),
                    )
                    return
            self.logger.debug("Initializing SLIM Links")
            rc, msg = self._initialize_links()
            if rc is not ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        rc,
                        msg,
                    ),
                )
                return
        except AttributeError as ae:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=ae,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "AttributeError encountered. Ensure SlimLink devices are running.",
                ),
            )
            return
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=df,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    df.args[0].desc,
                ),
            )
            return

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Configure completed OK",
            ),
        )

    def configure(
        self: SlimComponentManager,
        config_str: str,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> Tuple[ResultCode, str]:
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._configure,
            args=[config_str],
            is_cmd_allowed=self.is_configure_allowed,
            task_callback=task_callback,
        )

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
            self.logger.error(msg)
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
            self.logger.error(f"Failed to load YAML: {e}")
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
        self.logger.debug(
            f"Creating {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            self.logger.warn(
                "No active links are defined in the mesh configuration"
            )
            return ResultCode.OK, "_initialize_links completed OK"
        if len(self._active_links) > len(self._dp_links):
            msg = "Too many links defined in the link configuration. Not enough SlimLink devices exist."
            self.logger.error(msg)
            return ResultCode.FAILED, msg
        try:
            for idx, txrx in enumerate(self._active_links):
                self._dp_links[idx].txDeviceName = txrx[0]
                self._dp_links[idx].rxDeviceName = txrx[1]

                # The SLIM link may need to wait for Tx/Rx to initialize
                self._dp_links[idx].set_timeout_millis(10000)
                [rc, msg] = self._dp_links[idx].ConnectTxRx()
                self._dp_links[idx].set_timeout_millis(3000)

                # TODO: Need to add guard incase LRC was rejected.
                # TODO: Need to add LRC wait mechanism
                if rc[0] is not ResultCode.OK:
                    return rc[0], msg[0]

                # TODO: Should replace polling here with a subscription to the link's healthState
                # poll link health every 20 seconds
                self._dp_links[idx].poll_command("VerifyConnection", 20000)
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to initialize SLIM links: {df.args[0].desc}"
            )
            raise df
        except IndexError as ie:
            msg = "Not enough Links defined in device properties"
            self.logger.error(f"msg - {ie}")
            tango.Except.throw_exception(
                "IndexError",
                msg,
                "_initialize_links()",
            )

        self.logger.info("Successfully initialized SLIM links")
        self._mesh_configured = True
        return ResultCode.OK, "_initialize_links completed OK"

    def _disconnect_links(self) -> Tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to disconnect and cease polling health states.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            f"Disconnecting {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            self.logger.info(
                "No active links are defined in the SlimLink configuration"
            )
            return ResultCode.OK, "_disconnect_links completed OK"
        try:
            for idx, txrx in enumerate(self._active_links):
                self._dp_links[idx].stop_poll_command("VerifyConnection")
                [rc, msg] = self._dp_links[idx].DisconnectTxRx()

                # TODO: Need to add guard incase LRC was rejected.
                # TODO: Need to add LRC wait mechanism
                if rc[0] is not ResultCode.OK:
                    return rc[0], msg[0]
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to disconnect SLIM links: {df.args[0].desc}"
            )
            raise df

        self.logger.info("Successfully disconnected SLIM links")
        self._mesh_configured = False
        return ResultCode.OK, "_disconnect_links completed OK"
