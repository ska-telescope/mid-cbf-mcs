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
from ska_control_model import CommunicationStatus, PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.obs_component_manager import (
    CbfObsComponentManager,
)

FSP_CORR_PARAM_PATH = "mnt/fsp_param/internal_params_fsp_corr_subarray.json"


class FspCorrSubarrayComponentManager(CbfObsComponentManager):
    """
    A component manager for the FspCorrSubarray device.
    """

    def __init__(
        self: FspCorrSubarrayComponentManager,
        *args: Any,
        hps_fsp_corr_controller_fqdn: str,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        # TODO: for Mid.CBF, param hps_fsp_corr_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_corr_controller_fqdn: FQDN of the HPS FSP Correlator controller device
        """
        super().__init__(*args, **kwargs)

        self._hps_fsp_corr_controller_fqdn = hps_fsp_corr_controller_fqdn
        self._proxy_hps_fsp_corr_controller = None

        self.delay_model = ""
        self.vcc_ids = []
        self.frequency_band = 0
        self.frequency_slice_id = 0
        self.scan_id = 0
        self.config_id = ""
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
    # Communication
    # -------------

    def _start_communicating(
        self: FspCorrSubarrayComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_corr_controller = context.DeviceProxy(
                    device_name=self._hps_fsp_corr_controller_fqdn
                )
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to connect to {self._hps_fsp_corr_controller_fqdn}; {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    "Failed to establish proxy to HPS FSP Corr controller device.",
                )

        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    # -------------
    # Class Helpers
    # -------------

    def _assign_vcc(
        self: FspCorrSubarrayComponentManager, argin: list[int]
    ) -> None:
        """
        Assign specified VCCs to the FSP CORR subarray.

        :param argin: IDs of VCCs to add.
        """

        for vccID in argin:
            if vccID not in self.vcc_ids:
                self.logger.info(f"VCC {vccID} assigned.")
                self.vcc_ids.append(vccID)
            else:
                log_msg = f"VCC {vccID} already assigned to current FSP CORR subarray."
                self.logger.warning(log_msg)

    def _release_vcc(
        self: FspCorrSubarrayComponentManager, argin: list[int]
    ) -> None:
        """
        Release assigned VCC from the FSP CORR subarray.

        :param argin: IDs of VCCs to remove.
        """
        for vccID in argin:
            if vccID in self.vcc_ids:
                self.logger.info(f"VCC {vccID} released.")
                self.vcc_ids.remove(vccID)
            else:
                log_msg = (
                    "VCC {vccID} not assigned to FSP CORR subarray. Skipping."
                )
                self.logger.warning(log_msg)

    def _build_hps_fsp_config(
        self: FspCorrSubarrayComponentManager, configuration: dict
    ) -> str:
        """
        Build the input JSON string for the HPS FSP Corr controller ConfigureScan command
        """
        # append all internal parameters to the configuration to pass to HPS
        # first construct HPS FSP ConfigureScan input
        hps_fsp_configuration = dict({"configure_scan": configuration})

        self.logger.debug(f"{hps_fsp_configuration}")

        # VCC IDs must be sorted in ascending order for the HPS
        hps_fsp_configuration["configure_scan"]["subarray_vcc_ids"].sort()
        hps_fsp_configuration["configure_scan"]["corr_vcc_ids"].sort()

        hps_fsp_configuration["configure_scan"][
            "subarray_vcc_ids"
        ] = hps_fsp_configuration["configure_scan"]["corr_vcc_ids"]

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

        # TODO: zoom-factor removed from configurescan, but required by HPS, to
        # be inferred from channel_width introduced in ADR-99 when ready to
        # implement zoom
        hps_fsp_configuration["configure_scan"]["zoom_factor"] = 0

        self.logger.debug(
            f"HPS FSP Corr configuration: {hps_fsp_configuration}."
        )

        return json.dumps(hps_fsp_configuration)

    def _deconfigure(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        """Deconfigure scan configuration parameters."""
        self.frequency_band = 0
        self.frequency_slice_id = 0
        self.scan_id = 0
        self.config_id = ""

        # release all assigned VCC to reset to IDLE state
        self._release_vcc(self.vcc_ids.copy())

    # -------------
    # Fast Commands
    # -------------

    def update_delay_model(
        self: FspCorrSubarrayComponentManager, model: str
    ) -> tuple[ResultCode, str]:
        """
        Update the FSP's delay model (serialized JSON object)

        :param model: the delay model data
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.info("Entering FspCorrSubarray.update_delay_model()")

        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_corr_controller.UpdateDelayModels(model)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    "Failed to issue UpdateDelayModels command to HPS FSP Corr controller",
                )

        # the whole delay model must be stored
        self.delay_model = model
        self.device_attr_change_callback("delayModel", model)
        self.device_attr_archive_callback("delayModel", model)

        return (ResultCode.OK, "UpdateDelayModel completed OK")

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

        # Load configuration JSON, store key read attribute parameters
        configuration = json.loads(argin)
        self.config_id = configuration["config_id"]
        self.frequency_band = freq_band_dict()[
            configuration["frequency_band"]
        ]["band_index"]
        self.frequency_slice_id = int(configuration["frequency_slice_id"])

        # Assign newly specified VCCs
        self._assign_vcc(configuration["corr_vcc_ids"])

        # Issue ConfigureScan to HPS FSP Corr controller
        if not self.simulation_mode:
            hps_fsp_configuration = self._build_hps_fsp_config(configuration)
            try:
                self._proxy_hps_fsp_corr_controller.set_timeout_millis(
                    self._lrc_timeout * 1000
                )
                self._proxy_hps_fsp_corr_controller.ConfigureScan(
                    hps_fsp_configuration
                )
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

    def _scan(
        self: FspCorrSubarrayComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Begin scan operation.

        :param argin: scan ID integer

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Scan", task_callback, task_abort_event
        ):
            return

        self.scan_id = argin

        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_corr_controller.Scan(self.scan_id)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Scan command to HPS FSP Corr controller device.",
                    ),
                )
                return

        # Update obsState callback
        self._update_component_state(scanning=True)

        task_callback(
            result=(ResultCode.OK, "Scan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _end_scan(
        self: FspCorrSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        End scan operation.

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "EndScan", task_callback, task_abort_event
        ):
            return

        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_corr_controller.EndScan()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue EndScan command to HPS FSP Corr controller device.",
                    ),
                )
                return

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "EndScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _go_to_idle(
        self: FspCorrSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "GoToIdle", task_callback, task_abort_event
        ):
            return

        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_corr_controller.GoToIdle()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Unconfigure command to HPS FSP Corr controller device.",
                    ),
                )
                return

        # reset configured attributes
        self._deconfigure()

        # Update obsState callback
        self._update_component_state(configured=False)

        task_callback(
            result=(ResultCode.OK, "GoToIdle completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _abort(
        self: FspCorrSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Abort the current scan operation.

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Abort", task_callback, task_abort_event
        ):
            return
        try:
            # TODO: Abort command not implemented for the HPS FSP application
            pass
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Abort command to HPS FSP Corr controller device.",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "Abort completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _obs_reset(
        self: FspCorrSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset the scan operation from ABORTED or FAULT.

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ObsReset", task_callback, task_abort_event
        ):
            return

        if not self.simulation_mode:
            try:
                pass
                # TODO: ObsReset command not implemented for the HPS FSP application, see CIP-1850
                # self._proxy_hps_fsp_corr_controller.ObsReset()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue ObsReset to HPS FSP Corr controller device.",
                    ),
                )
                return

        # reset configured attributes
        self._deconfigure()

        # Update obsState callback
        # There is no obsfault == False action implemented, however,
        # we reset it it False so that obsfault == True may be triggered in the future
        self._update_component_state(configured=False, obsfault=False)

        task_callback(
            result=(ResultCode.OK, "ObsReset completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return
