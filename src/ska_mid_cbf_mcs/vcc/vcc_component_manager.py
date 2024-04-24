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
VccComponentManager
Sub-element VCC component manager for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

import json
import threading
from typing import Any, Callable, Optional

# tango imports
import tango
from ska_control_model import (
    CommunicationStatus,
    ObsState,
    PowerState,
    SimulationMode,
    TaskStatus,
)
from ska_tango_base.commands import ResultCode
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
    """Component manager for Vcc class."""

    @property
    def dish_id(self: VccComponentManager) -> str:
        """
        DISH ID

        :return: the DISH ID
        """
        return self._dish_id

    @dish_id.setter
    def dish_id(self: VccComponentManager, dish_id: str) -> None:
        """
        Set the DISH ID.

        :param dish_id: DISH ID
        """
        self._dish_id = dish_id

    @property
    def frequency_band(self: VccComponentManager) -> int:
        """
        Frequency Band

        :return: the frequency band as the integer index in an array
                of frequency band labels: ["1", "2", "3", "4", "5a", "5b"]
        """
        return self._frequency_band

    def __init__(
        self: VccComponentManager,
        *args: Any,
        vcc_id: int,
        talon_lru: str,
        vcc_controller: str,
        vcc_band: list[str],
        search_window: list[str],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a new instance.

        :param vcc_id: integer ID of this VCC
        :param talon_lru: FQDN of the TalonLRU device
        :param vcc_controller: FQDN of the HPS VCC controller device
        :param vcc_band: FQDNs of HPS VCC band devices
        :param search_window: FQDNs of VCC search windows
        :param simulation_mode: simulation mode identifies if the real VCC HPS
            applications or the simulator should be connected
        """
        super().__init__(*args, **kwargs)

        self.simulation_mode = simulation_mode

        self._vcc_id = vcc_id
        self._talon_lru_fqdn = talon_lru
        self._vcc_controller_fqdn = vcc_controller
        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        # Initialize attribute values
        self._dish_id = ""

        self._scan_id = 0
        self._config_id = ""

        self._frequency_band = 0
        self._freq_band_name = ""

        # Initialize list of band proxies and band -> index translation;
        # entry for each of: band 1 & 2, band 3, band 4, band 5
        self._band_proxies = []
        self._freq_band_index = dict(
            zip(freq_band_dict().keys(), [0, 0, 1, 2, 3, 3])
        )

        self._talon_lru_proxy = None
        self._vcc_controller_proxy = None

        # Create simulators
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

    def start_communicating(self: VccComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        try:
            self._talon_lru_proxy = context.DeviceProxy(
                device_name=self._talon_lru_fqdn
            )
        except tango.DevFailed:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            self.logger.error("Error in proxy connection")
            return

        super().start_communicating()
        self._update_component_state(power=self._get_power_mode())

    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
        self._update_component_state(power=PowerState.UNKNOWN)
        super().stop_communicating()

    def _get_power_mode(self: VccComponentManager) -> PowerState:
        """
        Get the power mode of this VCC based on the current power
        mode of the LRU this VCC belongs to.

        :return: VCC power mode
        """
        try:
            return self._talon_lru_proxy.LRUPowerState
        except tango.DevFailed:
            self.logger.error("Could not connect to Talon LRU device")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return PowerState.UNKNOWN

    def on(self: VccComponentManager) -> tuple[ResultCode, str]:
        """
        Turn on VCC component. This attempts to establish communication
        with the VCC devices on the HPS.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)

        :raise ConnectionError: if unable to connect to HPS VCC devices
        """
        self.logger.info("Entering VccComponentManager.on")
        try:
            # Try to connect to HPS devices, which are deployed during the
            # CbfController OnCommand sequence
            if not self.simulation_mode:
                self.logger.info(
                    "Connecting to HPS VCC controller and band devices"
                )

                self._vcc_controller_proxy = context.DeviceProxy(
                    device_name=self._vcc_controller_fqdn
                )

                self._band_proxies = [
                    context.DeviceProxy(device_name=fqdn)
                    for fqdn in self._vcc_band_fqdn
                ]

        except tango.DevFailed as df:
            self.logger.error(str(df.args[0].desc))
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return (ResultCode.FAILED, "Failed to connect to HPS VCC devices")

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On command completed OK")

    def off(self: VccComponentManager) -> tuple[ResultCode, str]:
        """
        Turn off VCC component; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off command completed OK")

    def _deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self._frequency_band = 0
        self._device_attr_change_callback(
            "frequencyBand", self._frequency_band
        )
        self._device_attr_archive_callback(
            "frequencyBand", self._frequency_band
        )
        self._freq_band_name = ""
        self._config_id = ""
        self._scan_id = 0

    def is_configure_band_allowed(self: VccComponentManager) -> bool:
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
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Configure VCC band-specific devices

        :param argin: JSON string with the configure band parameters

        :return: None
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        # TODO CIP-2380
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc.ConfigureBand command aborted by task executor Abort Event.",
                ),
            )
            return

        band_config = json.loads(argin)
        freq_band_name = band_config["frequency_band"]

        # Configure the band via the VCC Controller device
        self.logger.info(f"Configuring VCC band {freq_band_name}")
        frequency_band = freq_band_dict()[freq_band_name]["band_index"]

        self.logger.info(f"simulation mode: {self.simulation_mode}")

        if self.simulation_mode:
            self._vcc_controller_simulator.ConfigureBand(frequency_band)
        else:
            try:
                self._vcc_controller_proxy.ConfigureBand(frequency_band)

            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to connect to HPS VCC devices.",
                    ),
                )
                return

        # Set internal params for the configured band
        self.logger.info(
            f"Configuring internal parameters for VCC band {freq_band_name}"
        )

        internal_params_file_name = f"{VCC_PARAM_PATH}internal_params_receptor{self._dish_id}_band{freq_band_name}.json"
        self.logger.debug(
            f"Using parameters stored in {internal_params_file_name}"
        )
        try:
            with open(internal_params_file_name, "r") as f:
                json_string = f.read()
        except FileNotFoundError:
            self.logger.info(
                f"Could not find internal parameters file for receptor {self._dish_id}, band {freq_band_name}; using default."
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
                self._update_component_state(fault=True)
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Missing default internal parameters file.",
                    ),
                )
                return

        self.logger.info(f"VCC internal parameters: {json_string}")

        args = json.loads(json_string)
        args.update({"dish_sample_rate": band_config["dish_sample_rate"]})
        args.update({"samples_per_frame": band_config["samples_per_frame"]})
        json_string = json.dumps(args)

        idx = self._freq_band_index[freq_band_name]

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc ConfigureBand command aborted by task executor Abort Event.",
                ),
            )
            return

        if self.simulation_mode:
            self._band_simulators[idx].SetInternalParameters(json_string)
        else:
            self._band_proxies[idx].SetInternalParameters(json_string)

        self._freq_band_name = freq_band_name

        self._frequency_band = frequency_band
        self._device_attr_change_callback(
            "frequencyBand", self._frequency_band
        )
        self._device_attr_archive_callback(
            "frequencyBand", self._frequency_band
        )

        task_callback(
            result=(ResultCode.OK, "ConfigureBand completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return

    def configure_band(
        self: VccComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
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

    def _configure_scan(
        self: VccComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Execute configure scan operation.

        :param argin: JSON string with the configure scan parameters

        :return: None
        """

        task_callback(status=TaskStatus.IN_PROGRESS)

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc.ConfigureScan command aborted by task executor Abort Event.",
                ),
            )
            return

        configuration = json.loads(argin)
        self._config_id = configuration["config_id"]

        # TODO: The frequency band attribute is optional but
        # if not specified the previous frequency band set should be used
        # (see Mid.CBF Scan Configuration in ICD). Therefore, the previous frequency
        # band value needs to be stored, and if the frequency band is not
        # set in the config it should be replaced with the previous value.
        freq_band = freq_band_dict()[configuration["frequency_band"]][
            "band_index"
        ]
        if self._frequency_band != freq_band:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    f"Error in Vcc.ConfigureScan; scan configuration frequency band {freq_band} "
                    + f"not the same as enabled band device {self._frequency_band}",
                ),
            )
            return

        if "rfi_flagging_mask" not in configuration:
            self.logger.warning("'rfiFlaggingMask' not given. Proceeding.")

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc.ConfigureScan command aborted by task executor Abort Event.",
                ),
            )
            return

        # Send the ConfigureScan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self.simulation_mode:
            self._band_simulators[idx].ConfigureScan(argin)
        else:
            try:
                self._band_proxies[idx].ConfigureScan(argin)
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self._update_component_state(fault=True)
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to connect to HPS VCC devices.",
                    ),
                )
                return

        # Update obsState callback
        self._update_component_state(configured=True)

        task_callback(
            result=(ResultCode.OK, "ConfigureScan completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return

    def _scan(
        self: VccComponentManager,
        argin: int,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Begin scan operation.

        :param argin: scan ID integer

        :return: None
        """

        task_callback(status=TaskStatus.IN_PROGRESS)

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc Scan command aborted by task executor Abort Event.",
                ),
            )
            return

        self._scan_id = argin

        # Send the Scan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self.simulation_mode:
            self._band_simulators[idx].Scan(self._scan_id)
        else:
            try:
                self._band_proxies[idx].Scan(self._scan_id)
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self._update_component_state(fault=True)
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to connect to HPS VCC devices.",
                    ),
                )
                return

        # Update obsState callback
        self._update_component_state(scanning=True)

        task_callback(
            result=(ResultCode.OK, "Scan completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return

    def _end_scan(
        self: VccComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        End scan operation.

        :return: None
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc EndScan command aborted by task executor Abort Event.",
                ),
            )
            return

        # Send the EndScan command to the HPS
        idx = self._freq_band_index[self._freq_band_name]
        if self.simulation_mode:
            self._band_simulators[idx].EndScan()
        else:
            try:
                self._band_proxies[idx].EndScan()
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to connect to HPS VCC band devices.",
                    ),
                )
                return

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "EndScan completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return

    def _go_to_idle(
        self: VccComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :return: None
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc GoToIdle command aborted by task executor Abort Event.",
                ),
            )
            return

        if self.simulation_mode:
            self._vcc_controller_simulator.Unconfigure()
        else:
            try:
                pass
                # TODO CIP-1850
                # self._vcc_controller_proxy.Unconfigure()
            except tango.DevFailed as df:
                self.logger.error(str(df.args[0].desc))
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to connect to HPS VCC band devices.",
                    ),
                )
                return

        self._deconfigure()

        # Update obsState callback
        self._update_component_state(configured=False)

        task_callback(
            result=(ResultCode.OK, "GoToIdle completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return

    def _abort_scan(
        self: VccComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Abort the current scan operation.

        :return: None
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc AbortScan command aborted by task executor Abort Event.",
                ),
            )
            return

        if self._freq_band_name != "":
            idx = self._freq_band_index[self._freq_band_name]
            if self.simulation_mode:
                self._band_simulators[idx].Abort()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._vcc_controller_proxy.Unconfigure()
                    # self._band_proxies[idx].Abort()
                except tango.DevFailed as df:
                    self.logger.error(str(df.args[0].desc))
                    self._update_communication_state(
                        communication_state=CommunicationStatus.NOT_ESTABLISHED
                    )
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            ResultCode.FAILED,
                            "Failed to connect to HPS VCC band devices.",
                        ),
                    )
                    return
        else:
            # if no value for _freq_band_name, assume in IDLE state,
            # either from initialization or after deconfigure has been called
            self.logger.info(
                "Aborting from IDLE; not issuing Abort command to VCC band devices"
            )

        task_callback(
            result=(ResultCode.OK, "AbortScan completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return

    def _obs_reset(
        self: VccComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """Reset the configuration."""
        task_callback(status=TaskStatus.IN_PROGRESS)

        # TODO CIP-2380
        if task_abort_event and task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    "Vcc AbortScan command aborted by task executor Abort Event.",
                ),
            )
            return

        if self._freq_band_name != "":
            idx = self._freq_band_index[self._freq_band_name]
            if self.simulation_mode:
                self._band_simulators[idx].ObsReset()
            else:
                try:
                    pass
                    # TODO CIP-1850
                    # self._band_proxies[idx].ObsReset()
                except tango.DevFailed as df:
                    self.logger.error(str(df.args[0].desc))
                    self._update_communication_state(
                        communication_state=CommunicationStatus.NOT_ESTABLISHED
                    )
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            ResultCode.FAILED,
                            "Failed to connect to HPS VCC band devices.",
                        ),
                    )
                    return
        else:
            # if no value for _freq_band_name, assume in IDLE state,
            # either from initialization or after deconfigure has been called
            self.logger.info(
                "Aborted from IDLE; not issuing ObsReset command to VCC band devices"
            )

        task_callback(
            result=(ResultCode.OK, "ObsReset completed OK."),
            status=TaskStatus.COMPLETED,
        )
        return
