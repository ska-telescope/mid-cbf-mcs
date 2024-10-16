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
from typing import Callable, Optional

# tango imports
import tango
from ska_control_model import (
    CommunicationStatus,
    ObsState,
    PowerState,
    ResultCode,
    TaskStatus,
)
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_mid_cbf_mcs.component.obs_component_manager import (
    CbfObsComponentManager,
)
from ska_mid_cbf_mcs.vcc.vcc_band_simulator import VccBandSimulator
from ska_mid_cbf_mcs.vcc.vcc_controller_simulator import VccControllerSimulator

__all__ = ["VccComponentManager"]

VCC_PARAM_PATH = "mnt/vcc_param/"


class VccComponentManager(CbfObsComponentManager):
    """
    Component manager for Vcc class.
    """

    def __init__(
        self: VccComponentManager,
        *args: any,
        talon_lru: str,
        vcc_controller: str,
        vcc_band: list[str],
        **kwargs: any,
    ) -> None:
        """
        Initialize a new instance.

        :param talon_lru: FQDN of the TalonLRU device
        :param vcc_controller: FQDN of the HPS VCC controller device
        :param vcc_band: FQDNs of HPS VCC band devices
        """
        super().__init__(*args, **kwargs)

        self._talon_lru_fqdn = talon_lru
        self._vcc_controller_fqdn = vcc_controller
        self._vcc_band_fqdn = vcc_band

        # --- Attribute Values --- #
        self.dish_id = ""

        self.scan_id = 0
        self.config_id = ""

        self.frequency_band = 0
        self._freq_band_name = ""

        # Initialize list of band proxies and band -> index translation;
        # entry for each of: band 1 & 2, band 3, band 4, band 5
        self._band_proxies = []
        self._freq_band_index = dict(
            zip(freq_band_dict().keys(), [0, 0, 1, 2, 3, 3])
        )

        self._vcc_controller_proxy = None

        # --- Simulators --- #
        self._band_simulators = [
            VccBandSimulator(vcc_band[0]),
            VccBandSimulator(vcc_band[1]),
            VccBandSimulator(vcc_band[2]),
            VccBandSimulator(vcc_band[3]),
        ]
        self._vcc_controller_simulator = VccControllerSimulator(
            vcc_controller,
            self._band_simulators[0],
            self._band_simulators[1],
            self._band_simulators[2],
            self._band_simulators[3],
        )

    # -------------
    # Communication
    # -------------

    def _start_communicating(
        self: VccComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if not self.simulation_mode:
            self.logger.info(
                "Connecting to HPS VCC controller and band devices"
            )
            try:
                self._vcc_controller_proxy = context.DeviceProxy(
                    device_name=self._vcc_controller_fqdn
                )
                self._band_proxies = [
                    context.DeviceProxy(device_name=fqdn)
                    for fqdn in self._vcc_band_fqdn
                ]
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return (
                    ResultCode.FAILED,
                    "Failed to establish proxies to HPS VCC devices.",
                )

        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    # --------------
    # Helper Methods
    # --------------

    def _deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self.frequency_band = 0
        self.device_attr_change_callback("frequencyBand", self.frequency_band)
        self.device_attr_archive_callback("frequencyBand", self.frequency_band)
        self._freq_band_name = ""
        self.config_id = ""
        self.scan_id = 0

    def _load_internal_params(
        self: VccComponentManager,
        freq_band_name: str,
        dish_sample_rate: int,
        samples_per_frame: int,
    ) -> str:
        """
        Helper for loading VCC internal parameter file.

        :param freq_band_name: the name of the configured frequency band
        :param dish_sample rate: the configured DISH sample rate
        :param samples_per_frame: the configured samples per frame
        :return: JSON string with internal parameters, or empty string if file not found
        """
        self.logger.info(
            f"Configuring internal parameters for VCC band {freq_band_name}"
        )

        internal_params_file_name = f"{VCC_PARAM_PATH}internal_params_receptor{self.dish_id}_band{freq_band_name}.json"
        self.logger.debug(
            f"Using parameters stored in {internal_params_file_name}"
        )
        try:
            with open(internal_params_file_name, "r") as f:
                json_string = f.read()
        except FileNotFoundError:
            self.logger.info(
                f"Could not find internal parameters file for receptor {self.dish_id}, band {freq_band_name}; using default."
            )
            try:
                with open(
                    f"{VCC_PARAM_PATH}internal_params_default.json", "r"
                ) as f:
                    json_string = f.read()
            except FileNotFoundError:
                self.logger.error(
                    "Could not find default internal parameters file."
                )
                return ""

        self.logger.debug(f"VCC internal parameters: {json_string}")

        # add dish_sample_rate and samples_per_frame to internal params json
        args = json.loads(json_string)
        args.update({"dish_sample_rate": dish_sample_rate})
        args.update({"samples_per_frame": samples_per_frame})
        json_string = json.dumps(args)
        return json_string

    # -------------
    # Fast Commands
    # -------------

    # None at this time

    # ---------------------
    # Long Running Commands
    # ---------------------

    def is_configure_band_allowed(self: VccComponentManager) -> bool:
        """
        Check if ConfigureBand is allowed.

        :return: True if ConfigureBand is allowed, False otherwise
        """
        self.logger.debug("Checking if VCC ConfigureBand is allowed.")
        if self.obs_state not in [ObsState.IDLE, ObsState.READY]:
            self.logger.warning(
                f"VCC ConfigureBand not allowed in ObsState {self.obs_state}; \
                    must be in ObsState.IDLE or READY"
            )
            return False
        return True

    def _configure_band(
        self: VccComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Configure VCC band-specific devices

        :param argin: JSON string with the configure band parameters

        :return: None
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ConfigureBand", task_callback, task_abort_event
        ):
            return

        band_config = json.loads(argin)
        freq_band_name = band_config["frequency_band"]

        # Configure the band via the VCC Controller device
        self.logger.info(f"Configuring VCC band {freq_band_name}")
        try:
            frequency_band = freq_band_dict()[freq_band_name]["band_index"]

        except KeyError as ke:
            self.logger.error(str(ke))
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    f"frequency_band {freq_band_name} is invalid.",
                ),
            )
            return

        if self.simulation_mode:
            self._vcc_controller_simulator.ConfigureBand(frequency_band)
        else:
            try:
                self._vcc_controller_proxy.ConfigureBand(frequency_band)

            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue ConfigureBand command to HPS VCC controller.",
                    ),
                )
                return

        # Set internal params for the configured band
        json_string = self._load_internal_params(
            freq_band_name=freq_band_name,
            dish_sample_rate=band_config["dish_sample_rate"],
            samples_per_frame=band_config["samples_per_frame"],
        )
        if not json_string:
            self._update_component_state(fault=True)
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Missing default internal parameters file.",
                ),
            )
            return

        fb_index = self._freq_band_index[freq_band_name]

        if self.simulation_mode:
            self._band_simulators[fb_index].SetInternalParameters(json_string)
        else:
            self._band_proxies[fb_index].SetInternalParameters(json_string)

        self._freq_band_name = freq_band_name

        self.frequency_band = frequency_band
        self.device_attr_change_callback("frequencyBand", self.frequency_band)
        self.device_attr_archive_callback("frequencyBand", self.frequency_band)

        task_callback(
            result=(ResultCode.OK, "ConfigureBand completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def configure_band(
        self: VccComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Configure the corresponding band. At the HPS level, this reconfigures the
        FPGA to the correct bitstream and enables the respective band device. All
        other band devices are disabled.

        :param argin: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            self._configure_band,
            args=[argin],
            is_cmd_allowed=self.is_configure_band_allowed,
            task_callback=task_callback,
        )

    # def _update_expected_dish_id(
    #     self: VccComponentManager,
    # ) -> tuple[bool, str]:
    #     """
    #     Update HPS WIB's ExpectedDishID with this VCC's dish_id attr.

    #     :return: A tuple indicating if the update was successful, and an error message if not.
    #     """
    #     try:
    #         # Get WIB FQDN, then proxy.
    #         wib_fqdn = self._band_proxies[0].get_property(
    #             "WidebandInputBufferFQDN"
    #         )["WidebandInputBufferFQDN"][0]
    #         wib_proxy = context.DeviceProxy(device_name=wib_fqdn)

    #         # Get property, then update with vcc_proxy.dishID.
    #         old_expDishID = wib_proxy.ExpectedDishID
    #         wib_proxy.ExpectedDishID = self.dish_id
    #         self.logger.debug(
    #             f"Updated ExpectedDishID from [{old_expDishID}] to [{wib_proxy.ExpectedDishID}]"
    #         )
    #     except tango.DevFailed as df:
    #         msg = f"Failed to update ExpectedDishID device property of {wib_fqdn}; {df}"
    #         self.logger.error(msg)
    #         self._update_communication_state(
    #             communication_state=CommunicationStatus.NOT_ESTABLISHED
    #         )
    #         return False, msg
    #     return True, ""

    def _configure_scan(
        self: VccComponentManager,
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

        # # Update ExpectedDishID property of HPS WIB (only Band 1/2 for AA0.5)
        # if not self.simulation_mode:
        #     updated, msg = self._update_expected_dish_id()
        #     if not updated:
        #         task_callback(
        #             status=TaskStatus.FAILED,
        #             result=(
        #                 ResultCode.FAILED,
        #                 msg,
        #             ),
        #         )
        #         return

        configuration = json.loads(argin)
        self.config_id = configuration["config_id"]

        # Add expected_dish_id to HPS configuration arg
        configuration["expected_dish_id"] = self.dish_id

        # TODO: The frequency band attribute is optional but
        # if not specified the previous frequency band set should be used
        # (see Mid.CBF Scan Configuration in ICD). Therefore, the previous frequency
        # band value needs to be stored, and if the frequency band is not
        # set in the config it should be replaced with the previous value.
        freq_band = freq_band_dict()[configuration["frequency_band"]][
            "band_index"
        ]
        if self.frequency_band != freq_band:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    f"Error in ConfigureScan; scan configuration frequency band {freq_band} "
                    + f"not the same as enabled band device {self.frequency_band}",
                ),
            )
            return

        # Send the ConfigureScan command to the HPS
        fb_index = self._freq_band_index[self._freq_band_name]

        if self.simulation_mode:
            self._band_simulators[fb_index].ConfigureScan(
                json.dumps(configuration)
            )
        else:
            try:
                self._band_proxies[fb_index].ConfigureScan(
                    json.dumps(configuration)
                )
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        f"Failed to issue ConfigureScan command to HPS VCC band {fb_index} device.",
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
        self: VccComponentManager,
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

        # Send the Scan command to the HPS
        fb_index = self._freq_band_index[self._freq_band_name]
        if self.simulation_mode:
            self._band_simulators[fb_index].Scan(self.scan_id)
        else:
            try:
                self._band_proxies[fb_index].Scan(self.scan_id)
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        f"Failed to issue Scan command to HPS VCC band {fb_index} device.",
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
        self: VccComponentManager,
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

        # Send the EndScan command to the HPS
        fb_index = self._freq_band_index[self._freq_band_name]

        if self.simulation_mode:
            self._band_simulators[fb_index].EndScan()
        else:
            try:
                self._band_proxies[fb_index].EndScan()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        f"Failed to issue EndScan command to HPS VCC band {fb_index} device.",
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
        self: VccComponentManager,
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

        if self.simulation_mode:
            self._vcc_controller_simulator.Unconfigure()
        else:
            try:
                pass
                # TODO CIP-1850
                # self._vcc_controller_proxy.Unconfigure()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Unconfigure command to HPS VCC controller device.",
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
        self: VccComponentManager,
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

        if self._freq_band_name != "":
            fb_index = self._freq_band_index[self._freq_band_name]

            if self.simulation_mode:
                self._band_simulators[fb_index].Abort()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._band_proxies[fb_index].Abort()
                except tango.DevFailed as df:
                    self.logger.error(f"{df}")
                    self._update_communication_state(
                        communication_state=CommunicationStatus.NOT_ESTABLISHED
                    )
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            ResultCode.FAILED,
                            f"Failed to issue Abort command to HPS VCC band {fb_index} device.",
                        ),
                    )
                    return
        else:
            # if no value for _freq_band_name, assume in IDLE state,
            # either from initialization or after deconfigure has been called
            self.logger.info(
                "Aborting from IDLE; not issuing Abort command to VCC band devices"
            )

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "Abort completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _obs_reset(
        self: VccComponentManager,
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

        if self._freq_band_name != "":
            fb_index = self._freq_band_index[self._freq_band_name]

            if self.simulation_mode:
                self._band_simulators[fb_index].ObsReset()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._band_proxies[fb_index].ObsReset()
                except tango.DevFailed as df:
                    self.logger.error(f"{df}")
                    self._update_communication_state(
                        communication_state=CommunicationStatus.NOT_ESTABLISHED
                    )
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            ResultCode.FAILED,
                            f"Failed to issue ObsReset to HPS VCC band {fb_index} device.",
                        ),
                    )
                    return
        else:
            # if no value for _freq_band_name, assume in IDLE state,
            # either from initialization or after deconfigure has been called
            self.logger.info(
                "Aborted from IDLE; not issuing ObsReset command to VCC band devices"
            )

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
