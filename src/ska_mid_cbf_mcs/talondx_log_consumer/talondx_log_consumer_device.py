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
from typing import List

# tango imports
import tango
from ska_tango_base import SKABaseDevice
from ska_tango_base.base.base_device import (
    _LMC_TO_PYTHON_LOGGING_LEVEL,
    _Log4TangoLoggingLevel,
)
from ska_tango_base.control_model import LoggingLevel
from ska_tango_base.faults import LoggingLevelError
from tango.server import command, run

# Additional import
# PROTECTED REGION ID(TalonDxLogConsumer.additional_import) ENABLED START #
from ska_mid_cbf_mcs.talondx_log_consumer.talondx_log_consumer_component_manager import (
    LogComponentManager,
)

# PROTECTED REGION END #    //  TalonDxLogConsumer.additional_import

__all__ = ["TalonDxLogConsumer", "main"]


class TalonDxLogConsumer(SKABaseDevice):
    """
    TANGO device class for consuming logs from the Tango devices
    run on the Talon boards, converting them to the SKA format,
    and outputting them via the logging framework.
    """

    def create_component_manager(self):
        """Create the component manager LogComponentManager

        :return: Instance of LogComponentManager
        :rtype: LogComponentManager
        """
        return LogComponentManager(self.logger)

    @command(dtype_in=[str], doc_out="Consume a log message from TLS")
    def Log(self, log_message: List[str]):
        """Write the log to stdout as received from TLS

        Sample log:
        ['1650964795495', 'ERROR', 'ska001/elt/master',
        'TangoUtils::DeviceAttributeToCorbaAny() - A Message',
        '', '@7f48dcc80700 [7]']

        Details of the list items here:
        https://tango-controls.readthedocs.io/projects/rfc/
        en/latest/14/Logging.html#log-consumer

        :param log_message: Parts of the TLS log message
        :type log_message: List[str]
        """
        timestamp, tango_log_level, tango_device, message, _, _ = log_message
        self.component_manager.log(
            timestamp, tango_log_level, tango_device, message
        )

    @command(
        dtype_in=str, doc_in="name of the device to add new logging target"
    )
    def SetTalonDxLogConsumerTarget(self, device_name: str) -> None:
        """Add TalonDxLogConsumer as a logging target destination on device"""
        logging_device = tango.DeviceProxy(device_name)
        logging_device.add_logging_target(f"device::{self.get_name()}")

        self.Log(
            [
                "1650964795495",
                "INFO",
                f"device::{self.get_name()}",
                f"TangoUtils::DeviceAttributeToCorbaAny() - Current logging targets: {logging_device.get_logging_target(self)}",
                "",
                "",
            ]
        )

    @command(
        dtype_in=str, doc_in="name of the device to remove logging target"
    )
    def RemoveTalonDxLogConsumerTarget(self, device_name: str) -> None:
        """Remove TalonDxLogConsumer as a logging target destination on device"""
        logging_device = tango.DeviceProxy(device_name)
        logging_device.remove_logging_target(f"device::{self.get_name()}")

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


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonDxLogConsumer.main) ENABLED START #
    return run((TalonDxLogConsumer,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonDxLogConsumer.main


if __name__ == "__main__":
    main()
