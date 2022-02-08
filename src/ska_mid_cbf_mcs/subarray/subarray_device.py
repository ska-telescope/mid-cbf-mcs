# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""
CbfSubarray
Sub-element subarray device for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints
from logging import log
from typing import Any, Dict, List, Tuple
import sys
import json
from random import randint
from threading import Thread, Lock
import time
import copy
from itertools import repeat

# Tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import DevState, AttrWriteType, AttrQuality
# Additional import
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #

# SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.attribute_proxy import CbfAttributeProxy
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import ObsState, AdminMode, HealthState
from ska_tango_base import SKASubarray, SKABaseDevice
from ska_tango_base.commands import ResultCode, BaseCommand, ResponseCommand

# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


def validate_ip(ip: str) -> bool:
    """
    Validate IP address format.

    :param ip: IP address to be evaluated

    :return: whether or not the IP address format is valid
    :rtype: bool
    """
    splitip = ip.split('.')
    if len(splitip) != 4:
        return False
    for ipparts in splitip:
        if not ipparts.isdigit():
            return False
        ipval = int(ipparts)
        if ipval < 0 or ipval > 255:
            return False
    return True


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """

    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #
    def init_command_objects(self: CbfSubarray) -> None:
        """
        Sets up the command objects. Register the new Commands here.
        """
        super().init_command_objects()
        device_args = (self, self.obs_state_model, self.logger)
        # resource_args = (self.resource_manager, self.state_model, self.logger) 
        # only use resource_args if we want to have separate resource_manager object

        # self.register_command_object(
        #     "On",
        #     self.OnCommand(*device_args)
        # )
        self.register_command_object(
            "Off",
            self.OffCommand(*device_args)
        )
        #TODO: is this command needed (vs ConfigureScan)
        # self.register_command_object(
        #     "Configure",
        #     self.ConfigureCommand(*device_args)
        # )
        self.register_command_object(
            "AddReceptors",
            self.AddReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveReceptors",
            self.RemoveReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveAllReceptors",
            self.RemoveAllReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "ConfigureScan",
            self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "Scan",
            self.ScanCommand(*device_args)
        )
        self.register_command_object(
            "EndScan",
            self.EndScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle",
            self.GoToIdleCommand(*device_args)
        )
        
    # ----------
    # Helper functions
    # ----------

    def _doppler_phase_correction_event_callback(
        self: CbfSubarray,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
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
                self._group_vcc.write_attribute("dopplerPhaseCorrection", value)
                log_msg = f"Value of {name} is {value}"
                self.logger.debug(log_msg)
            except Exception as e:
                self.logger.error(str(e))
        else:
            self.logger.warn(f"None value for {fqdn}")

    def _delay_model_event_callback(
        self: CbfSubarray,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """"
        Callback for delayModel change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self.logger.debug("Entering _delay_model_event_callback()")

        if value is not None:
            if self._obs_state not in [ObsState.READY, ObsState.SCANNING]:
                log_msg = "Ignoring delay model (obsState not correct)."
                self.logger.warn(log_msg)
                return
            try:
                self.logger.info("Received delay model update.")

                if value == self._last_received_delay_model:
                    log_msg = "Ignoring delay model (identical to previous)."
                    self.logger.warn(log_msg)
                    return

                self._last_received_delay_model = value
                delay_model_all = json.loads(value)

                for delay_model in delay_model_all["delayModel"]:
                    t = Thread(
                        target=self._update_delay_model,
                        args=(int(delay_model["epoch"]), 
                              json.dumps(delay_model["delayDetails"])
                        )
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            self.logger.warn(f"None value for {fqdn}")

    def _update_delay_model(
        self: CbfSubarray,
        epoch: int,
        model: str
    ) -> None:
        """
        Update FSP and VCC delay models.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param model: delay model
        """
        # This method is always called on a separate thread
        log_msg = f"Delay model active at {epoch} (currently {time.time()})..."
        self.logger.info(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = f"Updating delay model at specified epoch {epoch}..."
        self.logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, model)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_delay_model_config.acquire()
        self._group_vcc.command_inout("UpdateDelayModel", data)
        self._group_fsp.command_inout("UpdateDelayModel", data)
        self._mutex_delay_model_config.release()

    def _jones_matrix_event_callback(
        self: CbfSubarray,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """"
        Callback for jonesMatrix change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self.logger.debug("CbfSubarray._jones_matrix_event_callback")

        if value is not None:
            if self._obs_state not in [ObsState.READY, ObsState.SCANNING]:
                log_msg = "Ignoring Jones matrix (obsState not correct)."
                self.logger.warn(log_msg)
                return
            try:
                self.logger.info("Received Jones Matrix update.")

                if value == self._last_received_jones_matrix:
                    log_msg = "Ignoring Jones matrix (identical to previous)."
                    self.logger.warn(log_msg)
                    return

                self._last_received_jones_matrix = value
                jones_matrix_all = json.loads(value)

                for jones_matrix in jones_matrix_all["jonesMatrix"]:
                    t = Thread(
                        target=self._update_jones_matrix,
                        args=(int(jones_matrix["epoch"]), 
                              json.dumps(jones_matrix["matrixDetails"])
                        )
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            self.logger.warn(f"None value for {fqdn}")

    def _update_jones_matrix(
        self: CbfSubarray,
        epoch: int,
        matrix_details: str
    ) -> None:
        """
        Update FSP and VCC Jones matrices.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param matrix_details: Jones matrix value
        """
        #This method is always called on a separate thread
        self.logger.debug("CbfSubarray._update_jones_matrix")
        log_msg = f"Jones matrix active at {epoch} (currently {time.time()})..."
        self.logger.info(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = f"Updating Jones Matrix at specified epoch {epoch}..."
        self.logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, matrix_details)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_jones_matrix_config.acquire()
        self._group_vcc.command_inout("UpdateJonesMatrix", data)
        self._group_fsp.command_inout("UpdateJonesMatrix", data)
        self._mutex_jones_matrix_config.release()

    def _beam_weights_event_callback(
        self: CbfSubarray,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """"
        Callback for beamWeights change event subscription.

        :param fqdn: attribute FQDN
        :param name: attribute name
        :param value: attribute value
        :param quality: attribute quality
        """
        self.logger.debug("CbfSubarray._beam_weights_event_callback")

        if value is not None:
            if self._obs_state not in [ObsState.READY, ObsState.SCANNING]:
                log_msg = "Ignoring beam weights (obsState not correct)."
                self.logger.warn(log_msg)
                return
            try:
                self.logger.info("Received beam weights update.")

                if value == self._last_received_beam_weights:
                    log_msg = "Ignoring beam weights (identical to previous)."
                    self.logger.warn(log_msg)
                    return

                self._last_received_beam_weights = value
                beam_weights_all = json.loads(value)

                for beam_weights in beam_weights_all["beamWeights"]:
                    t = Thread(
                        target=self._update_beam_weights,
                        args=(int(beam_weights["epoch"]), 
                              json.dumps(beam_weights["beamWeightsDetails"])
                        )
                    )
                    t.start()
            except Exception as e:
                self.logger.error(str(e))
        else:
            self.logger.warn(f"None value for {fqdn}")

    def _update_beam_weights(
        self: CbfSubarray,
        epoch: int,
        weights_details: str
    ) -> None:
        """
        Update FSP beam weights.

        :param destination_type: type of device to send the delay model to
        :param epoch: system time of delay model reception
        :param weights_details: beam weights value
        """
        #This method is always called on a separate thread
        self.logger.debug("CbfSubarray._update_beam_weights")
        log_msg = f"Beam weights active at {epoch} (currently {time.time()})..."
        self.logger.info(log_msg)

        if epoch > time.time():
            time.sleep(epoch - time.time())

        log_msg = f"Updating beam weights at specified epoch {epoch}..."
        self.logger.info(log_msg)

        data = tango.DeviceData()
        data.insert(tango.DevString, weights_details)

        # we lock the mutex, forward the configuration, then immediately unlock it
        self._mutex_beam_weights_config.acquire()
        self._group_fsp.command_inout("UpdateBeamWeights", data)
        self._mutex_beam_weights_config.release()

    def _state_change_event_callback(
        self: CbfSubarray,
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality
    ) -> None:
        """"
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
                        self.logger.warn(log_msg)
                        return
                elif "State" in name:
                    if "vcc" in fqdn:
                        self._vcc_state[fqdn] = value
                    elif "fsp" in fqdn:
                        self._fsp_state[fqdn] = value
                    else:
                        # should NOT happen!
                        log_msg = f"Received state change for unknown device {name}"
                        self.logger.warn(log_msg)
                        return

                log_msg = f"New value for {fqdn} {name} is {value}"
                self.logger.info(log_msg)

            except Exception as except_occurred:
                self.logger.error(str(except_occurred))
        else:
            self.logger.warn(f"None value for {fqdn}")

    def _validate_scan_configuration(
        self: CbfSubarray,
        argin: str
    ) -> None:
        """
        Validate scan configuration.

        :param argin: The configuration as JSON formatted string.

        :raises: ``tango.DevFailed`` if the configuration data validation fails.
        """
        # try to deserialize input string to a JSON object
        try:
            full_configuration = json.loads(argin)
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        for proxy in self._proxies_assigned_vcc:
            if proxy.State() != tango.DevState.ON:
                msg = f"VCC {self._proxies_vcc.index(proxy) + 1} is not ON. Aborting configuration."
                self._raise_configure_scan_fatal_error(msg)
        
        # Validate frequencyBandOffsetStream1.
        if "frequency_band_offset_stream_1" not in configuration:
            configuration["frequency_band_offset_stream_1"] = 0
        if abs(int(configuration["frequency_band_offset_stream_1"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
            pass
        else:
            msg = "Absolute value of 'frequencyBandOffsetStream1' must be at most half " \
                    "of the frequency slice bandwidth. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        # Validate frequencyBandOffsetStream2.
        if "frequency_band_offset_stream_2" not in configuration:
            configuration["frequency_band_offset_stream_2"] = 0
        if abs(int(configuration["frequency_band_offset_stream_2"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
            pass
        else:
            msg = "Absolute value of 'frequencyBandOffsetStream2' must be at most " \
                    "half of the frequency slice bandwidth. Aborting configuration."
            self._raise_configure_scan_fatal_error(msg)

        # Validate band5Tuning, frequencyBandOffsetStream2 if frequencyBand is 5a or 5b.
        if common_configuration["frequency_band"] in ["5a", "5b"]:
            # band5Tuning is optional
            if "band_5_tuning" in common_configuration:
                pass
                # check if streamTuning is an array of length 2
                try:
                    assert len(common_configuration["band_5_tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                    self._raise_configure_scan_fatal_error(msg)

                stream_tuning = [*map(float, common_configuration["band_5_tuning"])]
                if common_configuration["frequency_band"] == "5a":
                    if all(
                            [const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0] <= stream_tuning[i]
                             <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1] for i in [0, 1]]
                    ):
                        pass
                    else:
                        msg = (
                            "Elements in 'band5Tuning must be floats between"
                            f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0]} and "
                            f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1]} "
                            f"(received {stream_tuning[0]} and {stream_tuning[1]})"
                            " for a 'frequencyBand' of 5a. "
                            "Aborting configuration."
                        )
                        self._raise_configure_scan_fatal_error(msg)
                else:  # configuration["frequency_band"] == "5b"
                    if all(
                            [const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0] <= stream_tuning[i]
                             <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1] for i in [0, 1]]
                    ):
                        pass
                    else:
                        msg = (
                            "Elements in 'band5Tuning must be floats between"
                            f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0]} and "
                            f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1]} "
                            f"(received {stream_tuning[0]} and {stream_tuning[1]})"
                            " for a 'frequencyBand' of 5b. "
                            "Aborting configuration."
                        )
                        self._raise_configure_scan_fatal_error(msg)
            else:
                # set band5Tuning to zero for the rest of the test. This won't 
                # change the argin in function "configureScan(argin)"
                common_configuration["band_5_tuning"] = [0, 0]

        # Validate dopplerPhaseCorrSubscriptionPoint.
        if "doppler_phase_corr_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["doppler_phase_corr_subscription_point"],
                    logger=self.logger
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['doppler_phase_corr_subscription_point']}"
                    " not found or not set up correctly for "
                    "'dopplerPhaseCorrSubscriptionPoint'. Aborting configuration."
                )
                self._raise_configure_scan_fatal_error(msg)

        # Validate delayModelSubscriptionPoint.
        if "delay_model_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["delay_model_subscription_point"],
                    logger=self.logger
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['delay_model_subscription_point']}"
                    " not found or not set up correctly for "
                    "'delayModelSubscriptionPoint'. Aborting configuration."
                )
                self._raise_configure_scan_fatal_error(msg)

        # Validate jonesMatrixSubscriptionPoint.
        if "jones_matrix_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["jones_matrix_subscription_point"],
                    logger=self.logger
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['jones_matrix_subscription_point']}"
                    " not found or not set up correctly for "
                    "'jonesMatrixSubscriptionPoint'. Aborting configuration."
                )
                self._raise_configure_scan_fatal_error(msg)
        
        # Validate beamWeightsSubscriptionPoint.
        if "timing_beam_weights_subscription_point" in configuration:
            try:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["timing_beam_weights_subscription_point"],
                    logger=self.logger
                )
                attribute_proxy.ping()
            except tango.DevFailed:  # attribute doesn't exist or is not set up correctly
                msg = (
                    f"Attribute {configuration['timing_beam_weights_subscription_point']}"
                    " not found or not set up correctly for "
                    "'beamWeightsSubscriptionPoint'. Aborting configuration."
                )
                self._raise_configure_scan_fatal_error(msg)


        # Validate searchWindow.
        if "search_window" in configuration:
            # check if searchWindow is an array of maximum length 2
            if len(configuration["search_window"]) > 2:
                msg = "'searchWindow' must be an array of maximum length 2. " \
                        "Aborting configuration."
                self._raise_configure_scan_fatal_error(msg)
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
                        proxy_fsp_subarray = self._proxies_fsp_corr_subarray[fspID - 1]
                    elif fsp["function_mode"] == "PSS-BF":
                        proxy_fsp_subarray = self._proxies_fsp_pss_subarray[fspID - 1]
                    elif fsp["function_mode"] == "PST-BF":
                        proxy_fsp_subarray = self._proxies_fsp_pst_subarray[fspID - 1]
                else:
                    msg = (
                        f"'fspID' must be an integer in the range [1, {self._count_fsp}]."
                        " Aborting configuration."
                    )
                    self._raise_configure_scan_fatal_error(msg)

                if proxy_fsp.State() != tango.DevState.ON:
                    msg = f"FSP {fspID} is not ON. Aborting configuration."
                    self._raise_configure_scan_fatal_error(msg)

                if proxy_fsp_subarray.State() != tango.DevState.ON:
                    msg = (
                        f"Subarray {self._subarray_id} of FSP {fspID} is not ON."
                        " Aborting configuration."
                    )
                    self._raise_configure_scan_fatal_error(msg)

                # Validate functionMode.
                function_modes = ["CORR", "PSS-BF", "PST-BF", "VLBI"]
                if fsp["function_mode"] in function_modes:
                    if function_modes.index(fsp["function_mode"]) + 1 == \
                            proxy_fsp.functionMode or \
                            proxy_fsp.functionMode == 0:
                        pass
                    else:
                        #TODO need to add this check for VLBI once implemented
                        for fsp_corr_subarray_proxy in self._proxies_fsp_corr_subarray:
                            if fsp_corr_subarray_proxy.obsState != ObsState.IDLE:
                                msg = (
                                    f"A different subarray is using FSP {fsp['fsp_id']} "
                                    "for a different function mode. Aborting configuration."
                                )
                                self._raise_configure_scan_fatal_error(msg)
                        for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
                            if fsp_pss_subarray_proxy.obsState != ObsState.IDLE:
                                msg = (
                                    f"A different subarray is using FSP {fsp['fsp_id']} "
                                    "for a different function mode. Aborting configuration."
                                )
                                self._raise_configure_scan_fatal_error(msg)
                        for fsp_pst_subarray_proxy in self._proxies_fsp_pst_subarray:
                            if fsp_pst_subarray_proxy.obsState != ObsState.IDLE:
                                msg = (
                                    f"A different subarray is using FSP {fsp['fsp_id']} "
                                    "for a different function mode. Aborting configuration."
                                )
                                self._raise_configure_scan_fatal_error(msg)
                else:
                    msg = (
                        f"'functionMode' must be one of {function_modes} "
                        f"(received {fsp['function_mode']}). "
                    )
                    self._raise_configure_scan_fatal_error(msg)

                # TODO - why add these keys to the fsp dict - not good practice!
                # TODO - create a new dict from a deep copy of the fsp dict.
                fsp["frequency_band"] = common_configuration["frequency_band"]
                fsp["frequency_band_offset_stream_1"] = configuration["frequency_band_offset_stream_1"]
                fsp["frequency_band_offset_stream_2"] = configuration["frequency_band_offset_stream_2"]
                if fsp["frequency_band"] in ["5a", "5b"]:
                    fsp["band_5_tuning"] = common_configuration["band_5_tuning"]

                # --------------------------------------------------------

                ########## CORR ##########

                if fsp["function_mode"] == "CORR":

                    if "receptor_ids" in fsp:
                        for this_rec in fsp["receptor_ids"]:
                            if this_rec not in self._receptors:
                                msg = (
                                    f"Receptor {self._receptors[this_rec]} "
                                    f"does not belong to subarray {self._subarray_id}."
                                )
                                self.logger.error(msg)
                                self._raise_configure_scan_fatal_error(msg)
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
                            range(1, num_frequency_slices[frequencyBand] + 1)):
                        pass
                    else:
                        msg = (
                            "'frequencySliceID' must be an integer in the range "
                            f"[1, {num_frequency_slices[frequencyBand]}] "
                            f"for a 'frequencyBand' of {fsp['frequency_band']}."
                        )
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # Validate zoom_factor.
                    if int(fsp["zoom_factor"]) in list(range(0, 7)):
                        pass
                    else:
                        msg = "'zoom_factor' must be an integer in the range [0, 6]."
                        # this is a fatal error
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # Validate zoomWindowTuning.
                    if int(fsp["zoom_factor"]) > 0:  # zoomWindowTuning is required
                        if "zoom_window_tuning" in fsp:

                            if fsp["frequency_band"] not in ["5a", "5b"]:  # frequency band is not band 5
                                frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(fsp["frequency_band"])
                                frequency_band_start = [*map(lambda j: j[0] * 10 ** 9, [
                                    const.FREQUENCY_BAND_1_RANGE,
                                    const.FREQUENCY_BAND_2_RANGE,
                                    const.FREQUENCY_BAND_3_RANGE,
                                    const.FREQUENCY_BAND_4_RANGE
                                ])][frequencyBand] + fsp["frequency_band_offset_stream_1"]
                                
                                frequency_slice_range = (
                                    frequency_band_start + \
                                    (fsp["frequency_slice_id"] - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6,
                                    frequency_band_start +
                                    fsp["frequency_slice_id"] * const.FREQUENCY_SLICE_BW * 10 ** 6
                                )

                                if frequency_slice_range[0] <= \
                                        int(fsp["zoom_window_tuning"]) * 10 ** 3 <= \
                                        frequency_slice_range[1]:
                                    pass
                                else:
                                    msg = "'zoomWindowTuning' must be within observed frequency slice."
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg,
                                                                    "ConfigureScan execution",
                                                                    tango.ErrSeverity.ERR)
                            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                                if common_configuration["band_5_tuning"] == [0,0]: # band5Tuning not specified
                                    pass
                                else:

                                    # TODO: these validations of BW range are done many times
                                    # in many places - use a commom function; also may be possible
                                    # to do them only once (ex. for band5Tuning)

                                    frequency_slice_range_1 = (
                                        fsp["band_5_tuning"][0] * 10 ** 9 + fsp["frequency_band_offset_stream_1"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        (fsp["frequency_slice_id"] - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6,
                                        fsp["band_5_tuning"][0] * 10 ** 9 + fsp["frequency_band_offset_stream_1"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        fsp["frequency_slice_id"] * const.FREQUENCY_SLICE_BW * 10 ** 6
                                    )

                                    frequency_slice_range_2 = (
                                        fsp["band_5_tuning"][1] * 10 ** 9 + fsp["frequency_band_offset_stream_2"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        (fsp["frequency_slice_id"] - 1) * const.FREQUENCY_SLICE_BW * 10 ** 6,
                                        fsp["band_5_tuning"][1] * 10 ** 9 + fsp["frequency_band_offset_stream_2"] - \
                                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2 + \
                                        fsp["frequency_slice_id"] * const.FREQUENCY_SLICE_BW * 10 ** 6
                                    )

                                    if (frequency_slice_range_1[0] <= int(fsp["zoom_window_tuning"]) * 10 ** 3 <=
                                        frequency_slice_range_1[1]) or \
                                            (frequency_slice_range_2[0] <=
                                            int(fsp["zoom_window_tuning"]) * 10 ** 3 <=
                                            frequency_slice_range_2[1]):
                                        pass
                                    else:
                                        msg = "'zoomWindowTuning' must be within observed frequency slice."
                                        self.logger.error(msg)
                                        tango.Except.throw_exception("Command failed", msg,
                                                                    "ConfigureScan execution",
                                                                    tango.ErrSeverity.ERR)
                        else:
                            msg = "FSP specified, but 'zoomWindowTuning' not given."
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg,
                                                            "ConfigureScan execution",
                                                            tango.ErrSeverity.ERR)

                    # Validate integrationTime.
                    if int(fsp["integration_factor"]) in list(
                            range (self.MIN_INT_TIME, 10 * self.MIN_INT_TIME + 1, self.MIN_INT_TIME)
                    ):
                        pass
                    else:
                        msg = (
                            "'integrationTime' must be an integer in the range"
                            f" [1, 10] multiplied by {self.MIN_INT_TIME}."
                        )
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # Validate fspChannelOffset
                    try: 
                        if int(fsp["channel_offset"])>=0: 
                            pass
                        #TODO has to be a multiple of 14880
                        else:
                            msg="fspChannelOffset must be greater than or equal to zero"
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)
                    except:
                        msg="fspChannelOffset must be an integer"
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                        tango.ErrSeverity.ERR)

                    # validate outputlink
                    # check the format
                    try:
                        for element in fsp["output_link_map"]:
                            a, b = (int(element[0]), int(element[1]))
                    except:
                        msg = "'outputLinkMap' format not correct."
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                    tango.ErrSeverity.ERR)

                    # Validate channelAveragingMap.
                    if "channel_averaging_map" in fsp:
                        try:
                            # validate dimensions
                            for i in range(0,len(fsp["channel_averaging_map"])):
                                assert len(fsp["channel_averaging_map"][i]) == 2

                            # validate averaging factor
                            for i in range(0,len(fsp["channel_averaging_map"])):
                                # validate channel ID of first channel in group
                                if int(fsp["channel_averaging_map"][i][0]) == \
                                        i * self.NUM_FINE_CHANNELS / self.NUM_CHANNEL_GROUPS:
                                    pass  # the default value is already correct
                                else:
                                    msg = (
                                        f"'channelAveragingMap'[{i}][0] is not the channel ID of the "
                                        f"first channel in a group (received {fsp['channel_averaging_map'][i][0]})."
                                    )
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg,
                                                                 "ConfigureScan execution",
                                                                 tango.ErrSeverity.ERR)

                                # validate averaging factor
                                if int(fsp["channel_averaging_map"][i][1]) in [0, 1, 2, 3, 4, 6, 8]:
                                    pass
                                else:
                                    msg = (
                                        f"'channelAveragingMap'[{i}][1] must be one of "
                                        f"[0, 1, 2, 3, 4, 6, 8] (received {fsp['channel_averaging_map'][i][1]})."
                                    )
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg,
                                                                    "ConfigureScan execution",
                                                                    tango.ErrSeverity.ERR)
                        except (TypeError, AssertionError):  # dimensions not correct
                            msg = "channel Averaging Map dimensions not correct"
                            self.logger.error(msg)
                            tango.Except.throw_exception("Command failed", msg, "ConfigureScan execution",
                                                            tango.ErrSeverity.ERR)

                    # TODO: validate destination addresses: outputHost, outputMac, outputPort?

                # --------------------------------------------------------

                ########## PSS-BF ##########
                # TODO currently only CORR function mode is supported outside of Mid.CBF MCS
                if fsp["function_mode"] == "PSS-BF":
                    if int(fsp["search_window_id"]) in [1, 2]:
                        pass
                    else:  # searchWindowID not in valid range
                        msg = (
                            "'searchWindowID' must be one of [1, 2] "
                            f"(received {fsp['search_window_id']})."
                        )
                        self._raise_configure_scan_fatal_error(msg)
                    if len(fsp["search_beam"]) <= 192:
                        for searchBeam in fsp["search_beam"]:
                            if 1 > int(searchBeam["search_beam_id"]) > 1500:
                                # searchbeamID not in valid range
                                msg = (
                                    "'searchBeamID' must be within range 1-1500 "
                                    f"(received {searchBeam['search_beam_id']})."
                                )
                                self._raise_configure_scan_fatal_error(msg)
                            
                            for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
                                searchBeamID = fsp_pss_subarray_proxy.searchBeamID
                                if searchBeamID is None:
                                    pass
                                else:
                                    for search_beam_ID in searchBeamID:
                                        if int(searchBeam["search_beam_id"]) != search_beam_ID:
                                            pass
                                        elif fsp_pss_subarray_proxy.obsState == ObsState.IDLE:
                                            pass
                                        else:
                                            msg = (
                                                f"'searchBeamID' {searchBeam['search_beam_id']} "
                                                "is already being used on another fspSubarray."
                                            )
                                            self._raise_configure_scan_fatal_error(msg)
                            
                                # Validate receptors.
                                # This is always given, due to implementation details.
                                #TODO assume always given, as there is currently only support for 1 receptor/beam
                            if "receptor_ids" not in searchBeam:
                                searchBeam["receptor_ids"] = self._receptors

                            # Sanity check:
                            for this_rec in searchBeam["receptor_ids"]:
                                if this_rec not in self._receptors:
                                    msg = (
                                        f"Receptor {self._receptors[this_rec]} "
                                        f"does not belong to subarray {self._subarray_id}."
                                    )
                                    self.logger.error(msg)
                                    tango.Except.throw_exception("Command failed", msg, 
                                    "ConfigureScan execution", tango.ErrSeverity.ERR)

                            if searchBeam["enable_output"] is False or searchBeam["enable_output"] is True:
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                self._raise_configure_scan_fatal_error(msg)

                            if isinstance(searchBeam["averaging_interval"], int):
                                pass
                            else:
                                msg = "'averagingInterval' is not a valid integer"
                                self._raise_configure_scan_fatal_error(msg)

                            if validate_ip(searchBeam["search_beam_destination_address"]):
                                pass
                            else:
                                msg = "'searchBeamDestinationAddress' is not a valid IP address"
                                self._raise_configure_scan_fatal_error(msg)

                    else:
                        msg = "More than 192 SearchBeams defined in PSS-BF config"
                        self._raise_configure_scan_fatal_error(msg)
                
                # --------------------------------------------------------

                ########## PST-BF ##########
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
                                self._raise_configure_scan_fatal_error(msg)
                            for fsp_pst_subarray_proxy in self._proxies_fsp_pst_subarray:
                                timingBeamID = fsp_pst_subarray_proxy.timingBeamID
                                if timingBeamID is None:
                                    pass
                                else:
                                    for timing_beam_ID in timingBeamID:
                                        if int(timingBeam["timing_beam_id"]) != timing_beam_ID:
                                            pass
                                        elif fsp_pst_subarray_proxy.obsState == ObsState.IDLE:
                                            pass
                                        else:
                                            msg = (
                                                f"'timingBeamID' {timingBeam['timing_beam_id']} "
                                                "is already being used on another fspSubarray."
                                            )
                                            self._raise_configure_scan_fatal_error(msg)

                            # Validate receptors.
                            # This is always given, due to implementation details.
                            if "receptor_ids" in timingBeam:
                                for this_rec in timingBeam["receptor_ids"]:
                                    if this_rec not in self._receptors:
                                        msg = (
                                            f"Receptor {self._receptors[this_rec]} "
                                            f"does not belong to subarray {self._subarray_id}."
                                        )
                                        self.logger.error(msg)
                                        self._raise_configure_scan_fatal_error(msg)
                            else:
                                timingBeam["receptor_ids"] = self._receptors

                            if timingBeam["enable_output"] is False or timingBeam["enable_output"] is True:
                                pass
                            else:
                                msg = "'outputEnabled' is not a valid boolean"
                                self._raise_configure_scan_fatal_error(msg)

                            if validate_ip(timingBeam["timing_beam_destination_address"]):
                                pass
                            else:
                                msg = "'timingBeamDestinationAddress' is not a valid IP address"
                                self._raise_configure_scan_fatal_error(msg)

                    else:
                        msg = "More than 16 TimingBeams defined in PST-BF config"
                        self._raise_configure_scan_fatal_error(msg)

            except tango.DevFailed:  # exception in ConfigureScan
                msg = (
                    "An exception occurred while configuring FSPs:"
                    f"\n{sys.exc_info()[1].args[0].desc}\n" \
                    "Aborting configuration"
                 )

                self._raise_configure_scan_fatal_error(msg)

        # At this point, everything has been validated.

    def _raise_configure_scan_fatal_error(self: CbfSubarray, msg: str) -> None:
        """
        Raise fatal error in ConfigureScan execution

        :param msg: error message
        """
        self.logger.error(msg)
        tango.Except.throw_exception(
            "Command failed", msg, "ConfigureScan execution", tango.ErrSeverity.ERR
        )

    # PROTECTED REGION END #    //  CbfSubarray.class_variable



    def _deconfigure(self:CbfSubarray) -> None:
        """Completely deconfigure the subarray; all initialization performed 
        by by the ConfigureScan command must be 'undone' here."""
        
        # TODO: the deconfiguration should happen in reverse order of the
        #       initialization:

        # unsubscribe from TMC events
        for event_id in list(self._events_telstate.keys()):
            self._events_telstate[event_id].remove_event(event_id)
            del self._events_telstate[event_id]

        # unsubscribe from FSP state change events
        for fspID in list(self._events_state_change_fsp.keys()):
            proxy_fsp = self._proxies_fsp[fspID - 1]
            proxy_fsp.remove_event(
                "State",
                self._events_state_change_fsp[fspID][0]
            )
            proxy_fsp.remove_event(
                "healthState",
                self._events_state_change_fsp[fspID][1]
            )
            del self._events_state_change_fsp[fspID]
            del self._fsp_state[self._fqdn_fsp[fspID - 1]]
            del self._fsp_health_state[self._fqdn_fsp[fspID - 1]]

        for group in [
            self._group_fsp_corr_subarray, 
            self._group_fsp_pss_subarray,
            self._group_fsp_pst_subarray
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
            # self.logger.info(data)
            self._group_fsp.command_inout("RemoveSubarrayMembership", data)
            self._group_fsp.remove_all()

        # reset all private data to their initialization values:
        self._scan_ID = 0       
        self._config_ID = ""
        self._frequency_band = 0
        self._last_received_delay_model  = "{}"
        self._last_received_jones_matrix = "{}"
        self._last_received_beam_weights = "{}"

        # TODO: what happens if 
        #       fsp_corr_subarray_proxy.State() == tango.DevState.OFF ??
        #       that should not happen
        # TODO: why is this done after the group command_inout?
        for fsp_corr_subarray_proxy in self._proxies_fsp_corr_subarray:
            if fsp_corr_subarray_proxy.State() == tango.DevState.ON:
                fsp_corr_subarray_proxy.GoToIdle()
        for fsp_pss_subarray_proxy in self._proxies_fsp_pss_subarray:
            if fsp_pss_subarray_proxy.State() == tango.DevState.ON:
                fsp_pss_subarray_proxy.GoToIdle()
        for fsp_pst_subarray_proxy in self._proxies_fsp_pst_subarray:
            if fsp_pst_subarray_proxy.State() == tango.DevState.ON:
                fsp_pst_subarray_proxy.GoToIdle()
        # TODO: add 'GoToIdle' for VLBI once implemented

    def _remove_receptors_helper(self: CbfSubarray, argin: List[int]) -> None:
        """Helper function to remove receptors for removeAllReceptors. 
        Takes in a list of integers.

        :param argin: list of receptors to remove
        """
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
        for receptorID in argin:
            # check for invalid receptorID
            if not 0 < receptorID < 198:
                log_msg = f"Invalid receptor ID {receptorID}. Skipping."
                self.logger.warn(log_msg)
            elif receptorID in self._receptors:
                vccID = receptor_to_vcc[receptorID]
                vccFQDN = self._fqdn_vcc[vccID - 1]
                vccProxy = self._proxies_vcc[vccID - 1]

                # unsubscribe from events
                vccProxy.remove_event(
                    "State",
                    self._events_state_change_vcc[vccID][0]
                )
                vccProxy.remove_event(
                    "healthState",
                    self._events_state_change_vcc[vccID][1]
                )
                
                del self._events_state_change_vcc[vccID]
                del self._vcc_state[vccFQDN]
                del self._vcc_health_state[vccFQDN]


                # reset receptorID and subarrayMembership Vcc attribute:
                # TODO: should VCC receptorID be altered here?
                # currently the mapping is set in the controller
                # vccProxy.receptorID = 0
                vccProxy.subarrayMembership = 0

                self._receptors.remove(receptorID)
                self._proxies_assigned_vcc.remove(vccProxy)
                self._group_vcc.remove(vccFQDN)
            else:
                log_msg = f"Receptor {receptorID} not assigned to subarray. Skipping."
                self.logger.warn(log_msg)


    # Used by commands that needs resource manager in SKASubarray 
    # base class (for example AddReceptors command). 
    # The base class define len as len(resource_manager), 
    # so we need to change that here. TODO - to clarify.
    def __len__(self: CbfSubarray) -> int:
        """
        Returns the number of resources currently assigned. Note that
        this also functions as a boolean method for whether there are
        any assigned resources: ``if len()``.

        :return: number of resources assigned
        :rtype: int
        """

        return len(self._receptors)


    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16',
    )

    CbfControllerAddress = device_property(
        dtype='str',
        doc="FQDN of CBF CController",
        default_value="mid_csp_cbf/sub_elt/controller"
    )

    PssConfigAddress = device_property(
        dtype='str'
    )

    PstConfigAddress = device_property(
        dtype='str'
    )

    SW1Address = device_property(
        dtype='str'
    )

    SW2Address = device_property(
        dtype='str'
    )

    VCC = device_property(
        dtype=('str',)
    )

    FSP = device_property(
        dtype=('str',)
    )

    FspCorrSubarray = device_property(
        dtype=('str',)
    )

    FspPssSubarray = device_property(
        dtype=('str',)
    )

    FspPstSubarray = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    configID = attribute(
        dtype='str',
        access=AttrWriteType.READ,
        label="Config ID",
        doc="config ID",
    )

    scanID = attribute(
        dtype='uint',
        access=AttrWriteType.READ,
        label="Scan ID",
        doc="Scan ID",
    )

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="receptor_ids",
        doc="List of receptors assigned to subarray",
    )


    vccState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
        label="VCC state",
        polling_period=1000,
        doc="Report the state of the assigned VCCs as an array of DevState",
    )

    vccHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC health status",
        polling_period=1000,
        abs_change=1,
        doc="Report the health state of assigned VCCs as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    fspState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
        label="FSP state",
        polling_period=1000,
        doc="Report the state of the assigned FSPs",
    )

    fspHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP health status",
        polling_period=1000,
        abs_change=1,
        doc="Report the health state of the assigned FSPs.",
    )

    fspList = attribute(
        dtype=(('uint16',),),
        max_dim_x=4,
        max_dim_y=27,
        label="List of FSP's used by subarray",
        doc="fsp[1][x] = CORR [2][x] = PSS [1][x] = PST [1][x] = VLBI",
    )

    latestScanConfig = attribute(
        dtype='DevString',
        label="lastest Scan Configuration",
        doc="for storing lastest scan configuration",
    )


    # ---------------
    # General methods
    # ---------------
    class InitCommand(SKASubarray.InitCommand):
        """
        A class for the CbfSubarray's init_device() "command".
        """
        def do(self: CbfSubarray.InitCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation. 
            Initialize the attributes and the properties of the CbfSubarray.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            
            """
            # SKASubarray.init_device(self)
            # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
            # self.set_state(DevState.INIT)
            (result_code, message) = super().do()

            device=self.target
            
            device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            device._element_logging_level = tango.LogLevel.LOG_DEBUG
            device._central_logging_level = tango.LogLevel.LOG_DEBUG

            # get subarray ID
            if device.SubID:
                device._subarray_id = device.SubID
            else:
                device._subarray_id = int(device.get_name()[-2:])  # last two chars of FQDN

            # initialize attribute values
            device._receptors = []
            device._frequency_band = 0
            device._config_ID = ""
            device._scan_ID = 0
            device._fsp_list = [[], [], [], []]
            # device._output_links_distribution = {"configID": ""}# ???
            device._vcc_state = {}
            device._vcc_health_state = {}
            device._fsp_state = {}
            device._fsp_health_state = {}
            # store list of fsp configs being used for each function mode
            device._corr_config = []
            device._pss_config = []
            device._pst_config = []
            # store list of fsp being used for each function mode
            device._corr_fsp_list = []
            device._pss_fsp_list = []
            device._pst_fsp_list = []
            device._latest_scan_config=""
            # device._published_output_links = False# ???
            # device._last_received_vis_destination_address = "{}"#???
            device._last_received_delay_model = "{}"
            device._last_received_jones_matrix = "{}"
            device._last_received_beam_weights = "{}"

            device._mutex_delay_model_config = Lock()
            device._mutex_jones_matrix_config = Lock()
            device._mutex_beam_weights_config = Lock()

            # for easy device-reference
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._stream_tuning = [0, 0]

            device.MIN_INT_TIME = const.MIN_INT_TIME
            device.NUM_CHANNEL_GROUPS = const.NUM_CHANNEL_GROUPS
            device.NUM_FINE_CHANNELS = const.NUM_FINE_CHANNELS

            # device proxy for easy reference to CBF controller
            device._proxy_cbf_controller = None

            device._controller_max_capabilities = {}
            device._count_vcc = 0
            device._count_fsp = 0

            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._fqdn_fsp = list(device.FSP)[:device._count_fsp]
            device._fqdn_fsp_corr_subarray = list(device.FspCorrSubarray)
            device._fqdn_fsp_pss_subarray = list(device.FspPssSubarray)
            device._fqdn_fsp_pst_subarray = list(device.FspPstSubarray)

            device._proxies_vcc = []
            device._proxies_fsp = []
            device._proxies_fsp_corr_subarray = []
            device._proxies_fsp_pss_subarray = []
            device._proxies_fsp_pst_subarray = []

            # Note vcc connected both individual and in group
            device._proxies_assigned_vcc = []
            device._proxies_assigned_fsp = []

            # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
            device._events_telstate = {}

            # store the subscribed state change events as vcc_ID:[event_ID, event_ID] key:value pairs
            device._events_state_change_vcc = {}

            # store the subscribed state change events as fsp_ID:[event_ID, event_ID] key:value pairs
            device._events_state_change_fsp = {}

            # initialize groups
            device._group_vcc = None
            device._group_fsp = None
            device._group_fsp_corr_subarray = None
            device._group_fsp_pss_subarray = None
            device._group_fsp_pst_subarray = None

            return (ResultCode.OK, "successfull")

    def always_executed_hook(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        if self._proxy_cbf_controller is None:
            self._proxy_cbf_controller = CbfDeviceProxy(
                fqdn=self.CbfControllerAddress, logger=self.logger
            )
            self._controller_max_capabilities = dict(
                pair.split(":") for pair in
                self._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
            )
            self._count_vcc = int(self._controller_max_capabilities["VCC"])
            self._count_fsp = int(self._controller_max_capabilities["FSP"])
            self._fqdn_vcc = list(self.VCC)[:self._count_vcc]
            self._fqdn_fsp = list(self.FSP)[:self._count_fsp]
            self._fqdn_fsp_corr_subarray = list(self.FspCorrSubarray)
            self._fqdn_fsp_pss_subarray = list(self.FspPssSubarray)
            self._fqdn_fsp_pst_subarray = list(self.FspPstSubarray)

        if len(self._proxies_vcc) == 0:
            self._proxies_vcc = [
                CbfDeviceProxy(fqdn=fqdn, logger=self.logger) 
                for fqdn in self._fqdn_vcc
            ]
        if len(self._proxies_fsp) == 0:
            self._proxies_fsp = [
                CbfDeviceProxy(fqdn=fqdn, logger=self.logger)
                for fqdn in self._fqdn_fsp
            ]
        if len(self._proxies_fsp_corr_subarray) == 0:
            self._proxies_fsp_corr_subarray = [
                CbfDeviceProxy(fqdn=fqdn, logger=self.logger)
                for fqdn in self._fqdn_fsp_corr_subarray
            ]
        if len(self._proxies_fsp_pss_subarray) == 0:
            self._proxies_fsp_pss_subarray = [
                CbfDeviceProxy(fqdn=fqdn, logger=self.logger)
                for fqdn in self._fqdn_fsp_pss_subarray
            ]
        if len(self._proxies_fsp_pst_subarray) == 0:
            self._proxies_fsp_pst_subarray = [
                CbfDeviceProxy(fqdn=fqdn, logger=self.logger)
                for fqdn in self._fqdn_fsp_pst_subarray
            ]
        
        if self._group_vcc is None:
            self._group_vcc = CbfGroupProxy(name="VCC", logger=self.logger)
        if self._group_fsp is None:
            self._group_fsp = CbfGroupProxy(name="FSP",logger=self.logger)
        if self._group_fsp_corr_subarray is None:
            self._group_fsp_corr_subarray = CbfGroupProxy(
                name="FSP Subarray Corr", logger=self.logger)
        if self._group_fsp_pss_subarray is None:
            self._group_fsp_pss_subarray = CbfGroupProxy(
                name="FSP Subarray Pss", logger=self.logger)
        if self._group_fsp_pst_subarray is None:
            self._group_fsp_pst_subarray = CbfGroupProxy(
                name="FSP Subarray Pst", logger=self.logger)
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        """hook to delete device. Set State to DISABLE, romove all receptors, go to OBsState IDLE"""

        pass
        # PROTECTED REGION END #    //  CbfSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_frequencyBand(self: CbfSubarray) -> int:
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_read) ENABLED START #
        """
        Return frequency band assigned to this subarray. 
        One of ["1", "2", "3", "4", "5a", "5b", ]

        :return: the frequency band
        :rtype: int
        """
        return self._frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def read_configID(self: CbfSubarray) -> str:
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """
        Return attribute configID
        
        :return: the configuration ID
        :rtype: str
        """
        return self._config_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def read_scanID(self: CbfSubarray) -> int:
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """
        Return attribute scanID
        
        :return: the scan ID
        :rtype: int
        """
        return self._scan_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def read_receptors(self: CbfSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        """
        Return list of receptors assgined to subarray
        
        :return: the list of receptors
        :rtype: List[int]
        """
        return self._receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read

    def write_receptors(self: CbfSubarray, value: List[int]) -> None:
        # PROTECTED REGION ID(CbfSubarray.receptors_write) ENABLED START #
        """
        Set receptors of this array to the input value. 
        Input should be an array of int
        
        :param value: the list of receptors
        """
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  CbfSubarray.receptors_write


    def read_vccState(self: CbfSubarray) -> Dict[str, DevState]:
        # PROTECTED REGION ID(CbfSubarray.vccState_read) ENABLED START #
        """
        Return the attribute vccState: array of DevState
        
        :return: the list of VCC states
        :rtype: Dict[str, DevState]
        """
        return list(self._vcc_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccState_read

    def read_vccHealthState(self: CbfSubarray) -> Dict[str, HealthState]:
        # PROTECTED REGION ID(CbfSubarray.vccHealthState_read) ENABLED START #
        """
        returns vccHealthState attribute: an array of unsigned short
        
        :return: the list of VCC health states
        :rtype: Dict[str, HealthState]
        """
        return list(self._vcc_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccHealthState_read

    def read_fspState(self: CbfSubarray) -> Dict[str, DevState]:
        # PROTECTED REGION ID(CbfSubarray.fspState_read) ENABLED START #
        """
        Return the attribute fspState: array of DevState
        
        :return: the list of FSP states
        :rtype: Dict[str, DevState]
        """
        return list(self._fsp_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspState_read

    def read_fspHealthState(self: CbfSubarray) -> Dict[str, HealthState]:
        # PROTECTED REGION ID(CbfSubarray.fspHealthState_read) ENABLED START #
        """
        returns fspHealthState attribute: an array of unsigned short
        
        :return: the list of FSP health states
        :rtype: Dict[str, HealthState]
        """
        return list(self._fsp_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspHealthState_read

    def read_fspList(self: CbfSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(CbfSubarray.fspList_read) ENABLED START #
        """
        return fspList attribute 
        2 dimentional array the fsp used by all the subarrays
        
        :return: the array of FSP IDs
        :rtype: List[List[int]]
        """
        return self._fsp_list
        # PROTECTED REGION END #    //  CbfSubarray.fspList_read

    def read_latestScanConfig(self: CbfSubarray) -> str:
        # PROTECTED REGION ID(CbfSubarray.latestScanConfig_read) ENABLED START #
        """
        Return the latestScanConfig attribute.
        
        :return: the latest scan configuration string
        :rtype: str
        """
        return self._latest_scan_config
        # PROTECTED REGION END #    //  CbfSubarray.latestScanConfig_read

    # --------
    # Commands
    # --------

    # class OnCommand(SKASubarray.OnCommand):
    #     """
    #     A class for the SKASubarray's On() command.
    #     """
    #     def do(self):
    #         """
    #         Stateless hook for On() command functionality.

    #         :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #         :rtype: (ResultCode, str)
    #         """
    #         return super().do()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the SKASubarray's Off() command.
        """
        def do(self: CbfSubarray.OffCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message) = super().do()
            device = self.target
            self.logger.info(f"Subarray ObsState is {device._obs_state}")

            return (result_code, message)


    ##################  Receptors Related Commands  ###################

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    def RemoveReceptors(
        self: CbfSubarray,
        argin: List[int]
    ) -> Tuple[ResultCode, str]:
        """
        Remove from list of receptors. Turn Subarray to ObsState = EMPTY if no receptors assigned.
        Uses RemoveReceptorsCommand class.

        :param argin: list of receptor IDs to remove
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("RemoveReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class RemoveReceptorsCommand(SKASubarray.ReleaseResourcesCommand):
        """
        A class for CbfSubarray's RemoveReceptors() command.
        Equivalent to the ReleaseResourcesCommand in ADR-8.
        """
        def do(
            self: CbfSubarray.RemoveReceptorsCommand,
            argin: List[int]
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for RemoveReceptors() command functionality.

            :param argin: The receptors to be released
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            #(result_code,message) = super().do(argin)
            device = self.target

            device._remove_receptors_helper(argin)
            message = "CBFSubarray RemoveReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)


    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )

    @DebugIt()
    def RemoveAllReceptors(self: CbfSubarray) -> Tuple[ResultCode, str]:
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
        """
        Remove all receptors. Turn Subarray OFF if no receptors assigned

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        command = self.get_command_object("RemoveAllReceptors")
        (return_code, message) = command()
        return [[return_code], [message]]  
        # PROTECTED REGION END #    //  CbfSubarray.RemoveAllReceptors

    class RemoveAllReceptorsCommand(SKASubarray.ReleaseAllResourcesCommand):
        """
        A class for CbfSubarray's RemoveAllReceptors() command.
        """
        def do(
            self: CbfSubarray.RemoveAllReceptorsCommand
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for RemoveAllReceptors() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            # (result_code,message) = super().do()
            self.logger.debug("Entering RemoveAllReceptors()")

            device = self.target

            # TODO
            # For LMC0.6.0: use a helper instead of a command so that it doesn't care about the obsState
            device._remove_receptors_helper(device._receptors[:])

            message = "CBFSubarray RemoveAllReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )

    @DebugIt()
    def AddReceptors(
        self: CbfSubarray,
        argin: List[int]
    ) -> Tuple[ResultCode, str]:
        """
        Assign Receptors to this subarray. 
        Turn subarray to ObsState = IDLE if previously no receptor is assigned.

        :param argin: list of receptors to add
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("AddReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]  

    
    class AddReceptorsCommand(SKASubarray.AssignResourcesCommand):
        # NOTE: doesn't inherit SKASubarray._ResourcingCommand 
        # because will give error on len(self.target); TODO: to resolve
        """
        A class for CbfSubarray's AddReceptors() command.
        """
        def do(
            self: CbfSubarray.AddReceptorsCommand,
            argin: List[int]
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for AddReceptors() command functionality.

            :param argin: The receptors to be assigned
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            errs = []  # list of error messages

            receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                                device._proxy_cbf_controller.receptorToVcc)

            for receptorID in argin:
                try:
                    # check for invalid receptorID
                    #TODO replace hardcoded values?
                    if not 0 < receptorID < 198:
                        errs.append(f"Invalid receptor ID {receptorID}.")
                        raise KeyError

                    vccID = receptor_to_vcc[receptorID]
                    vccProxy = device._proxies_vcc[vccID - 1]

                    self.logger.debug(
                        "receptorID = {receptorID}, vccProxy.receptorID = "
                        f"{vccProxy.receptorID}"
                    )

                    # TODO - may not be needed?
                    # vccProxy.receptorID = receptorID

                    subarrayID = vccProxy.subarrayMembership

                    # only add receptor if it does not already belong to a 
                    # different subarray
                    if subarrayID not in [0, device._subarray_id]:
                        errs.append(
                            f"Receptor {receptorID} already in use by "
                            f"subarray {subarrayID}."
                        )
                    else:
                        if receptorID not in device._receptors:
                            # change subarray membership of vcc
                            vccProxy.subarrayMembership = device._subarray_id

                            # TODO: is this note still relevant? 
                            # Note:json does not recognize NumPy data types. 
                            # Convert the number to a Python int 
                            # before serializing the object.
                            # The list of receptors is serialized when the FSPs  
                            # are configured for a scan.

                            device._receptors.append(int(receptorID))
                            device._proxies_assigned_vcc.append(vccProxy)
                            device._group_vcc.add(device._fqdn_vcc[vccID - 1])

                            # subscribe to VCC state and healthState changes
                            event_id_state = vccProxy.add_change_event_callback(
                                "State",
                                device._state_change_event_callback
                            )
                            self.logger.debug(f"State event ID: {event_id_state}")

                            event_id_health_state = vccProxy.add_change_event_callback(
                                "healthState",
                                device._state_change_event_callback
                            )
                            self.logger.debug(
                                f"Health state event ID: {event_id_health_state}"
                            )

                            device._events_state_change_vcc[vccID] = [
                                event_id_state,
                                event_id_health_state
                            ]
                        else:
                            log_msg = (
                                f"Receptor {receptorID} already assigned to "
                                "current subarray."
                            )
                            self.logger.warn(log_msg)

                except KeyError:  # invalid receptor ID
                    errs.append(f"Invalid receptor ID: {receptorID}")

            if errs:
                msg = "\n".join(errs)
                self.logger.error(msg)
                
                return (ResultCode.FAILED, msg)

            message = "CBFSubarray AddReceptors command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)


    ############  Configure Related Commands   ##############

    class ConfigureScanCommand(SKASubarray.ConfigureCommand):
        """
        A class for CbfSubarray's ConfigureScan() command.
        """
        def do(
            self: CbfSubarray.ConfigureScanCommand,
            argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            device = self.target

            # Code here
            device._corr_config = []
            device._pss_config = []
            device._pst_config = []
            device._corr_fsp_list = []
            device._pss_fsp_list = []
            device._pst_fsp_list = []
            device._fsp_list = [[], [], [], []]

            # validate scan configuration first 
            try:
                device._validate_scan_configuration(argin)
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self.logger.warn("validate scan configuration error")
                # device._raise_configure_scan_fatal_error(msg)

            # Call this just to release all FSPs and unsubscribe to events.
            # Can't call GoToIdle, otherwise there will be state transition problem.
            # TODO - to clarify why can't call GoToIdle
            device._deconfigure()

            full_configuration = json.loads(argin)
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
            # set band5Tuning to [0,0] if not specified
            if "band_5_tuning" not in common_configuration: 
                common_configuration["band_5_tuning"] = [0,0]
            if "frequency_band_offset_stream_1" not in common_configuration: 
                configuration["frequency_band_offset_stream_1"] = 0
            if "frequency_band_offset_stream_2" not in common_configuration: 
                configuration["frequency_band_offset_stream_2"] = 0
            if "rfi_flagging_mask" not in configuration: 
                configuration["rfi_flagging_mask"] = {}

            # Configure configID.
            device._config_ID = str(common_configuration["config_id"])

            # Configure frequencyBand.
            frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
            device._frequency_band = frequency_bands.index(common_configuration["frequency_band"])

            data = tango.DeviceData()
            data.insert(tango.DevString, common_configuration["frequency_band"])
            device._group_vcc.command_inout("ConfigureBand", data)

            # Configure band5Tuning, if frequencyBand is 5a or 5b.
            if device._frequency_band in [4, 5]:
                stream_tuning = [*map(float, common_configuration["band_5_tuning"])]
                device._stream_tuning = stream_tuning

            # Configure frequencyBandOffsetStream1.
            if "frequency_band_offset_stream_1" in configuration:
                device._frequency_band_offset_stream_1 = int(configuration["frequency_band_offset_stream_1"])
            else:
                device._frequency_band_offset_stream_1 = 0
                log_msg = "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
                self.logger.warn(log_msg)

            # Validate frequencyBandOffsetStream2.
            # If not given, use a default value.
            # If malformed, use a default value, but append an error.
            if "frequency_band_offset_stream_2" in configuration:
                device._frequency_band_offset_stream_2 = int(configuration["frequency_band_offset_stream_2"])
            else:
                device._frequency_band_offset_stream_2 = 0
                log_msg = "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
                self.logger.warn(log_msg)

            config_dict = {
                "config_id": device._config_ID,
                "frequency_band": common_configuration["frequency_band"],
                "band_5_tuning": device._stream_tuning,
                "frequency_band_offset_stream_1": device._frequency_band_offset_stream_1,
                "frequency_band_offset_stream_2": device._frequency_band_offset_stream_2,
                "rfi_flagging_mask": configuration["rfi_flagging_mask"],
            }
            json_str = json.dumps(config_dict)
            data = tango.DeviceData()
            data.insert(tango.DevString, json_str)
            device._group_vcc.command_inout("ConfigureScan", data)

            # Configure dopplerPhaseCorrSubscriptionPoint.
            if "doppler_phase_corr_subscription_point" in configuration:
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["doppler_phase_corr_subscription_point"],
                    logger=device.logger
                )
                attribute_proxy.ping()
                event_id = attribute_proxy.add_change_event_callback(
                    device._doppler_phase_correction_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure delayModelSubscriptionPoint.
            if "delay_model_subscription_point" in configuration:
                device._last_received_delay_model = "{}"
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["delay_model_subscription_point"],
                    logger=device.logger
                )
                attribute_proxy.ping() #To be sure the connection is good(don't know if the device is running)
                event_id = attribute_proxy.add_change_event_callback(
                    device._delay_model_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure jonesMatrixSubscriptionPoint
            if "jones_matrix_subscription_point" in configuration:
                device._last_received_jones_matrix = "{}"
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["jones_matrix_subscription_point"],
                    logger=device.logger
                )
                attribute_proxy.ping()
                event_id = attribute_proxy.add_change_event_callback(
                    device._jones_matrix_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure beamWeightsSubscriptionPoint
            if "timing_beam_weights_subscription_point" in configuration:
                device._last_received_beam_weights= "{}"
                attribute_proxy = CbfAttributeProxy(
                    fqdn=configuration["timing_beam_weights_subscription_point"],
                    logger=device.logger
                )
                attribute_proxy.ping()
                event_id = attribute_proxy.add_change_event_callback(
                    device._beam_weights_event_callback
                )
                device._events_telstate[event_id] = attribute_proxy

            # Configure searchWindow.
            if "search_window" in configuration:
                for search_window in configuration["search_window"]:
                    search_window["frequency_band"] = common_configuration["frequency_band"]
                    search_window["frequency_band_offset_stream_1"] = \
                        device._frequency_band_offset_stream_1
                    search_window["frequency_band_offset_stream_2"] = \
                        device._frequency_band_offset_stream_2
                    if search_window["frequency_band"] in ["5a", "5b"]:
                        search_window["band_5_tuning"] = common_configuration["band_5_tuning"]
                    # pass on configuration to VCC
                    data = tango.DeviceData()
                    data.insert(tango.DevString, json.dumps(search_window))
                    device._group_vcc.command_inout("ConfigureSearchWindow", data)
            else:
                log_msg = "'searchWindow' not given."
                self.logger.warn(log_msg)

            # TODO: the entire vcc configuration should move to Vcc
            # for now, run ConfigScan only wih the following data, so that
            # the obsState are properly (implicitly) updated by the command
            # (And not manually by SetObservingState as before)

            ######## FSP #######
            # Configure FSP.
            for fsp in configuration["fsp"]:
                # Configure fspID.
                fspID = int(fsp["fsp_id"])
                proxy_fsp = device._proxies_fsp[fspID - 1]

                device._group_fsp.add(device._fqdn_fsp[fspID - 1])
                device._group_fsp_corr_subarray.add(device._fqdn_fsp_corr_subarray[fspID - 1])
                device._group_fsp_pss_subarray.add(device._fqdn_fsp_pss_subarray[fspID - 1])
                device._group_fsp_pst_subarray.add(device._fqdn_fsp_pst_subarray[fspID - 1])

                # change FSP subarray membership
                proxy_fsp.AddSubarrayMembership(device._subarray_id)

                # Configure functionMode.
                proxy_fsp.SetFunctionMode(fsp["function_mode"])

                # subscribe to FSP state and healthState changes
                event_id_state, event_id_health_state = proxy_fsp.add_change_event_callback(
                    "State",
                    device._state_change_event_callback
                ), proxy_fsp.add_change_event_callback(
                    "healthState",
                    device._state_change_event_callback
                )
                device._events_state_change_fsp[int(fsp["fsp_id"])] = [event_id_state,
                                                                    event_id_health_state]
                
                # Add configID to fsp. It is not included in the "FSP" portion in configScan JSON
                fsp["config_id"] = common_configuration["config_id"]
                fsp["frequency_band"] = common_configuration["frequency_band"]
                fsp["band_5_tuning"] = common_configuration["band_5_tuning"]
                fsp["frequency_band_offset_stream_1"] = device._frequency_band_offset_stream_1
                fsp["frequency_band_offset_stream_2"] = device._frequency_band_offset_stream_2

                if fsp["function_mode"] == "CORR":
                    if "receptor_ids" not in fsp:
                        # TODO In this case by the ICD, all subarray allocated resources should be used.
                        fsp["receptor_ids"] = [device._receptors[0]]
                    device._corr_config.append(fsp)
                    device._corr_fsp_list.append(fsp["fsp_id"])
                
                # TODO currently only CORR function mode is supported outside of Mid.CBF MCS
                elif fsp["function_mode"] == "PSS-BF":
                    for searchBeam in fsp["search_beam"]:
                        if "receptor_ids" not in searchBeam:
                            # In this case by the ICD, all subarray allocated resources should be used.
                            searchBeam["receptor_ids"] = device._receptors
                    device._pss_config.append(fsp)
                    device._pss_fsp_list.append(fsp["fsp_id"])
                elif fsp["function_mode"] == "PST-BF":
                    for timingBeam in fsp["timing_beam"]:
                        if "receptor_ids" not in timingBeam:
                            # In this case by the ICD, all subarray allocated resources should be used.
                            timingBeam["receptor_ids"] = device._receptors
                    device._pst_config.append(fsp)
                    device._pst_fsp_list.append(fsp["fsp_id"])

            # Call ConfigureScan for all FSP Subarray devices (CORR/PSS/PST)

            # NOTE:_corr_config is a list of fsp config JSON objects, each 
            #      augmented by a number of vcc-fsp common parameters 
            #      created by the function _validate_scan_configuration()
            if len(device._corr_config) != 0: 
                #device._proxy_corr_config.ConfigureFSP(json.dumps(device._corr_config))
                # Michelle - WIP - TODO - this is to replace the call to 
                #  _proxy_corr_config.ConfigureFSP()
                for this_fsp in device._corr_config:
                    try:                      
                        this_proxy = device._proxies_fsp_corr_subarray[int(this_fsp["fsp_id"])-1]
                        this_proxy.ConfigureScan(json.dumps(this_fsp))
                    except tango.DevFailed:
                        msg = "An exception occurred while configuring " \
                        "FspCorrSubarray; Aborting configuration"
                        device._raise_configure_scan_fatal_error(msg)

            # NOTE: _pss_config is costructed similarly to _corr_config
            if len(device._pss_config) != 0:
                for this_fsp in device._pss_config:
                    try:
                        this_proxy = device._proxies_fsp_pss_subarray[int(this_fsp["fsp_id"])-1]
                        this_proxy.ConfigureScan(json.dumps(this_fsp))
                    except tango.DevFailed:
                        msg = "An exception occurred while configuring  " \
                        "FspPssSubarray; Aborting configuration"
                        device._raise_configure_scan_fatal_error(msg)

            # NOTE: _pst_config is costructed similarly to _corr_config
            if len(device._pst_config) != 0:
                for this_fsp in device._pst_config:
                    try:
                        this_proxy = device._proxies_fsp_pst_subarray[int(this_fsp["fsp_id"])-1]
                        this_proxy.ConfigureScan(json.dumps(this_fsp))
                    except tango.DevFailed:
                        msg = "An exception occurred while configuring  " \
                        "FspPstSubarray; Aborting configuration"
                        device._raise_configure_scan_fatal_error(msg)

            # TODO add VLBI to this once they are implemented
            # what are these for?
            device._fsp_list[0].append(device._corr_fsp_list)
            device._fsp_list[1].append(device._pss_fsp_list)
            device._fsp_list[2].append(device._pst_fsp_list)

            #save configuration into latestScanConfig
            device._latest_scan_config = str(configuration)
            message = "CBFSubarray Configure command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    @command(
        dtype_in='str',
        doc_in="Scan configuration",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )

    @DebugIt()
    def ConfigureScan(self: CbfSubarray, argin: str) -> Tuple[ResultCode, str]:
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
        # """
        """Change state to CONFIGURING.
        Configure attributes from input JSON. Subscribe events. Configure VCC, VCC subarray, FSP, FSP Subarray. 
        publish output links.

        :param argin: The configuration as JSON formatted string.
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]    

    class ScanCommand(SKASubarray.ScanCommand):
        """
        A class for CbfSubarray's Scan() command.
        """
        def do(
            self: CbfSubarray.ScanCommand,
            argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :param argin: The scan ID as JSON formatted string.
            :type argin: str
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            # overwrites the do hook

            device = self.target

            scan = json.loads(argin)

            device._scan_ID = int(scan["scan_id"])

            data = tango.DeviceData()
            data.insert(tango.DevString, str(device._scan_ID))
            device._group_vcc.command_inout("Scan", data)

            device._group_fsp_corr_subarray.command_inout("Scan", data)
            device._group_fsp_pss_subarray.command_inout("Scan", data)
            device._group_fsp_pst_subarray.command_inout("Scan", data)

            # return message
            message = "Scan command successful"
            self.logger.info(message)
            return (ResultCode.STARTED, message)


    class EndScanCommand(SKASubarray.EndScanCommand):
        """
        A class for CbfSubarray's EndScan() command.
        """
        def do(self: CbfSubarray.EndScanCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for EndScan() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message)=super().do()
            device=self.target

            # EndScan for all subordinate devices:
            device._group_vcc.command_inout("EndScan")
            device._group_fsp_corr_subarray.command_inout("EndScan")
            device._group_fsp_pss_subarray.command_inout("EndScan")
            device._group_fsp_pst_subarray.command_inout("EndScan")

            device._scan_ID = 0

            message = "EndScan command OK"
            self.logger.info(message)
            return (ResultCode.OK, message)


    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )
    def GoToIdle(self: CbfSubarray) -> Tuple[ResultCode, str]:
        """
        deconfigure a scan, set ObsState to IDLE

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        
        command = self.get_command_object("GoToIdle")
        (return_code, message) = command()
        return [[return_code], [message]]

    class GoToIdleCommand(SKASubarray.EndCommand):
        """
        A class for SKASubarray's GoToIdle() command.
        """
        def do(self: CbfSubarray.GoToIdleCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for GoToIdle() command functionality.
            
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")
            
            device=self.target
            device._deconfigure()

            message = "GoToIdle command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    ############### abort, restart and reset #####################

    class AbortCommand(SKASubarray.AbortCommand):
        """
        A class for SKASubarray's Abort() command.
        """
        def do(self: CbfSubarray.AbortCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Abort() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            # if aborted from SCANNING, end VCC and FSP Subarray scans
            if device._scan_ID != 0:
                self.logger.info("Aborting from scanning")
                device._group_vcc.command_inout("EndScan")
                device._group_fsp_corr_subarray.command_inout("EndScan")
                device._group_fsp_pss_subarray.command_inout("EndScan")
                device._group_fsp_pst_subarray.command_inout("EndScan")
            
            (result_code,message)=super().do()
            
            return (result_code,message)

    
    # RestartCommand already registered in SKASubarray, so no "def restart" needed
    class RestartCommand(SKASubarray.RestartCommand):
        """
        A class for CbfSubarray's Restart() command.
        """
        def do(self: CbfSubarray.RestartCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Restart() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            # We might have interrupted a long-running command such as a Configure
            # or a Scan, so we need to clean up from that.

            # Now totally deconfigure
            device._deconfigure()

            # and release all receptors
            device._remove_receptors_helper(device._receptors[:])

            message = "Restart command completed OK"
            self.logger.info(message)
            return (ResultCode.OK,message)


    class ObsResetCommand(SKASubarray.ObsResetCommand):
        """
        A class for CbfSubarray's ObsReset() command.
        """
        def do(self: CbfSubarray.ObsResetCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ObsReset() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            # We might have interrupted a long-running command such as a Configure
            # or a Scan, so we need to clean up from that.

            # totally deconfigure
            device._deconfigure()

            message = "ObsReset command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)





# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == '__main__':
    main()