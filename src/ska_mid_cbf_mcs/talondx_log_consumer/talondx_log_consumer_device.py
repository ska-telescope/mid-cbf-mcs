# -*- coding: utf-8 -*-
#
# This file is part of the TalonDxLogConsumer project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging
import re
from typing import List

# tango imports
import tango
from ska_tango_base import SKABaseDevice

# Additional import
# PROTECTED REGION ID(TalonDxLogConsumer.additional_import) ENABLED START #
from ska_tango_base.base.base_device import (
    _LMC_TO_PYTHON_LOGGING_LEVEL,
    _Log4TangoLoggingLevel,
)
from ska_tango_base.commands import BaseCommand, ResultCode
from ska_tango_base.control_model import LoggingLevel
from ska_tango_base.faults import LoggingLevelError
from tango.server import command, run

# PROTECTED REGION END #    //  TalonDxLogConsumer.additional_import

__all__ = ["TalonDxLogConsumer", "main"]


class TalonDxLogConsumer(SKABaseDevice):
    """
    TANGO device class for consuming logs from the Tango devices run on the Talon boards,
    converting them to the SKA format, and outputting them via the logging framework.
    """

    # PROTECTED REGION ID(TalonDxLogConsumer.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  TalonDxLogConsumer.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: TalonDxLogConsumer) -> None:
        # PROTECTED REGION ID(TalonDxLogConsumer.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TalonDxLogConsumer.always_executed_hook

    def delete_device(self: TalonDxLogConsumer) -> None:
        # PROTECTED REGION ID(TalonDxLogConsumer.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TalonDxLogConsumer.delete_device

    def init_command_objects(self: TalonDxLogConsumer) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)
        self.register_command_object("log", self.LogCommand(*device_args))

    # ------------------
    # Attributes methods
    # ------------------

    def write_loggingLevel(self: TalonDxLogConsumer, value: LoggingLevel):
        # PROTECTED REGION ID(SKABaseDevice.loggingLevel_write) ENABLED START #
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

                :param device_name: FQDN of the TalonDxLogConsumer device that this filter is for
                :param log_level: logging level of the TalonDxLogConsumer device
                """
                self.device_name = device_name
                self.log_level = log_level

            def filter(
                self: TalonDxLogConsumerFilter, record: logging.LogRecord
            ) -> bool:
                """
                Filter all TalonDxLogConsumer logs that do not satisfy the log level requirement.
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
            self._logging_level = lmc_logging_level
        except ValueError:
            raise LoggingLevelError(
                "Invalid level - {} - must be one of {} ".format(
                    value, [v for v in LoggingLevel.__members__.values()]
                )
            )

        # Remove all previous filters
        for filt in list(self.logger.filters):
            self.logger.removeFilter(filt)

        # Create new filter
        log_filter = TalonDxLogConsumerFilter(
            self.get_name(), _LMC_TO_PYTHON_LOGGING_LEVEL[lmc_logging_level]
        )
        self.logger.addFilter(log_filter)

    # --------
    # Commands
    # --------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TalonDxLogConsumer's init_device() "command".
        """

        def do(self: TalonDxLogConsumer.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            return super().do()

    class LogCommand(BaseCommand):
        """
        The command class for the log command.
        """

        _TANGO_LOGGING_TO_PYTHON_LOGGING_LEVEL = {
            "FATAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }

        def do(self: TalonDxLogConsumer.LogCommand, argin: List[str]) -> None:
            """
            Implement log command functionality.

            :param argin: the outlet ID of the outlet to switch on
            """
            # Drop the log message if it has invalid arguments, we could log
            # an error here instead but this should not typically be an issue
            try:
                epoch_ms = int(argin[0])
            except ValueError:
                return

            try:
                log_level = self._TANGO_LOGGING_TO_PYTHON_LOGGING_LEVEL[
                    argin[1]
                ]
            except ValueError:
                return

            lineno = 0
            filename = ""
            msg_out = argin[3]
            # Format: [file_path:lineno] log message
            matched = re.match(r"\[(.+?)\:(\d+)\](.+)", argin[3])
            if matched is not None:
                filename = matched.group(1)
                lineno = int(matched.group(2))
                msg_out = matched.group(3)
                filename = filename.split("/")[-1]  # file basename

            # Forward the log message to the logger
            attrdict = {
                "created": epoch_ms / 1000,  # Seconds
                "msecs": epoch_ms % 1000,  # Milliseconds
                "levelname": argin[1],
                "levelno": log_level,
                "threadName": argin[5],
                "funcName": "",
                "filename": filename,
                "lineno": lineno,
                "tags": f"tango-device:{argin[2]}",
                "msg": msg_out,
            }

            # Filter out "LogCommand" messages
            if not ("LogCommand" in attrdict["msg"]):
                rec = logging.makeLogRecord(attrdict)
                self.logger.handle(rec)

    @command(
        dtype_in="DevVarStringArray",
        doc_in="Log consumer input arguments",
    )
    def log(
        self: TalonDxLogConsumer, argin: int
    ) -> tango.DevVarLongStringArray:
        handler = self.get_command_object("log")
        handler(argin)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonDxLogConsumer.main) ENABLED START #
    return run((TalonDxLogConsumer,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonDxLogConsumer.main


if __name__ == "__main__":
    main()
