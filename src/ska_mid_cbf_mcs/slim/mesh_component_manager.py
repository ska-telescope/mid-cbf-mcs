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
from typing import Callable, List, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.slim.slim_common import parse_links_yaml
from ska_mid_cbf_mcs.slim.slim_link import SLIMLink

__all__ = ["MeshComponentManager"]


class MeshComponentManager(CbfComponentManager):
    """
    Manages a Serial Lightweight Interconnect Mesh (SLIM).

    :param defn_str: a string of a yaml defining the links in the mesh
    """

    def __init__(
        self: MeshComponentManager,
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        self._mesh_configured = False
        self._config_str = ""
        self.connected = False

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""
        self._logger.info("Entering MeshComponentManager.start_communicating")

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = True

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self._logger.info("Entering MeshComponentManager.stop_communicating")
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False

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
        self._logger.debug("Entering MeshComponentManager.on")
        self.update_component_power_mode(PowerMode.ON)
        return (ResultCode.OK, "")

    def off(self) -> Tuple[ResultCode, str]:
        """
        Off command. Currently just returns OK. The device
        does nothing until mesh configuration is provided via
        the Configure command.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug("Entering MeshComponentManager.off")
        self.update_component_power_mode(PowerMode.OFF)
        return (ResultCode.OK, "")

    def configure(self, config: str) -> Tuple[ResultCode, str]:
        """
        Configure command. Parses the mesh configuration

        :param config: a string in YAML format describing the links to be created
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        # each element is [tx_fqdn, rx_fqdn]
        self.links_list_ = parse_links_yaml(config)
        self._config_str = config

        rc, msg = self.initialize_links()

        if rc is not ResultCode.OK:
            return (rc, msg)

        self._mesh_configured = True

    def initialize_links(self) -> Tuple[ResultCode, str]:
        # try:
        #     for txrx in self.links_list_:
        #         link = SLIMLink(tx_fqdn=txrx[0], rx_fqdn=txrx[1])
        #         link.connect()
        # except tango.DevFailed:
        #     log_msg = "Failed to initialize SLIM links"
        #     self._logger.error(log_msg)
        #     return (ResultCode.FAILED, log_msg)
        return (ResultCode.OK, "")

    def get_configuration_string(self) -> str:
        return self._config_str

    def get_status_summary(self) -> List[bool]:
        summary = []
        return summary

    def get_bit_error_rate(self) -> List[float]:
        ber = []
        return ber
