# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import threading
from typing import Callable, Optional

import backoff
import tango
from ska_control_model import HealthState, PowerState, TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.slim.slim_link_simulator import SlimLinkSimulator


class SlimLinkComponentManager(CbfComponentManager):
    """
    A component manager for a SLIM link, which is made up of a Tx and Rx device
    from the ds-slim-tx-rx HPS device server.
    """

    def __init__(
        self: SlimLinkComponentManager,
        *args: any,
        **kwargs: any,
    ) -> None:
        """
        Initialize a new instance.
        """
        super().__init__(*args, **kwargs)

        self._link_name = ""
        self._tx_device_name = ""
        self._rx_device_name = ""
        self._tx_device_proxy = None
        self._rx_device_proxy = None
        self._link_enabled = False  # True when tx rx are connected

        self.slim_link_simulator = SlimLinkSimulator(
            logger=self.logger,
            health_state_callback=kwargs["health_state_callback"],
        )

    # -----------------
    # Device Properties
    # -----------------

    @property
    def tx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the HPS tx device that the link is associated with.

        :return: the tx device name.
        :rtype: str
        """
        if self.simulation_mode:
            return self.slim_link_simulator._tx_device_name
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
        if self.simulation_mode:
            return self.slim_link_simulator._rx_device_name
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
        if self.simulation_mode:
            return self.slim_link_simulator.link_name
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
        if self.simulation_mode:
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
        if self.simulation_mode:
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
        if self.simulation_mode:
            return self.slim_link_simulator.bit_error_rate

        if self._rx_device_proxy is None:
            tango.Except.throw_exception(
                "SlimLink_Bit_Error_Rate",
                "Tx Rx are not yet connected",
                "bit_error_rate()",
            )

        return self._rx_device_proxy.bit_error_rate

    @property
    def rx_debug_alignment_and_lock_status(
        self: SlimLinkComponentManager,
    ) -> list[bool]:
        """
        An array holding the debug flag values from the HPS rx device, in the order:
        [0] 66b block alignment lost
        [1] 66b block aligned
        [2] Clock data recovery lock lost
        [3] Clock data recovery locked

        Empty if rx_device_proxy is not connected or tango.DevFailed is caught when accessing rx_debug_alignment_and_lock_status

        :return: Debug Alignment and Lock Status flags of the rx HPS Device
        :rtype: list[int]
        """
        res = []

        if self.simulation_mode:
            return self.slim_link_simulator.rx_debug_alignment_and_lock_status

        if self._rx_device_proxy is None:
            self.logger.error(
                "error reading  rx_debug_alignment_and_lock_status: Tx Rx are not yet connected"
            )
            return res

        try:
            return self._rx_device_proxy.debug_alignment_and_lock_status
        except tango.DevFailed as df:
            self.logger.error(
                f"error reading rx_debug_alignment_and_lock_status: {df}"
            )
            return res

    @property
    def rx_link_occupancy(self: SlimLinkComponentManager) -> float:
        """
        Retrieves and return the link occupancy of the rx device

        :return: Link Occupancy of the rx Device, defaults to -1.0 if not possible
        :raise Tango exception: if the rx device is not set.
        :rtype: float
        """
        res = -1.0

        if self.simulation_mode:
            return self.slim_link_simulator.rx_link_occupancy

        if self._rx_device_proxy is None:
            self.logger.error(
                "error reading rx_link_occupancy: Tx Rx are not yet connected"
            )
            return res

        try:
            return self._rx_device_proxy.link_occupancy
        except tango.DevFailed as df:
            self.logger.error(f"error reading rx_link_occupancy: {df}")
            return res

    @property
    def tx_link_occupancy(self: SlimLinkComponentManager) -> float:
        """
        Retrieves and return the link occupancy of the tx device

        :return: Link Occupancy of the tx Device, defaults to -1.0 if not possible
        :raise Tango exception: if the tx device is not set.
        :rtype: float
        """
        res = -1.0

        if self.simulation_mode:
            return self.slim_link_simulator.tx_link_occupancy

        if self._tx_device_proxy is None:
            self.logger.error(
                "error reading tx_link_occupancy: Tx Rx are not yet connected"
            )
            return res

        try:
            return self._tx_device_proxy.link_occupancy
        except tango.DevFailed as df:
            self.logger.error(f"error reading tx_link_occupancy: {df}")
            return res

    # -------------
    # Communication
    # -------------

    def _start_communicating(
        self: SlimLinkComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.debug(
            "Entering SlimLinkComponentManager.start_communicating"
        )

        super()._start_communicating()
        # This moves the op state model
        self._update_component_state(power=PowerState.ON)

    def _stop_communicating(
        self: SlimLinkComponentManager, *args, **kwargs
    ) -> None:
        """
        Stop communication with the component.
        """

        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model
        super()._stop_communicating()

    # ---------------
    # General Methods
    # ---------------

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
        if self.simulation_mode:
            return self.slim_link_simulator.read_counters

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

    @backoff.on_exception(
        backoff.constant,
        (Exception, tango.DevFailed),
        max_tries=6,
        interval=1.5,
        jitter=None,
    )
    def ping_slim_tx_rx(self: SlimLinkComponentManager) -> None:
        """
        Attempts to ping each of the HPS SLIM devices while incrementing a count of the attempts made.
        """
        self._ping_count += 1
        self._tx_device_proxy.ping()
        self._rx_device_proxy.ping()

    def sync_idle_ctrl_words(self: SlimLinkComponentManager) -> None:
        """
        If IdleCtrlWord is not set in the Tx device, generate a new one and set it in both Tx and Rx devices.
        Otherwise set the Rx device's IdleCtrlWord to the Tx device's IdleCtrlWord.
        """
        idle_ctrl_word = self.tx_idle_ctrl_word

        # If Tx's IdleCtrlWord reads as None, regenerate.
        if idle_ctrl_word is None:
            # 56-bit mask to match register length.
            idle_ctrl_word = hash(self._tx_device_name) & 0x00FFFFFFFFFFFFFF
            self.logger.warning(
                f"SlimTx idle_ctrl_word could not be read. Regenerating idle_ctrl_word={idle_ctrl_word}."
            )
            self._tx_device_proxy.idle_ctrl_word = idle_ctrl_word
        self._rx_device_proxy.idle_ctrl_word = idle_ctrl_word

    def get_tx_loopback_fqdn(self: SlimLinkComponentManager) -> None:
        """
        Determine the Tx device name for serial loopback.
        """
        # To put SLIM Rx back in serial loopback, we need to determine
        # the Tx device name it should reference for ICW comparisons.
        rx = self._rx_device_name
        index = rx.split("/")[2].split("-")[1][2:]
        mesh = rx.split("/")[2].split("-")[0]
        rx_arr = rx.split("/")
        tx = rx_arr[0] + "/" + rx_arr[1] + "/" + mesh + "-tx" + index
        return tx

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

        if self.simulation_mode:
            return self.slim_link_simulator.verify_connection()

        if (
            (not self._link_enabled)
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            self.logger.warning("Tx and Rx devices have not been connected.")
            self.update_device_health_state(HealthState.UNKNOWN)
            return ResultCode.OK, "VerifyConnection completed OK"

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
            if self.bit_error_rate > const.BER_PASS_THRESHOLD:
                error_flag = True
                error_msg += (
                    f"bit-error-rate higher than {const.BER_PASS_THRESHOLD}. "
                )
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            error_msg = f"VerifyConnection FAILED: {self._link_name} - {df}"
            self.logger.error(error_msg)
            self.update_device_health_state(HealthState.FAILED)
            return ResultCode.FAILED, error_msg
        if error_flag:
            self.logger.warning(
                f"{self._link_name}: failed health check - {error_msg}"
            )
            self.update_device_health_state(HealthState.FAILED)
            return ResultCode.OK, "VerifyConnection completed OK"
        self.update_device_health_state(HealthState.OK)
        return ResultCode.OK, "VerifyConnection completed OK"

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
        if self.simulation_mode:
            return self.slim_link_simulator.clear_counters()

        if (
            (not self._link_enabled)
            or (self._tx_device_proxy is None)
            or (self._rx_device_proxy is None)
        ):
            self.logger.warning("Tx and Rx devices have not been connected.")
            return ResultCode.OK, "ClearCounters completed OK"

        try:
            self._tx_device_proxy.clear_read_counters()
            self._rx_device_proxy.clear_read_counters()
        except tango.DevFailed:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            result_msg = f"Clearing counters failed: {self._link_name}"
            self.logger.error(result_msg)
            return ResultCode.FAILED, result_msg

        return ResultCode.OK, "ClearCounters completed OK"

    # -------------
    # Fast Commands
    # -------------

    # None so far.

    # ---------------------
    # Long Running Commands
    # ---------------------

    # --- ConnectTxRx Command --- #

    def is_connect_slim_tx_rx_allowed(self: SlimLinkComponentManager) -> bool:
        self.logger.debug("Checking if ConnectTxRx is allowed.")
        if not self.is_communicating:
            return False
        return True

    def _connect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Link the HPS Tx and Rx devices by synchronizing their idle control words
        and disabling serial loopback. Begin monitoring the Tx and Rx.

        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            f"Entering SlimLinkComponentManager.connect_slim_tx_rx()  -  {self._tx_device_name}->{self._rx_device_name}"
        )
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "ConnectTxRx", task_callback, task_abort_event
        ):
            return

        if self.simulation_mode:
            self.slim_link_simulator.connect_slim_tx_rx()
        else:
            # Tx and Rx device names must be set to create proxies.
            if self._rx_device_name == "" or self._tx_device_name == "":
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "DsSlimTxRx device names have not been set.",
                    ),
                )
                return

            try:
                self._tx_device_proxy = context.DeviceProxy(
                    device_name=self._tx_device_name
                )
                self._rx_device_proxy = context.DeviceProxy(
                    device_name=self._rx_device_name
                )
                self.logger.debug("DsSlimTxRx device proxies acquired.")

                self._ping_count = 0
                self.ping_slim_tx_rx()
                self.logger.debug(
                    f"DsSlimTxRx devices responded to pings after {self._ping_count} tries"
                )

                self.sync_idle_ctrl_words()
                self.logger.debug(
                    f"Tx idle_ctrl_word: {self._tx_device_proxy.idle_ctrl_word} type: {type(self._tx_device_proxy.idle_ctrl_word)}\n"
                    + f"Rx idle_ctrl_word: {self._rx_device_proxy.idle_ctrl_word} type: {type(self._rx_device_proxy.idle_ctrl_word)}"
                )

                # Take SLIM Rx out of serial loopback
                self._rx_device_proxy.initialize_connection(False)

            except AttributeError as ae:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    exception=ae,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "AttributeError encountered. Ensure DsSlimTxRx devices are running.",
                    ),
                )
                return
            except tango.DevFailed as df:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    exception=df.desc,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        df.desc,
                    ),
                )
                return
            self._link_enabled = True
            self._link_name = f"{self._tx_device_name}->{self._rx_device_name}"
            self.clear_counters()

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "ConnectTxRx completed OK",
            ),
        )

    def connect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[ResultCode, str]:
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._connect_slim_tx_rx,
            is_cmd_allowed=self.is_connect_slim_tx_rx_allowed,
            task_callback=task_callback,
        )

    # --- DisconnectTxRx Command --- #

    def is_disconnect_slim_tx_rx_allowed(
        self: SlimLinkComponentManager,
    ) -> bool:
        self.logger.debug("Checking if DisconnectTxRx is allowed.")
        if not self.is_communicating:
            return False
        return True

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

        if self.task_abort_event_is_set(
            "DisconnectTxRx", task_callback, task_abort_event
        ):
            return

        if self.simulation_mode:
            self.slim_link_simulator.disconnect_slim_tx_rx()
            self._link_enabled = False
        else:
            if self._rx_device_proxy is None:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Rx proxy is not set. SlimLink must be connected before it can be disconnected.",
                    ),
                )
                return

            try:
                # Fetch the tx fqdn required to initialize link in serial loopbaack
                loopback_tx = self.get_tx_loopback_fqdn()
                self._tx_device_proxy = context.DeviceProxy(
                    device_name=loopback_tx
                )
                self.sync_idle_ctrl_words()
                self._rx_device_proxy.initialize_connection(True)
            except AttributeError as ae:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    exception=ae,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "AttributeError encountered. Ensure DsSlimTxRx devices are running.",
                    ),
                )
                return
            except tango.DevFailed as df:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                task_callback(
                    exception=df.desc,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        df.desc,
                    ),
                )
                return
            finally:
                self._rx_device_proxy = None
                self._tx_device_proxy = None
                self._link_name = ""
                self._link_enabled = False
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "DisconnectTxRx completed OK",
            ),
        )

    def disconnect_slim_tx_rx(
        self: SlimLinkComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[ResultCode, str]:
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._disconnect_slim_tx_rx,
            is_cmd_allowed=self.is_disconnect_slim_tx_rx_allowed,
            task_callback=task_callback,
        )
