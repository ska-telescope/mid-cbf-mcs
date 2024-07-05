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

from ska_control_model import LoggingLevel

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.base.logging import (
    _LMC_TO_PYTHON_LOGGING_LEVEL,
    _LMC_TO_TANGO_LOGGING_LEVEL,
)
from ska_tango_base.faults import LoggingLevelError
from tango.server import command

from ska_mid_cbf_mcs.device.base_device import CbfFastCommand
from ska_mid_cbf_mcs.talondx_log_consumer.talondx_log_consumer_component_manager import (
    LogComponentManager,
)

__all__ = ["TalonDxLogConsumer", "main"]


class TalonDxLogConsumer(SKABaseDevice):
    """
    TANGO device class for consuming logs from the Tango devices
    run on the Talon boards, converting them to the SKA format,
    and outputting them via the logging framework.
    """

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: TalonDxLogConsumer) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        self.register_command_object(
            "Log",
            self.LogCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

        self.register_command_object(
            "SetTalonDxLogConsumerTarget",
            self.SetTalonDxLogConsumerTargetCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

        self.register_command_object(
            "RemoveTalonDxLogConsumerTarget",
            self.RemoveTalonDxLogConsumerTargetCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    def create_component_manager(self):
        """Create the component manager LogComponentManager

        :return: Instance of LogComponentManager
        :rtype: LogComponentManager
        """
        return LogComponentManager(
            logging_level=self._logging_level,
            log_consumer_name=self.get_name(),
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def set_logging_level(
        self: TalonDxLogConsumer, value: LoggingLevel
    ) -> None:
        """
        Sets logging level for the device. Both the Python logger and the
        Tango logger are updated. Overrides the base class attribute to
        accept all log levels coming from HPS devices, but still limit the
        logging level of TalonDxLogConsumer logs.

        :param value: Logging level for logger

        :raises LoggingLevelError: for invalid value
        """
        # Setting logger.propagate to False fixes the duplicated logs issue (CIP-1674)
        if self.logger.propagate:
            self.logger.propagate = False

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

        # Store old logging level for filter removal later
        previous_logging_level = self._logging_level

        try:
            self._logging_level = LoggingLevel(value)
        except ValueError as value_error:
            raise LoggingLevelError(
                f"Invalid level - {value} - must be one of "
                f"{list(LoggingLevel.__members__.values())} "
            ) from value_error

        # Remove previously applied filter
        if previous_logging_level is not None:
            self.logger.removeFilter(
                TalonDxLogConsumerFilter(
                    self.get_name(),
                    _LMC_TO_PYTHON_LOGGING_LEVEL[previous_logging_level],
                )
            )

        # Set the logger to DEBUG level so that all logs from the HPS devices
        # are forwarded to the logging targets. The log level for each HPS
        # device is controlled at the HPS device level
        self.logger.setLevel(_LMC_TO_PYTHON_LOGGING_LEVEL[LoggingLevel.DEBUG])
        self.logger.tango_logger.set_level(
            _LMC_TO_TANGO_LOGGING_LEVEL[LoggingLevel.DEBUG]
        )

        # Add new filter
        log_filter = TalonDxLogConsumerFilter(
            self.get_name(), _LMC_TO_PYTHON_LOGGING_LEVEL[self._logging_level]
        )
        self.logger.addFilter(log_filter)

    # --------
    # Commands
    # --------

    class LogCommand(CbfFastCommand):
        """
        A class for the TalonDxLogConsumer's Log command.
        """

        def do(
            self: TalonDxLogConsumer.LogCommand, log_message: list[str]
        ) -> None:
            """
            Stateless hook for Log command functionality.

            :param log_message: Parts of the TLS log message
            """
            (
                timestamp,
                tango_log_level,
                tango_device,
                message,
                _,
                _,
            ) = log_message
            self.component_manager.log(
                timestamp, tango_log_level, tango_device, message
            )

    @command(dtype_in=[str], doc_out="Consume a log message from TLS")
    def Log(self, log_message: list[str]) -> None:
        """
        Write the log to stdout as received from TLS

        Sample log:
        ['1650964795495', 'ERROR', 'ska001/elt/master',
        'TangoUtils::DeviceAttributeToCorbaAny() - A Message',
        '', '@7f48dcc80700 [7]']

        Details of the list items here:
        https://tango-controls.readthedocs.io/projects/rfc/
        en/latest/14/Logging.html#log-consumer

        :param log_message: Parts of the TLS log message
        :type log_message: list[str]
        """
        command_handler = self.get_command_object(command_name="Log")
        command_handler(log_message)

    class SetTalonDxLogConsumerTargetCommand(CbfFastCommand):
        """
        A class for the TalonDxLogConsumer's SetTalonDxLogConsumerTarget command.
        """

        def do(
            self: TalonDxLogConsumer.SetTalonDxLogConsumerTarget,
            device_name: str,
        ) -> None:
            """
            Stateless hook for SetTalonDxLogConsumerTarget command functionality.

            :param device_name: FQDN of target device
            """
            self.component_manager.add_logging_target(
                target=self.get_name(), device_name=device_name
            )

    @command(
        dtype_in=str, doc_in="FQDN of device to receive new logging target"
    )
    def SetTalonDxLogConsumerTarget(self, device_name: str) -> None:
        """
        Add TalonDxLogConsumer as a logging target destination on device

        :param device_name: FQDN of target device
        """
        command_handler = self.get_command_object(
            command_name="SetTalonDxLogConsumerTarget"
        )
        command_handler(device_name)

    class RemoveTalonDxLogConsumerTargetCommand(CbfFastCommand):
        """
        A class for the TalonDxLogConsumer's RemoveTalonDxLogConsumerTarget command.
        """

        def do(
            self: TalonDxLogConsumer.RemoveTalonDxLogConsumerTarget,
            device_name: str,
        ) -> None:
            """
            Stateless hook for SetTalonDxLogConsumerTarget command functionality.

            :param device_name: FQDN of target device
            """
            self.component_manager.remove_logging_target(
                target=self.get_name(), device_name=device_name
            )

    @command(
        dtype_in=str, doc_in="FQDN of device to remove logging target from"
    )
    def RemoveTalonDxLogConsumerTarget(self, device_name: str) -> None:
        """
        Remove TalonDxLogConsumer as a logging target destination on device

        :param device_name: FQDN of target device
        """
        command_handler = self.get_command_object(
            command_name="RemoveTalonDxLogConsumerTarget"
        )
        command_handler(device_name)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return TalonDxLogConsumer.run_server(args=args, **kwargs)


if __name__ == "__main__":
    main()
