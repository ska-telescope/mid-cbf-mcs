# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging

from ska_tango_base.base.base_component_manager import BaseComponentManager
from ska_tango_testing import context
from tango import DevFailed

_TANGO_LOGGING_TO_PYTHON_LOGGING_LEVEL = {
    "FATAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


class LogComponentManager(BaseComponentManager):
    """
    Component manager for TalonDxLogConsumer device
    """

    def __init__(
        self: LogComponentManager,
        *args: any,
        logger: logging.Logger,
        **kwargs: any,
    ) -> None:
        """
        Update logging config so that certain parts can be overridden

        :param logger: device logger
        :return: An instance of LogComponentManager
        :rtype: LogComponentManager
        """

        super().__init__(*args, logger=logger, **kwargs)

        class TangoDeviceTagsFilter(logging.Filter):
            """Reset the log record components if a TLS log"""

            @classmethod
            def filter(cls, record):
                # Log a TLS log
                if hasattr(record, "device_name"):
                    try:
                        source, funcName = record.src_funcName.split(" ", 1)
                        filename, lineno = source[1:-1].split(":")
                    except Exception:
                        funcName = record.src_funcName
                        filename = record.filename
                        lineno = record.lineno

                    record.tags = f"tango-device:{record.device_name}"
                    record.filename = filename
                    record.funcName = funcName
                    record.created = record.timestamp
                    record.lineno = int(lineno)
                return True

        self.logger.addFilter(TangoDeviceTagsFilter())

    # ---------------
    # Command methods
    # ---------------

    def log(
        self: LogComponentManager,
        timestamp: str,
        tango_log_level: str,
        tango_device: str,
        message: str,
    ) -> None:
        """
        Override log components and log to stdout.

        :param timestamp: The millisecond since epoch (01.01.1970)
        :type timestamp: str
        :param tango_log_level: The log level
        :type tango_log_level: str
        :param tango_device: The tango device
        :type tango_device: str
        :param message: The message to log
        :type message: str
        """
        try:
            function_name = ""
            if " - " in message:
                function_name, message = message.split(" - ", 1)

            log_level = _TANGO_LOGGING_TO_PYTHON_LOGGING_LEVEL[tango_log_level]
            log_timestamp = float(timestamp) / 1000
            self.logger.log(
                log_level,
                message,
                extra={
                    "device_name": tango_device,
                    "src_funcName": function_name,
                    "timestamp": log_timestamp,
                },
            )
        except KeyError as ke:
            self.logger.error(
                f"Invalid log level received: {tango_log_level}\n{ke}"
            )
        except BaseException as be:
            self.logger.exception(be)
            raise

    def add_logging_target(
        self: LogComponentManager, target: str, device_name: str
    ) -> None:
        """Add TalonDxLogConsumer as logging target for a given device"""
        try:
            logging_device = context.DeviceProxy(device_name)
            logging_device.add_logging_target(f"device::{target}")
        except DevFailed as df:
            self.logger.error(
                f"Failed to add logging target {target} for {device_name}; {df}"
            )

    def remove_logging_target(
        self: LogComponentManager, target: str, device_name: str
    ) -> None:
        """Remove TalonDxLogConsumer as logging target for a given device"""
        try:
            logging_device = context.DeviceProxy(device_name)
            logging_device.remove_logging_target(f"device::{target}")
        except DevFailed as df:
            self.logger.error(
                f"Failed to remove logging target {target} from {device_name}; {df}"
            )
