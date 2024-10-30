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
from typing import Any, Callable, Optional, Tuple

import tango
from ska_control_model import PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


class FspPstSubarrayComponentManager(CbfComponentManager):
    """A component manager for the FspPstSubarray device."""

    def __init__(
        self: FspPstSubarrayComponentManager,
        *args: Any,
        hps_fsp_pst_controller_fqdn: str,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        # TODO: for Mid.CBF, param hps_fsp_corr_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_corr_controller_fqdn: FQDN of the HPS FSP Correlator controller device
        """

        super().__init__(*args, **kwargs)

        self._hps_fsp_pst_controller_fqdn = hps_fsp_pst_controller_fqdn
        self._proxy_hps_fsp_pst_controller = None

        self._connected = False

        self.obs_faulty = False

        # TODO: Remove
        # self._fsp_id = fsp_id
        self._vcc_ids = []
        self._timing_beams = []
        self._timing_beam_id = []
        self._scan_id = 0
        self._output_enable = 0

        # TODO: Remove
        # super().__init__(
        #     logger=logger,
        #     push_change_event_callback=push_change_event_callback,
        #     communication_status_changed_callback=communication_status_changed_callback,
        #     component_power_mode_changed_callback=component_power_mode_changed_callback,
        #     component_fault_callback=component_fault_callback,
        #     obs_state_model=None,
        # )

    @property
    def fsp_id(self: FspPstSubarrayComponentManager) -> int:
        """
        Fsp ID

        :return: the fsp id
        :rtype: int
        """
        return self._fsp_id

    @property
    def timing_beams(self: FspPstSubarrayComponentManager) -> list[str]:
        """
        Timing Beams

        :return: the timing beams
        :rtype: list[str]
        """
        return self._timing_beams

    @property
    def timing_beam_id(self: FspPstSubarrayComponentManager) -> list[int]:
        """
        Timing Beam ID

        :return: list of timing beam ids
        :rtype: list[int]
        """
        return self._timing_beam_id

    @property
    def vcc_ids(self: FspPstSubarrayComponentManager) -> list[int]:
        """
        Assigned VCC IDs

        :return: list of VCC IDs
        :rtype: list[int]
        """
        return self._vcc_ids

    @property
    def scan_id(self: FspPstSubarrayComponentManager) -> int:
        """
        Scan ID

        :return: the scan id
        :rtype: int
        """
        return self._scan_id

    @property
    def output_enable(self: FspPstSubarrayComponentManager) -> bool:
        """
        Output Enable

        :return: output enable
        :rtype: bool
        """
        return self._output_enable

    # -------------
    # Communication
    # -------------

    def start_communicating(
        self: FspPstSubarrayComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_corr_controller = context.DeviceProxy(
                    device_name=self._hps_fsp_pst_controller_fqdn
                )
            except tango.DevFailed as df:
                self.logger.error(
                    f"Failed to connect to {self._hps_fsp_pst_controller_fqdn}; {df}"
                )
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    "Failed to establish proxy to HPS FSP PST controller device.",
                )

        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    # -------------
    # Class Helpers
    # -------------

    def _assign_vcc(
        self: FspPstSubarrayComponentManager, argin: list[int]
    ) -> None:
        """
        Assign specified VCCs to the FSP PST subarray.

        :param argin: IDs of VCCs to add.
        """
        for vccID in argin:
            if vccID not in self._vcc_ids:
                self.logger.info(f"VCC {vccID} added.")
                self._vcc_ids.append(vccID)
            else:
                log_msg = f"VCC {vccID} already assigned to current FSP PST subarray."
                self.logger.warning(log_msg)

    def _release_vcc(
        self: FspPstSubarrayComponentManager, argin: list[int]
    ) -> None:
        """
        Release assigned VCC from the FSP PST subarray.

        :param argin: IDs of VCCs to remove.
        """

        for vccID in argin:
            if vccID in self._vcc_ids:
                self.logger.info(f"VCC {vccID} removed.")
                self._vcc_ids.remove(vccID)
            else:
                log_msg = (
                    f"VCC {vccID} not assigned to FSP PST subarray. Skipping."
                )
                self.logger.warning(log_msg)
    
    def _deconfigure(
        self: FspPstSubarrayComponentManager,
    ) -> None:
        self._timing_beams = []
        self._timing_beam_id = []
        self._scan_id = 0
        self._output_enable = 0
    

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

        :return: None
        """
        self._deconfigure()


        configuration = json.loads(argin)

        # Note: subarray has translated DISH IDs to VCC IDs in the JSON at this point
        for timingBeam in configuration["timing_beam"]:
            self._assign_vcc(timingBeam["receptor_ids"])
            self._timing_beams.append(json.dumps(timingBeam))
            self._timing_beam_id.append(int(timingBeam["timing_beam_id"]))

        # Issue ConfigureScan to HPS FSP Corr controller
        if not self.simulation_mode:
            # hps_fsp_configuration = self._build_hps_fsp_config(configuration)
            try:
                self._proxy_hps_fsp_pst_controller.set_timeout_millis(
                    self._lrc_timeout * 1000
                )
                self._proxy_hps_fsp_psr_controller.ConfigureScan(
                    configuration
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
    def _scan(
        self: FspPstSubarrayComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Performs the Scan() command functionality

        :param argin: The scan id
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Scan", task_callback, task_abort_event
        ):
            return
        
        self._scan_id = argin
        
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_pst_controller.Scan(self.scan_id)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Scan command to HPS FSP PST controller device.",
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
        self: FspPstSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Performs the EndScan() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "EndScan", task_callback, task_abort_event
        ):
            return
        
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_pst_controller.EndScan()
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
        self: FspPstSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Performs the GoToIdle() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "GoToIdle", task_callback, task_abort_event
        ):
            return
        
        if not self.simulation_mode:
            try:
                self._proxy_hps_fsp_pst_controller.GoToIdle()
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
        self: FspPstSubarrayComponentManager,
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
                    "Failed to issue Abort command to HPS FSP PST controller device.",
                ),
            )
            return


    def _obs_reset(
        self: FspPstSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Performs the ObsReset() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
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
