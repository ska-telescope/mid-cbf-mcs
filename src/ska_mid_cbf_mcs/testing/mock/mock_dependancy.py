from __future__ import annotations

import datetime
import json
import re
from typing import Any, List

import requests
import influxdb_client.client.influxdb_client_async 

__all__ = ["MockDependancy"]

class MockDependancy:
    
    class Response:
        """A mock class to replace requests.Response."""

        def __init__(
            self: MockDependancy.Response,
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

            self._json: List[dict[str, Any]] = []

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

        def json(self: MockDependancy.Response) -> dict[str, Any]:
            """
            Replace the patched :py:meth:`request.Response.json` with mock.

            This implementation always returns the same key-value pairs.

            :return: representative JSON reponse as the power switch when
                        querying the outlets page
            """

            return self._json
        
    class InfluxDBClientAsync:
        """A mock class to replace influxdb_client_async.InfluxDBClientAsync."""
        
        def __init__(
            self: MockDependancy.InfluxDBClientAsync,
            url: str,
            token:str,
            org:str,
            timeout: int,
            sim_ping_fault: bool,
            sim
        ) -> None:
            """
            Initialise a new instance.

            """
            _sim_ping_fault = sim_ping_fault
            
        def ping(self: MockDependancy.InfluxDBClientAsync) -> bool:
            if self._sim_ping_fault:
                return False
            return True
        
        async def _query_common(self, client, query: str):
            result = {
                {
                    "_time": datetime.now(),
                    "_field": "usage",
                    "_value": 10
                },
                
            }
            results = []
            for table in result:
                for r in table.records:
                    results.append((r.get_field(), r.get_time(), r.get_value()))
            return results