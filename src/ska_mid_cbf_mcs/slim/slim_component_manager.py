# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2023 National Research Council of Canada


from __future__ import annotations

import threading
from typing import Callable, Optional

import backoff
import tango
from beautifultable import BeautifulTable
from ska_control_model import AdminMode, HealthState, PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.slim.slim_config import SlimConfig

__all__ = ["SlimComponentManager"]


class SlimComponentManager(CbfComponentManager):
    """
    Manages a Serial Lightweight Interconnect Mesh (SLIM).
    """

    def __init__(
        self: SlimComponentManager,
        *args: any,
        link_fqdns: list[str],
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param link_fqdns: a list of SLIM Link FQDNs
        """
        super().__init__(*args, **kwargs)

        self.mesh_configured = False
        self._config_str = ""

        self._slim_config = None

        # A list of [tx_fqdn, rx_fqdn] for active links.
        self._active_links = []

        # SLIM Link Device proxies
        self._link_fqdns = link_fqdns
        self._dp_links = []

    # -------------
    # Communication
    # -------------

    def _start_communicating(
        self: SlimComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.debug("Entering SlimComponentManager.start_communicating")

        self._dp_links = []
        self.logger.debug(f"Link FQDNs: {self._link_fqdns}")
        if self._link_fqdns is None:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.logger.error(
                "'Links' device property is unpopulated. Check charts."
            )
            return

        for fqdn in self._link_fqdns:
            try:
                dp = context.DeviceProxy(device_name=fqdn)
                dp.adminMode = AdminMode.ONLINE
                self.attr_event_subscribe(
                    proxy=dp,
                    attr_name="longRunningCommandResult",
                    callback=self.results_callback,
                )
                self._dp_links.append(dp)
            except (tango.DevFailed, AttributeError) as err:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                self.logger.error(f"Failed to initialize {fqdn}: {err}")
                return
        self.logger.info(
            f"event_ids after subscribing = {len(self.event_ids)}"
        )

        super()._start_communicating()
        # This moves the op state model.
        self._update_component_state(power=PowerState.OFF)

    def _stop_communicating(
        self: SlimComponentManager, *args, **kwargs
    ) -> None:
        """Stop communication with the component."""
        self.logger.debug("Entering SlimComponentManager.stop_communicating")
        for proxy in self._dp_links:
            self.unsubscribe_all_events(proxy)

        for dp in self._dp_links:
            dp.adminMode = AdminMode.OFFLINE

        super()._stop_communicating()

    # -------------
    # Fast Commands
    # -------------

    # --- Getters --- #

    def get_configuration_string(self: SlimComponentManager) -> str:
        """
        Returns the configurations string used to configure the SLIM.

        :return: the SLIM configuration string
        :rtype: str
        """
        return self._config_str

    def get_link_fqdns(self: SlimComponentManager) -> list[str]:
        """
        Returns a list of SLIM Link FQDNs.

        :return: the SLIM links associated with the mesh.
        :rtype: list[str]
        """
        fqdns = []
        for idx in range(len(self._active_links)):
            fqdn = self._link_fqdns[idx]
            fqdns.append(fqdn)
        return fqdns

    def get_link_names(self: SlimComponentManager) -> list[str]:
        """
        Returns a list of SLIM Link names, formatted 'tx_device_name->rx_device_name'.

        :return: the names of SLIM links associated with the mesh.
        :rtype: list[str]
        """
        names = []
        for idx in range(len(self._active_links)):
            name = self._dp_links[idx].linkName
            names.append(name)
        return names

    def get_health_summary(self: SlimComponentManager) -> list[HealthState]:
        """
        Returns a list of HealthState enums describing the status of each link.

        :return: the health state of each SLIM link in the mesh.
        :rtype: list[HealthState]
        """
        summary = []
        for idx in range(len(self._active_links)):
            link_health = self._dp_links[idx].healthState
            summary.append(link_health)
        return summary

    def get_bit_error_rate(self: SlimComponentManager) -> list[float]:
        """
        Returns a list containing the bit-error rates for each link.

        :return: the bit-error rate (BER) of each SLIM link in the mesh.
        :rtype: list[float]
        """
        bers = []
        for idx in range(len(self._active_links)):
            ber = self._dp_links[idx].bitErrorRate
            bers.append(ber)
        return bers

    # --- Slim Test Command --- #

    def _calculate_rx_idle_word_rate(
        self: SlimComponentManager,
        rx_idle_word_count: int,
        rx_idle_error_count: int,
    ) -> tuple[str, str]:
        """
        Calculates the ratio of Rx idle errors to idle words and a status flag
        that indicates if the link's error rate exceeds the pass threshold.

        :param: rx_idle_word_count: The number of idle words processed since the counters were last cleared
        :param: rx_idle_error_count: The number of idle errors encountered since the counters were last cleared
        :return: A tuple containing the rx_idle_word_error_rate and rx_ber_pass_status
        :rtype: tuple[str,str]
        """
        if rx_idle_word_count == 0:
            return ("NaN", "Unknown")

        rx_idle_word_rate_float = rx_idle_error_count / rx_idle_word_count
        rx_idle_word_error_rate = f"{rx_idle_word_rate_float:.3e}"
        rx_ber_pass_status = (
            "Passed"
            if rx_idle_word_rate_float < const.BER_PASS_THRESHOLD
            else "Failed"
        )

        return (rx_idle_word_error_rate, rx_ber_pass_status)

    def _slim_links_ber_check_summary(
        self: SlimComponentManager,
        counters: list[list[int]],
        names: list[str],
        rx_error_rate_and_status: list[tuple[str]],
    ) -> None:
        """
        Logs a summary health status for each SLIM link in the mesh.
        Specifically, this will compare the word-error-rate calculated for each rx device to the pass/fail threshold set in global_enum.py.

        :param: counters: A list of lists containing each active SLIM link's counters attr.
        :param: names: A list of strings containing each active SLIM link's linkName attr.
        :param: rx_error_rate_and_status: A list of tuples containing abridged health stats for each active SLIM Link.
        """

        res = "\nSLIM BER Check:\n\n"
        for idx in range(len(self._active_links)):
            rx_word_count = counters[idx][0]
            rx_idle_word_count = counters[idx][2]
            (
                rx_idle_word_error_rate,
                rx_ber_pass_status,
            ) = rx_error_rate_and_status[idx]
            rx_words = rx_word_count + rx_idle_word_count

            res += f"Link Name: {names[idx]}\n"
            res += f"Slim Link status (rx_status): {rx_ber_pass_status}\n"
            res += f"rx_wer:{rx_idle_word_error_rate}\n"
            res += f"rx_rate_gbps:{rx_idle_word_count / rx_words * const.GBPS if rx_words != 0 else 'NaN'}\n"
            res += "\n"
        self.logger.info(res)

    def _slim_table(
        self: SlimComponentManager,
        counters: list[list[int]],
        names: list[str],
        occupancy: list[list[float]],
        debug_flags: list[list[bool]],
        rx_error_rate_and_status: list[tuple[str, str]],
    ) -> None:
        """
        Logs a complete table of metrics for each SlimLink device in the mesh.

        :param: counters: A list of lists containing each active SLIM link's counters attr.
        :param: names: A list of strings containing each active SLIM link's linkName attr.
        :param: occupancy: A list of lists containing each active SLIM link's [0] tx and [1] rx link occupancies.
        :param: debug_flags: A list of lists containing each active SLIM link's rxDebugAlignmentAndLockStatus attr.
        :param: rx_error_rate_and_status: A list of tuples containing abridged health stats for each active SLIM link.
        """

        table = BeautifulTable(maxwidth=180)
        table.columns.header = [
            "Link",
            "CDR locked\n(lost)",
            "Block Aligned\n(lost)",
            "Tx Data (Gbps)\n(words)",
            "Tx Idle (Gbps)",
            "Rx Data\n(Gbps)\n(words)",
            "Rx Idle\n(Gbps)",
            "Idle Error\nCount",
            "Word\nError Rate",
        ]

        for idx in range(len(self._active_links)):
            rx_word_count = counters[idx][0]
            rx_idle_word_count = counters[idx][2]
            rx_idle_error_count = counters[idx][3]
            tx_word_count = counters[idx][6]
            tx_idle_word_count = counters[idx][8]
            tx_words = tx_word_count + tx_idle_word_count
            rx_words = rx_word_count + rx_idle_word_count
            link_flags = debug_flags[idx]

            # Making the tx rx name shorter by keeping only the board name and the tx/rx port
            tx_name = (
                (names[idx].split("->")[0].split("/"))[0]
                + "/"
                + (names[idx].split("->")[0].split("/"))[-1]
            )
            rx_name = (
                (names[idx].split("->")[1].split("/"))[0]
                + "/"
                + (names[idx].split("->")[1].split("/"))[-1]
            )

            data_row = (
                # Name
                f"{tx_name}\n->{rx_name}",
                # CDR locked/lost
                f"{link_flags[3]}\n({link_flags[2]})",
                # Block locked/lost
                f"{link_flags[1]}\n({link_flags[0]})",
                # Tx data
                f"{occupancy[idx][0] * const.GBPS:.2f}\n({tx_word_count})",
                # Tx idle - Guard for divide by zero
                (
                    f"{tx_idle_word_count/tx_words * const.GBPS:.2f}"
                    if tx_words != 0
                    else "NaN"
                ),
                # Rx data
                f"{occupancy[idx][1] * const.GBPS:.2f}\n({rx_word_count})",
                # Rx idle - Guard for divide by zero
                (
                    f"{rx_idle_word_count/rx_words * const.GBPS:.2f}"
                    if rx_words != 0
                    else "NaN"
                ),
                # Idle error count
                f"{rx_idle_error_count} /\n{rx_words:.2e}",
                # Word error rate
                rx_error_rate_and_status[idx][0],
            )
            table.rows.append(data_row)

        self.logger.info(f"\nSLIM Health Summary Table\n{table}")

    def slim_test(self: SlimComponentManager) -> tuple[ResultCode, str]:
        """
        Examines various attributes from active SLIM Links and logs the metrics in a summary table.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: tuple[ResultCode,str]
        """

        counters: list[list[int]] = []
        names: list[str] = []
        occupancy: list[list[float]] = []
        debug_flags: list[list[bool]] = []
        rx_error_rate_and_status: list[tuple[str, str]] = []

        try:
            for idx in range(len(self._active_links)):
                dp_link = self._dp_links[idx]
                counter = dp_link.counters
                rx_idle_word_count = counter[2]
                rx_idle_error_count = counter[3]
                counters.append(counter)
                names.append(dp_link.linkName)
                occupancy.append(
                    [dp_link.txLinkOccupancy, dp_link.rxLinkOccupancy]
                )
                debug_flags.append(dp_link.rxDebugAlignmentAndLockStatus)
                rx_error_rate_and_status.append(
                    self._calculate_rx_idle_word_rate(
                        rx_idle_word_count, rx_idle_error_count
                    )
                )
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.logger.error(f"Error reading SlimLink attr: {df}")

        # Summary check for SLIM Link Status and Bit Error Rate
        self._slim_links_ber_check_summary(
            counters, names, rx_error_rate_and_status
        )

        # More detailed table describing each SLIM Link
        self._slim_table(
            counters, names, occupancy, debug_flags, rx_error_rate_and_status
        )

        return (ResultCode.OK, "SLIM Test Completed")

    # ---------------------
    # Long Running Commands
    # ---------------------

    # --- On Command --- #

    def is_on_allowed(self: SlimComponentManager) -> bool:
        self.logger.debug("Checking if On is allowed.")
        if not self.is_communicating:
            return False
        if self.power_state != PowerState.OFF:
            self.logger.warning(
                f"On not allowed; PowerState is {self.power_state}"
            )
            return False
        return True

    def _on(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> tuple[ResultCode, str]:
        """
        On command.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering SlimComponentManager._on")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        self._update_component_state(power=PowerState.ON)

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "On completed OK",
            ),
        )

    def on(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[ResultCode, str]:
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._on,
            is_cmd_allowed=self.is_on_allowed,
            task_callback=task_callback,
        )

    # --- Configure Command --- #

    def _initialize_links(
        self: SlimComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to connect and starts polling each link's health state.
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            f"Creating {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            self.logger.warning(
                "No active links are defined in the mesh configuration"
            )
            return ResultCode.OK, "_initialize_links completed OK"

        if len(self._active_links) > len(self._dp_links):
            message = "Too many links defined in the link configuration. Not enough SlimLink devices exist."
            self.logger.error(message)
            return ResultCode.FAILED, message

        self.blocking_command_ids = set()
        for idx, txrx in enumerate(self._active_links):
            dev_name = self._dp_links[idx].dev_name()
            try:
                self._dp_links[idx].txDeviceName = txrx[0]
                self._dp_links[idx].rxDeviceName = txrx[1]
                [[result_code], [command_id]] = self._dp_links[
                    idx
                ].ConnectTxRx()
            except tango.DevFailed as df:
                message = f"Failed to initialize SLIM link {dev_name}: {df}"
                self.logger.error(message)
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                return ResultCode.FAILED, message
            except IndexError as ie:
                message = "Not enough Links defined in device properties"
                self.logger.error(f"{message}; {ie}")
                return ResultCode.FAILED, message

            # Guard incase LRC was rejected.
            if result_code == ResultCode.REJECTED:
                message = (
                    f"Nested LRC SlimLink.ConnectTxRx() to {dev_name} rejected"
                )
                self.logger.error(message)
                return ResultCode.FAILED, message

            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results(
            task_abort_event=task_abort_event
        )

        if lrc_status != TaskStatus.COMPLETED:
            message = "One or more calls to nested LRC SlimLink.ConnectTxRx() failed/timed out. Check SlimLink logs."
            self.logger.error(message)
            return ResultCode.FAILED, message

        if not self.simulation_mode:
            for idx, _ in enumerate(self._active_links):
                # Poll link health every 20 seconds, and also verify now.
                try:
                    (result, msg) = self._dp_links[idx].VerifyConnection()
                    if result != ResultCode.OK:
                        self.logger.error(msg)
                        self._update_communication_state(
                            CommunicationStatus.NOT_ESTABLISHED
                        )
                        return ResultCode.FAILED, msg
                    self._dp_links[idx].poll_command("VerifyConnection", 20000)

                except tango.DevFailed as df:
                    message = f"Failed to initialize SLIM links: {df}"
                    self.logger.error(message)
                    self._update_communication_state(
                        CommunicationStatus.NOT_ESTABLISHED
                    )
                    return ResultCode.FAILED, message
                except IndexError as ie:
                    message = "Not enough Links defined in device properties"
                    self.logger.error(f"{message}; {ie}")
                    return ResultCode.FAILED, message
                self.logger.debug(
                    f"VerifyConnection() polling activated on {self._dp_links[idx].linkName}"
                )

        self.logger.info("Successfully initialized SLIM links")
        self.mesh_configured = True
        return ResultCode.OK, "_initialize_links completed OK"

    def is_configure_allowed(self: SlimComponentManager) -> bool:
        self.logger.debug("Checking if Configure is allowed.")
        if not self.is_communicating:
            return False
        if self.power_state != PowerState.ON:
            self.logger.warning(
                f"Configure not allowed; PowerState is {self.power_state}"
            )
            return False
        return True

    def _configure(
        self: SlimComponentManager,
        config_str: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Configure command. Parses the mesh configuration.

        :param config_str: a string in YAML format describing the links to be created.
        :param task_callback: Calls device's _command_tracker.update_command_info(). Set by SubmittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        """
        self.logger.debug("Entering SlimComponentManager.configure()")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "Configure", task_callback, task_abort_event
        ):
            return
        # Each element in the config is [tx_fqdn, rx_fqdn]
        self._config_str = config_str

        try:
            self._slim_config = SlimConfig(self._config_str, self.logger)
            self._active_links = self._slim_config.active_links()

            self.logger.debug(
                f"Configuring {len(self._dp_links)} links with simulationMode = {self.simulation_mode}"
            )
            for dp in self._dp_links:
                dp.adminMode = AdminMode.OFFLINE
                dp.simulationMode = self.simulation_mode
                dp.adminMode = AdminMode.ONLINE

            if self.mesh_configured:
                self.logger.debug(
                    "SLIM was previously configured. Disconnecting links before re-initializing."
                )
                result_code, msg = self._disconnect_links(task_abort_event)
                if result_code is not ResultCode.OK:
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            result_code,
                            msg,
                        ),
                    )
                    return
            self.logger.debug("Initializing SLIM Links")
            result_code, msg = self._initialize_links(task_abort_event)
            if result_code is not ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        result_code,
                        msg,
                    ),
                )
                return

            # SLIM Rx devices can be slow to come up. Allow a few retries
            # before giving up.
            @backoff.on_exception(
                backoff.constant,
                (Exception, tango.DevFailed),
                max_tries=6,
                interval=1.5,
                jitter=None,
            )
            def ping_slim_rx(dp: context.DeviceProxy) -> None:
                dp.ping()

            # Need to disable the loopback on unused rx devices in the
            # visibilities mesh, in order to prevent visibilities
            unused_vis_rx = self._slim_config.get_unused_vis_rx()
            if len(unused_vis_rx) > 0:
                self.logger.info(
                    f"Disabling loopback on unused SLIM Rx devices: {unused_vis_rx}"
                )
                for rx in unused_vis_rx:
                    dp = context.DeviceProxy(device_name=rx)
                    ping_slim_rx(dp)  # wait for successful ping or timeout
                    dp.loopback_enable = False

        except AttributeError as ae:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=ae,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "AttributeError encountered. Ensure SlimLink devices are running.",
                ),
            )
            return
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=df,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    df,
                ),
            )
            return

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Configure completed OK",
            ),
        )

    def configure(
        self: SlimComponentManager,
        config_str: str,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[ResultCode, str]:
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._configure,
            args=[config_str],
            is_cmd_allowed=self.is_configure_allowed,
            task_callback=task_callback,
        )

    # --- Off Command --- #

    def _disconnect_links(
        self: SlimComponentManager,
        task_abort_event: Optional[threading.Event] = None,
    ) -> tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to disconnect and cease polling health states.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            f"Disconnecting {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            self.logger.info(
                "No active links are defined in the SlimLink configuration"
            )
            return ResultCode.OK, "_disconnect_links completed OK"

        self.blocking_command_ids = set()
        for idx in range(len(self._active_links)):
            try:
                if not self.simulation_mode:
                    self._dp_links[idx].stop_poll_command("VerifyConnection")

                [[result_code], [command_id]] = self._dp_links[
                    idx
                ].DisconnectTxRx()
            except tango.DevFailed as df:
                message = f"Failed to disconnect SLIM links: {df}"
                self.logger.error(message)
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                return ResultCode.FAILED, message
            except IndexError as ie:
                message = "Not enough Links defined in device properties"
                self.logger.error(f"{message}; {ie}")
                return ResultCode.FAILED, message

            # Guard incase LRC was rejected.
            if result_code == ResultCode.REJECTED:
                message = f"Nested LRC SlimLink.DisconnectTxRx() to {self._dp_links[idx].dev_name()} rejected"
                self.logger.error(message)
                return ResultCode.FAILED, message

            self.blocking_command_ids.add(command_id)

        lrc_status = self.wait_for_blocking_results(
            task_abort_event=task_abort_event
        )

        if lrc_status != TaskStatus.COMPLETED:
            message = "One or more calls to nested LRC SlimLink.DisconnectTxRx() failed/timed out. Check SlimLink logs."
            self.logger.error(message)
            return ResultCode.FAILED, message

        self.logger.info("Successfully disconnected SLIM links")
        self.mesh_configured = False
        return ResultCode.OK, "_disconnect_links completed OK"

    def is_off_allowed(self: SlimComponentManager) -> bool:
        self.logger.debug("Checking if Off is allowed.")
        if not self.is_communicating:
            return False
        if self.power_state != PowerState.ON:
            self.logger.warning(
                f"Off not allowed; PowerState is {self.power_state}"
            )
            return False
        return True

    def _off(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> tuple[ResultCode, str]:
        """
        Off command. Disconnects SLIM Links if mesh is configured, else returns OK.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering SlimComponentManager._off")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        try:
            rc, msg = self._disconnect_links(task_abort_event)
            if rc is not ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(rc, msg),
                )
                return
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=df,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    df,
                ),
            )
            return

        self._update_component_state(power=PowerState.OFF)
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Off completed OK",
            ),
        )

    def off(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[ResultCode, str]:
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )
