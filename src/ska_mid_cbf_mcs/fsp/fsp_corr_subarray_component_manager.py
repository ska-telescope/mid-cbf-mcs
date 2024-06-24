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
from ska_mid_cbf_mcs.fsp.hps_fsp_corr_controller_simulator import (
    HpsFspCorrControllerSimulator,
)

# Data file path
FSP_CORR_PARAM_PATH = "mnt/fsp_param/internal_params_fsp_corr_subarray.json"

# HPS device timeout in ms
HPS_FSP_CORR_TIMEOUT = 12000


class FspCorrSubarrayComponentManager(CbfObsComponentManager):
    """A component manager for the FspCorrSubarray device."""

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

        self.vcc_ids = []
        self.frequency_band = 0
        self.frequency_slice_id = 0
        self.scan_id = 0
        self.config_id = ""
        self.channel_averaging_map = [
            [
                int(i * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS)
                + 1,
                0,
            ]
            for i in range(const.NUM_CHANNEL_GROUPS)
        ]
        self.vis_destination_address = {
            "outputHost": [],
            "outputPort": [],
        }
        self.fsp_channel_offset = 0

        self.output_link_map = [[0, 0] for _ in range(40)]

    # ---------------
    # General methods
    # ---------------

    def start_communicating(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""
        if self._communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Already communicating.")
            return
        super().start_communicating()
        if self.power_state is None:
            self._update_component_state(power=PowerState.OFF)

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

    # ---------------
    # Command methods
    # ---------------

    def on(self: FspCorrSubarrayComponentManager) -> tuple[ResultCode, str]:
        """
        Turn on FSP Corr component. This attempts to establish communication
        with the FSP Corr controller device on the HPS.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)

        :raise ConnectionError: if unable to connect to HPS FSP Corr controller
        """
        self.logger.info("Entering FspCorrSubarrayComponentManager.on")

        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if not self.simulation_mode:
            if self._proxy_hps_fsp_corr_controller is None:
                try:
                    self._proxy_hps_fsp_corr_controller = context.DeviceProxy(
                        device_name=self._hps_fsp_corr_controller_fqdn
                    )
                except tango.DevFailed as df:
                    self.logger.error(str(df.args[0].desc))
                    self._update_communication_state(
                        communication_state=CommunicationStatus.NOT_ESTABLISHED
                    )
                    return (
                        ResultCode.FAILED,
                        "Failed to establish proxies to HPS FSP Corr controller device.",
                    )
        else:
            self._proxy_hps_fsp_corr_controller = (
                HpsFspCorrControllerSimulator(
                    self._hps_fsp_corr_controller_fqdn
                )
            )

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    def off(self: FspCorrSubarrayComponentManager) -> tuple[ResultCode, str]:
        """
        Turn off FSP component; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off completed OK")

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
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ConfigureScan", task_callback, task_abort_event
        ):
            return

        # load configuration JSON, store key read attribute parameters
        configuration = json.loads(argin)
        self.config_id = configuration["config_id"]
        self.frequency_band = freq_band_dict()[
            configuration["frequency_band"]
        ]["band_index"]
        self.frequency_slice_id = int(configuration["frequency_slice_id"])

        # release previously assigned VCCs and assign newly specified VCCs
        self._deconfigure()
        self._assign_vcc(configuration["corr_vcc_ids"])

        # issue ConfigureScan to HPS FSP Corr controller
        try:
            hps_fsp_configuration = self._build_hps_fsp_config(configuration)
            self._proxy_hps_fsp_corr_controller.set_timeout_millis(
                HPS_FSP_CORR_TIMEOUT
            )
            self._proxy_hps_fsp_corr_controller.ConfigureScan(
                hps_fsp_configuration
            )
        except tango.DevFailed as df:
            self.logger.error(str(df.args[0].desc))
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

        try:
            self._proxy_hps_fsp_corr_controller.Scan(self.scan_id)
        except tango.DevFailed as df:
            self.logger.error(str(df.args[0].desc))
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

        try:
            self._proxy_hps_fsp_corr_controller.EndScan()
        except tango.DevFailed as df:
            self.logger.error(str(df.args[0].desc))
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

        try:
            self._proxy_hps_fsp_corr_controller.GoToIdle()
        except tango.DevFailed as df:
            self.logger.error(str(df.args[0].desc))
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

    def _abort_scan(
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
            self.logger.error(str(df.args[0].desc))
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
        try:
            pass
            # TODO: ObsReset command not implemented for the HPS FSP application, see CIP-1850
            # self._proxy_hps_fsp_corr_controller.ObsReset()
        except tango.DevFailed as df:
            self.logger.error(str(df.args[0].desc))
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

        task_callback(
            result=(ResultCode.OK, "ObsReset completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return
