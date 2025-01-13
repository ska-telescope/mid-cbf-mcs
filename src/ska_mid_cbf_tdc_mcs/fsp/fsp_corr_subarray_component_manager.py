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

from ska_mid_cbf_tdc_mcs.commons.vcc_gain_utils import VccGainUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_tdc_mcs.fsp.fsp_mode_subarray_component_manager import (
    FspModeSubarrayComponentManager,
)

FSP_CORR_PARAM_PATH = "mnt/fsp_param/internal_params_fsp_corr_subarray.json"


class FspCorrSubarrayComponentManager(FspModeSubarrayComponentManager):
    """
    A component manager for the FspCorrSubarray device.
    """

    def __init__(
        self: FspCorrSubarrayComponentManager,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param hps_fsp_corr_controller_fqdn: FQDN of the HPS FSP Correlator controller device
        """
        super().__init__(
            *args,
            **kwargs,
        )

        self.frequency_band = 0
        self.frequency_slice_id = 0
        self.channel_averaging_map = [
            [
                int(
                    i
                    * const.NUM_FINE_CHANNELS
                    / const.NUM_CHANNELS_PER_SPEAD_STREAM
                )
                + 1,
                0,
            ]
            for i in range(const.NUM_CHANNELS_PER_SPEAD_STREAM)
        ]
        self.vis_destination_address = {
            "outputHost": [],
            "outputPort": [],
        }
        self.fsp_channel_offset = 0

        self.output_link_map = [[0, 0] for _ in range(40)]

    # -------------
    # Class Helpers
    # -------------

    def _build_hps_fsp_config(
        self: FspCorrSubarrayComponentManager, configuration: dict
    ) -> str:
        """
        Build the input JSON string for the HPS FSP Corr controller ConfigureScan command
        """
        # append all internal parameters to the configuration to pass to HPS
        # first construct HPS FSP ConfigureScan input

        # Access constants for CIP-2364 through configuration[band_number] and send that to gloabl enums for values
        hps_fsp_configuration = dict({"configure_scan": configuration})

        # self.logger.info(f"{hps_fsp_configuration}")

        # Get the internal parameters from file
        internal_params_file_name = FSP_CORR_PARAM_PATH
        with open(internal_params_file_name) as f:
            hps_fsp_configuration.update(
                json.loads(f.read().replace("\n", ""))
            )

        # append the fs_sample_rates to the configuration
        hps_fsp_configuration["fs_sample_rates"] = configuration[
            "fs_sample_rates"
        ]

        hps_fsp_configuration["vcc_id_to_rdt_freq_shifts"] = configuration[
            "vcc_id_to_rdt_freq_shifts"
        ]

        # TODO: Assume gain is an array, check with JSON Validator, consider lowering the size of the array for testing, also print on HPS side and validate
        # For now, we will reinitialize gain as a large (32k) sized array in the component manager
        # TODO: TEst comment tdc mcs build
        hps_fsp_configuration["fine_channelizer"]["gain"] = [1] * (16384)
        fs_id = hps_fsp_configuration["configure_scan"]["frequency_slice_id"]
        self.logger.info(f"Frequency slice id: {fs_id}")
        gain_corrections = VccGainUtils.get_vcc_ripple_correction(
            hps_fsp_configuration["configure_scan"]["frequency_band"],
            self.logger,
            fs_id
            # hps_fsp_configuration["configure_scan"]["frequency_slice_id"]
        )
        for gain_index, gain in enumerate(
            hps_fsp_configuration["fine_channelizer"]["gain"]
        ):
            gain = gain * gain_corrections[gain_index % 16384]
            hps_fsp_configuration["fine_channelizer"]["gain"][
                gain_index
            ] = gain

        # TODO: zoom-factor removed from configurescan, but required by HPS, to
        # be inferred from channel_width introduced in ADR-99 when ready to
        # implement zoom
        hps_fsp_configuration["configure_scan"]["zoom_factor"] = 0

        self.logger.info(
            f"HPS FSP Corr configuration: {hps_fsp_configuration}."
        )

        return json.dumps(hps_fsp_configuration)

    def _deconfigure(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        """Deconfigure scan configuration parameters."""
        self.frequency_band = 0
        self.frequency_slice_id = 0

        super()._deconfigure()

    # -------------
    # Fast Commands
    # -------------

    # ---------------------
    # Long Running Commands
    # ---------------------

    def _configure_scan(
        self: FspCorrSubarrayComponentManager,
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
        self.logger.info("STARTING CONFIGSCAN")
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ConfigureScan", task_callback, task_abort_event
        ):
            return

        # Release previously assigned VCCs
        self._deconfigure()

        # Load configuration JSON, store key read attribute parameters
        configuration = json.loads(argin)
        self.config_id = configuration["config_id"]
        self.frequency_band = freq_band_dict()[
            configuration["frequency_band"]
        ]["band_index"]
        self.logger.info(
            f"Here is the frequency band class attribute: {self.frequency_band}"
        )
        self.frequency_slice_id = int(configuration["frequency_slice_id"])

        # Assign newly specified VCCs
        self._assign_vcc(configuration["corr_vcc_ids"])

        # Issue ConfigureScan to HPS FSP Corr controller
        if not self.simulation_mode:
            self.logger.info("Building hps")
            hps_fsp_configuration = self._build_hps_fsp_config(configuration)
            self.last_hps_scan_configuration = hps_fsp_configuration
            try:
                self.logger.info("Entering HPS FSP configurescan")
                # self.logger.info("Printing HPS ConfigScan")
                # TODO: Validate this with JSON Validator
                # TODO: Update: Valid if replace ' ' with " "
                # self.logger.info(f"{hps_fsp_configuration}")
                # TODO: Error is here, does this call configurescan in DsFspCorrControllerComponentManager.cpp? Or where? Timeout happens but where is error? Can't find.
                self._proxy_hps_fsp_corr_controller.ConfigureScan(
                    hps_fsp_configuration
                )
                self.logger.info("Exiting HPS FSP configurescan")
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failure in issuing ConfigureScan to HPS FSP CORR; {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue ConfigureScan command to HPS FSP Corr controller device.",
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
