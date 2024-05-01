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
import logging
from typing import Callable, List, Optional, Tuple

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


class FspPstSubarrayComponentManager(
    CbfComponentManager, CspObsComponentManager
):
    """A component manager for the FspPstSubarray device."""

    def __init__(
        self: FspPstSubarrayComponentManager,
        logger: logging.Logger,
        fsp_id: int,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        component_obs_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param cbf_controller_address: address of the cbf controller device
        :param vcc_fqdns_all: list of all vcc fqdns
        :param subarray_id: the id indicating the subarray membership
            of the fsp pss subarray device
        :param fsp_id: the id of the corresponding fsp device
        :param push_change_event: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault (for op state model)
        :param component_obs_fault_callback: callback to be called in event of
            component fault (for obs state model)
        """
        self._logger = logger

        self._component_obs_fault_callback = component_obs_fault_callback

        self._connected = False

        self.obs_faulty = False

        self._fsp_id = fsp_id
        self._vcc_ids = []
        self._timing_beams = []
        self._timing_beam_id = []
        self._scan_id = 0
        self._output_enable = 0

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )

    @property
    def fsp_id(self: FspPstSubarrayComponentManager) -> int:
        """
        Fsp ID

        :return: the fsp id
        :rtype: int
        """
        return self._fsp_id

    @property
    def timing_beams(self: FspPstSubarrayComponentManager) -> List[str]:
        """
        Timing Beams

        :return: the timing beams
        :rtype: List[str]
        """
        return self._timing_beams

    @property
    def timing_beam_id(self: FspPstSubarrayComponentManager) -> List[int]:
        """
        Timing Beam ID

        :return: list of timing beam ids
        :rtype: List[int]
        """
        return self._timing_beam_id

    @property
    def vcc_ids(self: FspPstSubarrayComponentManager) -> List[int]:
        """
        Assigned VCC IDs

        :return: list of VCC IDs
        :rtype: List[int]
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

    def start_communicating(
        self: FspPstSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: FspPstSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        self._logger.info(
            "Entering FspPstSubarrayComponentManager.stop_communicating"
        )
        super().stop_communicating()

        self._connected = False

    def _assign_vcc(
        self: FspPstSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Assign specified VCCs to the FSP PST subarray.

        :param argin: IDs of VCCs to add.
        """
        for vccID in argin:
            if vccID not in self._vcc_ids:
                self._logger.info(f"VCC {vccID} added.")
                self._vcc_ids.append(vccID)
            else:
                log_msg = f"VCC {vccID} already assigned to current FSP PST subarray."
                self._logger.warning(log_msg)

    def _release_vcc(
        self: FspPstSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Release assigned VCC from the FSP PST subarray.

        :param argin: IDs of VCCs to remove.
        """

        for vccID in argin:
            if vccID in self._vcc_ids:
                self._logger.info(f"VCC {vccID} removed.")
                self._vcc_ids.remove(vccID)
            else:
                log_msg = (
                    f"VCC {vccID} not assigned to FSP PST subarray. Skipping."
                )
                self._logger.warning(log_msg)

    def _release_all_vcc(self: FspPstSubarrayComponentManager) -> None:
        """Release all assigned VCCs from the FSP PST subarray."""
        self._release_vcc(self._vcc_ids.copy())

    def configure_scan(
        self: FspPstSubarrayComponentManager, configuration: str
    ) -> Tuple[ResultCode, str]:
        """
        Performs the ConfigureScan() command functionality

        :param configuration: The configuration as JSON formatted string
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._deconfigure()

        # release previously assigned VCCs and assign newly specified VCCs
        self._release_all_vcc()

        configuration = json.loads(configuration)

        # Note: subarray has translated DISH IDs to VCC IDs in the JSON at this point
        for timingBeam in configuration["timing_beam"]:
            self._assign_vcc(timingBeam["receptor_ids"])
            self._timing_beams.append(json.dumps(timingBeam))
            self._timing_beam_id.append(int(timingBeam["timing_beam_id"]))

        return (
            ResultCode.OK,
            "FspPstSubarray ConfigureScan command completed OK",
        )

    def scan(
        self: FspPstSubarrayComponentManager, scan_id: int
    ) -> Tuple[ResultCode, str]:
        """
        Performs the Scan() command functionality

        :param scan_id: The scan id
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._scan_id = scan_id
        try:
            # TODO: Scan command not implemented for the PST application
            pass
        except tango.DevFailed as df:
            self._component_obs_fault_callback(True)
            self._logger.error(str(df))
            return (ResultCode.FAILED, "FspPstSubarray Scan command failed")

        return (ResultCode.OK, "FspPstSubarray Scan command completed OK")

    def end_scan(
        self: FspPstSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the EndScan() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            # TODO: EndScan command not implemented for the PST application
            pass
        except tango.DevFailed as df:
            self._component_obs_fault_callback(True)
            self._logger.error(str(df))
            return (ResultCode.FAILED, "FspPstSubarray EndScan command failed")

        return (ResultCode.OK, "FspPstSubarray EndScan command completed OK")

    def _deconfigure(
        self: FspPstSubarrayComponentManager,
    ) -> None:
        self._timing_beams = []
        self._timing_beam_id = []
        self._output_enable = 0

    def go_to_idle(
        self: FspPstSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the GoToIdle() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            self._deconfigure()
            self._release_all_vcc()
            # TODO: GoToIdle command not implemented for the PST application
        except tango.DevFailed as df:
            self._component_obs_fault_callback(True)
            self._logger.error(str(df))
            return (
                ResultCode.FAILED,
                "FspPstSubarray GoToIdle command failed",
            )

        return (ResultCode.OK, "FspPstSubarray GoToIdle command completed OK")

    def obsreset(
        self: FspPstSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the ObsReset() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            self._deconfigure()
            self._release_all_vcc()
            # TODO: ObsReset command not implemented for the HPS FSP application, see CIP-1850
        except tango.DevFailed as df:
            self._component_obs_fault_callback(True)
            self._logger.error(str(df))
            return (
                ResultCode.FAILED,
                "FspPstSubarray ObsReset command failed",
            )

        return (ResultCode.OK, "FspPstSubarray ObsReset command completed OK")

    def abort(
        self: FspPstSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the Abort() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            # TODO: Abort command not implemented for the HPS FSP application
            pass
        except tango.DevFailed as df:
            self._component_obs_fault_callback(True)
            self._logger.error(str(df))
            return (ResultCode.FAILED, "FspPstSubarray Abort command failed")

        return (ResultCode.OK, "Abort command not implemented")
