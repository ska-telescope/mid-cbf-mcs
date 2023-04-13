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
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)


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
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
        check_power_mode_callback: Callable,
    ) -> None:
        """
        Initialise a new instance.

        :param hostname: Hostname of the Talon DX board
        :param influx_port: Influxdb port
        :param influx_org: Influxdb organization
        :param influx_bucket: Influxdb bucket to query
        :param influx_auth_token: Influxdb authentication token
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
        :param check_power_mode_callback: callback to be called in event of
            power switch simulationMode change
        """
        self.connected = False

        self._hostname = hostname
        self._influx_port = influx_port
        self._influx_org = influx_org
        self._influx_bucket = influx_bucket
        self._influx_auth_token = influx_auth_token

        self._last_check = datetime.now() - timedelta(hours=1)
        self._telemetry = dict()

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
        )

        self._logger.info("Using Influxdb {self._hostname}:{self._influx_port}")

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.ON)
        self.connected = True

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = False

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

    def _query_if_needed(self):
        td = datetime.now() - self._last_check
        if td.total_seconds() > 10:
            try:
                asyncio.run(self.do_queries())
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

    # Asynchronus functions to query the influxdb.

    async def _query_common(self, client, query: str):
        query_api = client.query_api()
        result = await query_api.query(org=self._influx_org, query=query)
        results = []
        for table in result:
            for r in table.records:
                results.append((r.get_field(), r.get_time(), r.get_value()))
        return results

    async def _query_temperatures(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /temperature-sensors_.*?temp$/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_mbo_temperatures(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /MBOs_[0-9]_[TR]X_temperature/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_mbo_voltages(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /MBOs_[0-9]_[TR]X_.*?voltage$/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_fans_pwm(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /fans_pwm_[0-5]/)\
        |>last()'
        return await self._query_common(client, query)

    async def do_queries(self):
        """
        The main query function that asynchronously queries
        the Influxdb for all the monitored devices. The results
        are saved to in the dict self._telemetry.
        """
        async with InfluxDBClientAsync(
            url=f"http://{self._hostname}:{self._influx_port}",
            token=self._influx_auth_token,
            org=self._influx_org,
        ) as client:
            res = await asyncio.gather(
                self._query_temperatures(client),
                self._query_mbo_temperatures(client),
                self._query_mbo_voltages(client),
                self._query_fans_pwm(client),
            )
        for result in res:
            for r in result:
                # each result is a tuple of (field, time, value)
                self._telemetry[r[0]] = (r[1], r[2])
