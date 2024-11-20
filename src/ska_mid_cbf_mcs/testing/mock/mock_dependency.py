from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

import requests
from pysnmp import error as snmp_error

__all__ = ["MockDependency"]


class MockDependency:
    class ResponseSNMP:
        """A mock class to replace requests.ResponseSNMP."""

        def do(
            self: MockDependency.ResponseSNMP,
            simulate_response_error: bool,
            sim_state: bool,
        ) -> tuple:
            if simulate_response_error:
                raise snmp_error.PySnmpError()

            state = 1 if sim_state else 2

            errorIndication = None
            errorStatus = None
            errorIndex = None

            varBinds = [(1, state)]

            return (errorIndication, errorStatus, errorIndex, varBinds)

    class Response:
        """A mock class to replace requests.Response."""

        def __init__(
            self: MockDependency.Response,
            url: str,
            simulate_response_error: bool,
            sim_state: bool,
        ) -> None:
            """
            Initialise a new instance.

            :param url: URL of the request
            :param simulate_response_error: set to True to simulate error response
            """
            outlet_state_url = re.compile(
                r"http:\/\/[\d.]+\/restapi\/relay\/outlets\/\d+\/"
            )
            outlet_list_url = re.compile(
                r"http:\/\/[\d.]+\/restapi\/relay\/outlets\/"
            )

            self._json: list[dict[str, any]] = []

            if simulate_response_error:
                self.status_code = 404
            else:
                self.status_code = requests.codes.ok

                for i in range(0, 8):
                    outlet_cfg = {
                        "name": f"Outlet {i}",
                        "locked": False,
                        "critical": False,
                        "cycle_delay": 0,
                        "state": sim_state,
                        "physical_state": True,
                        "transient_state": True,
                    }

                    self._json.append(outlet_cfg)

                if outlet_list_url.fullmatch(url):
                    self.text = json.dumps(self._json)

                elif outlet_state_url.fullmatch(url):
                    url.split("/")
                    outlet = url[-2]

                    self._json = self._json[int(outlet)]
                    self.text = json.dumps(self._json)

        def json(self: MockDependency.Response) -> dict[str, any]:
            """
            Replace the patched :py:meth:`request.Response.json` with mock.

            This implementation always returns the same key-value pairs.

            :return: representative JSON reponse as the power switch when
                        querying the outlets page
            """

            return self._json

    class Asyncio:
        """A mock class to replace Asyncio"""

        def __init__(
            self: MockDependency.Asyncio,
        ) -> None:
            return

        def run(self: MockDependency.Asyncio, result: any) -> any:
            return result

    class InfluxdbQueryClient:
        """A mock class to replace InfluxdbQueryClient"""

        def __init__(
            self: MockDependency.InfluxdbQueryClient,
            sim_ping_fault: Optional[bool] = False,
        ) -> None:
            """
            Initialize a new instance.

            """
            self._sim_ping_fault = sim_ping_fault

        async def ping(self) -> bool:
            if self._sim_ping_fault:
                return False
            return True

        async def do_queries(
            self: MockDependency.InfluxdbQueryClient,
        ) -> list[list]:
            return [
                # _query_temperatures
                [
                    (
                        "temperature-sensors_fpga-die-temp",
                        datetime.now(),
                        32.0,
                    ),
                    (
                        "temperature-sensors_humidity-temp",
                        datetime.now(),
                        32.0,
                    ),
                    (
                        "temperature-sensors_dimm-temps_0_temp",
                        datetime.now(),
                        32.0,
                    ),
                    (
                        "temperature-sensors_dimm-temps_1_temp",
                        datetime.now(),
                        32.0,
                    ),
                    (
                        "temperature-sensors_dimm-temps_2_temp",
                        datetime.now(),
                        32.0,
                    ),
                    (
                        "temperature-sensors_dimm-temps_3_temp",
                        datetime.now(),
                        32.0,
                    ),
                ],
                # _query_voltages
                [
                    (
                        "voltage-sensors_fpga-die-voltage-0",
                        datetime.now(),
                        12.0,
                    ),
                    (
                        "voltage-sensors_fpga-die-voltage-1",
                        datetime.now(),
                        2.5,
                    ),
                    (
                        "voltage-sensors_fpga-die-voltage-2",
                        datetime.now(),
                        0.8,
                    ),
                    (
                        "voltage-sensors_fpga-die-voltage-3",
                        datetime.now(),
                        1.8,
                    ),
                    (
                        "voltage-sensors_fpga-die-voltage-4",
                        datetime.now(),
                        1.8,
                    ),
                    (
                        "voltage-sensors_fpga-die-voltage-5",
                        datetime.now(),
                        0.9,
                    ),
                    (
                        "voltage-sensors_fpga-die-voltage-6",
                        datetime.now(),
                        1.8,
                    ),
                ],
                # _query_mbo_temperatures
                [
                    ("MBOs_0_TX_temperature", datetime.now(), 32.0),
                    ("MBOs_1_TX_temperature", datetime.now(), 32.0),
                    ("MBOs_2_TX_temperature", datetime.now(), 32.0),
                    ("MBOs_3_TX_temperature", datetime.now(), 32.0),
                    ("MBOs_4_TX_temperature", datetime.now(), 32.0),
                    #     ("MBOs_0_RX_temperature", datetime.now(), 32.0),
                    #     ("MBOs_1_RX_temperature", datetime.now(), 32.0),
                    #     ("MBOs_2_RX_temperature", datetime.now(), 32.0),
                    #     ("MBOs_3_RX_temperature", datetime.now(), 32.0),
                    #     ("MBOs_4_RX_temperature", datetime.now(), 32.0),
                ],
                # _query_mbo_voltages
                [
                    ("MBOs_0_TX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_1_TX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_2_TX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_3_TX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_4_TX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_0_RX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_1_RX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_2_RX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_3_RX_vcc-3.3-voltage", datetime.now(), 3.3),
                    ("MBOs_4_RX_vcc-3.3-voltage", datetime.now(), 3.3),
                ],
                # _query_mbo_faults
                [
                    ("MBOs_0_TX_tx-fault-status", datetime.now(), False),
                    ("MBOs_1_TX_tx-fault-status", datetime.now(), False),
                    ("MBOs_2_TX_tx-fault-status", datetime.now(), False),
                    ("MBOs_3_TX_tx-fault-status", datetime.now(), False),
                    ("MBOs_4_TX_tx-fault-status", datetime.now(), False),
                ],
                # _query_mbo_lol
                [
                    ("MBOs_0_TX_tx-lol-status", datetime.now(), False),
                    ("MBOs_1_TX_tx-lol-status", datetime.now(), False),
                    ("MBOs_2_TX_tx-lol-status", datetime.now(), False),
                    ("MBOs_3_TX_tx-lol-status", datetime.now(), False),
                    ("MBOs_4_TX_tx-lol-status", datetime.now(), False),
                    ("MBOs_0_RX_rx-lol-status", datetime.now(), False),
                    ("MBOs_1_RX_rx-lol-status", datetime.now(), False),
                    ("MBOs_2_RX_rx-lol-status", datetime.now(), False),
                    ("MBOs_3_RX_rx-lol-status", datetime.now(), False),
                    ("MBOs_4_RX_rx-lol-status", datetime.now(), False),
                ],
                # _query_mbo_los
                [
                    ("MBOs_0_TX_tx-los-status", datetime.now(), False),
                    ("MBOs_1_TX_tx-los-status", datetime.now(), False),
                    ("MBOs_2_TX_tx-los-status", datetime.now(), False),
                    ("MBOs_3_TX_tx-los-status", datetime.now(), False),
                    ("MBOs_4_TX_tx-los-status", datetime.now(), False),
                    ("MBOs_0_RX_rx-los-status", datetime.now(), False),
                    ("MBOs_1_RX_rx-los-status", datetime.now(), False),
                    ("MBOs_2_RX_rx-los-status", datetime.now(), False),
                    ("MBOs_3_RX_rx-los-status", datetime.now(), False),
                    ("MBOs_4_RX_rx-los-status", datetime.now(), False),
                ],
                # _query_fans_input
                [
                    ("fans_fan-input_0", datetime.now(), 100),
                    ("fans_fan-input_1", datetime.now(), 100),
                    ("fans_fan-input_2", datetime.now(), 100),
                    ("fans_fan-input_3", datetime.now(), 100),
                ],
                # _query_fans_pwm
                [
                    ("fans_pwm_0", datetime.now(), 255),
                    ("fans_pwm_1", datetime.now(), 255),
                    ("fans_pwm_2", datetime.now(), 255),
                    ("fans_pwm_3", datetime.now(), 255),
                ],
                # _query_fans_pwm_enable
                [
                    ("fans_pwm-enable_0", datetime.now(), 1),
                    ("fans_pwm-enable_1", datetime.now(), 1),
                    ("fans_pwm-enable_2", datetime.now(), 1),
                    ("fans_pwm-enable_3", datetime.now(), 1),
                ],
                # _query_fans_fault
                [
                    ("fans_fan-fault_0", datetime.now(), False),
                    ("fans_fan-fault_1", datetime.now(), False),
                    ("fans_fan-fault_2", datetime.now(), False),
                    ("fans_fan-fault_3", datetime.now(), False),
                ],
                # _query_ltm_voltages
                [
                    ("LTMs_0_LTM_voltage-input", datetime.now(), 12.0),
                    ("LTMs_1_LTM_voltage-input", datetime.now(), 12.0),
                    ("LTMs_2_LTM_voltage-input", datetime.now(), 12.0),
                    ("LTMs_3_LTM_voltage-input", datetime.now(), 12.0),
                    ("LTMs_0_LTM_voltage-output-1", datetime.now(), 1.5),
                    ("LTMs_1_LTM_voltage-output-1", datetime.now(), 1.5),
                    ("LTMs_2_LTM_voltage-output-1", datetime.now(), 1.5),
                    ("LTMs_3_LTM_voltage-output-1", datetime.now(), 1.5),
                    ("LTMs_0_LTM_voltage-output-2", datetime.now(), 1.5),
                    ("LTMs_1_LTM_voltage-output-2", datetime.now(), 1.5),
                    ("LTMs_2_LTM_voltage-output-2", datetime.now(), 1.5),
                    ("LTMs_3_LTM_voltage-output-2", datetime.now(), 1.5),
                    (
                        "LTMs_0_LTM_voltage-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_voltage-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_voltage-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_voltage-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_0_LTM_voltage-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_voltage-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_voltage-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_voltage-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_0_LTM_voltage-input-crit-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_voltage-input-crit-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_voltage-input-crit-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_voltage-input-crit-alarm",
                        datetime.now(),
                        False,
                    ),
                ],
                # _query_ltm_currents
                [
                    ("LTMs_0_LTM_current-input", datetime.now(), 1.0),
                    ("LTMs_1_LTM_current-input", datetime.now(), 1.0),
                    ("LTMs_2_LTM_current-input", datetime.now(), 1.0),
                    ("LTMs_3_LTM_current-input", datetime.now(), 1.0),
                    ("LTMs_0_LTM_current-output-1", datetime.now(), 1.0),
                    ("LTMs_1_LTM_current-output-1", datetime.now(), 1.0),
                    ("LTMs_2_LTM_current-output-1", datetime.now(), 1.0),
                    ("LTMs_3_LTM_current-output-1", datetime.now(), 1.0),
                    ("LTMs_0_LTM_current-output-2", datetime.now(), 1.0),
                    ("LTMs_1_LTM_current-output-2", datetime.now(), 1.0),
                    ("LTMs_2_LTM_current-output-2", datetime.now(), 1.0),
                    ("LTMs_3_LTM_current-output-2", datetime.now(), 1.0),
                    (
                        "LTMs_0_LTM_current-input-max-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_current-input-max-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_current-input-max-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_current-input-max-alarm",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_0_LTM_current-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_current-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_current-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_current-output-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_0_LTM_current-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_current-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_current-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_current-output-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                ],
                # _query_ltm_temperatures
                [
                    ("LTMs_0_LTM_temperature-1", datetime.now(), 32.0),
                    ("LTMs_1_LTM_temperature-1", datetime.now(), 32.0),
                    ("LTMs_2_LTM_temperature-1", datetime.now(), 32.0),
                    ("LTMs_3_LTM_temperature-1", datetime.now(), 32.0),
                    ("LTMs_0_LTM_temperature-2", datetime.now(), 32.0),
                    ("LTMs_1_LTM_temperature-2", datetime.now(), 32.0),
                    ("LTMs_2_LTM_temperature-2", datetime.now(), 32.0),
                    ("LTMs_3_LTM_temperature-2", datetime.now(), 32.0),
                    (
                        "LTMs_0_LTM_temperature-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_temperature-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_temperature-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_temperature-max-alarm-1",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_0_LTM_temperature-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_1_LTM_temperature-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_2_LTM_temperature-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                    (
                        "LTMs_3_LTM_temperature-max-alarm-2",
                        datetime.now(),
                        False,
                    ),
                ],
            ]
