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
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Tuple

# Tango imports
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    ObsState,
    PowerMode,
    SimulationMode,
)
from ska_tango_base.csp.subarray.component_manager import (
    CspSubarrayComponentManager,
)
from ska_telmodel.schema import validate as telmodel_validate
from tango import AttrQuality

from ska_mid_cbf_mcs.attribute_proxy import CbfAttributeProxy
from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import (
    FspModes,
    const,
    freq_band_dict,
    mhz_to_hz,
    vcc_oversampling_factor,
)
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.component.util import check_communicating

# SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.visibility_transport.visibility_transport import (
    VisibilityTransport,
)


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
    def dish_ids(self: CbfSubarrayComponentManager) -> List[str]:
        """Return the DISH/receptor ID list."""
        return self._dish_ids

    @property
    def vcc_ids(self: CbfSubarrayComponentManager) -> List[int]:
        """Return the VCC ID list."""
        return self._vcc_ids

    def __init__(
        self: CbfSubarrayComponentManager,
        subarray_id: int,
        controller: str,
        vcc: List[str],
        fsp: List[str],
        fsp_corr_sub: List[str],
        fsp_pss_sub: List[str],
        fsp_pst_sub: List[str],
        talon_board: List[str],
        vis_slim: str,
        logger: logging.Logger,
        simulation_mode: SimulationMode,
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
        :param talon_board: FQDNs of talon board devices
        :param vis_slim: FQDN of the visibility SLIM device
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

        self._simulation_mode = simulation_mode

        self._logger.info("Entering CbfSubarrayComponentManager.__init__)")

        self._dish_utils = None

        self._component_op_fault_callback = component_fault_callback
        self._component_obs_fault_callback = component_obs_fault_callback

        self._subarray_id = subarray_id
        self._fqdn_controller = controller
        self._fqdn_vcc = vcc
        self._fqdn_fsp = fsp
        self._fqdn_fsp_corr_subarray_device = fsp_corr_sub
        self._fqdn_fsp_pss_subarray_device = fsp_pss_sub
        self._fqdn_fsp_pst_subarray_device = fsp_pst_sub
        self._fqdn_talon_board_device = talon_board
        self._fqdn_vis_slim_device = vis_slim

        # set to determine if resources are assigned
        self._resourced = False
        # set to determine if ready to receive subscribed parameters;
        # also indicates whether component is currently configured
        self._ready = False

        self.connected = False

        self.obs_faulty = False

        # initialize attribute values
        self._sys_param_str = ""
        self._dish_ids = []
        self._vcc_ids = []
        self._frequency_band = 0
        self._config_id = ""
        self._scan_id = 0

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

        # for easy device-reference
        self._frequency_band_offset_stream1 = 0
        self._frequency_band_offset_stream2 = 0
        self._stream_tuning = [0, 0]

        # Controls the visibility transport from FSP outputs to SDP
        self._vis_transport = VisibilityTransport(
            logger=self._logger,
        )

        # device proxy for easy reference to CBF controller
        self._proxy_cbf_controller = None
        self._controller_max_capabilities = {}
        self._count_vcc = 0
        self._count_fsp = 0

        # proxies to subordinate devices
        self._proxies_vcc = []
        self._proxies_assigned_vcc = {}
        self._proxies_fsp = []
        self._proxies_fsp_corr_subarray_device = []
        self._proxies_fsp_pss_subarray_device = []
        self._proxies_fsp_pst_subarray_device = []
        self._proxies_talon_board_device = []

        # subarray does not control the visibility SLIM. It only
        # queries the config to figure out how to route the visibilities,
        # and updates the scan configuration accordingly.
        self._proxy_vis_slim = None

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

                self._fqdn_vcc = self._fqdn_vcc[: self._count_vcc]
                self._fqdn_fsp = self._fqdn_fsp[: self._count_fsp]
                self._fqdn_fsp_corr_subarray_device = (
                    self._fqdn_fsp_corr_subarray_device[: self._count_fsp]
                )
                self._fqdn_fsp_pss_subarray_device = (
                    self._fqdn_fsp_pss_subarray_device[: self._count_fsp]
                )
                self._fqdn_fsp_pst_subarray_device = (
                    self._fqdn_fsp_pst_subarray_device[: self._count_fsp]
                )

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

            if len(self._proxies_fsp_corr_subarray_device) == 0:
                for fqdn in self._fqdn_fsp_corr_subarray_device:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_fsp_corr_subarray_device.append(proxy)

            if len(self._proxies_fsp_pss_subarray_device) == 0:
                for fqdn in self._fqdn_fsp_pss_subarray_device:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_fsp_pss_subarray_device.append(proxy)

            if len(self._proxies_fsp_pst_subarray_device) == 0:
                for fqdn in self._fqdn_fsp_pst_subarray_device:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_fsp_pst_subarray_device.append(proxy)

            if len(self._proxies_talon_board_device) == 0:
                for fqdn in self._fqdn_talon_board_device:
                    proxy = CbfDeviceProxy(fqdn=fqdn, logger=self._logger)
                    self._proxies_talon_board_device.append(proxy)

            if self._proxy_vis_slim is None:
                self._proxy_vis_slim = CbfDeviceProxy(
                    fqdn=self._fqdn_vis_slim_device, logger=self._logger
                )

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

            for proxy in self._proxies_fsp_corr_subarray_device:
                proxy.adminMode = AdminMode.ONLINE
            for proxy in self._proxies_fsp_pss_subarray_device:
                proxy.adminMode = AdminMode.ONLINE
            for proxy in self._proxies_fsp_pst_subarray_device:
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
        for proxy in self._proxies_fsp_corr_subarray_device:
            proxy.adminMode = AdminMode.OFFLINE
        for proxy in self._proxies_fsp_pss_subarray_device:
            proxy.adminMode = AdminMode.OFFLINE
        for proxy in self._proxies_fsp_pst_subarray_device:
            proxy.adminMode = AdminMode.OFFLINE
        self.connected = False
        self.update_component_power_mode(PowerMode.UNKNOWN)

    @check_communicating
    def on(self: CbfSubarrayComponentManager) -> None:
        for proxy in self._proxies_fsp_corr_subarray_device:
            proxy.On()
        for proxy in self._proxies_fsp_pss_subarray_device:
            proxy.On()
        for proxy in self._proxies_fsp_pst_subarray_device:
            proxy.On()

        self.update_component_power_mode(PowerMode.ON)

    @check_communicating
    def off(self: CbfSubarrayComponentManager) -> None:
        for proxy in self._proxies_fsp_corr_subarray_device:
            proxy.Off()
        for proxy in self._proxies_fsp_pss_subarray_device:
            proxy.Off()
        for proxy in self._proxies_fsp_pst_subarray_device:
            proxy.Off()

        self.update_component_power_mode(PowerMode.OFF)

    @check_communicating
    def standby(self: CbfSubarrayComponentManager) -> None:
        self._logger.warning(
            "Operating state Standby invalid for CbfSubarray."
        )

    def update_sys_param(
        self: CbfSubarrayComponentManager, sys_param_str: str
    ) -> None:
        self._logger.debug(f"Received sys param: {sys_param_str}")
        self._sys_param_str = sys_param_str
        sys_param = json.loads(sys_param_str)
        self._dish_utils = DISHUtils(sys_param)
        self._logger.info(
            "Updated DISH ID to VCC ID and frequency offset k mapping"
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
                log_msg = f"Ignoring delay model (obsState not correct). Delay model being passed in is: {value}"
                self._logger.warning(log_msg)
                return
            try:
                self._logger.info("Received delay model update.")

                if value == self._last_received_delay_model:
                    log_msg = "Ignoring delay model (identical to previous)."
                    self._logger.warning(log_msg)
                    return

                self._last_received_delay_model = value
                delay_model_json = json.loads(value)

                # Validate delay_model_json against the telescope model
                self._logger.info(
                    f"Attempting to validate the following json against the telescope model: {delay_model_json}"
                )
                try:
                    telmodel_validate(
                        version=delay_model_json["interface"],
                        config=delay_model_json,
                        strictness=1,
                    )
                    self._logger.info("Delay model is valid!")
                except ValueError as e:
                    msg = f"Delay model validation against the telescope model failed with the following exception:\n {str(e)}."
                    self.raise_update_delay_model_fatal_error(msg)

                # pass DISH ID as VCC ID integer to FSPs and VCCs
                for delay_detail in delay_model_json["receptor_delays"]:
                    dish_id = delay_detail["receptor"]
                    delay_detail[
                        "receptor"
                    ] = self._dish_utils.dish_id_to_vcc_id[dish_id]
                t = Thread(
                    target=self._update_delay_model,
                    args=(json.dumps(delay_model_json),),
                )
                t.start()
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def _update_delay_model(
        self: CbfSubarrayComponentManager, model: str
    ) -> None:
        """
        Update FSP and VCC delay models.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param model: delay model
        """
        # This method is always called on a separate thread
        self._logger.debug("CbfSubarray._update_delay_model")

        log_msg = f"Updating delay model ...{model}"
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

                for jones_matrix in jones_matrix_all["jones_matrix"]:
                    # pass DISH ID as VCC ID integer to FSPs and VCCs
                    for matrix in jones_matrix["matrix_details"]:
                        dish_id = matrix["receptor"]
                        matrix[
                            "receptor"
                        ] = self._dish_utils.dish_id_to_vcc_id[dish_id]
                    t = Thread(
                        target=self._update_jones_matrix,
                        args=(json.dumps(jones_matrix),),
                    )
                    t.start()
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def _update_jones_matrix(
        self: CbfSubarrayComponentManager, matrix: str
    ) -> None:
        """
        Update FSP and VCC Jones matrices.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param matrix: Jones matrix value
        """
        # This method is always called on a separate thread
        self._logger.debug("CbfSubarray._update_jones_matrix")

        log_msg = f"Updating Jones Matrix {matrix}"
        self._logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, matrix)

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
                timing_beam_weights = json.loads(value)

                # pass DISH ID as VCC ID integer to FSPs and VCCs
                for weights in timing_beam_weights[
                    "timing_beam_weights_details"
                ]:
                    dish_id = weights["receptor"]
                    weights["receptor"] = self._dish_utils.dish_id_to_vcc_id[
                        dish_id
                    ]
                    t = Thread(
                        target=self._update_timing_beam_weights,
                        args=(
                            int(timing_beam_weights["epoch"]),
                            json.dumps(
                                timing_beam_weights[
                                    "timing_beam_weights_details"
                                ]
                            ),
                        ),
                    )
                    t.start()
            except Exception as e:
                self._logger.error(str(e))
        else:
            self._logger.warning(f"None value for {fqdn}")

    def _update_timing_beam_weights(
        self: CbfSubarrayComponentManager, weights: str
    ) -> None:
        """
        Update FSP beam weights.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param weights: beam weights value
        """
        # This method is always called on a separate thread
        self._logger.debug("CbfSubarray._update_timing_beam_weights")

        log_msg = f"Updating timing beam weights {weights}"
        self._logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, weights)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_beam_weights_config.acquire()
        self._group_fsp.command_inout("UpdateTimingBeamWeights", data)
        self._mutex_beam_weights_config.release()

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

    def raise_update_delay_model_fatal_error(
        self: CbfSubarrayComponentManager, msg: str
    ) -> Tuple[ResultCode, str]:
        """
        Raise fatal error in UpdateDelayModel execution

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
            "UpdateDelayModel execution",
            tango.ErrSeverity.ERR,
        )

    @check_communicating
    def _deconfigure(
        self: CbfSubarrayComponentManager,
    ) -> None:
        """Completely deconfigure the subarray; all initialization performed
        by by the ConfigureScan command must be 'undone' here."""
        # component_manager._deconfigure is invoked by GoToIdle, ConfigureScan,
        # ObsReset and Restart here in the CbfSubarray

        if self._ready:
            if self._group_fsp.get_size() > 0:
                # change FSP subarray membership
                data = tango.DeviceData()
                data.insert(tango.DevUShort, self._subarray_id)
                self._logger.debug(data)
                self._group_fsp.command_inout("RemoveSubarrayMembership", data)
                self._group_fsp.remove_all()

            for group in [
                self._group_fsp_corr_subarray,
                self._group_fsp_pss_subarray,
                self._group_fsp_pst_subarray,
            ]:
                if group.get_size() > 0:
                    group.remove_all()

        try:
            # unsubscribe from TMC events
            for event_id in list(self._events_telstate.keys()):
                self._events_telstate[event_id].remove_event(event_id)
                del self._events_telstate[event_id]
        except tango.DevFailed:
            self._component_obs_fault_callback(True)

        # reset all private data to their initialization values:
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

    def go_to_idle(
        self: CbfSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Send subarray from READY to IDLE.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._deconfigure()

        # issue GoToIdle to assigned VCCs
        if self._group_vcc.get_size() > 0:
            results = self._group_vcc.command_inout("GoToIdle")
            self._logger.info("Results from VCC GoToIdle:")
            for res in results:
                self._logger.info(res.get_data())

        self.update_component_configuration(False)

        return (ResultCode.OK, "GoToIdle command completed OK")

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
            msg = f"Scan configuration object is not a valid JSON object. Aborting configuration. argin is: {argin}"
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
            except (
                tango.DevFailed
            ):  # attribute doesn't exist or is not set up correctly
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
            except (
                tango.DevFailed
            ):  # attribute doesn't exist or is not set up correctly
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
            except (
                tango.DevFailed
            ):  # attribute doesn't exist or is not set up correctly
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
            except (
                tango.DevFailed
            ):  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['timing_beam_weights_subscription_point']}"
                    " not found or not set up correctly for "
                    "'beamWeightsSubscriptionPoint'. Aborting configuration."
                )
                return (False, msg)

        for dish_id, proxy in self._proxies_assigned_vcc.items():
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
                        dish = receptor["receptor_id"]
                        if dish not in self._dish_ids:
                            msg = (
                                f"'searchWindow' DISH ID {dish} "
                                + "not assigned to subarray. Aborting configuration."
                            )
                            return (False, msg)
        else:
            pass

        # Validate fsp.
        for fsp in configuration["fsp"]:
            try:
                # Validate fsp_id.
                if int(fsp["fsp_id"]) in list(range(1, self._count_fsp + 1)):
                    fsp_id = int(fsp["fsp_id"])
                    fsp_proxy = self._proxies_fsp[fsp_id - 1]
                else:
                    msg = (
                        f"'fsp_id' must be an integer in the range [1, {self._count_fsp}]."
                        " Aborting configuration."
                    )
                    return (False, msg)

                # Validate functionMode.
                valid_function_modes = [
                    "IDLE",
                    "CORR",
                    "PSS-BF",
                    "PST-BF",
                    "VLBI",
                ]
                try:
                    function_mode_value = valid_function_modes.index(
                        fsp["function_mode"]
                    )
                except ValueError:
                    return (
                        False,
                        f"{fsp['function_mode']} is not a valid FSP function mode.",
                    )
                fsp_function_mode = fsp_proxy.functionMode
                if fsp_function_mode not in [
                    FspModes.IDLE.value,
                    function_mode_value,
                ]:
                    msg = f"FSP {fsp_id} currently set to function mode {valid_function_modes.index(fsp_function_mode)}, \
                            cannot be used for {fsp['function_mode']} \
                            until it is returned to IDLE."
                    return (False, msg)

                # TODO - why add these keys to the fsp dict - not good practice!
                # TODO - create a new dict from a deep copy of the fsp dict.
                fsp["frequency_band"] = common_configuration["frequency_band"]
                if "frequency_band_offset_stream1" in configuration:
                    fsp["frequency_band_offset_stream1"] = configuration[
                        "frequency_band_offset_stream1"
                    ]
                if "frequency_band_offset_stream2" in configuration:
                    fsp["frequency_band_offset_stream2"] = configuration[
                        "frequency_band_offset_stream2"
                    ]
                if fsp["frequency_band"] in ["5a", "5b"]:
                    fsp["band_5_tuning"] = common_configuration[
                        "band_5_tuning"
                    ]

                # CORR #

                if fsp["function_mode"] == "CORR":
                    # dishes may not be specified in the
                    # configuration at all, or the list may be empty
                    if "receptors" in fsp and len(fsp["receptors"]) > 0:
                        self._logger.debug(
                            f"List of receptors: {self._dish_ids}"
                        )
                        for dish in fsp["receptors"]:
                            if dish not in self._dish_ids:
                                msg = (
                                    f"Receptor {dish} does not belong to "
                                    f"subarray {self._subarray_id}."
                                )
                                self._logger.error(msg)
                                return (False, msg)
                    else:
                        msg = (
                            "'receptors' not specified for Fsp CORR config."
                            "Per ICD all receptors allocated to subarray are used"
                        )
                        self._logger.info(msg)

                    frequencyBand = freq_band_dict()[fsp["frequency_band"]][
                        "band_index"
                    ]
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
                    if int(fsp["zoom_factor"]) in list(range(7)):
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
                                    "frequency_band_offset_stream1"
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
                                    # in many places - use a common function; also may be possible
                                    # to do them only once (ex. for band5Tuning)

                                    frequency_slice_range_1 = (
                                        fsp["band_5_tuning"][0] * 10**9
                                        + fsp["frequency_band_offset_stream1"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + (fsp["frequency_slice_id"] - 1)
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                        fsp["band_5_tuning"][0] * 10**9
                                        + fsp["frequency_band_offset_stream1"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + fsp["frequency_slice_id"]
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                    )

                                    frequency_slice_range_2 = (
                                        fsp["band_5_tuning"][1] * 10**9
                                        + fsp["frequency_band_offset_stream2"]
                                        - const.BAND_5_STREAM_BANDWIDTH
                                        * 10**9
                                        / 2
                                        + (fsp["frequency_slice_id"] - 1)
                                        * const.FREQUENCY_SLICE_BW
                                        * 10**6,
                                        fsp["band_5_tuning"][1] * 10**9
                                        + fsp["frequency_band_offset_stream2"]
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
                        if "channel_offset" in fsp:
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

                    # TODO: validate destination addresses: outputHost, outputPort

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
                            ) in self._proxies_fsp_pss_subarray_device:
                                searchBeamID = (
                                    fsp_pss_subarray_proxy.searchBeamID
                                )
                                fsp_id = fsp_pss_subarray_proxy.get_property(
                                    "FspID"
                                )["FspID"][0]
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
                                                f"'searchBeamID' {search_beam_ID} is already "
                                                f"being used in another subarray by FSP {fsp_id}"
                                            )
                                            return (False, msg)

                            # Validate dishes
                            # if not given, assign first DISH ID in subarray, as
                            # there is currently only support for 1 DISH per beam
                            if "receptor_ids" not in searchBeam:
                                searchBeam["receptor_ids"] = [
                                    self._dish_ids.copy()[0]
                                ]

                            # Sanity check:
                            for dish in searchBeam["receptor_ids"]:
                                if dish not in self._dish_ids:
                                    msg = (
                                        f"Receptor {dish} does not belong to "
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
                            if 1 > int(timingBeam["timing_beam_id"]) > 16:
                                # timingBeamID not in valid range
                                msg = (
                                    "'timingBeamID' must be within range 1-16 "
                                    f"(received {timingBeam['timing_beam_id']})."
                                )
                                return (False, msg)
                            for (
                                fsp_pst_subarray_proxy
                            ) in self._proxies_fsp_pst_subarray_device:
                                timingBeamID = (
                                    fsp_pst_subarray_proxy.timingBeamID
                                )
                                fsp_id = fsp_pst_subarray_proxy.get_property(
                                    "FspID"
                                )["FspID"][0]
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
                                                f"'timingBeamID' {timing_beam_ID} is already "
                                                f"being used in another subarray by FSP {fsp_id}"
                                            )
                                            return (False, msg)

                            # Validate dishes
                            # if not given, assign all DISH IDs belonging to subarray
                            if "receptor_ids" not in timingBeam:
                                timingBeam[
                                    "receptor_ids"
                                ] = self._dish_ids.copy()

                            for dish in timingBeam["receptor_ids"]:
                                if dish not in self._dish_ids:
                                    msg = (
                                        f"Receptor {dish} does not belong to "
                                        f"subarray {self._subarray_id}."
                                    )
                                    self._logger.error(msg)
                                    return (False, msg)
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
        # deconfigure to reset assigned FSPs and unsubscribe to events.
        self._deconfigure()

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

        # Prepare args for ConfigureBand
        for dish_id in self._dish_ids:
            if dish_id in self._dish_utils.dish_id_to_vcc_id.keys():
                # Fetch K-value based on dish_id
                vccID = self._dish_utils.dish_id_to_vcc_id[dish_id]
                vccProxy = self._proxies_vcc[vccID - 1]
                freq_offset_k = self._dish_utils.dish_id_to_k[dish_id]
                # Calculate dish sample rate
                dish_sample_rate = self._calculate_dish_sample_rate(
                    freq_band_dict()[common_configuration["frequency_band"]],
                    freq_offset_k,
                )
                # Fetch samples per frame for this freq band
                samples_per_frame = freq_band_dict()[
                    common_configuration["frequency_band"]
                ]["num_samples_per_frame"]

                args = {
                    "frequency_band": common_configuration["frequency_band"],
                    "dish_sample_rate": int(dish_sample_rate),
                    "samples_per_frame": int(samples_per_frame),
                }
                data = tango.DeviceData()
                data.insert(tango.DevString, json.dumps(args))
                vccProxy.command_inout("ConfigureBand", data)
            else:
                return (
                    ResultCode.FAILED,
                    f"Invalid receptor {dish_id}. ConfigureScan command failed.",
                )

        # Configure band5Tuning, if frequencyBand is 5a or 5b.
        if self._frequency_band in [4, 5]:
            stream_tuning = [
                *map(float, common_configuration["band_5_tuning"])
            ]
            self._stream_tuning = stream_tuning

        # Configure frequencyBandOffsetStream1.
        if "frequency_band_offset_stream1" in configuration:
            self._frequency_band_offset_stream1 = int(
                configuration["frequency_band_offset_stream1"]
            )
        else:
            self._frequency_band_offset_stream1 = 0
            log_msg = (
                "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            )
            self._logger.warning(log_msg)

        # If not given, use a default value.
        # If malformed, use a default value, but append an error.
        if "frequency_band_offset_stream2" in configuration:
            self._frequency_band_offset_stream2 = int(
                configuration["frequency_band_offset_stream2"]
            )
        else:
            self._frequency_band_offset_stream2 = 0
            log_msg = (
                "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
            )
            self._logger.warn(log_msg)

        config_dict = {
            "config_id": self._config_id,
            "frequency_band": common_configuration["frequency_band"],
            "band_5_tuning": self._stream_tuning,
            "frequency_band_offset_stream1": self._frequency_band_offset_stream1,
            "frequency_band_offset_stream2": self._frequency_band_offset_stream2,
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
            self._logger.info(
                f"Subscribing to doppler phase correction event of id: {event_id}"
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
            self._logger.info(
                f"Subscribing to delay model event of id: {event_id}"
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
            self._logger.info(
                f"Subscribing to jones matrix event of id: {event_id}"
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
            self._logger.info(
                f"Subscribing to timing beam weights event of id: {event_id}"
            )
            self._events_telstate[event_id] = attribute_proxy

        # Configure searchWindow.
        if "search_window" in configuration:
            for search_window in configuration["search_window"]:
                search_window["frequency_band"] = common_configuration[
                    "frequency_band"
                ]
                search_window[
                    "frequency_band_offset_stream1"
                ] = self._frequency_band_offset_stream1
                search_window[
                    "frequency_band_offset_stream2"
                ] = self._frequency_band_offset_stream2
                if search_window["frequency_band"] in ["5a", "5b"]:
                    search_window["band_5_tuning"] = common_configuration[
                        "band_5_tuning"
                    ]
                # pass DISH ID as VCC ID integer to VCCs
                if search_window["tdc_enable"]:
                    for tdc_dest in search_window["tdc_destination_address"]:
                        tdc_dest[
                            "receptor_id"
                        ] = self._dish_utils.dish_id_to_vcc_id[
                            tdc_dest["receptor_id"]
                        ]
                # pass on configuration to VCC
                data = tango.DeviceData()
                data.insert(tango.DevString, json.dumps(search_window))
                self._logger.debug(
                    f"configuring search window: {json.dumps(search_window)}"
                )
                self._group_vcc.command_inout("ConfigureSearchWindow", data)
        else:
            log_msg = "'searchWindow' not given."
            self._logger.warning(log_msg)

        # TODO: the entire vcc configuration should move to Vcc
        # for now, run ConfigScan only wih the following data, so that
        # the obsState are properly (implicitly) updated by the command
        # (And not manually by SetObservingState as before) - relevant???

        # FSP ##################################################################
        # Configure FSP.
        # TODO add VLBI once implemented

        for fsp in configuration["fsp"]:
            # Configure fsp_id.
            fsp_id = int(fsp["fsp_id"])
            fsp_proxy = self._proxies_fsp[fsp_id - 1]
            fsp_corr_proxy = self._proxies_fsp_corr_subarray_device[fsp_id - 1]
            fsp_pss_proxy = self._proxies_fsp_pss_subarray_device[fsp_id - 1]
            fsp_pst_proxy = self._proxies_fsp_pst_subarray_device[fsp_id - 1]

            self._group_fsp.add(self._fqdn_fsp[fsp_id - 1])

            # Set simulation mode of FSPs to subarray sim mode
            self._logger.info(
                f"Setting Simulation Mode of FSP {fsp_id} proxies to: {self._simulation_mode} and turning them on."
            )
            for proxy in [
                fsp_proxy,
                fsp_corr_proxy,
                fsp_pss_proxy,
                fsp_pst_proxy,
            ]:
                proxy.write_attribute("adminMode", AdminMode.OFFLINE)
                proxy.write_attribute("simulationMode", self._simulation_mode)
                proxy.write_attribute("adminMode", AdminMode.ONLINE)
                proxy.command_inout("On")

            # Configure functionMode if IDLE
            if fsp_proxy.functionMode == FspModes.IDLE.value:
                fsp_proxy.SetFunctionMode(fsp["function_mode"])

            # change FSP subarray membership
            fsp_proxy.AddSubarrayMembership(self._subarray_id)

            # Add configID, frequency_band, band_5_tuning, and sub_id to fsp. They are not included in the "FSP" portion in configScan JSON
            fsp["config_id"] = common_configuration["config_id"]
            fsp["sub_id"] = common_configuration["subarray_id"]
            fsp["frequency_band"] = common_configuration["frequency_band"]
            if fsp["frequency_band"] in ["5a", "5b"]:
                fsp["band_5_tuning"] = common_configuration["band_5_tuning"]
            if "frequency_band_offset_stream1" in configuration:
                fsp[
                    "frequency_band_offset_stream1"
                ] = self._frequency_band_offset_stream1
            if "frequency_band_offset_stream2" in configuration:
                fsp[
                    "frequency_band_offset_stream2"
                ] = self._frequency_band_offset_stream2

            # Add channel_offset if it was omitted from the configuration (it is optional).
            if "channel_offset" not in fsp:
                self._logger.warning(
                    "channel_offset not defined in configuration. Assigning default of 0."
                )
                fsp["channel_offset"] = 0

            # Add all DISH IDs for subarray and for correlation to fsp
            # Parameter named "subarray_vcc_ids" used by HPS contains all the
            # VCCs assigned to the subarray
            # Parameter named "corr_vcc_ids" used by HPS contains the
            # subset of the subarray VCCs for which the correlation results
            # are requested to be used in Mid.CBF output products (visibilities)

            fsp["subarray_vcc_ids"] = []
            for dish in self._dish_ids:
                fsp["subarray_vcc_ids"].append(
                    self._dish_utils.dish_id_to_vcc_id[dish]
                )

            # Add the fs_sample_rate for all dishes
            fsp["fs_sample_rates"] = self._calculate_fs_sample_rates(
                common_configuration["frequency_band"]
            )

            match fsp["function_mode"]:
                case "CORR":
                    # dishes may not be specified in the
                    # configuration at all, or the list may be empty
                    fsp["corr_vcc_ids"] = []
                    if "receptors" not in fsp or len(fsp["receptors"]) == 0:
                        # In this case by the ICD, all subarray allocated resources should be used.
                        fsp["corr_vcc_ids"] = fsp["subarray_vcc_ids"].copy()
                    else:
                        for dish in fsp["receptors"]:
                            fsp["corr_vcc_ids"].append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )

                    self._corr_config.append(fsp)
                    self._corr_fsp_list.append(fsp["fsp_id"])
                    self._group_fsp_corr_subarray.add(
                        self._fqdn_fsp_corr_subarray_device[fsp_id - 1]
                    )

                # TODO: PSS, PST below may fall out of date; currently only CORR function mode is supported outside of Mid.CBF MCS
                case "PSS-BF":
                    for searchBeam in fsp["search_beam"]:
                        search_beam_vcc_ids = []
                        for dish in searchBeam["receptor_ids"]:
                            search_beam_vcc_ids.append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )
                        searchBeam["receptor_ids"] = search_beam_vcc_ids
                    self._pss_config.append(fsp)
                    self._pss_fsp_list.append(fsp["fsp_id"])
                    self._group_fsp_pss_subarray.add(
                        self._fqdn_fsp_pss_subarray_device[fsp_id - 1]
                    )

                case "PST-BF":
                    for timingBeam in fsp["timing_beam"]:
                        timing_beam_vcc_ids = []
                        for dish in timingBeam["receptor_ids"]:
                            timing_beam_vcc_ids.append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )
                        timingBeam["receptor_ids"] = timing_beam_vcc_ids
                    self._pst_config.append(fsp)
                    self._pst_fsp_list.append(fsp["fsp_id"])
                    self._group_fsp_pst_subarray.add(
                        self._fqdn_fsp_pst_subarray_device[fsp_id - 1]
                    )

        # Call ConfigureScan for all FSP Subarray devices (CORR/PSS/PST)
        # NOTE:_corr_config is a list of fsp config JSON objects, each
        #      augmented by a number of vcc-fsp common parameters
        if len(self._corr_config) != 0:
            for this_fsp in self._corr_config:
                try:
                    self._logger.info(
                        f"cbf_subarray this_fsp: {json.dumps(this_fsp)}"
                    )
                    this_proxy = self._proxies_fsp_corr_subarray_device[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.set_timeout_millis(12000)
                    this_proxy.ConfigureScan(json.dumps(this_fsp))
                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring "
                        "FspCorrSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        # NOTE: _pss_config is constructed similarly to _corr_config
        if len(self._pss_config) != 0:
            for this_fsp in self._pss_config:
                try:
                    this_proxy = self._proxies_fsp_pss_subarray_device[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.set_timeout_millis(12000)
                    this_proxy.ConfigureScan(json.dumps(this_fsp))
                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring  "
                        "FspPssSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        # NOTE: _pst_config is constructed similarly to _corr_config
        if len(self._pst_config) != 0:
            for this_fsp in self._pst_config:
                try:
                    this_proxy = self._proxies_fsp_pst_subarray_device[
                        int(this_fsp["fsp_id"]) - 1
                    ]
                    this_proxy.set_timeout_millis(12000)
                    this_proxy.ConfigureScan(json.dumps(this_fsp))
                except tango.DevFailed:
                    msg = (
                        "An exception occurred while configuring  "
                        "FspPstSubarray; Aborting configuration"
                    )
                    self.raise_configure_scan_fatal_error(msg)

        # Route visibilities from each FSP to the outputting board
        if self._simulation_mode == SimulationMode.FALSE:
            self._logger.info("Configuring visibility transport")
            vis_slim_yaml = self._proxy_vis_slim.meshConfiguration
            self._logger.info(f"fsp config is: {configuration['fsp']}")
            self._logger.info(f"vis slim yaml is: {vis_slim_yaml}")
            self._vis_transport.configure(configuration["fsp"], vis_slim_yaml)

        # save configuration into latestScanConfig
        self._latest_scan_config = str(configuration)

        self.update_component_configuration(True)

        return (ResultCode.OK, "ConfigureScan command completed OK")

    @check_communicating
    def release_vcc(
        self: CbfSubarrayComponentManager, argin: List[str]
    ) -> Tuple[ResultCode, str]:
        """
        Remove receptor/dish from subarray.

        :param argin: The list of receptor/DISH IDs to be released
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(f"Current receptors: {*self._dish_ids,}")
        for dish_id in argin:
            self._logger.debug(f"Attempting to remove {dish_id}")
            if dish_id in self._dish_ids:
                if dish_id in self._dish_utils.dish_id_to_vcc_id.keys():
                    vccID = self._dish_utils.dish_id_to_vcc_id[dish_id]
                else:
                    return (
                        ResultCode.FAILED,
                        f"Invalid receptor {dish_id}. RemoveReceptors command failed.",
                    )
                vccFQDN = self._fqdn_vcc[vccID - 1]
                vccProxy = self._proxies_vcc[vccID - 1]

                self._dish_ids.remove(dish_id)
                self._vcc_ids.remove(vccID)
                self._group_vcc.remove(vccFQDN)
                del self._proxies_assigned_vcc[dish_id]

                try:
                    # reset subarrayMembership Vcc attribute:
                    vccProxy.subarrayMembership = 0
                    self._logger.debug(
                        f"VCC {vccID} subarray_id: "
                        + f"{vccProxy.subarrayMembership}"
                    )
                except tango.DevFailed as df:
                    msg = str(df.args[0].desc)
                    self._component_obs_fault_callback(True)
                    return (ResultCode.FAILED, msg)

                # clear the subarray ID off the talon board with the matching
                # DISH ID
                self._assign_talon_board_subarray_id(
                    dish_id=dish_id, assign=False
                )

            else:
                msg = f"Receptor {dish_id} not found. Skipping."
                self._logger.warning(msg)

        if len(self._dish_ids) == 0:
            self.update_component_resources(False)
            self._logger.info("No receptors remaining.")
        else:
            self._logger.info(f"Receptors remaining: {*self._dish_ids,}")

        return (ResultCode.OK, "RemoveReceptors completed OK")

    @check_communicating
    def release_all_vcc(
        self: CbfSubarrayComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Remove all receptors/dishes from subarray.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        if len(self._dish_ids) > 0:
            (rc, msg) = self.release_vcc(self._dish_ids.copy())
            return (rc, msg.replace("RemoveReceptors", "RemoveAllReceptors"))
        return (
            ResultCode.FAILED,
            "RemoveAllReceptors failed; no receptors currently assigned",
        )

    @check_communicating
    def assign_vcc(
        self: CbfSubarrayComponentManager, argin: List[str]
    ) -> Tuple[ResultCode, str]:
        """
        Add receptors/dishes to subarray.

        :param argin: The list of receptor/DISH IDs to be assigned
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(f"Current receptors: {*self._dish_ids,}")
        for dish_id in argin:
            self._logger.debug(f"Attempting to add receptor {dish_id}")

            self._logger.debug(
                f"Receptor to vcc keys: {self._dish_utils.dish_id_to_vcc_id.keys()}"
            )

            if dish_id in self._dish_utils.dish_id_to_vcc_id.keys():
                vccID = self._dish_utils.dish_id_to_vcc_id[dish_id]
            else:
                return (
                    ResultCode.FAILED,
                    f"Invalid receptor {dish_id}. AddReceptors command failed.",
                )

            if vccID > const.MAX_VCC:
                return (
                    ResultCode.FAILED,
                    f"VCC ID {vccID} is not supported. AddReceptors command failed.",
                )

            vccProxy = self._proxies_vcc[vccID - 1]

            self._logger.debug(
                f"dish_id = {dish_id}, vccProxy.dishID = "
                + f"{vccProxy.dishID}"
            )

            vccSubarrayID = vccProxy.subarrayMembership
            self._logger.debug(f"VCC {vccID} subarray_id: {vccSubarrayID}")

            # only add dish if it does not already belong to a
            # different subarray
            if vccSubarrayID not in [0, self._subarray_id]:
                msg = (
                    f"{dish_id} already in use by "
                    + f"subarray {vccSubarrayID}. Skipping."
                )
                self._logger.warning(msg)
            elif dish_id not in self._dish_ids:
                try:
                    # Setting simulation mode of VCC proxies based on simulation mode of subarray
                    self._logger.info(
                        f"Writing VCC simulation mode to: {self._simulation_mode}"
                    )
                    vccProxy.write_attribute("adminMode", AdminMode.OFFLINE)
                    vccProxy.write_attribute(
                        "simulationMode", self._simulation_mode
                    )
                    vccProxy.write_attribute("adminMode", AdminMode.ONLINE)
                    vccProxy.command_inout("On")

                    # update resourced state once first dish is added
                    if len(self._dish_ids) == 0:
                        self.update_component_resources(True)

                    self._dish_ids.append(dish_id)
                    self._vcc_ids.append(vccID)
                    self._group_vcc.add(self._fqdn_vcc[vccID - 1])
                    self._proxies_assigned_vcc[dish_id] = vccProxy

                    # change subarray membership of vcc
                    vccProxy.subarrayMembership = self._subarray_id
                    self._logger.debug(
                        f"VCC {vccID} subarray_id: "
                        + f"{vccProxy.subarrayMembership}"
                    )

                    # assign the subarray ID to the talon board with the matching
                    # DISH ID
                    self._assign_talon_board_subarray_id(
                        dish_id=dish_id, assign=True
                    )
                except tango.DevFailed as df:
                    msg = str(df.args[0].desc)
                    self._component_obs_fault_callback(True)
                    return (ResultCode.FAILED, msg)
            else:
                msg = f"{dish_id} already assigned to " + "subarray. Skipping."
                self._logger.warning(msg)

        self._logger.info(f"Receptors after adding: {*self._dish_ids,}")

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

        # Validate scan_json against the telescope model
        try:
            telmodel_validate(
                version=argin["interface"], config=argin, strictness=1
            )
            self._logger.info("Scan is valid!")
        except ValueError as e:
            msg = f"Scan validation against ska-telmodel schema failed with exception:\n {str(e)}"
            return (False, msg)

        scan_id = argin["scan_id"]
        data = tango.DeviceData()
        data.insert(tango.DevShort, scan_id)
        for group in [
            self._group_vcc,
            self._group_fsp_corr_subarray,
            self._group_fsp_pss_subarray,
            self._group_fsp_pst_subarray,
        ]:
            if group.get_size() > 0:
                results = group.command_inout("Scan", data)
                self._logger.info("Results from Scan:")
                for res in results:
                    self._logger.info(res.get_data())

        if self._simulation_mode == SimulationMode.FALSE:
            self._logger.info("Visibility transport enable output")
            self._vis_transport.enable_output(self._subarray_id)

        self._scan_id = scan_id
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
        # EndScan for all subordinate devices:
        for group in [
            self._group_vcc,
            self._group_fsp_corr_subarray,
            self._group_fsp_pss_subarray,
            self._group_fsp_pst_subarray,
        ]:
            if group.get_size() > 0:
                results = group.command_inout("EndScan")
                self._logger.info("Results from EndScan:")
                for res in results:
                    self._logger.info(res.get_data())

        if self._simulation_mode == SimulationMode.FALSE:
            self._logger.info("Visibility transport disable output")
            self._vis_transport.disable_output()

        self._scan_id = 0
        self._component_scanning_callback(False)
        return (ResultCode.OK, "EndScan command completed OK")

    @check_communicating
    def abort(self: CbfSubarrayComponentManager) -> None:
        """
        Abort subarray configuration or operation.
        """
        # reset ready flag
        self._ready = False

        for group in [
            self._group_vcc,
            self._group_fsp_corr_subarray,  # TODO CIP-1850 Abort/ObsReset per FSP subarray
            self._group_fsp_pss_subarray,
            self._group_fsp_pst_subarray,
        ]:
            if group.get_size() > 0:
                results = group.command_inout("Abort")
                self._logger.info("Results from Abort:")
                for res in results:
                    self._logger.info(res.get_data())

    @check_communicating
    def obsreset(self: CbfSubarrayComponentManager) -> None:
        """
        Reset to IDLE from abort/fault.
        """
        # if subarray is in FAULT, we must first abort VCC and FSP operation
        # this will allow us to call ObsReset on them even if they are not in FAULT
        if self.obs_faulty:
            self.abort()
            # use callback to reset FAULT state
            self._component_obs_fault_callback(False)

        try:
            # send Vcc devices to IDLE
            if self._group_vcc.get_size() > 0:
                self._group_vcc.command_inout("ObsReset")

            # send any previously assigned FSPs to IDLE
            for group in [
                self._group_fsp_corr_subarray,
                self._group_fsp_pss_subarray,
                self._group_fsp_pst_subarray,
            ]:
                # TODO CIP-1850 Abort/ObsReset per FSP subarray
                if group.get_size() > 0:
                    results = group.command_inout("ObsReset")
                    self._logger.info("Results from ObsReset:")
                    for res in results:
                        self._logger.info(res.get_data())

        except tango.DevFailed:
            self._component_obs_fault_callback(True)

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        self._deconfigure()

    @check_communicating
    def restart(self: CbfSubarrayComponentManager) -> None:
        """
        Restart to EMPTY from abort/fault.
        """
        # leverage obsreset to send assigned resources to IDLE and deconfigure
        self.obsreset()

        # remove all assigned VCCs to return to EMPTY
        self.release_all_vcc()

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
        self._logger.debug(
            f"update_component_configuration({configured}); configured == {configured}, self._ready == {self._ready}"
        )
        # perform component_configured/unconfigured callback if in a VALID case
        # Cases:
        # configured == False and self._ready == False -> INVALID: cannot issue component_unconfigured from IDLE
        # configured == True and self._ready == False -> VALID: can issue component_configured from IDLE
        # configured == False and self._ready == True -> VALID: can issue component_unconfigured from READY
        # configured == True and self._ready == True -> INVALID: cannot issue component_configured from READY
        if configured and not self._ready:
            self._component_configured_callback(True)
            self._ready = True
        elif not configured and self._ready:
            self._component_configured_callback(False)
            self._ready = False

    def _calculate_fs_sample_rate(
        self: CbfSubarrayComponentManager, freq_band: str, dish: str
    ) -> Dict:
        log_msg = (
            f"Calculate fs_sample_rate for freq_band:{freq_band} and {dish}"
        )
        self._logger.info(log_msg)

        # convert the DISH ID to a VCC ID integer using DISHUtils
        vcc_id = self._dish_utils.dish_id_to_vcc_id[dish]

        # find the k value for this DISH
        freq_offset_k = self._dish_utils.dish_id_to_k[dish]
        freq_band_info = freq_band_dict()[freq_band]

        total_num_fs = freq_band_info["total_num_FSs"]

        dish_sample_rate = self._calculate_dish_sample_rate(
            freq_band_info, freq_offset_k
        )

        log_msg = f"dish_sample_rate: {dish_sample_rate}"
        self._logger.debug(log_msg)
        fs_sample_rate = int(
            dish_sample_rate * vcc_oversampling_factor / total_num_fs
        )
        fs_sample_rate_for_band = {
            "vcc_id": vcc_id,
            "fs_sample_rate": fs_sample_rate,
        }
        log_msg = f"fs_sample_rate_for_band: {fs_sample_rate_for_band}"
        self._logger.info(log_msg)

        return fs_sample_rate_for_band

    def _calculate_fs_sample_rates(
        self: CbfSubarrayComponentManager, freq_band: str
    ) -> List[Dict]:
        output_sample_rates = []
        for dish in self._dish_ids:
            output_sample_rates.append(
                self._calculate_fs_sample_rate(freq_band, dish)
            )

        return output_sample_rates

    def _calculate_dish_sample_rate(
        self: CbfSubarrayComponentManager, freq_band_info, freq_offset_k
    ):
        base_dish_sample_rate_MH = freq_band_info["base_dish_sample_rate_MHz"]
        sample_rate_const = freq_band_info["sample_rate_const"]

        return (base_dish_sample_rate_MH * mhz_to_hz) + (
            sample_rate_const * freq_offset_k * const.DELTA_F
        )

    def _assign_talon_board_subarray_id(
        self: CbfSubarrayComponentManager, dish_id: str, assign: bool
    ) -> None:
        """
        Assign subarray ID to the talon board with the dish_id

        :param dish_id: the DISH ID
        :param assign: true to assign the subarray id, false to remove
        """
        for proxy in self._proxies_talon_board_device:
            board_dish_id = proxy.read_attribute("dishID").value
            if board_dish_id == dish_id:
                if assign:
                    proxy.write_attribute("subarrayID", str(self._subarray_id))
                else:
                    proxy.write_attribute("subarrayID", "")
                return
        return
