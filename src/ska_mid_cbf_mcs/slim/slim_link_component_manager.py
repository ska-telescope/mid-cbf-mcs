# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional, Tuple

import backoff
import tango
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    HealthState,
    PowerState,
    SimulationMode,
)

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.slim.slim_link_simulator import SlimLinkSimulator

BER_PASS_THRESHOLD = 8.000e-11


class SlimLinkComponentManager(CbfComponentManager):
    """
    A component manager for a SLIM link, which is made up of a Tx and Rx device
    from the ds-slim-tx-rx HPS device server.
    """

    def __init__(
        self: SlimLinkComponentManager,
        *args: Any,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a new instance.

        :param simulation_mode: Enum that identifies if the simulator should be used
        """
        super().__init__(*args, **kwargs)
        self.simulation_mode = simulation_mode

        self._link_name = ""
        self._tx_device_name = ""
        self._rx_device_name = ""
        self._tx_device_proxy = None
        self._rx_device_proxy = None
        self._link_enabled = False  # True when tx rx are connected

        self.slim_link_simulator = SlimLinkSimulator(
            logger=self.logger,
        )

    @property
    def tx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the HPS tx device that the link is associated with.

        :return: the tx device name.
        :rtype: str
        """
        return self._tx_device_name

    @tx_device_name.setter
    def tx_device_name(
        self: SlimLinkComponentManager, tx_device_name: str
    ) -> None:
        """
        Sets the tx device name value.

        :param tx_device_name: The tx device name.
        """
        if self.simulation_mode:
            self.slim_link_simulator.tx_device_name = tx_device_name
        self._tx_device_name = tx_device_name

    @property
    def rx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the HPS rx device that the link is associated with.

        :return: the rx device name.
        :rtype: str
        """
        return self._rx_device_name

    @rx_device_name.setter
    def rx_device_name(
        self: SlimLinkComponentManager, rx_device_name: str
    ) -> None:
        """
        Sets the rx device name value.

        :param rx_device_name: The rx device name.
        """
        if self.simulation_mode:
            self.slim_link_simulator.rx_device_name = rx_device_name
        self._rx_device_name = rx_device_name

    @property
    def link_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the SLIM link.

        :return: the link name.
        :rtype: str
        """
        return self._link_name

    @property
    def tx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        The idle control word set in the tx device. Initially generated
        in the HPS by hashing the tx device's FQDN.

        :return: the tx idle control word.
        :raise Tango exception: if the tx device is not set.
        :rtype: int
        """
        if self.simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.tx_idle_ctrl_word
        if self._tx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_tx_idle_ctrl_word",
                "Tx Rx are not yet connected",
                "tx_idle_ctrl_word()",
            )

        return self._tx_device_proxy.idle_ctrl_word

    @property
    def rx_idle_ctrl_word(self: SlimLinkComponentManager) -> int:
        """
        The last idle control word received in the datastream by the HPS rx device.

        :return: the rx idle control word.
        :raise Tango exception: if the rx device is not set.
        :rtype: int
        """
        if self.simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.rx_idle_ctrl_word
        if self._rx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_rx_idle_ctrl_word",
                "Tx Rx are not yet connected",
                "rx_idle_ctrl_word()",
            )

        return self._rx_device_proxy.idle_ctrl_word

    @property
    def bit_error_rate(self: SlimLinkComponentManager) -> float:
        """
        The bit-error rate in 66b-word-errors per second.

        :return: The bit error rate.
        :raise Tango exception: if the rx device is not set.
        :rtype: float
        """
        if self.simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.bit_error_rate

        if self._rx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_Bit_Error_Rate",
                "Tx Rx are not yet connected",
                "bit_error_rate()",
            )

        return self._rx_device_proxy.bit_error_rate

    def read_counters(
        self: SlimLinkComponentManager,
    ) -> list[int]:
        """
        An array holding the counter values from the HPS tx and rx devices in the order:
        [0] rx_word_count
        [1] rx_packet_count
        [2] rx_idle_word_count
        [3] rx_idle_error_count
        [4] rx_block_lost_count
        [5] rx_cdr_lost_count
        [6] tx_word_count
        [7] tx_packet_count
        [8] tx_idle_word_count

        :return: The read_counters array.
        :raise Tango exception: if link is not enabled.
        :rtype: list[int]
        """
        if self.simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.read_counters()

        if (
            not self._link_enabled
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            tango.Except.throw_exception(
                "SlimLink_Read_Counters",
                "Tx Rx are not yet connected",
                "read_counters()",
            )

        tx_counts = self._tx_device_proxy.read_counters
        rx_counts = self._rx_device_proxy.read_counters
        self.logger.debug(f"tx_counts = {tx_counts}")
        self.logger.debug(f"rx_counts = {rx_counts}")
        return [
            rx_counts[0],
            rx_counts[1],
            rx_counts[2],
            rx_counts[3],
            rx_counts[4],
            rx_counts[5],
            tx_counts[0],
            tx_counts[1],
            tx_counts[2],
        ]

    def start_communicating(self: SlimLinkComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        super().start_communicating()
        # This moves the op state model
        self._update_component_state(power=PowerState.ON)

    def stop_communicating(self: SlimLinkComponentManager) -> None:
        """Stop communication with the component."""

        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model
        super().stop_communicating()

    def is_connect_slim_tx_rx_allowed(self: SlimLinkComponentManager) -> bool:
        self.logger.info("Checking if ConnectTxRx is allowed.")
        return self.communication_state == CommunicationStatus.ESTABLISHED

    def _connect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Link the HPS tx and rx devices by synchronizing their idle control words
        and disabling serial loopback. Begin monitoring the Tx and Rx.

        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self.logger.info(
            f"Entering SlimLinkComponentManager.connect_slim_tx_rx()  -  {self._tx_device_name}->{self._rx_device_name}"
        )
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.simulation_mode == SimulationMode.TRUE:
            self.slim_link_simulator.connect_slim_tx_rx()
        else:
            # Tx and Rx device names must be set to create proxies.
            if self._rx_device_name == "" or self._tx_device_name == "":
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Tx or Rx device FQDN have not been set.",
                    ),
                )
                return
            task_callback(progress=10)

            try:
                if task_abort_event and task_abort_event.is_set():
                    task_callback(
                        status=TaskStatus.ABORTED,
                        result=(
                            ResultCode.ABORTED,
                            f"Connect Tx Rx aborted for {self._tx_device_name}->{self._rx_device_name}",
                        ),
                    )
                    return
                self._tx_device_proxy = CbfDeviceProxy(
                    fqdn=self._tx_device_name, logger=self.logger
                )
                self._rx_device_proxy = CbfDeviceProxy(
                    fqdn=self._rx_device_name, logger=self.logger
                )
                task_callback(progress=20)

                @backoff.on_exception(
                    backoff.constant,
                    (Exception, tango.DevFailed),
                    max_tries=6,
                    interval=1.5,
                    jitter=None,
                )
                def ping_slim_tx_rx() -> None:
                    """
                    Attempts to connect to the Talon board for the first time
                    after power-on.
                    """
                    self._ping_count += 1
                    self._tx_device_proxy.ping()
                    self._rx_device_proxy.ping()

                self._ping_count = 0
                ping_slim_tx_rx()
                self.logger.debug(
                    f"Successfully pinged DsSlimTx and DsSlimRx devices after {self._ping_count} tries"
                )
                task_callback(progress=30)

                # Sync the idle ctrl word between Tx and Rx
                idle_ctrl_word = self.tx_idle_ctrl_word

                # If Tx's IdleCtrlWord reads as None, regenerate.
                if idle_ctrl_word is None:
                    idle_ctrl_word = (
                        hash(self._tx_device_name) & 0x00FFFFFFFFFFFFFF
                    )
                    self.logger.warning(
                        f"SlimTx idle_ctrl_word could not be read. Regenerating idle_ctrl_word={idle_ctrl_word}."
                    )
                    self._tx_device_proxy.idle_ctrl_word = idle_ctrl_word
                self._rx_device_proxy.idle_ctrl_word = idle_ctrl_word

                task_callback(progress=60)

                self.logger.info(
                    f"Tx idle_ctrl_word: {self._tx_device_proxy.idle_ctrl_word} type: {type(self._tx_device_proxy.idle_ctrl_word)}\n"
                    + f"Rx idle_ctrl_word: {self._rx_device_proxy.idle_ctrl_word} type: {type(self._rx_device_proxy.idle_ctrl_word)}"
                )

                # Take SLIM Rx out of serial loopback
                self._rx_device_proxy.initialize_connection(False)
                self.clear_counters()
                task_callback(progress=80)
            except tango.DevFailed as df:
                self._update_component_state(fault=True)
                task_callback(
                    exception=df,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        f"Failed to connect Tx Rx for {self._tx_device_name}->{self._rx_device_name}: {df.args[0].desc}",
                    ),
                )
        self._link_enabled = True
        self._link_name = f"{self._tx_device_name}->{self._rx_device_name}"
        task_callback(
            progress=100,
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                f"Connected Tx Rx successfully: {self._link_name}",
            ),
        )

    def connect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> Tuple[ResultCode, str]:
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._connect_slim_tx_rx,
            is_cmd_allowed=self.is_connect_slim_tx_rx_allowed,
            task_callback=task_callback,
        )

    def verify_connection(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Performs a health check on the SLIM link. No check is done if the link
        is not active; instead, the health state is set to UNKNOWN.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            "Entering SlimLinkComponentManager.verify_connection()  -  "
            + self._link_name
        )

        if self.simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.verify_connection()

        if (
            (not self._link_enabled)
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            msg = "Tx and Rx devices have not been connected."
            self.logger.debug(msg)
            self._update_device_health_state(HealthState.UNKNOWN)
            return ResultCode.OK, msg

        error_msg = ""
        error_flag = False
        try:
            if self.rx_idle_ctrl_word != self.tx_idle_ctrl_word:
                error_flag = True
                error_msg += (
                    "Expected and received idle control word do not match. "
                )
            counters = self.read_counters()
            if counters[4] != 0:
                error_flag = True
                error_msg += "block_lost_count not zero. "
            if counters[5] != 0:
                error_flag = True
                error_msg += "cdr_lost_count not zero. "
            if self.bit_error_rate > BER_PASS_THRESHOLD:
                error_flag = True
                error_msg += (
                    f"bit-error-rate higher than {BER_PASS_THRESHOLD}. "
                )
        except tango.DevFailed as df:
            error_msg = f"verify_connection() failed for {self._link_name}: {df.args[0].desc}"
            self.logger.error(error_msg)
            self._update_device_health_state(HealthState.FAILED)
            return ResultCode.FAILED, error_msg
        if error_flag:
            self.logger.warn(
                f"Link failed health check for {self._link_name}: {error_msg}"
            )
            self._update_device_health_state(HealthState.FAILED)
            return ResultCode.OK, error_msg
        self._update_device_health_state(HealthState.OK)
        return ResultCode.OK, f"Link health check OK: {self._link_name}"

    def is_disconnect_slim_tx_rx_allowed(
        self: SlimLinkComponentManager,
    ) -> bool:
        self.logger.info("Checking if DisconnectTxRx is allowed.")
        return self.communication_state == CommunicationStatus.ESTABLISHED

    def _disconnect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Stops controlling and monitoring the HPS tx and rx devices. The link
        becomes inactive. Serial loopback is re-established.

        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            "Entering SlimLinkComponentManager.disconnect_slim_tx_rx()  -  "
            + self._link_name
        )
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.simulation_mode == SimulationMode.TRUE:
            self.slim_link_simulator.disconnect_slim_tx_rx()
        else:
            try:
                if self._rx_device_proxy is not None:
                    # To put SLIM Rx back in serial loopback, we need to determine
                    # the Tx device name it should reference for ICW comparisons.
                    rx = self._rx_device_name
                    index = rx.split("/")[2].split("-")[1][2:]
                    mesh = rx.split("/")[2].split("-")[0]
                    rx_arr = rx.split("/")
                    tx = (
                        rx_arr[0]
                        + "/"
                        + rx_arr[1]
                        + "/"
                        + mesh
                        + "-tx"
                        + index
                    )

                    self._tx_device_name = tx
                    task_callback(progress=20)

                    if task_abort_event and task_abort_event.is_set():
                        task_callback(
                            status=TaskStatus.ABORTED,
                            result=(
                                ResultCode.ABORTED,
                                f"Disconnect Tx Rx aborted for {self._tx_device_name}->{self._rx_device_name}",
                            ),
                        )
                        return

                    self._tx_device_proxy = CbfDeviceProxy(
                        fqdn=self._tx_device_name, logger=self.logger
                    )
                    task_callback(progress=40)
                    # Sync the idle ctrl word between Tx and Rx
                    idle_ctrl_word = self.tx_idle_ctrl_word
                    self._rx_device_proxy.idle_ctrl_word = idle_ctrl_word
                    task_callback(progress=60)

                    self._rx_device_proxy.initialize_connection(True)
                    task_callback(progress=80)
            except tango.DevFailed as df:
                task_callback(
                    exception=df,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        f"Failed to enable Rx loopback for {self._tx_device_name}->{self._rx_device_name}: {df.args[0].desc}",
                    ),
                )
            finally:
                self._rx_device_proxy = None
                self._tx_device_proxy = None
                self._link_name = ""
                self._link_enabled = False
        task_callback(
            progress=100,
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                f"Disonnected Tx Rx. {self._rx_device_name} now in serial loopback.",
            ),
        )

    def disconnect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> Tuple[ResultCode, str]:
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._disconnect_slim_tx_rx,
            is_cmd_allowed=self.is_disconnect_slim_tx_rx_allowed,
            task_callback=task_callback,
        )

    def clear_counters(
        self: SlimLinkComponentManager,
    ) -> tuple[ResultCode, str]:
        """
        Clears the HPS tx and rx device's read counters.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            "Entering SlimLinkComponentManager.clearCounters()  -  "
            + self._link_name
        )
        if self.simulation_mode == SimulationMode.TRUE:
            return self.slim_link_simulator.clear_counters()

        if (
            (not self._link_enabled)
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            msg = "Tx and Rx devices have not been connected."
            return ResultCode.OK, msg

        try:
            self._tx_device_proxy.clear_read_counters()
            self._rx_device_proxy.clear_read_counters()
        except tango.DevFailed:
            result_msg = f"Clearing counters failed: {self._link_name}"
            self.logger.error(result_msg)
            return ResultCode.FAILED, result_msg

        return ResultCode.OK, f"Counters cleared: {self._link_name}"
