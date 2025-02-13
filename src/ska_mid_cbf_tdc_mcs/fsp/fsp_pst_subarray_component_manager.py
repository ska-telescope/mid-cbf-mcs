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
from threading import Event
from typing import Any, Callable, Optional

import tango
from ska_control_model import CommunicationStatus, TaskStatus
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_tdc_mcs.fsp.fsp_mode_subarray_component_manager import (
    FspModeSubarrayComponentManager,
)

FSP_PST_PARAM_PATH = "mnt/fsp_param/internal_params_fsp_pst_subarray.json"


class FspPstSubarrayComponentManager(FspModeSubarrayComponentManager):
    """A component manager for the FspPstSubarray device."""

    def __init__(
        self: FspPstSubarrayComponentManager,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param hps_fsp_pst_controller_fqdn: FQDN of the HPS FSP PST controller device
        """

        super().__init__(
            internal_parameter_path=FSP_PST_PARAM_PATH,
            *args,
            **kwargs,
        )

        self._timing_beam_id = []

    # -------------
    # Class Helpers
    # -------------

    def _build_hps_fsp_config_mode_specific(
        self: FspPstSubarrayComponentManager,
        configuration: dict,
        hps_fsp_configuration: dict,
    ) -> None:
        """
        Helper function for _build_hps_fsp_config in base class.

        Builds the parameters that are specific to PST HPS FSP configuration.

        Sets the timingBeamID attribute from the timing beam provided in the
        configuration pass down by the Subarray Devices.

        :param configuration: A FSP scan configuration, refer to
                              CbfSubarrayComponentManager._fsp_configure_scan
        :param hps_fsp_configuration: A work in progress HPS FSP configuration
        """
        hps_fsp_configuration["timing_beams"] = configuration["timing_beams"]

        for timing_beam in hps_fsp_configuration["timing_beams"]:
            self._timing_beam_id.append(timing_beam["timing_beam_id"])

    # -------------
    # Fast Commands
    # -------------

    # ---------------------
    # Long Running Commands
    # ---------------------

    def _configure_scan(
        self: FspPstSubarrayComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute configure scan operation.

        :param argin: JSON string with the configure scan parameters
        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort event

        :return: None
        """

        # Set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ConfigureScan", task_callback, task_abort_event
        ):
            return

        # Release previously assigned VCCs
        self._deconfigure()

        configuration = json.loads(argin)

        # Assign newly specified VCCs
        self._assign_vcc(configuration["bf_vcc_ids"])

        # Issue ConfigureScan to HPS FSP PST controller
        if not self.simulation_mode:
            hps_fsp_configuration = self._build_hps_fsp_config(configuration)
            self.last_hps_scan_configuration = hps_fsp_configuration
            try:
                self._proxy_hps_fsp_mode_controller.ConfigureScan(
                    hps_fsp_configuration
                )
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failure in issuing ConfigureScan to HPS FSP PST; {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue ConfigureScan command to HPS FSP PST controller device.",
                    ),
                )
                return

        # Update obsState callback
        self._update_component_state(configured=True)

        task_callback(
            result=(ResultCode.OK, "ConfigureScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return
