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
from ska_control_model import PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_tdc_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_tdc_mcs.component.obs_component_manager import (
    CbfObsComponentManager,
)


class FspModeSubarrayComponentManager(CbfObsComponentManager):
    """
    A base class component manager for the FspModeSubarray devices.
    """

    def __init__(
        self: FspModeSubarrayComponentManager,
        hps_fsp_mode_controller_fqdn: str,
        internal_parameter_path: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param hps_fsp_mode_controller_fqdn: FQDN of the HPS FSP controller device for a given FSP Mode
        :param internal_parameter_path: Path of the internal parameter JSON file.
                                        Contains parameters that is used to build the HPS FSP Configuration for a specific FSP Mode

        TODO: for Mid.CBF, param hps_fsp_hsp_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_corr_controller_fqdn: FQDN of the HPS FSP Correlator controller device
        """
        super().__init__(*args, **kwargs)

        self._proxy_hps_fsp_mode_controller = None
        self._hps_fsp_mode_controller_fqdn = hps_fsp_mode_controller_fqdn
        self._internal_parameter_path = internal_parameter_path
        self.delay_model = ""
        self.vcc_ids = []
        self.scan_id = 0
        self.config_id = ""
        self.last_hps_scan_configuration = ""

    # -------------
    # Communication
    # -------------

    def _start_communicating(
        self: FspModeSubarrayComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_mode_controller = context.DeviceProxy(
                    device_name=self._hps_fsp_mode_controller_fqdn
                )
                self._proxy_hps_fsp_mode_controller.set_timeout_millis(
                    self._lrc_timeout * 1000
                )
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to connect to {self._hps_fsp_mode_controller_fqdn}; {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    "Failed to establish proxy to HPS FSP controller device.",
                )

        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    # -------------
    # Class Helpers
    # -------------

    def _assign_vcc(
        self: FspModeSubarrayComponentManager, argin: list[int]
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
                log_msg = (
                    f"VCC {vccID} already assigned to current FSP subarray."
                )
                self.logger.warning(log_msg)

    def _release_vcc(
        self: FspModeSubarrayComponentManager, argin: list[int]
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
                log_msg = "VCC {vccID} not assigned to FSP subarray. Skipping."
                self.logger.warning(log_msg)

    def _deconfigure(
        self: FspModeSubarrayComponentManager,
    ) -> None:
        self.delay_model = ""
        self.vcc_ids = []
        self.scan_id = 0
        self.config_id = ""
        self.last_hps_scan_configuration = ""

        self._release_vcc(self.vcc_ids.copy())

    def _build_hps_fsp_config(
        self: FspModeSubarrayComponentManager, configuration: dict
    ) -> str:
        """
        Builds the input JSON string for the HPS FSP controller ConfigureScan command.
        This is the common base class implementations.
        Override the _build_hps_fsp_config_mode_specific function in the child
        classes for FSP mode specific requirements.

        :param configuration: A FSP scan configuration, refer to
                              CbfSubarrayComponentManager._fsp_configure_scan

        :return: A JSON string representing a HPS FSP configuration
        :rtype: str
        """

        # append all internal parameters to the configuration to pass to HPS
        # first construct HPS FSP ConfigureScan input
        hps_fsp_configuration = dict({"configure_scan": configuration})

        self.logger.debug(f"{hps_fsp_configuration}")

        self._build_hps_fsp_config_common(configuration, hps_fsp_configuration)
        self._build_hps_fsp_config_mode_specific(
            configuration, hps_fsp_configuration
        )

        self.logger.debug(f"HPS FSP configuration: {hps_fsp_configuration}.")

        return json.dumps(hps_fsp_configuration)

    def _build_hps_fsp_config_common(
        self: FspModeSubarrayComponentManager,
        configuration: dict,
        hps_fsp_configuration: dict,
    ) -> None:
        """
        Helper function for _build_hps_fsp_config.

        Builds the parameters for HPS FSP configuration that is common to all
        function modes.

        :param configuration: A FSP scan configuration, refer to
                              CbfSubarrayComponentManager._fsp_configure_scan
        :param hps_fsp_configuration: A work in progress HPS FSP configuration


        """
        # Get the internal parameters from file
        internal_params_file_name = self._internal_parameter_path
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

    def _build_hps_fsp_config_mode_specific(
        self: FspModeSubarrayComponentManager,
        configuration: dict,
        hps_fsp_configuration: dict,
    ) -> None:
        """
        Helper function for _build_hps_fsp_config.

        Builds the parameters for HPS FSP configuration that is specific for a
        function mode.

        Abstract function; To be implemented in specific FSP Mode classes.

        :raises NotImplementedError: Not implemented in abstract class

        :param configuration: A FSP scan configuration, refer to
                              CbfSubarrayComponentManager._fsp_configure_scan
        :param hps_fsp_configuration: A work in progress HPS FSP configuration
        """

        raise NotImplementedError(
            "_build_hps_fsp_config_mode_specific needs to be implemented in child class."
        )

    # -------------
    # Fast Commands
    # -------------

    def update_delay_model(
        self: FspModeSubarrayComponentManager, model: str
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
                self._proxy_hps_fsp_mode_controller.UpdateDelayModels(model)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    "Failed to issue UpdateDelayModels command to HPS FSP controller",
                )

        # the whole delay model must be stored
        self.delay_model = model
        self.device_attr_change_callback("delayModel", model)
        self.device_attr_archive_callback("delayModel", model)

        return (ResultCode.OK, "UpdateDelayModel completed OK")

    def _scan(
        self: FspModeSubarrayComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Performs the Scan() command functionality

        :param argin: The scan id
        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort event

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
                self._proxy_hps_fsp_mode_controller.Scan(self.scan_id)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Scan command to HPS FSP controller device.",
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
        self: FspModeSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Performs the EndScan() command functionality

        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort event

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
                self._proxy_hps_fsp_mode_controller.EndScan()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue EndScan command to HPS FSP controller device.",
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
        self: FspModeSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort event

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
                self._proxy_hps_fsp_mode_controller.GoToIdle()
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
        self: FspModeSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Abort the current scan operation.

        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort eve

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
                    "Failed to issue Abort command to HPS FSP controller device.",
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
        self: FspModeSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset the scan operation from ABORTED or FAULT.

        :param task_callback: command tracker update_command_info callback
        :param task_abort_event: task executor abort eve

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
                # self._proxy_hps_fsp_mode_controller.ObsReset()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue ObsReset to HPS FSP controller device.",
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
