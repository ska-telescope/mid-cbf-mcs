# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

import asyncio
import logging

from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync


class InfluxdbQueryClient:
    def __init__(
        self,
        hostname: str,
        influx_port: int,
        influx_org: str,
        influx_bucket: str,
        influx_auth_token: str,
        logger: logging.Logger,
    ):
        """
        Initialise a new instance.

        :param hostname: Hostname of the Talon DX board
        :param influx_port: Influxdb port
        :param influx_org: Influxdb organization
        :param influx_bucket: Influxdb bucket to query
        :param influx_auth_token: Influxdb authentication token
        """

        self._hostname = hostname
        self._influx_port = influx_port
        self._influx_org = influx_org
        self._influx_bucket = influx_bucket
        self._influx_auth_token = influx_auth_token

        self._logger = logger
        self._logger.info(
            f"InfluxdbQueryClient: using {self._hostname}:{self._influx_port}"
        )

    async def ping(self) -> bool:
        """
        Check readiness of the InfluxDB via the /ping endpoint

        :return: boolean value. True if ping is successful. False otherwise.
        """
        try:
            async with InfluxDBClientAsync(
                url=f"http://{self._hostname}:{self._influx_port}",
                token=self._influx_auth_token,
                org=self._influx_org,
            ) as client:
                ready = await client.ping()
                self._logger.info(
                    f"Ping InfluxDB at {self._hostname}:{self._influx_port}: {ready}"
                )
                return ready
        except Exception as e:
            self._logger.error(
                f"Unexpected error when pinging InfluxDB at {self._hostname}:{self._influx_port}: {e}"
            )
            return False

    async def do_queries(self):
        """
        The main query function that asynchronously queries
        the Influxdb for all the monitored devices. The results
        are saved to in the dict self._telemetry.

        :return: 2D array of tuples of (field, time, value)
        """
        async with InfluxDBClientAsync(
            url=f"http://{self._hostname}:{self._influx_port}",
            token=self._influx_auth_token,
            org=self._influx_org,
            timeout=2000,
        ) as client:
            res = await asyncio.gather(
                self._query_temperatures(client),
                self._query_mbo_temperatures(client),
                self._query_mbo_voltages(client),
                self._query_fans_pwm(client),
                self._query_fans_fault(client),
                self._query_ltm_voltages(client),
                self._query_ltm_currents(client),
                self._query_ltm_temperatures(client),
            )
            self.logger.info(f"3. RES={res}")
        return res

    async def _query_common(self, client, query: str):
        query_api = client.query_api()
        self.logger.info(f"1. QUERY={query}")
        result = await query_api.query(org=self._influx_org, query=query)
        self.logger.info(f"2. RES={res}")
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

    async def _query_mbo_status(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /MBOs_[0-9]_[TR]X_.*?status$/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_fans_pwm(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /fans_pwm.*?_[0-5]/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_fans_fault(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /fans_fan-fault_[0-5]/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_ltm_voltages(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /LTMs_[0-9]_LTM_voltage.*?/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_ltm_currents(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /LTMs_[0-9]_LTM_current.*?/)\
        |>last()'
        return await self._query_common(client, query)

    async def _query_ltm_temperatures(self, client):
        query = f'from(bucket: "{self._influx_bucket}")\
        |>range(start: -5m)\
        |>filter(fn: (r) => r["_measurement"] == "exec")\
        |>filter(fn: (r) => r["_field"] =~ /LTMs_[0-9]_LTM_temperature.*?/)\
        |>last()'
        return await self._query_common(client, query)
