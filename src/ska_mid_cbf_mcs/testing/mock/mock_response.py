from __future__ import annotations

import json
import re
from typing import Any, List

import requests

__all__ = ["MockResponse"]


class MockResponse:
    """A mock class to replace requests.Response."""

    def __init__(
        self: MockResponse,
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
        
        # Would need to parametrize for this logic in the MockResponse constructor
        # These state code work for st switch 2 driver, hard written
        # sim_state = "On" if sim_state else "Off"

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

    def json(self: MockResponse) -> dict[str, Any]:
        """
        Replace the patched :py:meth:`request.Response.json` with mock.

        This implementation always returns the same key-value pairs.

        :return: representative JSON reponse as the power switch when
                    querying the outlets page
        """

        return self._json
