# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements infrastructure for mocking commands."""
from __future__ import annotations  # allow forward references in type hints

import time
import unittest.mock
import uuid

from ska_control_model import ResultCode

__all__ = ["MockCommand"]


class MockCommand:
    """
    This class implements a mock Tango command callable.
    """

    def __init__(
        self: MockCommand,
        return_value: any = None,
        is_lrc: bool = False,
        mock_device: unittest.mock.Mock = None,
    ):
        """
        Initialise a new instance.

        :param return_value: what to return when called
        :param is_lrc: True if this is a mock LRC, in which case change events
            must be mocked; defaults to False
        :param mock_device: mock device containing attribute change event callbacks,
            necessary only for LRCs
        """
        self._return_value: any = return_value
        self._is_lrc = is_lrc
        self._mock_device = mock_device

    def __call__(self: MockCommand, *args: any, **kwargs: any) -> any:
        """
        Handle a call to this mock command.

        For a fast command (`is_lrc == False`) the stored return value is immediately
        returned.
        For a long-running command (`is_lrc == True`) the return value supplied
        must be a dictionary containing certain key parameters:
        - "name": str - LRC name
        - "queued": bool - True if the LRC should return ResultCode.QUEUED, False
          if it should return ResultCode.REJECTED
        - "result_code": ResultCode - what ResultCode to push to the `lrcFinished`
          attribute change event callback
        - "message": str - what message string to push to the `lrcFinished`
          attribute change event callback
        - "attr_values": dict - optional dictionary of attribute names and values to push
          change events for
        - "sleep_time_s": int - optional time value in seconds to wait between each
          change event callback

        ```
        {
            "name": name,               # LRC name
            "queued": queued,           # True if the LRC should return ResultCode.QUEUED
            "result_code": result_code,
            "message": message,
            "attr_values": attr_values,
            "sleep_time_s": sleep_time_s,
        }
        ```

        :param args: positional args in the call
        :param kwargs: keyword args in the call

        :return: the object's return value
        """
        called_mock = unittest.mock.Mock()
        called_mock(*args, **kwargs)

        # If FastCommand, simply return the return value
        if not self._is_lrc:
            return self._return_value

        # If LRC, return value should be a dict to parse
        # First check if we want to return ResultCode.QUEUED or REJECTED
        if self._return_value["queued"]:
            name = self._return_value["name"]
            result_code = self._return_value["result_code"]
            message = self._return_value["message"]
            attr_values = self._return_value["attr_values"]
            sleep_time_s = self._return_value["sleep_time_s"]

            # Add LRC result value and push all attribute change events
            command_id = f"{time.time()}_{uuid.uuid4().fields[-1]}_{name}"
            attr_values["lrcFinished"] = (
                f"{command_id}",
                f"[{result_code.value}, {message}]",
            )
            for attr_name, attr_value in self._return_value[
                "attr_values"
            ].items():
                callback = self._mock_device.attr_change_event_callbacks[
                    attr_name
                ]
                self._mock_device.mock_event(
                    attr_name=attr_name,
                    attr_value=attr_value,
                    callback=callback,
                    sleep_time_s=sleep_time_s,
                )

            return [[ResultCode.QUEUED], [command_id]]

        return [[ResultCode.REJECTED], ["Command is not allowed"]]
