# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
CbfSubarray
Sub-element subarray device for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

import copy
import json
import logging
import sys
import time
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Tuple

# Tango imports
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    ObsState,
    PowerMode,
)
from ska_tango_base.csp.subarray.component_manager import (
    CspSubarrayComponentManager,
)
from tango import AttrQuality, DevState

from ska_mid_cbf_mcs.attribute_proxy import CbfAttributeProxy
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.component.util import check_communicating

# SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy


class CbfSubarrayComponentManager(
    CbfComponentManager, CspSubarrayComponentManager
):
    """A component manager for the CbfSubarray class."""

    @property
    def config_id(self: CbfSubarrayComponentManager) -> str:
        """Return the configuration ID."""
        return self._config_id

    @property
    def scan_id(self: CbfSubarrayComponentManager) -> int:
        """Return the scan ID."""
        return self._scan_id

    @property
    def subarray_id(self: CbfSubarrayComponentManager) -> int:
        """Return the subarray ID."""
        return self._subarray_id

    @property
    def frequency_band(self: CbfSubarrayComponentManager) -> int:
        """Return the frequency band."""
        return self._frequency_band

    @property
    def receptors(self: CbfSubarrayComponentManager) -> List[int]:
        """Return the receptor list."""
        return self._receptors

    @property
    def vcc_state(self: CbfSubarrayComponentManager) -> Dict[str, DevState]:
        """Return the VCC operational states."""
        return self._vcc_state

    @property
    def vcc_health_state(
        self: CbfSubarrayComponentManager,
    ) -> Dict[str, HealthState]:
        """Return the VCC health states."""
        return self._vcc_health_state

    @property
    def fsp_state(self: CbfSubarrayComponentManager) -> Dict[str, DevState]:
        """Return the FSP operational states."""
        return self._fsp_state

    @property
    def fsp_health_state(
        self: CbfSubarrayComponentManager,
    ) -> Dict[str, HealthState]:
        """Return the FSP health states."""
        return self._fsp_health_state

    @property
    def fsp_list(self: CbfSubarrayComponentManager) -> List[List[int]]:
        """Return the FSP function mode device IDs."""
        return self._fsp_list

    def __init__(
        self: CbfSubarrayComponentManager,
        subarray_id: int,
        controller: str,
        vcc: List[str],
        fsp: List[str],
        fsp_corr_sub: List[str],
        fsp_pss_sub: List[str],
        fsp_pst_sub: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        component_resourced_callback: Callable[[bool], None],
        component_configured_callback: Callable[[bool], None],
        component_scanning_callback: Callable[[bool], None],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable,
        component_obs_fault_callback: Callable,
    ) -> None:
        """
        Initialise a new instance.

        :param subarray_id: ID of subarray
        :param controller: FQDN of controller device
        :param vcc: FQDNs of subordinate VCC devices
        :param fsp: FQDNs of subordinate FSP devices
        :param fsp_corr_sub: FQDNs of subordinate FSP CORR subarray devices
        :param fsp_pss_sub: FQDNs of subordinate FSP PSS-BF subarray devices
        :param fsp_pst_sub: FQDNs of subordinate FSP PST-BF devices
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param component_resourced_callback: callback to be called when
            the component resource status changes
        :param component_configured_callback: callback to be called when
            the component configuration status changes
        :param component_scanning_callback: callback to be called when
            the component scanning status changes
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between the
            component manager and its component changes
        :param component_power_mode_changed_callback: callback to be called when
            the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault (for op state model)
        :param component_obs_fault_callback: callback to be called in event of
            component fault (for obs state model)
        """

        self._logger = logger

        self._logger.info("Entering CbfSubarrayComponentManager.__init__)")

        self._component_op_fault_callback = component_fault_callback
        self._component_obs_fault_callback = component_obs_fault_callback

        self._subarray_id = subarray_id
        self._fqdn_controller = controller
        self._fqdn_vcc = vcc
        self._fqdn_fsp = fsp
        self._fqdn_fsp_corr_subarray = fsp_corr_sub
        self._fqdn_fsp_pss_subarray = fsp_pss_sub
        self._fqdn_fsp_pst_subarray = fsp_pst_sub

        # set to determine if resources are assigned
        self._resourced = False
        # set to determine if ready to receive subscribed parameters;
        # also indicates whether component is currently configured
        self._ready = False

        self.connected = False

        # initialize attribute values
        self._receptors = []
        self._frequency_band = 0
        self._config_id = ""
        self._scan_id = 0
        self._fsp_list = [[], [], [], []]

        # store list of fsp configurations being used for each function mode
        self._corr_config = []
        self._pss_config = []
        self._pst_config = []
        # store list of fsp being used for each function mode
        self._corr_fsp_list = []
        self._pss_fsp_list = []
        self._pst_fsp_list = []
        self._latest_scan_config = ""

        # TODO
        # self._output_links_distribution = {"configID": ""}
        # self._published_output_links = False
        # self._last_received_vis_destination_address = "{}"

        self._last_received_delay_model = "{}"
        self._last_received_jones_matrix = "{}"
        self._last_received_timing_beam_weights = "{}"

        self._mutex_delay_model_config = Lock()
        self._mutex_jones_matrix_config = Lock()
        self._mutex_beam_weights_config = Lock()

        # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
        self._events_telstate = {}

        # store the subscribed state change events as vcc_ID:[event_ID, event_ID] key:value pairs
        self._events_state_change_vcc = {}

        # store the subscribed state change events as fsp_ID:[event_ID, event_ID] key:value pairs
        self._events_state_change_fsp = {}

        self._vcc_state = {}
        self._vcc_health_state = {}
        self._fsp_state = {}
        self._fsp_health_state = {}

        # for easy device-reference
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._stream_tuning = [0, 0]

        # device proxy for easy reference to CBF controller
        self._proxy_cbf_controller = None
        self._controller_max_capabilities = {}
        self._count_vcc = 0
        self._count_fsp = 0
        self._receptor_to_vcc = None

        # proxies to subordinate devices
        self._proxies_vcc = []
        self._proxies_assigned_vcc = {}
        self._proxies_fsp = []
        self._proxies_fsp_corr_subarray = []
        self._proxies_fsp_pss_subarray = []
        self._proxies_fsp_pst_subarray = []
        # group proxies to subordinate devices
        # Note: VCC connected both individual and in group
        self._group_vcc = None
        self._group_fsp = None
        self._group_fsp_corr_subarray = None
        self._group_fsp_pss_subarray = None
        self._group_fsp_pst_subarray = None

        self._component_resourced_callback = component_resourced_callback
        self._component_configured_callback = component_configured_callback
        self._component_scanning_callback = component_scanning_callback

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )

    def start_communicating(self: CbfSubarrayComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        self._logger.info(
            "Entering CbfSubarrayComponentManager.start_communicating"
        )

        if self.connected:
            self._logger.info("Already connected.")
            return

        super().start_communicating()

        try:
            if self._proxy_cbf_controller is None:
                self._proxy_cbf_controller = CbfDeviceProxy(
                    fqdn=self._fqdn_controller, logger=self._logger
                )
                self._controller_max_capabilities = dict(
                    pair.split(":")
                    for pair in self._proxy_cbf_controller.get_property(
                        "MaxCapabilities"
                    )["MaxCapabilities"]
                )
                self._count_vcc = int(self._controller_max_capabilities["VCC"])
                self._count_fsp = int(self._controller_max_capabilities["FSP"])
                self._receptor_to_vcc = dict(
                    [*map(int, pair.split(":"))]
                    for pair in self._proxy_cbf_controller.receptorToVcc
                )
                self._logger.debug(f"{self._receptor_to_vcc}")

                self._fqdn_vcc = self._fqdn_vcc[: self._count_vcc]
                self._fqdn_fsp = self._fqdn_fsp[: self._count_fsp]
                self._fqdn_fsp_corr_subarray = self._fqdn_fsp_corr_subarray[
                    : self._count_fsp
                ]
                self._fqdn_fsp_pss_subarray = self._fqdn_fsp_pss_subarray[
                    : self._count_fsp
                ]
                self._fqdn_fsp_pst_subarray = self._fqdn_fsp_pst_subarray[
                    : self._count_fsp
                ]

            if len(self._proxies_vcc) == 0:
                self._proxies_vcc = [
                    CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    for fqdn in self._fqdn_vcc
                ]

            if len(self._proxies_fsp) == 0:
                self._proxies_fsp = [
                    CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    for fqdn in self._fqdn_fsp
                ]

            if len(self._proxies_fsp_corr_subarray) == 0:
                for fqdn in self._fqdn_fsp_corr_subarray:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_fsp_corr_subarray.append(proxy)

            if len(self._proxies_fsp_pss_subarray) == 0:
                for fqdn in self._fqdn_fsp_pss_subarray:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_fsp_pss_subarray.append(proxy)

            if len(self._proxies_fsp_pst_subarray) == 0:
                for fqdn in self._fqdn_fsp_pst_subarray:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_fsp_pst_subarray.append(proxy)

            if self._group_vcc is None:
                self._group_vcc = CbfGroupProxy(
                    name="VCC", logger=self._logger
                )
            if self._group_fsp is None:
                self._group_fsp = CbfGroupProxy(
                    name="FSP", logger=self._logger
                )
            if self._group_fsp_corr_subarray is None:
                self._group_fsp_corr_subarray = CbfGroupProxy(
                    name="FSP Subarray Corr", logger=self._logger
                )
            if self._group_fsp_pss_subarray is None:
                self._group_fsp_pss_subarray = CbfGroupProxy(
                    name="FSP Subarray Pss", logger=self._logger
                )
            if self._group_fsp_pst_subarray is None:
                self._group_fsp_pst_subarray = CbfGroupProxy(
                    name="FSP Subarray Pst", logger=self._logger
                )

            for proxy in self._proxies_fsp_corr_subarray:
                proxy.adminMode = AdminMode.ONLINE
            for proxy in self._proxies_fsp_pss_subarray:
                proxy.adminMode = AdminMode.ONLINE
            for proxy in self._proxies_fsp_pst_subarray:
                proxy.adminMode = AdminMode.ONLINE

        except tango.DevFailed as dev_failed:
            self.update_component_power_mode(PowerMode.UNKNOWN)
            self.update_communication_status(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self._component_op_fault_callback(True)
            raise ConnectionError("Error in proxy connection.") from dev_failed

        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.OFF)
        self._component_op_fault_callback(False)

    def stop_communicating(self: CbfSubarrayComponentManager) -> None:
        """Stop communication with the component."""
        self._logger.info(
            "Entering CbfSubarrayComponentManager.stop_communicating"
        )
        super().stop_communicating()
        for proxy in self._proxies_fsp_corr_subarray:
            proxy.adminMode = AdminMode.OFFLINE
        for proxy in self._proxies_fsp_pss_subarray:
            proxy.adminMode = AdminMode.OFFLINE
        for proxy in self._proxies_fsp_pst_subarray:
            proxy.adminMode = AdminMode.OFFLINE
        self.connected = False
        self.update_component_power_mode(PowerMode.UNKNOWN)

    @check_communicating
    def on(self: CbfSubarrayComponentManager) -> None:
        for proxy in self._proxies_fsp_corr_subarray:
            proxy.On()
        for proxy in self._proxies_fsp_pss_subarray:
            proxy.On()
        for proxy in self._proxies_fsp_pst_subarray:
            proxy.On()

        self.update_component_power_mode(PowerMode.ON)

    @check_communicating
    def off(self: CbfSubarrayComponentManager) -> None:
        for proxy in self._proxies_fsp_corr_subarray:
            proxy.Off()
        for proxy in self._proxies_fsp_pss_subarray:
            proxy.Off()
        for proxy in self._proxies_fsp_pst_subarray:
            proxy.Off()

        self.update_component_power_mode(PowerMode.OFF)

    @check_communicating
    def standby(self: CbfSubarrayComponentManager) -> None:
        self._logger.warning(
            "Operating state Standby invalid for CbfSubarray."
        )

    @check_communicating
    def _doppler_phase_correction_event_callback(
        self: CbfSubarrayComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
    ) -> None:
        """
        Callback for dopplerPhaseCorrection change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        # TODO: investigate error in this callback (subarray logs)
        if value is not None:
            try:
                self._group_vcc.write_attribute(
                    "dopplerPhaseCorrection", value
                )
                log_msg = f"Value of {name} is {value}"
                self._logger.debug(log_msg)
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    @check_communicating
    def _delay_model_event_callback(
        self: CbfSubarrayComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
    ) -> None:
        """ "
        Callback for delayModel change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self._logger.debug("Entering _delay_model_event_callback()")

        if value is not None:
            if not self._ready:
                log_msg = "Ignoring delay model (obsState not correct)."
                self._logger.warning(log_msg)
                return
            try:
                self._logger.info("Received delay model update.")

                if value == self._last_received_delay_model:
                    log_msg = "Ignoring delay model (identical to previous)."
                    self._logger.warning(log_msg)
                    return

                self._last_received_delay_model = value
                delay_model_all = json.loads(value)

                for delay_model in delay_model_all["delayModel"]:
                    t = Thread(
                        target=self._update_delay_model,
                        args=(
                            int(delay_model["epoch"]),
                            json.dumps(delay_model["delayDetails"]),
                        ),
                    )
                    t.start()
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def _update_delay_model(
        self: CbfSubarrayComponentManager, epoch: int, model: str
    ) -> None:
        """
        Update FSP and VCC delay models.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param model: delay model
        """
        # This method is always called on a separate thread
        self._logger.debug("CbfSubarray._update_delay_model")
        log_msg = f"Delay model active at {epoch} (currently {time.time()})..."
        self._logger.info(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = f"Updating delay model at specified epoch {epoch}..."
        self._logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, model)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_delay_model_config.acquire()
        self._group_vcc.command_inout("UpdateDelayModel", data)
        self._group_fsp.command_inout("UpdateDelayModel", data)
        self._mutex_delay_model_config.release()

    @check_communicating
    def _jones_matrix_event_callback(
        self: CbfSubarrayComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
    ) -> None:
        """ "
        Callback for jonesMatrix change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self._logger.debug("CbfSubarray._jones_matrix_event_callback")

        if value is not None:
            if not self._ready:
                log_msg = "Ignoring Jones matrix (obsState not correct)."
                self._logger.warning(log_msg)
                return
            try:
                self._logger.info("Received Jones Matrix update.")

                if value == self._last_received_jones_matrix:
                    log_msg = "Ignoring Jones matrix (identical to previous)."
                    self._logger.warning(log_msg)
                    return

                self._last_received_jones_matrix = value
                jones_matrix_all = json.loads(value)

                for jones_matrix in jones_matrix_all["jonesMatrix"]:
                    t = Thread(
                        target=self._update_jones_matrix,
                        args=(
                            int(jones_matrix["epoch"]),
                            json.dumps(jones_matrix["matrixDetails"]),
                        ),
                    )
                    t.start()
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def _update_jones_matrix(
        self: CbfSubarrayComponentManager, epoch: int, matrix_details: str
    ) -> None:
        """
        Update FSP and VCC Jones matrices.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param matrix_details: Jones matrix value
        """
        # This method is always called on a separate thread
        self._logger.debug("CbfSubarray._update_jones_matrix")
        log_msg = (
            f"Jones matrix active at {epoch} (currently {time.time()})..."
        )
        self._logger.info(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = f"Updating Jones Matrix at specified epoch {epoch}..."
        self._logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, matrix_details)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_jones_matrix_config.acquire()
        self._group_vcc.command_inout("UpdateJonesMatrix", data)
        self._group_fsp.command_inout("UpdateJonesMatrix", data)
        self._mutex_jones_matrix_config.release()

    @check_communicating
    def _timing_beam_weights_event_callback(
        self: CbfSubarrayComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
    ) -> None:
        """ "
        Callback for beamWeights change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self._logger.debug("CbfSubarray._timing_beam_weights_event_callback")

        if value is not None:
            if not self._ready:
                log_msg = (
                    "Ignoring timing beam weights (obsState not correct)."
                )
                self._logger.warning(log_msg)
                return
            try:
                self._logger.info("Received timing beam weights update.")

                if value == self._last_received_timing_beam_weights:
                    log_msg = (
                        "Ignoring timing beam weights (identical to previous)."
                    )
                    self._logger.warning(log_msg)
                    return

                self._last_received_timing_beam_weights = value
                timing_beam_weights_all = json.loads(value)

                for beam_weights in timing_beam_weights_all["beamWeights"]:
                    t = Thread(
                        target=self._update_timing_beam_weights,
                        args=(
                            int(beam_weights["epoch"]),
                            json.dumps(beam_weights["beamWeightsDetails"]),
                        ),
                    )
                    t.start()
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def _update_timing_beam_weights(
        self: CbfSubarrayComponentManager, epoch: int, weights_details: str
    ) -> None:
        """
        Update FSP beam weights.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param weights_details: beam weights value
        """
        # This method is always called on a separate thread
        self._logger.debug("CbfSubarray._update_timing_beam_weights")
        log_msg = f"Timing beam weights active at {epoch} (currently {time.time()})..."
        self._logger.info(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = f"Updating timing beam weights at specified epoch {epoch}..."
        self._logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, weights_details)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_beam_weights_config.acquire()
        self._group_fsp.command_inout("UpdateTimingBeamWeights", data)
        self._mutex_beam_weights_config.release()

    def _state_change_event_callback(
        self: CbfSubarrayComponentManager,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,
    ) -> None:
        """ "
        Callback for state and healthState change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        if value is not None:
            try:
                if "healthState" in name:
                    if "vcc" in fqdn:
                        self._vcc_health_state[fqdn] = value
                    elif "fsp" in fqdn:
                        self._fsp_health_state[fqdn] = value
                    else:
                        # should NOT happen!
                        log_msg = f"Received healthState change for unknown device {name}"
                        self._logger.warning(log_msg)
                        return
                elif "State" in name:
                    if "vcc" in fqdn:
                        self._vcc_state[fqdn] = value
                    elif "fsp" in fqdn:
                        self._fsp_state[fqdn] = value
                    else:
                        # should NOT happen!
                        log_msg = (
                            f"Received state change for unknown device {name}"
                        )
                        self._logger.warning(log_msg)
                        return

                log_msg = f"New value for {fqdn} {name} is {value}"
                self._logger.info(log_msg)

            except Exception as except_occurred:
                self._logger.error(str(except_occurred))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def validate_ip(self: CbfSubarrayComponentManager, ip: str) -> bool:
        """
        Validate IP address format.

        :param ip: IP address to be evaluated

        :return: whether or not the IP address format is valid
        :rtype: bool
        """
        splitip = ip.split(".")
        if len(splitip) != 4:
            return False
        for ipparts in splitip:
            if not ipparts.isdigit():
                return False
            ipval = int(ipparts)
            if ipval < 0 or ipval > 255:
                return False
        return True

    def raise_configure_scan_fatal_error(
        self: CbfSubarrayComponentManager, msg: str
    ) -> Tuple[ResultCode, str]:
        """
        Raise fatal error in ConfigureScan execution

        :param msg: error message
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._component_obs_fault_callback(True)
        self._logger.error(msg)
        tango.Except.throw_exception(
            "Command failed",
            msg,
            "ConfigureScan execution",
            tango.ErrSeverity.ERR,
        )

    @check_communicating
    def deconfigure(
        self: CbfSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """Completely deconfigure the subarray; all initialization performed
        by by the ConfigureScan command must be 'undone' here."""
        try:
            # unsubscribe from TMC events
            for event_id in list(self._events_telstate.keys()):
                self._events_telstate[event_id].remove_event(event_id)
                del self._events_telstate[event_id]

            # unsubscribe from FSP state change events
            for fspID in list(self._events_state_change_fsp.keys()):
                proxy_fsp = self._proxies_fsp[fspID - 1]
                proxy_fsp.remove_event(
                    "State", self._events_state_change_fsp[fspID][0]
                )
                proxy_fsp.remove_event(
                    "healthState", self._events_state_change_fsp[fspID][1]
                )
                del self._events_state_change_fsp[fspID]
                del self._fsp_state[self._fqdn_fsp[fspID - 1]]
                del self._fsp_health_state[self._fqdn_fsp[fspID - 1]]

            if self._ready:
                # TODO: add 'GoToIdle' for VLBI once implemented
                for group in [
                    self._group_fsp_corr_subarray,
                    self._group_fsp_pss_subarray,
                    self._group_fsp_pst_subarray,
                ]:
                    if group.get_size() > 0:
                        group.command_inout("GoToIdle")
                        # remove channel info from FSP subarrays
                        # already done in GoToIdle
                        group.remove_all()

                if self._group_vcc.get_size() > 0:
                    self._group_vcc.command_inout("GoToIdle")

                if self._group_fsp.get_size() > 0:
                    # change FSP subarray membership
                    data = tango.DeviceData()
                    data.insert(tango.DevUShort, self._subarray_id)
                    # self._logger.info(data)
                    self._group_fsp.command_inout(
                        "RemoveSubarrayMembership", data
                    )
                    self._group_fsp.remove_all()

        except tango.DevFailed as df:
            self._component_op_fault_callback(True)
            msg = str(df.args[0].desc)
            return (ResultCode.FAILED, msg)

        # reset all private data to their initialization values:
        self._fsp_list = [[], [], [], []]
        self._pst_fsp_list = []
        self._pss_fsp_list = []
        self._corr_fsp_list = []
        self._pst_config = []
        self._pss_config = []
        self._corr_config = []

        self._scan_id = 0
        self._config_id = ""
        self._frequency_band = 0
        self._last_received_delay_model = "{}"
        self._last_received_jones_matrix = "{}"
        self._last_received_timing_beam_weights = "{}"

        self.update_component_configuration(False)

        return (ResultCode.OK, "Deconfiguration completed OK")

    @check_communicating
    def validate_input(
        self: CbfSubarrayComponentManager, argin: str
    ) -> Tuple[bool, str]:
        """
        Validate scan configuration.

        :param argin: The configuration as JSON formatted string.

        :return: A tuple containing a boolean indicating if the configuration
            is valid and a string message. The message is for information
            purpose only.
        :rtype: (bool, str)
        """
        # try to deserialize input string to a JSON object
        try:
            full_configuration = json.loads(argin)
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            return (False, msg)

        # Validate dopplerPhaseCorrSubscriptionPoint.
        if "doppler_phase_corr_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration[
                        "doppler_phase_corr_subscription_point"
                    ],
                    logger=self._logger,
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['doppler_phase_corr_subscription_point']}"
                    " not found or not set up correctly for "
                    "'dopplerPhaseCorrSubscriptionPoint'. Aborting configuration."
                )
                return (False, msg)

        # Validate delayModelSubscriptionPoint.
        if "delay_model_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["delay_model_subscription_point"],
                    logger=self._logger,
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['delay_model_subscription_point']}"
                    " not found or not set up correctly for "
                    "'delayModelSubscriptionPoint'. Aborting configuration."
                )
                return (False, msg)

        # Validate jonesMatrixSubscriptionPoint.
        if "jones_matrix_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["jones_matrix_subscription_point"],
                    logger=self._logger,
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['jones_matrix_subscription_point']}"
                    " not found or not set up correctly for "
                    "'jonesMatrixSubscriptionPoint'. Aborting configuration."
                )
                return (False, msg)

        # Validate beamWeightsSubscriptionPoint.
        if "timing_beam_weights_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration[
                        "timing_beam_weights_subscription_point"
                    ],
                    logger=self._logger,
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['timing_beam_weights_subscription_point']}"
                    " not found or not set up correctly for "
                    "'beamWeightsSubscriptionPoint'. Aborting configuration."
                )
                return (False, msg)

        for receptor_id, proxy in self._proxies_assigned_vcc.items():
            if proxy.State() != tango.DevState.ON:
                msg = f"VCC {self._proxies_vcc.index(proxy) + 1} is not ON. Aborting configuration."
                return (False, msg)

        # Validate searchWindow.
        if "search_window" in configuration:
            # check if searchWindow is an array of maximum length 2
            if len(configuration["search_window"]) > 2:
                msg = (
                    "'searchWindow' must be an array of maximum length 2. "
                    "Aborting configuration."
                )
                return (False, msg)
            for sw in configuration["search_window"]:
                if sw["tdc_enable"]:
                    for receptor in sw["tdc_destination_address"]:
                        receptor_id = receptor["receptor_id"]
                        if receptor_id not in self._receptors:
                            msg = (
                                f"'searchWindow' receptor ID {receptor_id} "
                                + "not assigned to subarray. Aborting configuration."
                            )
                            return (False, msg)
        else:
            pass

        # Validate fsp.
        for fsp in configuration["fsp"]:
            try:
                # Validate fspID.
                if int(fsp["fsp_id"]) in list(range(1, self._count_fsp + 1)):
                    fspID = int(fsp["fsp_id"])
                    proxy_fsp = self._proxies_fsp[fspID - 1]
                    if fsp["function_mode"] == "CORR":
                        proxy_fsp_subarray = self._proxies_fsp_corr_subarray[
                            fspID - 1
                        ]
                    elif fsp["function_mode"] == "PSS-BF":
                        proxy_fsp_subarray = self._proxies_fsp_pss_subarray[
                            fspID - 1
                        ]
                    elif fsp["function_mode"] == "PST-BF":
                        proxy_fsp_subarray = self._proxies_fsp_pst_subarray[
                            fspID - 1
                        ]
                else:
                    msg = (
                        f"'fspID' must be an integer in the range [1, {self._count_fsp}]."
                        " Aborting configuration."
                    )
                    return (False, msg)

                if proxy_fsp.State() != tango.DevState.ON:
                    msg = f"FSP {fspID} is not ON. Aborting configuration."
                    return (False, msg)

                if proxy_fsp_subarray.State() != tango.DevState.ON:
                    msg = (
                        f"Subarray {self._subarray_id} of FSP {fspID} is not ON."
                        " Aborting configuration."
                    )
                    return (False, msg)

                # Validate functionMode.
                function_modes = ["CORR", "PSS-BF", "PST-BF", "VLBI"]
                if fsp["function_mode"] in function_modes:
                    if (
                        function_modes.index(fsp["function_mode"]) + 1
                        == proxy_fsp.functionMode
                        or proxy_fsp.functionMode == 0
                    ):
                        pass
                    else:
                        # TODO need to add this check for VLBI once implemented
                        for (
                            fsp_corr_subarray_proxy
                        ) in self._proxies_fsp_corr_subarray:
                            if (
                                fsp_corr_subarray_proxy.obsState
                                != ObsState.IDLE
                            ):
                                msg = (
                                    f"A different subarray is using FSP {fsp['fsp_id']} "
                                    "for a different function mode. Aborting configuration."
                                )
                                return (False, msg)
                        for (
                            fsp_pss_subarray_proxy
                        ) in self._proxies_fsp_pss_subarray:
                            if (
                                fsp_pss_subarray_proxy.obsState
                                != ObsState.IDLE
                            ):
                                msg = (
                                    f"A different subarray is using FSP {fsp['fsp_id']} "
                                    "for a different function mode. Aborting configuration."
                                )
                                return (False, msg)
                        for (
                            fsp_pst_subarray_proxy
                        ) in self._proxies_fsp_pst_subarray:
                            if (
                                fsp_pst_subarray_proxy.obsState
                                != ObsState.IDLE
                            ):
                                msg = (
                                    f"A different subarray is using FSP {fsp['fsp_id']} "
                                    "for a different function mode. Aborting configuration."
                                )
                                return (False, msg)
                else:
                    msg = (
                        f"'functionMode' must be one of {function_modes} "
                        f"(received {fsp['function_mode']}). "
                    )
                    return (False, msg)

                # TODO - why add these keys to the fsp dict - not good practice!
                # TODO - create a new dict from a deep copy of the fsp dict.
                fsp["frequency_band"] = common_configuration["frequency_band"]
                fsp["frequency_band_offset_stream_1"] = configuration[
                    "frequency_band_offset_stream_1"
                ]
                fsp["frequency_band_offset_stream_2"] = configuration[
                    "frequency_band_offset_stream_2"
                ]
                if fsp["frequency_band"] in ["5a", "5b"]:
                    fsp["band_5_tuning"] = common_configuration[
                        "band_5_tuning"
                    ]

                # CORR #

                if fsp["function_mode"] == "CORR":

                    if "receptor_ids" in fsp:
                        for this_rec in fsp["receptor_ids"]:
                            if this_rec not in self._receptors:
                                msg = (
                                    f"Receptor {this_rec} does not belong to "
                                    f"subarray {self._subarray_id}."
                                )
                                self._logger.error(msg)
                                return (False, msg)
                    else:
                        msg = "'receptors' not specified for Fsp CORR config"
                        # TODO - In this case by the ICD, all subarray allocated resources should be used.
                        # TODO add support for more than one receptor per fsp
                        # fsp["receptor_ids"] = self._receptors
                        fsp["receptor_ids"] = self._receptors[0]

                    frequencyBand = freq_band_dict()[fsp["frequency_band"]]
                    # Validate frequencySliceID.
                    # TODO: move these to consts
                    # See for ex. Fig 8-2 in the Mid.CBF DDD
                    num_frequency_slices = [4, 5, 7, 12, 26, 26]
                    if int(fsp["frequency_slice_id"]) in list(
                        range(1, num_frequency_slices[frequencyBand] + 1)
                    ):
                        pass
                    else:
                        msg = (
                            "'frequencySliceID' must be an integer in the range "
                            f"[1, {num_frequency_slices[frequencyBand]}] "
                            f"for a 'frequencyBand' of {fsp['frequency_band']}."
                        )
                        self._logger.error(msg)
                        return (False, msg)

                    # Validate zoom_factor.
                    if int(fsp["zoom_factor"]) in list(range(0, 7)):
                        pass
                    else:
                        msg = "'zoom_factor' must be an integer in the range [0, 6]."
                        # this is a fatal error
                        self._logger.error(msg)
                        return (False, msg)

                    # Validate zoomWindowTuning.
                    if (
                        int(fsp["zoom_factor"]) > 0
                    ):  # zoomWindowTuning is required
                        if "zoom_window_tuning" in fsp:

                            if fsp["frequency_band"] not in [
                                "5a",
                                "5b",
                            ]:  # frequency band is not band 5
                                frequencyBand = [
                                    "1",
                                    "2",
                                    "3",
                                    "4",
                                    "5a",
                                    "5b",
                                ].index(fsp["frequency_band"])
                                frequency_band_start = [
                                    *map(
                                        lambda j: j[0] * 10**9,
                                        [
                                            const.FREQUENCY_BAND_1_RANGE,
                                            const.FREQUENCY_BAND_2_RANGE,
                                            const.FREQUENCY_BAND_3_RANGE,
                                            const.FREQUENCY_BAND_4_RANGE,
                                        ],
                                    )
                                ][frequencyBand] + fsp[
                                    "frequency_band_offset_stream_1"
                                ]

                                frequency_slice_range = (
                                    frequency_band_start
                                    + (fsp["frequency_slice_id"] - 1)
                                    * const.FREQUENCY_SLICE_BW
                                    * 10**6,
                                    frequency_band_start
                                    + fsp["frequency_slice_id"]
                                    * const.FREQUENCY_SLICE_BW
                                    * 10**6,
                                )

                                if (
                                    frequency_slice_range[0]
                                    <= int(fsp["zoom_window_tuning"]) * 10**3
                                    <= frequency_slice_range[1]
                                ):
                                    pass
                                else:
                                    msg = "'zoomWindowTuning' must be within observed frequency slice."
                                    self._logger.error(msg)
                                    return (False, msg)
                            # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                            else:
                                if common_configuration["band_5_tuning"] == [
                                    0,
                                    0,
                                ]:  # band5Tuning not specified
                                    pass
                                else:

                                    # TODO: these validations of BW range are done many times
                                    # in many places - use a commom function; also may be possible
                                    # to do them only once (ex. for band5Tuning)

                                    frequency_slice_range_1 = (
                                        fsp["band_5_tuning"][0] * 10**9
                                        + fsp["frequency_band_offset_stream_1"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + (fsp["frequency_slice_id"] - 1)
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                        fsp["band_5_tuning"][0] * 10**9
                                        + fsp["frequency_band_offset_stream_1"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + fsp["frequency_slice_id"]
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                    )

                                    frequency_slice_range_2 = (
                                        fsp["band_5_tuning"][1] * 10**9
                                        + fsp["frequency_band_offset_stream_2"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + (fsp["frequency_slice_id"] - 1)
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                        fsp["band_5_tuning"][1] * 10**9
                                        + fsp["frequency_band_offset_stream_2"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + fsp["frequency_slice_id"]
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                    )

                                    if (
                                        frequency_slice_range_1[0]
                                        <= int(fsp["zoom_window_tuning"])
                                        * 10**3
                                        <= frequency_slice_range_1[1]
                                    ) or (
                                        frequency_slice_range_2[0]
                                        <= int(fsp["zoom_window_tuning"])
                                        * 10**3
                                        <= frequency_slice_range_2[1]
                                    ):
                                        pass
                                    else:
                                        msg = "'zoomWindowTuning' must be within observed frequency slice."
                                        self._logger.error(msg)
                                        return (False, msg)
                        else:
                            msg = "FSP specified, but 'zoomWindowTuning' not given."
                            self._logger.error(msg)
                            return (False, msg)

                    # Validate integrationTime.
                    if int(fsp["integration_factor"]) in list(
                        range(
                            const.MIN_INT_TIME,
                            10 * const.MIN_INT_TIME + 1,
                            const.MIN_INT_TIME,
                        )
                    ):
                        pass
                    else:
                        msg = (
                            "'integrationTime' must be an integer in the range"
                            f" [1, 10] multiplied by {const.MIN_INT_TIME}."
                        )
                        self._logger.error(msg)
                        return (False, msg)

                    # Validate fspChannelOffset
                    try:
                        if int(fsp["channel_offset"]) >= 0:
                            pass
                        # TODO has to be a multiple of 14880
                        else:
                            msg = "fspChannelOffset must be greater than or equal to zero"
                            self._logger.error(msg)
                            return (False, msg)
                    except (TypeError, ValueError):
                        msg = "fspChannelOffset must be an integer"
                        self._logger.error(msg)
                        return (False, msg)

                    # validate outputlink
                    # check the format
                    try:
                        for element in fsp["output_link_map"]:
                            (int(element[0]), int(element[1]))
                    except (TypeError, ValueError, IndexError):
                        msg = "'outputLinkMap' format not correct."
                        self._logger.error(msg)
                        return (False, msg)

                    # Validate channelAveragingMap.
                    if "channel_averaging_map" in fsp:
                        try:
                            # validate dimensions
                            for i in range(
                                0, len(fsp["channel_averaging_map"])
                            ):
                                assert (
                                    len(fsp["channel_averaging_map"][i]) == 2
                                )

                            # validate averaging factor
                            for i in range(
                                0, len(fsp["channel_averaging_map"])
                            ):
                                # validate channel ID of first channel in group
                                if (
                                    int(fsp["channel_averaging_map"][i][0])
                                    == i
                                    * const.NUM_FINE_CHANNELS
                                    / const.NUM_CHANNEL_GROUPS
                                ):
                                    pass  # the default value is already correct
                                else:
                                    msg = (
                                        f"'channelAveragingMap'[{i}][0] is not the channel ID of the "
                                        f"first channel in a group (received {fsp['channel_averaging_map'][i][0]})."
                                    )
                                    self._logger.error(msg)
                                    return (False, msg)

                                # validate averaging factor
                                if int(fsp["channel_averaging_map"][i][1]) in [
                                    0,
                                    1,
                                    2,
                                    3,
                                    4,
                                    6,
                                    8,
                                ]:
                                    pass
                                else:
                                    msg = (
                                        f"'channelAveragingMap'[{i}][1] must be one of "
                                        f"[0, 1, 2, 3, 4, 6, 8] (received {fsp['channel_averaging_map'][i][1]})."
                                    )
                                    self._logger.error(msg)
                                    return (False, msg)
                        except (
                            TypeError,
                            AssertionError,
                        ):  # dimensions not correct
                            msg = (
                                "channel Averaging Map dimensions not correct"
                            )
                            self._logger.error(msg)
                            return (False, msg)

                    # TODO: validate destination addresses: outputHost, outputMac, outputPort

                # PSS-BF #

                # TODO currently only CORR function mode is supported outside of Mid.CBF MCS
                if fsp["function_mode"] == "PSS-BF":
                    if int(fsp["search_window_id"]) in [1, 2]:
                        pass
                    else:  # searchWindowID not in valid range
                        msg = (
                            "'searchWindowID' must be one of [1, 2] "
                            f"(received {fsp['search_window_id']})."
                        )
                        return (False, msg)
                    if len(fsp["search_beam"]) <= 192:
                        for searchBeam in fsp["search_beam"]:
                            if 1 > int(searchBeam["search_beam_id"]) > 1500:
                                # searchbeamID not in valid range
                                msg = (
                                    "'searchBeamID' must be within range 1-1500 "
                                    f"(received {searchBeam['search_beam_id']})."
                                )
                                return (False, msg)

                            for (
                                fsp_pss_subarray_proxy
                            ) in self._proxies_fsp_pss_subarray:
                                searchBeamID = (
                                    fsp_pss_subarray_proxy.searchBeamID
                                )
                                if searchBeamID is None:
                                    pass
                                else:
                                    for search_beam_ID in searchBeamID:
                                        if (
                                            int(searchBeam["search_beam_id"])
                                            != search_beam_ID
                                        ):
                                            pass
                                        elif (
                                            fsp_pss_subarray_proxy.obsState
                                            == ObsState.IDLE
                                        ):
                                            pass
                                        else:
                                            msg = (
                                                f"'searchBeamID' {searchBeam['search_beam_id']} "
                                                "is already being used on another fspSubarray."
                                            )
                                            return (False, msg)

                                # Validate receptors.
                                # This is always given, due to implementation details.
                                # TODO assume always given, as there is currently only support for 1 receptor/beam
                            if "receptor_ids" not in searchBeam:
                                searchBeam["receptor_ids"] = self._receptors

                            # Sanity check:
                            for this_rec in searchBeam["receptor_ids"]:
                                if this_rec not in self._receptors:
                                    msg = (
                                        f"Receptor {this_rec} does not belong to "
                                        f"subarray {self._subarray_id}."
                                    )
                                    self._logger.error(msg)
                                    return (False, msg)

                            if (
                                searchBeam["enable_output"] is False
                                or searchBeam["enable_output"] is True
                            ):
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                return (False, msg)

                            if isinstance(
                                searchBeam["averaging_interval"], int
                            ):
                                pass
                            else:
                                msg = "'averagingInterval' is not a valid integer"
                                return (False, msg)

                            if self.validate_ip(
                                searchBeam["search_beam_destination_address"]
                            ):
                                pass
                            else:
                                msg = "'searchBeamDestinationAddress' is not a valid IP address"
                                return (False, msg)

                    else:
                        msg = "More than 192 SearchBeams defined in PSS-BF config"
                        return (False, msg)

                # PST-BF #

                # TODO currently only CORR function mode is supported outside of Mid.CBF MCS
                if fsp["function_mode"] == "PST-BF":
                    if len(fsp["timing_beam"]) <= 16:
                        for timingBeam in fsp["timing_beam"]:
                            if 1 <= int(timingBeam["timing_beam_id"]) <= 16:
                                pass
                            else:  # timingBeamID not in valid range
                                msg = (
                                    "'timingBeamID' must be within range 1-16 "
                                    f"(received {timingBeam['timing_beam_id']})."
                                )
                                return (False, msg)
                            for (
                                fsp_pst_subarray_proxy
                            ) in self._proxies_fsp_pst_subarray:
                                timingBeamID = (
                                    fsp_pst_subarray_proxy.timingBeamID
                                )
                                if timingBeamID is None:
                                    pass
                                else:
                                    for timing_beam_ID in timingBeamID:
                                        if (
                                            int(timingBeam["timing_beam_id"])
                                            != timing_beam_ID
                                        ):
                                            pass
                                        elif (
                                            fsp_pst_subarray_proxy.obsState
                                            == ObsState.IDLE
                                        ):
                                            pass
                                        else:
                                            msg = (
                                                f"'timingBeamID' {timingBeam['timing_beam_id']} "
                                                "is already being used on another fspSubarray."
                                            )
                                            return (False, msg)

                            # Validate receptors.
                            # This is always given, due to implementation details.
                            if "receptor_ids" in timingBeam:
                                for this_rec in timingBeam["receptor_ids"]:
                                    if this_rec not in self._receptors:
                                        msg = (
                                            f"Receptor {this_rec} does not belong to "
                                            f"subarray {self._subarray_id}."
                                        )
                                        self._logger.error(msg)
                                        return (False, msg)
                            else:
                                timingBeam["receptor_ids"] = self._receptors

                            if (
                                timingBeam["enable_output"] is False
                                or timingBeam["enable_output"] is True
                            ):
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                return (False, msg)

                            if self.validate_ip(
                                timingBeam["timing_beam_destination_address"]
                            ):
                                pass
                            else:
                                msg = "'timingBeamDestinationAddress' is not a valid IP address"
                                return (False, msg)

                    else:
                        msg = (
                            "More than 16 TimingBeams defined in PST-BF config"
                        )
                        return (False, msg)

            except tango.DevFailed:  # exception in ConfigureScan
                msg = (
                    "An exception occurred while configuring FSPs:"
                    f"\n{sys.exc_info()[1].args[0].desc}\n"
                    "Aborting configuration"
                )
                return (False, msg)

        # At this point, everything has been validated.
        return (True, "Scan configuration is valid.")

    @check_communicating
    def configure_scan(
        self: CbfSubarrayComponentManager, argin: str
    ) -> Tuple[ResultCode, str]:
        """
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        full_configuration = json.loads(argin)
        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["cbf"])

        # Configure configID.
        self._config_id = str(common_configuration["config_id"])
        self._logger.debug(f"config_id: {self._config_id}")

        # Configure frequencyBand.
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        self._frequency_band = frequency_bands.index(
            common_configuration["frequency_band"]
        )
        self._logger.debug(f"frequency_band: {self._frequency_band}")

        data = tango.DeviceData()
        data.insert(tango.DevString, common_configuration["frequency_band"])
        self._group_vcc.command_inout("ConfigureBand", data)

        # Configure band5Tuning, if frequencyBand is 5a or 5b.
        if self._frequency_band in [4, 5]:
            stream_tuning = [
                *map(float, common_configuration["band_5_tuning"])
            ]
            self._stream_tuning = stream_tuning

        # Configure frequencyBandOffsetStream1.
        if "frequency_band_offset_stream_1" in configuration:
            self._frequency_band_offset_stream_1 = int(
                configuration["frequency_band_offset_stream_1"]
            )
        else:
            self._frequency_band_offset_stream_1 = 0
            log_msg = (
                "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            )
            self._logger.warning(log_msg)

        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "frequency_band_offset_stream_2" in configuration:
            self._frequency_band_offset_stream_2 = int(
                configuration["frequency_band_offset_stream_2"]
            )
        else:
            self._frequency_band_offset_stream_2 = 0
            log_msg = (
                "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
            )
            self._logger.warn(log_msg)

        config_dict = {
            "config_id": self._config_id,
            "frequency_band": common_configuration["frequency_band"],
            "band_5_tuning": self._stream_tuning,
            "frequency_band_offset_stream_1": self._frequency_band_offset_stream_1,
            "frequency_band_offset_stream_2": self._frequency_band_offset_stream_2,
            "rfi_flagging_mask": configuration["rfi_flagging_mask"],
        }

        # Add subset of FSP configuration to the VCC configure scan argument
        # TODO determine necessary parameters to send to VCC for each function mode
        # TODO VLBI
        reduced_fsp = []
        for fsp in configuration["fsp"]:
            function_mode = fsp["function_mode"]
            fsp_cfg = {"fsp_id": fsp["fsp_id"], "function_mode": function_mode}
            if function_mode == "CORR":
                fsp_cfg["frequency_slice_id"] = fsp["frequency_slice_id"]
            elif function_mode == "PSS-BF":
                fsp_cfg["search_window_id"] = fsp["search_window_id"]
            reduced_fsp.append(fsp_cfg)
        config_dict["fsp"] = reduced_fsp

        json_str = json.dumps(config_dict)
        data = tango.DeviceData()
        data.insert(tango.DevString, json_str)
        self._group_vcc.command_inout("ConfigureScan", data)

        # Configure dopplerPhaseCorrSubscriptionPoint.
        if "doppler_phase_corr_subscription_point" in configuration:
            attribute_proxy = CbfAttributeProxy(
                fqdn=configuration["doppler_phase_corr_subscription_point"],
                logger=self._logger,
            )
            event_id = attribute_proxy.add_change_event_callback(
                self._doppler_phase_correction_event_callback
            )
            self._events_telstate[event_id] = attribute_proxy

        # Configure delayModelSubscriptionPoint.
        if "delay_model_subscription_point" in configuration:
            self._last_received_delay_model = "{}"
            attribute_proxy = CbfAttributeProxy(
                fqdn=configuration["delay_model_subscription_point"],
                logger=self._logger,
            )
            event_id = attribute_proxy.add_change_event_callback(
                self._delay_model_event_callback
            )
            self._events_telstate[event_id] = attribute_proxy

        # Configure jonesMatrixSubscriptionPoint
        if "jones_matrix_subscription_point" in configuration:
            self._last_received_jones_matrix = "{}"
            attribute_proxy = CbfAttributeProxy(
                fqdn=configuration["jones_matrix_subscription_point"],
                logger=self._logger,
            )
            event_id = attribute_proxy.add_change_event_callback(
                self._jones_matrix_event_callback
            )
            self._events_telstate[event_id] = attribute_proxy

        # Configure beamWeightsSubscriptionPoint
        if "timing_beam_weights_subscription_point" in configuration:
            self._last_received_timing_beam_weights = "{}"
            attribute_proxy = CbfAttributeProxy(
                fqdn=configuration["timing_beam_weights_subscription_point"],
                logger=self._logger,
            )
            event_id = attribute_proxy.add_change_event_callback(
                self._timing_beam_weights_event_callback
            )
            self._events_telstate[event_id] = attribute_proxy

        # Configure searchWindow.
        if "search_window" in configuration:
            for search_window in configuration["search_window"]:
                search_window["frequency_band"] = common_configuration[
                    "frequency_band"
                ]
                search_window[
                    "frequency_band_offset_stream_1"
                ] = self._frequency_band_offset_stream_1
                search_window[
                    "frequency_band_offset_stream_2"
                ] = self._frequency_band_offset_stream_2
                if search_window["frequency_band"] in ["5a", "5b"]:
                    search_window["band_5_tuning"] = common_configuration[
                        "band_5_tuning"
                    ]
                # pass on configuration to VCC
                data = tango.DeviceData()
                data.insert(tango.DevString, json.dumps(search_window))
                self._group_vcc.command_inout("ConfigureSearchWindow", data)
        else:
            log_msg = "'searchWindow' not given."
            self._logger.warning(log_msg)

        # TODO: the entire vcc configuration should move to Vcc
        # for now, run ConfigScan only wih the following data, so that
        # the obsState are properly (implicitly) updated by the command
        # (And not manually by SetObservingState as before)

        # FSP #
        # Configure FSP.
        for fsp in configuration["fsp"]:
            # Configure fspID.
            fspID = int(fsp["fsp_id"])
            proxy_fsp = self._proxies_fsp[fspID - 1]

            self._group_fsp.add(self._fqdn_fsp[fspID - 1])
            self._group_fsp_corr_subarray.add(
                self._fqdn_fsp_corr_subarray[fspID - 1]
            )
            self._group_fsp_pss_subarray.add(
                self._fqdn_fsp_pss_subarray[fspID - 1]
            )
            self._group_fsp_pst_subarray.add(
                self._fqdn_fsp_pst_subarray[fspID - 1]
            )

            # change FSP subarray membership
            proxy_fsp.AddSubarrayMembership(self._subarray_id)

            # Configure functionMode.
            proxy_fsp.SetFunctionMode(fsp["function_mode"])

            # subscribe to FSP state and healthState changes
            (
                event_id_state,
                event_id_health_state,
            ) = proxy_fsp.add_change_event_callback(
                "State", self._state_change_event_callback
            ), proxy_fsp.add_change_event_callback(
                "healthState", self._state_change_event_callback
            )
            self._events_state_change_fsp[int(fsp["fsp_id"])] = [
                event_id_state,
                event_id_health_state,
            ]

            # Add configID to fsp. It is not included in the "FSP" portion in configScan JSON
            fsp["config_id"] = common_configuration["config_id"]
            fsp["frequency_band"] = common_configuration["frequency_band"]
            fsp["band_5_tuning"] = common_configuration["band_5_tuning"]
            fsp[
                "frequency_band_offset_stream_1"
            ] = self._frequency_band_offset_stream_1
            fsp[
                "frequency_band_offset_stream_2"
            ] = self._frequency_band_offset_stream_2

            if fsp["function_mode"] == "CORR":
                if "receptor_ids" not in fsp:
                    # TODO In this case by the ICD, all subarray allocated resources should be used.
                    fsp["receptor_ids"] = [self._receptors[0]]
                self._corr_config.append(fsp)
                self._corr_fsp_list.append(fsp["fsp_id"])

            # TODO currently only CORR function mode is supported outside of Mid.CBF MCS
            elif fsp["function_mode"] == "PSS-BF":
                for searchBeam in fsp["search_beam"]:
                    if "receptor_ids" not in searchBeam:
                        # In this case by the ICD, all subarray allocated resources should be used.
                        searchBeam["receptor_ids"] = self._receptors
                self._pss_config.append(fsp)
                self._pss_fsp_list.append(fsp["fsp_id"])
            elif fsp["function_mode"] == "PST-BF":
                for timingBeam in fsp["timing_beam"]:
                    if "receptor_ids" not in timingBeam:
                        # In this case by the ICD, all subarray allocated resources should be used.
                        timingBeam["receptor_ids"] = self._receptors
                self._pst_config.append(fsp)
                self._pst_fsp_list.append(fsp["fsp_id"])

        # Call ConfigureScan for all FSP Subarray devices (CORR/PSS/PST)

        # NOTE:_corr_config is a list of fsp config JSON objects, each
        #      augmented by a number of vcc-fsp common parameters
        #      created by the function validate_input()
        if len(self._corr_config) != 0:
            # self._proxy_corr_config.ConfigureFSP(json.dumps(self._corr_config))
            # Michelle - WIP - TODO - this is to replace the call to
            #  _proxy_corr_config.ConfigureFSP()
            for this_fsp in self._corr_config:
                try:
                    this_proxy = self._proxies_fsp_corr_subarray[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.ConfigureScan(json.dumps(this_fsp))
                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring "
                        "FspCorrSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        # NOTE: _pss_config is costructed similarly to _corr_config
        if len(self._pss_config) != 0:
            for this_fsp in self._pss_config:
                try:
                    this_proxy = self._proxies_fsp_pss_subarray[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.ConfigureScan(json.dumps(this_fsp))
                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring  "
                        "FspPssSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        # NOTE: _pst_config is costructed similarly to _corr_config
        if len(self._pst_config) != 0:
            for this_fsp in self._pst_config:
                try:
                    this_proxy = self._proxies_fsp_pst_subarray[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.ConfigureScan(json.dumps(this_fsp))
                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring  "
                        "FspPstSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        # TODO add VLBI to this once they are implemented
        # potentially remove
        self._fsp_list[0].append(self._corr_fsp_list)
        self._fsp_list[1].append(self._pss_fsp_list)
        self._fsp_list[2].append(self._pst_fsp_list)

        # save configuration into latestScanConfig
        self._latest_scan_config = str(configuration)

        self.update_component_configuration(True)

        return (ResultCode.OK, "ConfigureScan command completed OK")

    @check_communicating
    def remove_receptors(
        self: CbfSubarrayComponentManager, argin: List[int]
    ) -> Tuple[ResultCode, str]:
        """
        Remove receptor from subarray.

        :param argin: The receptors to be released
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(f"current receptors: {*self._receptors,}")
        for receptor_id in argin:
            self._logger.debug(f"Attempting to remove receptor {receptor_id}")
            # check for invalid receptorID
            if not 0 < receptor_id <= const.MAX_VCC:
                msg = f"Invalid receptor ID {receptor_id}. Skipping."
                self._logger.warning(msg)
            else:
                if receptor_id in self._receptors:
                    vccID = self._receptor_to_vcc[receptor_id]
                    vccFQDN = self._fqdn_vcc[vccID - 1]
                    vccProxy = self._proxies_vcc[vccID - 1]

                    self._receptors.remove(receptor_id)
                    self._group_vcc.remove(vccFQDN)
                    del self._proxies_assigned_vcc[receptor_id]

                    try:
                        # reset subarrayMembership Vcc attribute:
                        vccProxy.subarrayMembership = 0
                        self._logger.debug(
                            f"VCC {vccID} subarray_id: "
                            + f"{vccProxy.subarrayMembership}"
                        )

                        # unsubscribe from events
                        vccProxy.remove_event(
                            "State", self._events_state_change_vcc[vccID][0]
                        )
                        vccProxy.remove_event(
                            "healthState",
                            self._events_state_change_vcc[vccID][1],
                        )

                        del self._events_state_change_vcc[vccID]
                        del self._vcc_state[vccFQDN]
                        del self._vcc_health_state[vccFQDN]

                    except tango.DevFailed as df:
                        msg = str(df.args[0].desc)
                        self._component_obs_fault_callback(True)
                        return (ResultCode.FAILED, msg)

                else:
                    msg = f"Receptor {receptor_id} not found. Skipping."
                    self._logger.warning(msg)

        if len(self._receptors) == 0:
            self.update_component_resources(False)

        self._logger.debug(f"receptors remaining: {*self._receptors,}")

        return (ResultCode.OK, "RemoveReceptors completed OK")

    @check_communicating
    def remove_all_receptors(
        self: CbfSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Remove all receptors from subarray.

        :param receptor_id: The receptor to be released
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(f"current receptors: {*self._receptors,}")
        if len(self._receptors) > 0:
            for receptor_id in self._receptors[:]:
                self._logger.debug(
                    f"Attempting to remove receptor {receptor_id}"
                )
                vccID = self._receptor_to_vcc[receptor_id]
                vccFQDN = self._fqdn_vcc[vccID - 1]
                vccProxy = self._proxies_vcc[vccID - 1]

                self._receptors.remove(receptor_id)
                self._group_vcc.remove(vccFQDN)
                del self._proxies_assigned_vcc[receptor_id]

                try:
                    # reset subarrayMembership Vcc attribute:
                    vccProxy.subarrayMembership = 0
                    self._logger.debug(
                        f"VCC {vccID} subarray_id: "
                        + f"{vccProxy.subarrayMembership}"
                    )

                    # unsubscribe from events
                    vccProxy.remove_event(
                        "State", self._events_state_change_vcc[vccID][0]
                    )
                    vccProxy.remove_event(
                        "healthState", self._events_state_change_vcc[vccID][1]
                    )

                    del self._events_state_change_vcc[vccID]
                    del self._vcc_state[vccFQDN]
                    del self._vcc_health_state[vccFQDN]
                except tango.DevFailed as df:
                    msg = str(df.args[0].desc)
                    self._component_obs_fault_callback(True)
                    return (ResultCode.FAILED, msg)

            self._logger.debug(f"receptors remaining: {*self._receptors,}")
            self.update_component_resources(False)

            return (ResultCode.OK, "RemoveAllReceptors completed OK")

        else:
            return (
                ResultCode.FAILED,
                "RemoveAllReceptors failed; no receptors currently assigned",
            )

    @check_communicating
    def add_receptors(
        self: CbfSubarrayComponentManager, argin: List[int]
    ) -> Tuple[ResultCode, str]:
        """
        Add receptors to subarray.

        :param argin: The receptors to be assigned
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(f"current receptors: {*self._receptors,}")
        for receptor_id in argin:
            self._logger.debug(f"Attempting to add receptor {receptor_id}")
            # check for invalid receptorID
            if not 0 < receptor_id <= const.MAX_VCC:
                msg = f"Invalid receptor ID {receptor_id}. Skipping."
                self._logger.warning(msg)
            else:
                vccID = self._receptor_to_vcc[receptor_id]
                vccProxy = self._proxies_vcc[vccID - 1]

                self._logger.debug(
                    f"receptor_id = {receptor_id}, vccProxy.receptor_id = "
                    + f"{vccProxy.receptorID}"
                )

                vccSubarrayID = vccProxy.subarrayMembership
                self._logger.debug(f"VCC {vccID} subarray_id: {vccSubarrayID}")

                # only add receptor if it does not already belong to a
                # different subarray
                if vccSubarrayID not in [0, self._subarray_id]:
                    msg = (
                        f"Receptor {receptor_id} already in use by "
                        + f"subarray {vccSubarrayID}. Skipping."
                    )
                    self._logger.warning(msg)
                else:
                    if receptor_id not in self._receptors:
                        # update resourced state once first receptor is added
                        if len(self._receptors) == 0:
                            self.update_component_resources(True)

                        self._receptors.append(int(receptor_id))
                        self._group_vcc.add(self._fqdn_vcc[vccID - 1])
                        self._proxies_assigned_vcc[receptor_id] = vccProxy

                        try:
                            # change subarray membership of vcc
                            vccProxy.subarrayMembership = self._subarray_id
                            self._logger.debug(
                                f"VCC {vccID} subarray_id: "
                                + f"{vccProxy.subarrayMembership}"
                            )

                            # subscribe to VCC state and healthState changes
                            event_id_state = (
                                vccProxy.add_change_event_callback(
                                    "State", self._state_change_event_callback
                                )
                            )
                            self._logger.debug(
                                f"State event ID: {event_id_state}"
                            )

                            event_id_health_state = (
                                vccProxy.add_change_event_callback(
                                    "healthState",
                                    self._state_change_event_callback,
                                )
                            )
                            self._logger.debug(
                                f"Health state event ID: {event_id_health_state}"
                            )

                            self._events_state_change_vcc[vccID] = [
                                event_id_state,
                                event_id_health_state,
                            ]

                        except tango.DevFailed as df:
                            msg = str(df.args[0].desc)
                            self._component_obs_fault_callback(True)
                            return (ResultCode.FAILED, msg)

                    else:
                        msg = (
                            f"Receptor {receptor_id} already assigned to "
                            + "subarray. Skipping."
                        )
                        self._logger.warning(msg)

        self._logger.debug(f"receptors after adding: {*self._receptors,}")

        return (ResultCode.OK, "AddReceptors completed OK")

    @check_communicating
    def scan(
        self: CbfSubarrayComponentManager, argin: Dict[Any]
    ) -> Tuple[ResultCode, str]:
        """
        Start subarray Scan operation.

        :param argin: The scan ID as JSON formatted string.
        :type argin: str
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        scan_id = argin["scan_id"]
        try:
            data = tango.DeviceData()
            data.insert(tango.DevString, scan_id)
            self._group_vcc.command_inout("Scan", data)
            self._group_fsp_corr_subarray.command_inout("Scan", data)
            self._group_fsp_pss_subarray.command_inout("Scan", data)
            self._group_fsp_pst_subarray.command_inout("Scan", data)
        except tango.DevFailed as df:
            msg = str(df.args[0].desc)
            self._component_obs_fault_callback(True)
            return (ResultCode.FAILED, msg)

        self._scan_id = int(scan_id)
        self._component_scanning_callback(True)
        return (ResultCode.STARTED, "Scan command successful")

    @check_communicating
    def end_scan(self: CbfSubarrayComponentManager) -> Tuple[ResultCode, str]:
        """
        End subarray Scan operation.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        try:
            # EndScan for all subordinate devices:
            self._group_vcc.command_inout("EndScan")
            self._group_fsp_corr_subarray.command_inout("EndScan")
            self._group_fsp_pss_subarray.command_inout("EndScan")
            self._group_fsp_pst_subarray.command_inout("EndScan")
        except tango.DevFailed as df:
            msg = str(df.args[0].desc)
            self._component_obs_fault_callback(True)
            return (ResultCode.FAILED, msg)

        self._scan_id = 0
        self._component_scanning_callback(False)
        return (ResultCode.OK, "EndScan command completed OK")

    @check_communicating
    def abort(self: CbfSubarrayComponentManager) -> None:
        """
        Abort subarray configuration or operation.
        """
        # if aborted from SCANNING, end VCC and FSP Subarray scans
        if self.scan_id != 0:
            self.end_scan()

    @check_communicating
    def restart(self: CbfSubarrayComponentManager) -> None:
        """
        Restart from fault.
        """
        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        (result_code, msg) = self.deconfigure()
        if result_code == ResultCode.OK:
            self.remove_all_receptors()

    @check_communicating
    def obsreset(self: CbfSubarrayComponentManager) -> None:
        """
        Reset subarray scan configuration or operation.
        """
        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        (result_code, msg) = self.deconfigure()

    def update_component_resources(
        self: CbfSubarrayComponentManager, resourced: bool
    ) -> None:
        """
        Update the component resource status, calling callbacks as required.

        :param resourced: whether the component is resourced.
        """
        self._logger.debug(f"update_component_resources({resourced})")
        if resourced:
            # perform "component_resourced" if not previously resourced
            if not self._resourced:
                self._component_resourced_callback(True)
        elif self._resourced:
            self._component_resourced_callback(False)

        self._resourced = resourced

    def update_component_configuration(
        self: CbfSubarrayComponentManager, configured: bool
    ) -> None:
        """
        Update the component configuration status, calling callbacks as required.

        :param configured: whether the component is configured.
        """
        self._logger.debug(f"update_component_configuration({configured})")
        if configured:
            # perform "component_configured" if not previously configured
            if not self._ready:
                self._component_configured_callback(True)
        elif self._ready:
            self._component_configured_callback(False)

        self._ready = configured
