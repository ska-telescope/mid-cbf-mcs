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

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


class FspPssSubarrayComponentManager(
    CbfComponentManager, CspObsComponentManager
):
    """A component manager for the FspPssSubarray device."""

    def __init__(
        self: FspPssSubarrayComponentManager,
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

        self._scan_id = 0
        self._search_window_id = 0
        self._config_id = ""
        self._fsp_id = fsp_id
        self._output_enable = 0
        self._search_beams = []
        self._receptors = []
        self._search_beam_id = []

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )

    @property
    def scan_id(self: FspPssSubarrayComponentManager) -> int:
        """
        Scan ID

        :return: the scan id
        :rtype: int
        """
        return self._scan_id

    @property
    def config_id(self: FspPssSubarrayComponentManager) -> str:
        """
        Config ID

        :return: the config id
        :rtype: str
        """
        return self._config_id

    @property
    def fsp_id(self: FspPssSubarrayComponentManager) -> int:
        """
        Fsp ID

        :return: the fsp id
        :rtype: int
        """
        return self._fsp_id

    @property
    def search_window_id(self: FspPssSubarrayComponentManager) -> int:
        """
        Search Window ID

        :return: the search window id
        :rtype: int
        """
        return self._search_window_id

    @property
    def search_beams(self: FspPssSubarrayComponentManager) -> List[str]:
        """
        Search Beams

        :return: search beams
        :rtype: List[str]
        """
        return self._search_beams

    @property
    def search_beam_id(self: FspPssSubarrayComponentManager) -> List[int]:
        """
        Search Beam ID

        :return: search beam id
        :rtype: List[int]
        """
        return self._search_beam_id

    @property
    def output_enable(self: FspPssSubarrayComponentManager) -> bool:
        """
        Output Enable

        :return: output enable
        :rtype: bool
        """
        return self._output_enable

    @property
    def receptors(self: FspPssSubarrayComponentManager) -> List[int]:
        """
        Receptors

        :return: list of receptor ids
        :rtype: List[int]
        """
        return self._receptors

    def start_communicating(
        self: FspPssSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)

    def stop_communicating(self: FspPssSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        self._logger.info(
            "Entering FspPssSubarrayComponentManager.stop_communicating"
        )
        super().stop_communicating()

        self._connected = False

    def _add_receptors(
        self: FspPssSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Add specified receptors to the subarray.

        :param argin: ids of receptors to add.
        """
        errs = []  # list of error messages

        for receptorID in argin:
            try:
                if receptorID not in self._receptors:
                    self._logger.info(f"Receptor {receptorID} added.")
                    self._receptors.append(receptorID)
                else:
                    # TODO: this is not true if more receptors can be
                    #       specified for the same search beam
                    log_msg = f"Receptor {receptorID} already assigned to current FSP subarray."
                    self._logger.warning(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append(f"Invalid receptor ID: {receptorID}")

        if errs:
            msg = "\n".join(errs)
            self._logger.error(msg)

    def _remove_receptors(
        self: FspPssSubarrayComponentManager, argin: List[int]
    ) -> None:
        """
        Remove specified receptors from the subarray.

        :param argin: ids of receptors to remove.
        """

        for receptorID in argin:
            if receptorID in self._receptors:
                self._logger.info(f"Receptor {receptorID} removed.")
                self._receptors.remove(receptorID)
            else:
                log_msg = f"Receptor {receptorID} not assigned to FSP subarray. Skipping."
                self._logger.warning(log_msg)

    def _remove_all_receptors(self: FspPssSubarrayComponentManager) -> None:
        """Remove all receptors from the subarray."""
        self._remove_receptors(self._receptors[:])

    def configure_scan(
        self: FspPssSubarrayComponentManager, configuration: str
    ) -> Tuple[ResultCode, str]:
        """
        Performs the ConfigureScan() command functionality

        :param configuration: The configuration as JSON formatted string
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        configuration = json.loads(configuration)

        self._search_window_id = int(configuration["search_window_id"])

        self._remove_all_receptors()

        for searchBeam in configuration["search_beam"]:
            if len(searchBeam["receptor_ids"]) != 1:
                # TODO - to add support for multiple receptors
                msg = "Currently only 1 receptor per searchBeam is supported"
                self._logger.error(msg)
                return (ResultCode.FAILED, msg)

            # "receptor_ids" values are pairs of str and int
            receptors_to_add = [
                receptor[1] for receptor in searchBeam["receptor_ids"]
            ]
            self._add_receptors(receptors_to_add)
            self._search_beams.append(json.dumps(searchBeam))
            self._search_beam_id.append(int(searchBeam["search_beam_id"]))

        return (
            ResultCode.OK,
            "FspPssSubarray ConfigureScan command completed OK",
        )

    def scan(
        self: FspPssSubarrayComponentManager, scan_id: int
    ) -> Tuple[ResultCode, str]:
        """
        Performs the Scan() command functionality

        :param scan_id: The scan id
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            self._scan_id = scan_id
        except Exception as e:
            self._component_obs_fault_callback(True)
            self._logger.error(str(e))

        return (ResultCode.OK, "FspPssSubarray Scan command completed OK")

    def end_scan(
        self: FspPssSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Performs the EndScan() command functionality

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            pass
        except Exception as e:
            self._component_obs_fault_callback(True)
            self._logger.error(str(e))

        return (ResultCode.OK, "FspPssSubarray EndScan command completed OK")

    def _deconfigure(
        self: FspPssSubarrayComponentManager,
    ) -> None:
        self._search_beams = []
        self._search_window_id = 0
        self._search_beam_id = []
        self._output_enable = 0
        self._scan_id = 0
        self._config_id = ""

        self._remove_all_receptors()

    def go_to_idle(
        self: FspPssSubarrayComponentManager,
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
            self._remove_all_receptors()
        except Exception as e:
            self._component_obs_fault_callback(True)
            self._logger.error(str(e))

        return (ResultCode.OK, "FspPssSubarray GoToIdle command completed OK")

    def obsreset(
        self: FspPssSubarrayComponentManager,
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
            self._remove_all_receptors()
            # TODO: ObsReset command not implemented for the HPS FSP application, see CIP-1850
        except Exception as e:
            self._component_obs_fault_callback(True)
            self._logger.error(str(e))

        return (ResultCode.OK, "FspPssSubarray ObsReset command completed OK")

    def abort(
        self: FspPssSubarrayComponentManager,
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
        except Exception as e:
            self._component_obs_fault_callback(True)
            self._logger.error(str(e))

        return (ResultCode.OK, "Abort command not implemented")
