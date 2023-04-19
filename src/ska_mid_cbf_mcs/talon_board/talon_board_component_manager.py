# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import tango
from ska_mid_cbf_mcs.talon_board.influxdb_query_client import InfluxdbQueryClient
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy


class TalonBoardComponentManager(CbfComponentManager):
    """
    A component manager for a Talon board. Calls either the power
    switch driver or the power switch simulator based on the value of simulation
    mode.

    :param simulation_mode: simulation mode identifies if the real power switch
                          driver or the simulator should be used
    :param ip: IP address of the power switch
    :param logger: a logger for this object to use
    """

    def __init__(
        self: TalonBoardComponentManager,
        hostname: str,
        influx_port: int,
        influx_org: str,
        influx_bucket: str,
        influx_auth_token: str,        
        talon_sysid_address: str,
        eth_100g_0_address: str,
        eth_100g_1_address: str,
        talon_status_address: str,
        hps_master_address: str,
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new instance.

        :param hostname: Hostname of the Talon DX board
        :param influx_port: Influxdb port
        :param influx_org: Influxdb organization
        :param influx_bucket: Influxdb bucket to query
        :param influx_auth_token: Influxdb authentication token
        :param talon_sysid_address: Talon Sysid DS FQDN
        :param eth_100g_0_address: 100g ethernet 0 DS FQDN
        :param eth_100g_1_address: 100g ethernet 1 DS FQDN
        :param talon_status_address: Talon Status DS FQDN
        :param hps_master_address: HPS Master DS FQDN
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        self.connected = False

        # influxdb
        self._db_client = InfluxdbQueryClient(
            hostname=hostname, 
            influx_port=influx_port, 
            influx_org=influx_org, 
            influx_bucket=influx_bucket, 
            influx_auth_token=influx_auth_token, 
            logger=logger)

        # HPS device proxies
        self._talon_sysid_fqdn = talon_sysid_address
        self._eth_100g_0_fqdn = eth_100g_0_address
        self._eth_100g_1_fqdn = eth_100g_1_address
        self._talon_status_fqdn = talon_status_address
        self._hps_master_fqdn = hps_master_address

        # Subscribed device proxy attributes
        self._talon_sysid_attrs = {}
        self._talon_status_attrs = {}

        self._last_check = datetime.now() - timedelta(hours=1)
        self._telemetry = dict()
        self._proxies = dict()
        self._talon_sysid_events = []
        self._talon_status_events = []

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""
        self._logger.info("Entering TalonBoardComponentManager.start_communicating")

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.ON)
        self.connected = True

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self._logger.info("Entering TalonBoardComponentManager.stop_communicating")
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = False

    def on(self) -> Tuple[ResultCode, str]:
        """
        Turn on Talon Board component. This attempts to establish communication
        with the devices on the HPS, and subscribe to attribute changes.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)

        :raise ConnectionError: if unable to connect to HPS VCC devices
        """
        self._logger.info("Entering TalonBoardComponentManager.on")
        try:
            for fqdn in [self._talon_sysid_fqdn,
                self._eth_100g_0_fqdn,
                self._eth_100g_1_fqdn,
                self._talon_status_fqdn,
                self._hps_master_fqdn]:
                self._proxies[fqdn] = CbfDeviceProxy(
                    fqdn=fqdn, logger=self._logger
                ) 
        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            self.update_component_fault(True)
            return (ResultCode.FAILED, "Failed to connect to HPS devices")

        self._subscribe_change_events()

        # TODO: The InfluxDB takes some time to come up and this ping
        #       fails at the moment. We should make the on command
        #       an asynchronous long running command, and wait for
        #       ping to succeed before flipping device state to ON.
        # ping_res = asyncio.run(self._db_client.ping())
        # if not ping_res:
        #     self._logger.error(f'Cannot ping InfluxDB: {ping_res}')
            # self.update_component_fault(True)
            # return (ResultCode.FAILED, "Failed to connect to InfluxDB")
        
        self._logger.info("Completed TalonBoardComponentManager.on")
        self.update_component_power_mode(PowerMode.ON)
        return (ResultCode.OK, "On command completed OK")
    
    def _subscribe_change_events(self):
        """
        Subscribe to attribute change events from HPS device proxies
        """
        # Talon System ID attributes
        self._talon_sysid_events = []

        e = self._proxies[self._talon_sysid_fqdn].add_change_event_callback(
                            attribute_name='version',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_sysid_events.append(e)
        e = self._proxies[self._talon_sysid_fqdn].add_change_event_callback(
                            attribute_name='Bitstream',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_sysid_events.append(e)
        
        # Talon Status attributes
        self._talon_status_events = []

        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='iopll_locked_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='fs_iopll_locked_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='comms_iopll_locked_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='system_clk_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='emif_bl_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='emif_br_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='emif_tr_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='e100g_0_pll_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='e100g_1_pll_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        e = self._proxies[self._talon_status_fqdn].add_change_event_callback(
                            attribute_name='slim_pll_fault',
                            callback=self._attr_change_callback,
                            stateless=True,)
        self._talon_status_events.append(e)
        # TODO: Add attributes as needed

    def off(self) -> Tuple[ResultCode, str]:
        """
        Turn off Talon Board component; 

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.update_component_power_mode(PowerMode.OFF)

        for ev in self._talon_sysid_events:
            for name, id in ev.items():
                self._logger.info(
                    f"Unsubscribing from event {id}, device: {self._talon_sysid_fqdn}"
                )
                self._proxies[self._talon_sysid_fqdn].remove_event(name, id)
        
        for ev in self._talon_status_events:
            for name, id in ev.items():
                self._logger.info(
                    f"Unsubscribing from event {id}, device: {self._talon_status_fqdn}"
                )
                self._proxies[self._talon_status_fqdn].remove_event(name, id)
            
        return (ResultCode.OK, "Off command completed OK")

    def _attr_change_callback(
        self, 
        fqdn: str,
        name: str,
        value: Any,
        quality: AttrQuality,):
        if value is None:
            self._logger.warning(
                f"None value for attribute {name} of device {fqdn}"
            )
        self._logger.debug(f'Attr Change callback: {name} -> {value}')
        if fqdn == self._talon_sysid_fqdn:
            self._talon_sysid_attrs[name] = value
        elif fqdn == self._talon_status_fqdn:
            self._talon_status_attrs[name] = value
        else:
            self._logger.warning(f'Unexpected change callback from FQDN {fqdn}, attribute = {name}')

    # Talon board telemetry and status from device proxies 
    def talon_sysid_version(self) -> str:
        """Returns the bitstream version string"""
        return self._talon_sysid_attrs.get('version')

    def talon_sysid_bitstream(self) -> int:
        """Returns the least 32 bits of md5 checksum of the bitstream name"""
        return self._talon_sysid_attrs.get('bitstream')

    def talon_status_iopll_locked_fault(self) -> bool:
        """Returns the iopll_locked_fault"""
        return self._talon_status_attrs.get('iopll_locked_fault')

    def talon_status_fs_iopll_locked_fault(self) -> bool:
        """Returns the fs_iopll_locked_fault"""
        return self._talon_status_attrs.get('fs_iopll_locked_fault')

    def talon_status_comms_iopll_locked_fault(self) -> bool:
        """Returns the comms_iopll_locked_fault"""
        return self._talon_status_attrs.get('comms_iopll_locked_fault')

    def talon_status_system_clk_fault(self) -> bool:
        """Returns the system_clk_fault"""
        return self._talon_status_attrs.get('system_clk_fault')

    def talon_status_emif_bl_fault(self) -> bool:
        """Returns the emif_bl_fault"""
        return self._talon_status_attrs.get('emif_bl_fault')

    def talon_status_emif_br_fault(self) -> bool:
        """Returns the emif_br_fault"""
        return self._talon_status_attrs.get('emif_br_fault')

    def talon_status_emif_tr_fault(self) -> bool:
        """Returns the emif_tr_fault"""
        return self._talon_status_attrs.get('emif_tr_fault')

    def talon_status_e100g_0_pll_fault(self) -> bool:
        """Returns the e100g_0_pll_fault"""
        return self._talon_status_attrs.get('e100g_0_pll_fault')

    def talon_status_e100g_1_pll_fault(self) -> bool:
        """Returns the e100g_1_pll_fault"""
        return self._talon_status_attrs.get('e100g_1_pll_fault')

    def talon_status_slim_pll_fault(self) -> bool:
        """Returns the slim_pll_fault"""
        return self._talon_status_attrs.get('slim_pll_fault')

    # TODO: read attributes 100G 

    # Talon board telemetry and status from Influxdb 
    def fpga_die_temperature(self) -> float:
        self._query_if_needed()
        field = "temperature-sensors_fpga-die-temp"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def humidity_sensor_temperature(self) -> float:
        self._query_if_needed()
        field = "temperature-sensors_humidity-temp"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def dimm_temperatures(self) -> list[float]:
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

    def mbo_tx_fault_status(self):
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

    def mbo_tx_lol_status(self):
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

    def mbo_tx_los_status(self):
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

    def mbo_rx_lol_status(self):
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

    def mbo_rx_los_status(self):
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

    def fans_pwm(self) -> list[int]:
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
                self._logger.warn(msg)
                res.append(-1)
        return res

    def fans_pwm_enable(self) -> list[int]:
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
                self._logger.warn(msg)
                res.append(-1)
        return res

    def fans_fault(self) -> list[bool]:
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
                self._logger.warn(msg)
                res.append(-1)
        return res

    def _query_if_needed(self):
        td = datetime.now() - self._last_check
        if td.total_seconds() > 10:
            try:
                res = asyncio.run(self._db_client.do_queries())
                for result in res:
                    for r in result:
                        # each result is a tuple of (field, time, value)
                        self._telemetry[r[0]] = (r[1], r[2])
            except Exception as e:
                msg = f"Failed to query Influxdb of {self._hostname}: {e}"
                self._logger.error(msg)
                tango.Except.throw_exception(
                    "Query_Influxdb_Error", msg, "query_if_needed()"
                )

    def _validate_time(self, field, t) -> None:
        """
        Checks if the query result is too old

        :param record: a record from Influxdb query result
        """
        td = datetime.now(timezone.utc) - t
        if td.total_seconds() > 60:
            msg = f"Time of record {field} is too old. Currently not able to monitor device."
            self._logger.warn(msg)
