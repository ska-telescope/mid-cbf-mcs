# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from threading import Event, Lock, Thread
from typing import Optional

import tango
from ska_control_model import HealthState, PowerState
from ska_tango_testing import context

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.talon_board.influxdb_query_client import (
    InfluxdbQueryClient,
)
from ska_mid_cbf_mcs.talon_board.talon_board_simulator import SimulatedValues

# Eth100g, HPS Master polling period in seconds
POLLING_PERIOD = 2


class Eth100gClient:
    def __init__(self, eth_100g_fqdn: str):
        self._eth_100g_fqdn = eth_100g_fqdn
        self._eth_100g_id = 0 if "100g_0" in eth_100g_fqdn else 1
        self._dp_eth_100g = context.DeviceProxy(device_name=eth_100g_fqdn)
        self._tx_stats = []
        self._rx_stats = []
        self._stats_idx = {
            "fragments": 0,
            "jabbers": 1,
            "fcs": 2,
            "crcerr": 3,
            "mcast_data_err": 4,
            "bcast_data_err": 5,
            "ucast_data_err": 6,
            "mcast_ctrl_err": 7,
            "bcast_ctrl_err": 8,
            "ucast_ctrl_err": 9,
            "pause_err": 10,
            "64b": 11,
            "65to127b": 12,
            "128to255b": 13,
            "256to511b": 14,
            "512to1023b": 15,
            "1024to1518b": 16,
            "1519tomaxb": 17,
            "oversize": 18,
            "mcast_data_ok": 19,
            "bcast_data_ok": 20,
            "ucast_data_ok": 21,
            "mcast_ctrl": 22,
            "bcast_ctrl": 23,
            "ucast_ctrl": 24,
            "pause": 25,
            "runt": 26,
        }

    def read_eth_100g_stats(self):
        """
        Reads counters from the HPS 100g ethernet device.

        The get_tx_stats and get_rx_stats commands will take a snapshot
        of the statistics counters and return in a list. The counters are
        then reset and increment from 0. Therefore the counters are
        accumulated over the period between consecutive calls.
        """
        try:
            self._tx_stats = self._dp_eth_100g.get_tx_stats()
            self._rx_stats = self._dp_eth_100g.get_rx_stats()
            self._txframeoctetsok = self._dp_eth_100g.TxFrameOctetsOK
            self._rxframeoctetsok = self._dp_eth_100g.RxFrameOctetsOK
        except tango.DevFailed as df:
            self.logger.warning(f"Error reading 100g ethernet stats: {df}")
            self._tx_stats = []
            self._rx_stats = []
            self._txframeoctetsok = 0
            self._rxframeoctetsok = 0

    def has_data_flow(self) -> bool:
        """
        returns true if the board is receiving data at 100g ethernet input
        """
        self._throw_if_stats_not_available()
        if self._eth_100g_id == 0:  # eth_100g_0
            return (
                self._tx_stats[self._stats_idx["1519tomaxb"]] > 0
                and self._rx_stats[self._stats_idx["1519tomaxb"]] > 0
                and self._txframeoctetsok > 0
                and self._rxframeoctetsok > 0
            )
        else:  # eth_100g_1
            return self._tx_stats[self._stats_idx["1519tomaxb"]] > 0

    def get_data_counters(self) -> list[int]:
        """
        Returns a list of data counters
        [0]: number of transmitted frames between 1519 to max bytes
        [1]: number of transmitted bytes in frames with no FCS, undersized, oversized, or payload length errors
        [2]: number of received frames between 1519 to max bytes
        [3]: number of received bytes in frames with no FCS, undersized, oversized, or payload length errors
        """
        self._throw_if_stats_not_available()
        data_counters = [
            self._tx_stats[self._stats_idx["1519tomaxb"]],
            self._txframeoctetsok,
            self._rx_stats[self._stats_idx["1519tomaxb"]],
            self._rxframeoctetsok,
        ]
        return data_counters

    def has_error(self) -> bool:
        error_counters = self.get_error_counters()
        return any(x > 0 for x in error_counters)

    def get_error_counters(self) -> list[int]:
        """
        Returns a list of error counters:
        [0]: number of transmitted frames less than 64 bytes
        [1]: number of transmitted oversized frames
        [2]: number of transmitted CRC errors
        [3]: number of received frames less than 64 bytes
        [4]: number of received oversized frames
        [5]: number of received CRC errors
        """
        self._throw_if_stats_not_available()
        err_counters = [
            self._tx_stats[self._stats_idx["fragments"]],
            self._tx_stats[self._stats_idx["oversize"]],
            self._tx_stats[self._stats_idx["crcerr"]],
            self._rx_stats[self._stats_idx["fragments"]],
            self._rx_stats[self._stats_idx["oversize"]],
            self._rx_stats[self._stats_idx["crcerr"]],
        ]
        return err_counters

    def get_all_tx_counters(self) -> list[int]:
        """
        Returns the full list of Tx stats from 100g eth device's
        get_tx_stats() command.
        """
        self._throw_if_stats_not_available()
        return self._tx_stats

    def get_all_rx_counters(self) -> list[int]:
        """
        Returns the full list of Rx stats from 100g eth device's
        get_rx_stats() command.
        """
        self._throw_if_stats_not_available()
        return self._rx_stats

    def _throw_if_stats_not_available(self) -> None:
        if len(self._tx_stats) == 0 or len(self._rx_stats) == 0:
            tango.Except.throw_exception(
                "100g_get_error_counters_failed",
                f"100g stats are not available for {self._eth_100g_fqdn}.",
                "get_error_counters()",
            )
        return


class TalonBoardComponentManager(CbfComponentManager):
    """
    A component manager for a Talon board.
    """

    def __init__(
        self: TalonBoardComponentManager,
        *args: any,
        hostname: str,
        influx_port: int,
        influx_org: str,
        influx_bucket: str,
        influx_auth_token: str,
        talon_sysid_address: str,
        eth_100g_address: str,
        talon_status_address: str,
        hps_master_address: str,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param hostname: Hostname of the Talon DX board
        :param influx_port: Influxdb port
        :param influx_org: Influxdb organization
        :param influx_bucket: Influxdb bucket to query
        :param influx_auth_token: Influxdb authentication token
        :param talon_sysid_address: Talon Sysid device server name
        :param eth_100g_address: 100g ethernet device server name (missing index suffix)
        :param talon_status_address: Talon Status device server name
        :param hps_master_address: HPS Master device server name
        """

        super().__init__(*args, **kwargs)

        # Influxdb
        self._db_client = InfluxdbQueryClient(
            hostname=hostname,
            influx_port=influx_port,
            influx_org=influx_org,
            influx_bucket=influx_bucket,
            influx_auth_token=influx_auth_token,
            logger=self.logger,
        )

        # --- HPS device proxies --- #
        self._talon_sysid_fqdn = talon_sysid_address
        self._eth_100g_0_fqdn = f"{eth_100g_address}_0"
        self._eth_100g_1_fqdn = f"{eth_100g_address}_1"
        self._talon_status_fqdn = talon_status_address
        self._hps_master_fqdn = hps_master_address

        # --- Subscribed Device Proxy Attributes --- #
        self._talon_sysid_attrs = {}
        self._talon_status_attrs = {}

        self._last_check = datetime.now(timezone.utc) - timedelta(hours=1)
        self._telemetry = dict()
        self._proxies = dict()
        self._talon_sysid_events = {}
        self._talon_status_events = {}

        self._eth_100g_0_client = None
        self._eth_100g_0_client = None

        self._poll_thread = None
        self.ping_ok = False

        self._polled_attr_lock = Lock()
        self._polled_attr = dict()
        self._alt_attr_name = {
            "version": "bitstreamVersion",
            "Bitstream": "bitstreamChecksum",
            "iopll_locked_fault": "iopllLockedFault",
            "fs_iopll_locked_fault": "fsIopllLockedFault",
            "comms_iopll_locked_fault": "commsIopllLockedFault",
            "system_clk_fault": "systemClkFault",
            "emif_bl_fault": "emifBlFault",
            "emif_br_fault": "emifBrFault",
            "emif_tr_fault": "emifTrFault",
            "e100g_0_pll_fault": "ethernet0PllFault",
            "e100g_1_pll_fault": "ethernet1PllFault",
            "slim_pll_fault": "slimPllFault",
        }

    # -------------
    # Communication
    # -------------
    def _talon_attr_change_callback(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Thread to update latest state attribute events.

        :param event_data: Tango attribute change event data
        """
        if event_data.attr_value is None:
            return
        value = event_data.attr_value.value
        if value is None:
            return

        attr_name = event_data.attr_value.name
        dev_name = event_data.device.dev_name()
        self.logger.debug(
            f"{dev_name}/{attr_name} EventData attr_value: {value}"
        )

        with self._attr_event_lock:
            if dev_name == self._talon_sysid_fqdn:
                self._talon_sysid_attrs[attr_name] = value
            elif dev_name == self._talon_status_fqdn:
                self._talon_status_attrs[attr_name] = value
            else:
                self.logger.warning(
                    f"Unexpected change callback from FQDN {dev_name}/{attr_name}"
                )
                return
        self.logger.debug(
            f"Generating change event for TalonBoard/{self._alt_attr_name[attr_name]}"
        )
        self.device_attr_change_callback(self._alt_attr_name[attr_name], value)
        self.device_attr_archive_callback(
            self._alt_attr_name[attr_name], value
        )

    def talon_attr_change_callback(
        self: CbfComponentManager, event_data: Optional[tango.EventData]
    ) -> None:
        """
        Callback for state attribute events.

        :param event_data: Tango attribute change event data
        """
        Thread(
            target=self._talon_attr_change_callback, args=(event_data,)
        ).start()

    def _subscribe_change_events(self: TalonBoardComponentManager) -> None:
        """
        Subscribe to attribute change events from HPS device proxies
        """
        for fqdn, attr_list in [
            (self._talon_sysid_fqdn, ["version", "Bitstream"]),
            (
                self._talon_status_fqdn,
                [
                    "iopll_locked_fault",
                    "fs_iopll_locked_fault",
                    "comms_iopll_locked_fault",
                    "system_clk_fault",
                    "emif_bl_fault",
                    "emif_br_fault",
                    "emif_tr_fault",
                    "e100g_0_pll_fault",
                    "e100g_1_pll_fault",
                    "slim_pll_fault",
                ],
            ),
        ]:
            if fqdn is not None:
                for attr_name in attr_list:
                    self.attr_event_subscribe(
                        proxy=self._proxies[fqdn],
                        attr_name=attr_name,
                        callback=self.talon_attr_change_callback,
                    )

    def update_polled_attr(self: TalonBoardComponentManager) -> None:
        """
        Update the class member dict that maintains a copy of all the
        attributes managed by InfluxdbQueryClient and Eth100gClient.
        """
        for attr_name, getter_fn in [
            # InfluxdbQueryClient managed attr
            ("fpgaDieTemperature", self.fpga_die_temperature),
            ("fpgaDieVoltage0", self.fpga_die_voltage_0),
            ("fpgaDieVoltage1", self.fpga_die_voltage_1),
            ("fpgaDieVoltage2", self.fpga_die_voltage_2),
            ("fpgaDieVoltage3", self.fpga_die_voltage_3),
            ("fpgaDieVoltage4", self.fpga_die_voltage_4),
            ("fpgaDieVoltage5", self.fpga_die_voltage_5),
            ("fpgaDieVoltage6", self.fpga_die_voltage_6),
            ("humiditySensorTemperature", self.humidity_sensor_temperature),
            ("dimmTemperatures", self.dimm_temperatures),
            ("mboTxTemperatures", self.mbo_tx_temperatures),
            ("mboTxVccVoltages", self.mbo_tx_vcc_voltages),
            ("mboTxFaultStatus", self.mbo_tx_fault_status),
            ("mboTxLolStatus", self.mbo_tx_lol_status),
            ("mboTxLosStatus", self.mbo_tx_los_status),
            ("mboRxVccVoltages", self.mbo_rx_vcc_voltages),
            ("mboRxLolStatus", self.mbo_rx_lol_status),
            ("mboRxLosStatus", self.mbo_rx_los_status),
            ("hasFanControl", self.has_fan_control),
            ("fansPwm", self.fans_pwm),
            ("fansPwmEnable", self.fans_pwm_enable),
            ("fansRpm", self.fans_input),
            ("fansFault", self.fans_fault),
            ("ltmInputVoltage", self.ltm_input_voltage),
            ("ltmOutputVoltage1", self.ltm_output_voltage_1),
            ("ltmOutputVoltage2", self.ltm_output_voltage_2),
            ("ltmInputCurrent", self.ltm_input_current),
            ("ltmOutputCurrent1", self.ltm_output_current_1),
            ("ltmOutputCurrent2", self.ltm_output_current_2),
            ("ltmTemperature1", self.ltm_temperature_1),
            ("ltmTemperature2", self.ltm_temperature_2),
            ("ltmVoltageWarning", self.ltm_voltage_warning),
            ("ltmCurrentWarning", self.ltm_current_warning),
            ("ltmTemperatureWarning", self.ltm_temperature_warning),
            # Eth100gClient managed attrs
            ("eth100g0Counters", self.eth100g_0_counters),
            ("eth100g0ErrorCounters", self.eth100g_0_error_counters),
            ("eth100g0DataFlowActive", self.eth100g_0_data_flow_active),
            ("eth100g0HasDataError", self.eth100g_0_has_data_error),
            ("eth100g0AllTxCounters", self.eth100g_0_all_tx_counters),
            ("eth100g0AllRxCounters", self.eth100g_0_all_rx_counters),
            ("eth100g1Counters", self.eth100g_1_counters),
            ("eth100g1ErrorCounters", self.eth100g_1_error_counters),
            ("eth100g1DataFlowActive", self.eth100g_1_data_flow_active),
            ("eth100g1HasDataError", self.eth100g_1_has_data_error),
            ("eth100g1AllTxCounters", self.eth100g_1_all_tx_counters),
            ("eth100g1AllRxCounters", self.eth100g_1_all_rx_counters),
        ]:
            cur_val = getter_fn()
            with self._polled_attr_lock:
                try:
                    if cur_val != self._polled_attr[attr_name]:
                        self.device_attr_change_callback(attr_name, cur_val)
                        self.device_attr_archive_callback(attr_name, cur_val)
                except KeyError:
                    self.logger.debug(
                        f"{attr_name} not currently monitored for changes; starting now."
                    )
                    self.device_attr_change_callback(attr_name, cur_val)
                    self.device_attr_archive_callback(attr_name, cur_val)
                self._polled_attr[attr_name] = cur_val

    def _internal_polling_thread(
        self: TalonBoardComponentManager,
        eth0: Eth100gClient,
        eth1: Eth100gClient,
        db_client: InfluxdbQueryClient,
        event: Event,
    ):
        self.logger.info("Started polling")
        while True:
            # polls until event is set
            if event.wait(timeout=POLLING_PERIOD):
                break

            # Ping InfluxDB
            res = asyncio.run(db_client.ping())
            if not res:
                if self.ping_ok:
                    self.logger.error(
                        "Failed to ping Influxdb. Talon board may be down."
                    )
            else:
                if not self.ping_ok:
                    self.logger.info("Pinged influxdb successfully.")

            if res != self.ping_ok:
                self.device_attr_change_callback("pingResult", res)
                self.device_attr_archive_callback("pingResult", res)
            self.ping_ok = res

            # Poll eth100g stats
            eth0.read_eth_100g_stats()
            eth1.read_eth_100g_stats()
            # Maintain a local copy for comparison when generating change events
            self.update_polled_attr()

            # Poll HPS Master healthState
            self.update_device_health_state(
                self._proxies[self._hps_master_fqdn].healthState
            )
        self.logger.info("Stopped polling")

    def _start_communicating(
        self: TalonBoardComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.debug(
            "Entering TalonBoardComponentManager._start_communicating"
        )

        if not self.simulation_mode:
            try:
                for fqdn in [
                    self._talon_sysid_fqdn,
                    self._talon_status_fqdn,
                    self._hps_master_fqdn,
                ]:
                    if fqdn is not None:
                        self._proxies[fqdn] = context.DeviceProxy(
                            device_name=fqdn
                        )
                        self.logger.debug(f"Created device proxy for {fqdn}")
                    else:
                        self.logger.error(
                            "Failed to establish proxies to devices in properties. Check charts."
                        )
                        self._update_communication_state(
                            CommunicationStatus.NOT_ESTABLISHED
                        )
                        return

                self._eth_100g_0_client = Eth100gClient(self._eth_100g_0_fqdn)
                self._eth_100g_1_client = Eth100gClient(self._eth_100g_1_fqdn)

                # Begin the polling thread
                self._poll_thread_event = Event()
                self._poll_thread = Thread(
                    target=self._internal_polling_thread,
                    args=[
                        self._eth_100g_0_client,
                        self._eth_100g_1_client,
                        self._db_client,
                        self._poll_thread_event,
                    ],
                )
                self._poll_thread.start()

                self._subscribe_change_events()
            except tango.DevFailed as df:
                self.logger.error(f"{df}")
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                return
        super()._start_communicating()
        self._update_component_state(power=PowerState.ON)

    def _stop_communicating(
        self: TalonBoardComponentManager, *args, **kwargs
    ) -> None:
        """
        Thread for stop_communicating operation.
        """
        self.logger.debug(
            "Entering TalonBoardComponentManager._stop_communicating"
        )
        if not self.simulation_mode:
            for fqdn, events in [
                (self._talon_sysid_fqdn, self._talon_sysid_events),
                (self._talon_status_fqdn, self._talon_status_events),
            ]:
                for attr_name, event_id in events.items():
                    self.logger.info(
                        f"Unsubscribing from {fqdn}/{attr_name} event ID {event_id}"
                    )
                    try:
                        self._proxies[fqdn].unsubscribe_event(event_id)
                    except tango.DevFailed as df:
                        # Log exception but allow stop_communicating to continue
                        self.logger.error(f"{df}")
                        continue

            if self._poll_thread is not None:
                self._poll_thread_event.set()
                self._poll_thread.join()
            self._eth_100g_0_client = None
            self._eth_100g_1_client = None
            self.update_device_health_state(HealthState.UNKNOWN)

        self._proxies = {}
        self._talon_sysid_attrs = {}
        self._talon_status_attrs = {}
        self._talon_sysid_events = {}
        self._talon_status_events = {}

        super()._stop_communicating()

    # -------------
    # Fast Commands
    # -------------

    # None so far.

    # ---------------------
    # Long Running Commands
    # ---------------------

    # None so far.

    # ----------------------------------------------------
    # Talon Board Telemetry and Status from Device Proxies
    # ----------------------------------------------------

    # The attribute change callback should get the latest values. But
    # to be safe in case the callback hasn't happened for it, do read_attribute.
    def talon_sysid_version(self) -> str:
        """Returns the bitstream version string"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_sysid_version")

        if self._talon_sysid_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "System ID Device is not available",
                "talon_sysid_version()",
            )
        attr_name = "version"
        if attr_name not in self._talon_sysid_attrs:
            attr = self._proxies[self._talon_sysid_fqdn].read_attribute(
                attr_name
            )
            with self._attr_event_lock:
                self._talon_sysid_attrs[attr_name] = attr.value
        return self._talon_sysid_attrs.get(attr_name)

    def talon_sysid_bitstream(self) -> int:
        """Returns the least 32 bits of md5 checksum of the bitstream name"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_sysid_bitstream")

        if self._talon_sysid_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "System ID Device is not available",
                "talon_sysid_bitstream()",
            )
        attr_name = "bitstream"
        if attr_name not in self._talon_sysid_attrs:
            attr = self._proxies[self._talon_sysid_fqdn].read_attribute(
                attr_name
            )
            with self._attr_event_lock:
                self._talon_sysid_attrs[attr_name] = attr.value
        return self._talon_sysid_attrs.get(attr_name)

    def talon_status_iopll_locked_fault(self) -> bool:
        """Returns the iopll_locked_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_iopll_locked_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_iopll_locked_fault()",
            )
        attr_name = "iopll_locked_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_fs_iopll_locked_fault(self) -> bool:
        """Returns the fs_iopll_locked_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_fs_iopll_locked_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_fs_iopll_locked_fault()",
            )
        attr_name = "fs_iopll_locked_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_comms_iopll_locked_fault(self) -> bool:
        """Returns the comms_iopll_locked_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_comms_iopll_locked_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_comms_iopll_locked_fault()",
            )
        attr_name = "comms_iopll_locked_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_system_clk_fault(self) -> bool:
        """Returns the system_clk_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_system_clk_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_system_clk_fault()",
            )
        attr_name = "system_clk_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_emif_bl_fault(self) -> bool:
        """Returns the emif_bl_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_emif_bl_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_emif_bl_fault()",
            )
        attr_name = "emif_bl_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_emif_br_fault(self) -> bool:
        """Returns the emif_br_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_emif_br_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_emif_br_fault()",
            )
        attr_name = "emif_br_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_emif_tr_fault(self) -> bool:
        """Returns the emif_tr_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_emif_tr_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_emif_tr_fault()",
            )
        attr_name = "emif_tr_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_e100g_0_pll_fault(self) -> bool:
        """Returns the e100g_0_pll_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_e100g_0_pll_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_e100g_0_pll_fault()",
            )
        attr_name = "e100g_0_pll_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_e100g_1_pll_fault(self) -> bool:
        """Returns the e100g_1_pll_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_e100g_1_pll_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_e100g_1_pll_fault()",
            )
        attr_name = "e100g_1_pll_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_slim_pll_fault(self) -> bool:
        """Returns the slim_pll_fault"""
        if self.simulation_mode:
            return SimulatedValues.get("talon_status_slim_pll_fault")

        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_slim_pll_fault()",
            )
        attr_name = "slim_pll_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    # 100g Ethernet
    def eth100g_0_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_0_counters")
        return self._eth_100g_0_client.get_data_counters()

    def eth100g_0_error_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_0_error_counters")
        return self._eth_100g_0_client.get_error_counters()

    def eth100g_0_data_flow_active(self) -> bool:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_0_data_flow_active")
        return self._eth_100g_0_client.has_data_flow()

    def eth100g_0_has_data_error(self) -> bool:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_0_has_data_error")
        return self._eth_100g_0_client.has_error()

    def eth100g_0_all_tx_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_0_all_tx_counters")
        return self._eth_100g_0_client.get_all_tx_counters()

    def eth100g_0_all_rx_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_0_all_rx_counters")
        return self._eth_100g_0_client.get_all_rx_counters()

    def eth100g_1_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_1_counters")
        return self._eth_100g_1_client.get_data_counters()

    def eth100g_1_error_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_1_error_counters")
        return self._eth_100g_1_client.get_error_counters()

    def eth100g_1_data_flow_active(self) -> bool:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_1_data_flow_active")
        return self._eth_100g_1_client.has_data_flow()

    def eth100g_1_has_data_error(self) -> bool:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_1_has_data_error")
        return self._eth_100g_1_client.has_error()

    def eth100g_1_all_tx_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_1_all_tx_counters")
        return self._eth_100g_1_client.get_all_tx_counters()

    def eth100g_1_all_rx_counters(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("eth100g_1_all_rx_counters")
        return self._eth_100g_1_client.get_all_rx_counters()

    # ----------------
    # Helper Functions
    # ----------------

    def _query_if_needed(self) -> None:
        td = datetime.now(timezone.utc) - self._last_check
        if td.total_seconds() > 10:
            try:
                res = asyncio.run(self._db_client.do_queries())
                self._last_check = datetime.now(timezone.utc)
                for result in res:
                    for r in result:
                        # each result is a tuple of (field, time, value)
                        self._telemetry[r[0]] = (r[1], r[2])
            except (
                asyncio.exceptions.TimeoutError,
                asyncio.exceptions.CancelledError,
                Exception,
            ) as e:
                msg = f"Failed to query Influxdb of {self._db_client._hostname}: {e}"  # avoid repeated error logs
                self.logger.error(msg)
                tango.Except.throw_exception(
                    "Query_Influxdb_Error", msg, "query_if_needed()"
                )

    def _validate_time(self, field, t) -> None:
        """
        Checks if the query result is too old. When this happens, it means
        Influxdb hasn't received a new entry in the time series recently.

        :param field: The field for which itsvalue is being validated
        :param t: The timestamp reported from the latest query of the field
        """
        td = datetime.now(timezone.utc) - t
        if td.total_seconds() > 240:
            msg = f"Time of record {field} is too old. Currently not able to monitor device."
            self.logger.error(msg)
            tango.Except.throw_exception(
                "No new record available", msg, "validate_time()"
            )

    # ----------------------------------------------
    # Talon Board Telemetry and Status from Influxdb
    # ----------------------------------------------

    def fpga_die_temperature(self) -> float:
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_temperature")
        self._query_if_needed()
        field = "temperature-sensors_fpga-die-temp"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_0(self) -> float:
        """
        Gets the FPGA Die Voltage [0] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_0")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-0"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_1(self) -> float:
        """
        Gets the FPGA Die Voltage [1] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_1")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-1"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_2(self) -> float:
        """
        Gets the FPGA Die Voltage [2] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_2")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-2"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_3(self) -> float:
        """
        Gets the FPGA Die Voltage [3] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_3")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-3"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_4(self) -> float:
        """
        Gets the FPGA Die Voltage [4] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_4")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-4"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_5(self) -> float:
        """
        Gets the FPGA Die Voltage [5] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_5")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-5"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def fpga_die_voltage_6(self) -> float:
        """
        Gets the FPGA Die Voltage [6] Sensor Value from the Talon Board

        :return: The Sensor Reading in Volts
        :rtype: float
        """
        if self.simulation_mode:
            return SimulatedValues.get("fpga_die_voltage_6")
        self._query_if_needed()
        field = "voltage-sensors_fpga-die-voltage-6"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def humidity_sensor_temperature(self) -> float:
        if self.simulation_mode:
            return SimulatedValues.get("humidity_sensor_temperature")
        self._query_if_needed()
        field = "temperature-sensors_humidity-temp"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def dimm_temperatures(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("dimm_temperatures")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 4):
            field = f"temperature-sensors_dimm-temps_{i}_temp"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_tx_temperatures(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_tx_temperatures")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_temperature"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_tx_vcc_voltages(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_tx_vcc_voltages")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_vcc-3.3-voltage"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_tx_fault_status(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_tx_fault_status")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_tx-fault-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_tx_lol_status(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_tx_lol_status")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_tx-lol-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_tx_los_status(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_tx_los_status")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_tx-los-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_rx_vcc_voltages(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_rx_vcc_voltages")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_RX_vcc-3.3-voltage"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_rx_lol_status(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_rx_lol_status")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_RX_rx-lol-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_rx_los_status(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("mbo_rx_los_status")
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_RX_rx-los-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def has_fan_control(self) -> bool:
        if self.simulation_mode:
            return SimulatedValues.get("has_fan_control")
        # the fan*_input in the fans' MAX31790 driver will return 0
        # if tachometers cannot be read, which either means reading tachometers
        # is not yet enabled, or there is no fan control on this board. Either
        # way the values returned from the fan module should not be used.
        fans_input = self.fans_input()
        return any(x > 0 for x in fans_input)

    def fans_pwm(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("fans_pwm")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_pwm_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(int(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.warning(msg)
                res.append(-1)
        return res

    def fans_pwm_enable(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("fans_pwm_enable")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_pwm-enable_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(int(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.warning(msg)
                res.append(-1)
        return res

    def fans_input(self) -> list[int]:
        if self.simulation_mode:
            return SimulatedValues.get("fans_input")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_fan-input_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(int(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.error(msg)
                res.append(-1)
        return res

    def fans_fault(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("fans_fault")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_fan-fault_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.error(msg)
                res.append(-1)
        return res

    def ltm_input_voltage(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_input_voltage")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_voltage-input"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_input_voltage()",
                )
        return res

    def ltm_output_voltage_1(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_output_voltage_1")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_voltage-output-1"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_voltage_1()",
                )
        return res

    def ltm_output_voltage_2(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_output_voltage_2")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_voltage-output-2"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_voltage_2()",
                )
        return res

    def ltm_input_current(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_input_current")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_current-input"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_input_current()",
                )
        return res

    def ltm_output_current_1(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_output_current_1")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_current-output-1"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_current_1()",
                )
        return res

    def ltm_output_current_2(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_output_current_2")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_current-output-2"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_current_2()",
                )
        return res

    def ltm_temperature_1(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_temperature_1")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_temperature-1"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_temperature_1()",
                )
        return res

    def ltm_temperature_2(self) -> list[float]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_temperature_2")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_temperature-2"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_temperature_2()",
                )
        return res

    def ltm_voltage_warning(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_voltage_warning")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            flag = False
            # Set to true for the LTM if any of the voltage alarm fields is set to 1
            fields = [
                f"LTMs_{i}_LTM_voltage-output-max-alarm-1",
                f"LTMs_{i}_LTM_voltage-output-max-alarm-2",
                f"LTMs_{i}_LTM_voltage-input-crit-alarm",
            ]
            for field in fields:
                if field in self._telemetry:
                    t, val = self._telemetry[field]
                    self._validate_time(field, t)
                    flag = bool(val)
                    if flag:
                        break
            res.append(flag)
        return res

    def ltm_current_warning(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_current_warning")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            flag = False
            # Set to true for the LTM if any of the voltage alarm fields is set to 1
            fields = [
                f"LTMs_{i}_LTM_current-output-max-alarm-1",
                f"LTMs_{i}_LTM_current-output-max-alarm-2",
                f"LTMs_{i}_LTM_current-input-max-alarm",
            ]
            for field in fields:
                if field in self._telemetry:
                    t, val = self._telemetry[field]
                    self._validate_time(field, t)
                    flag = bool(val)
                    if flag:
                        break
            res.append(flag)
        return res

    def ltm_temperature_warning(self) -> list[bool]:
        if self.simulation_mode:
            return SimulatedValues.get("ltm_temperature_warning")
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            flag = False
            # Set to true for the LTM if any of the voltage alarm fields is set to 1
            fields = [
                f"LTMs_{i}_LTM_temperature-max-alarm-1",
                f"LTMs_{i}_LTM_temperature-max-alarm-2",
            ]
            for field in fields:
                if field in self._telemetry:
                    t, val = self._telemetry[field]
                    self._validate_time(field, t)
                    flag = bool(val)
                    if flag:
                        break
            res.append(flag)
        return res
