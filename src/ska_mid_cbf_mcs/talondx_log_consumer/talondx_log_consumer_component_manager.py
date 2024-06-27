# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging

from ska_control_model import LoggingLevel
from ska_tango_base.base.base_component_manager import BaseComponentManager
from ska_tango_base.base.logging import (
    _LMC_TO_PYTHON_LOGGING_LEVEL,
    _LMC_TO_TANGO_LOGGING_LEVEL,
    _Log4TangoLoggingLevel,
)
from ska_tango_base.faults import LoggingLevelError
from ska_tango_testing import context

_TANGO_LOGGING_TO_PYTHON_LOGGING_LEVEL = {
    "FATAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


class LogComponentManager(BaseComponentManager):
    def __init__(
        self: LogComponentManager,
        *args: any,
        logging_level: LoggingLevel,
        log_consumer_name: str,
        logger: logging.Logger,
        **kwargs: any,
    ) -> None:
        """
        Update logging config so that certain parts can be overridden

        :param logging_level: log consumer device logging level
        :param log_consumer_name: name of log consumer device
        :param logger: device logger
        :return: An instance of LogComponentManager
        :rtype: LogComponentManager
        """
        # Setting logger.propagate to false fixes the duplicated logs issue (CIP-1674),
        # however logs executed prior to this line will still be duplicated
        logger.propagate = False
        super().__init__(*args, logger=logger, **kwargs)

        self.logging_level = logging_level
        self._name = log_consumer_name

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

    # -----------------
    # Attribute methods
    # -----------------

    @property
    def logging_level(self: LogComponentManager) -> LoggingLevel:
        return self.logging_level

    @logging_level.setter
    def logging_level(self: LogComponentManager, value: LoggingLevel) -> None:
        """
        Sets logging level for the device. Both the Python logger and the
        Tango logger are updated. Overrides the base class attribute to
        accept all log levels coming from HPS devices, but still limit the
        logging level of TalonDxLogConsumer logs.

        :param value: Logging level for logger

        :raises LoggingLevelError: for invalid value
        """
        # Set the logger to DEBUG level so that all logs from the HPS devices
        # are forwarded to the logging targets. The log level for each HPS
        # device is controlled at the HPS device level
        self.logger.setLevel(logging.DEBUG)
        self.logger.tango_logger.set_level(_Log4TangoLoggingLevel.DEBUG)

        # Add a filter for the logging level of the TalonDxLogConsumer
        class TalonDxLogConsumerFilter(logging.Filter):
            """
            Filter for the logging level of the TalonDxLogConsumer.
            """

            def __init__(
                self: TalonDxLogConsumerFilter,
                device_name: str,
                log_level: int,
            ) -> None:
                """
                Create a new instance.

                :param device_name: FQDN of the TalonDxLogConsumer device that this
                    filter is for
                :param log_level: logging level of the TalonDxLogConsumer device
                """
                self.device_name = device_name
                self.log_level = log_level

            def filter(
                self: TalonDxLogConsumerFilter, record: logging.LogRecord
            ) -> bool:
                """
                Filter all TalonDxLogConsumer logs that do not satisfy the log
                    level requirement.
                Also adds the tango-device tag if it does not already exist.

                :param record: log record to filter
                """
                if not hasattr(record, "tags"):
                    record.tags = f"tango-device:{self.device_name}"

                    if self.log_level > record.levelno:
                        return False
                return True

        try:
            lmc_logging_level = LoggingLevel(value)
        except ValueError as value_error:
            raise LoggingLevelError(
                f"Invalid level - {value} - must be one of "
                f"{list(LoggingLevel.__members__.values())} "
            ) from value_error

        self.logging_level = lmc_logging_level

        # Remove all previous filters
        for filt in list(self.logger.filters):
            self.logger.removeFilter(filt)

        # Create new filter
        log_filter = TalonDxLogConsumerFilter(
            self._name, _LMC_TO_PYTHON_LOGGING_LEVEL[lmc_logging_level]
        )
        self.logger.addFilter(log_filter)

        self.logger.tango_logger.set_level(  # type: ignore[attr-defined]
            _LMC_TO_TANGO_LOGGING_LEVEL[lmc_logging_level]
        )
        self.logger.info(
            f"Logging level set to {lmc_logging_level} on Python and Tango loggers"
        )

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
        except Exception as e:
            self.logger.exception(e)
            raise

    def set_log_target(self: LogComponentManager, device_name: str) -> None:
        """Add TalonDxLogConsumer as logging target for a given device"""
        logging_device = context.DeviceProxy(device_name)
        logging_device.add_logging_target(f"device::{self._name}")

    def remove_log_target(self: LogComponentManager, device_name: str) -> None:
        """Remove TalonDxLogConsumer as logging target for a given device"""
        logging_device = context.DeviceProxy(device_name)
        logging_device.remove_logging_target(f"device::{self._name}")
