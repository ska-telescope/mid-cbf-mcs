# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

"""
CbfDevice

Generic Tango device for Mid.CBF
"""

from __future__ import annotations

from typing import cast

from ska_control_model import ResultCode
from ska_tango_base.base.base_device import (
    DevVarLongStringArrayType,
    SKABaseDevice,
)
from ska_tango_base.base.component_manager import BaseComponentManager
from ska_tango_base.commands import FastCommand
from tango import DebugIt
from tango.server import attribute, command

__all__ = ["CbfDevice", "main"]

# NOTE: to update max LRC queue size the following constants must be updated
# see TODO in SKABaseDevice for rationale
MAX_QUEUED_COMMANDS = 64
MAX_REPORTED_COMMANDS = 2 * MAX_QUEUED_COMMANDS + 2


class CbfDevice(SKABaseDevice):
    """
    A generic base device for Mid.CBF.
    Extends SKABaseDevice to override certain key values.
    """

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=MAX_QUEUED_COMMANDS
    )
    def longRunningCommandsInQueue(self: CbfDevice) -> list[str]:
        """
        Read the long running commands in the queue.

         Keep track of which commands are in the queue.
         Pop off from front as they complete.

        :return: tasks in the queue
        """
        return self._commands_in_queue

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=MAX_QUEUED_COMMANDS
    )
    def longRunningCommandIDsInQueue(
        self: CbfDevice,
    ) -> list[str]:
        """
        Read the IDs of the long running commands in the queue.

        Every client that executes a command will receive a command ID as response.
        Keep track of IDs in the queue. Pop off from front as they complete.

        :return: unique ids for the enqueued commands
        """
        return self._command_ids_in_queue

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=MAX_REPORTED_COMMANDS * 2  # 2 per command
    )
    def longRunningCommandStatus(self: CbfDevice) -> list[str]:
        """
        Read the status of the currently executing long running commands.

        ID, status pair of the currently executing command.
        Clients can subscribe to on_change event and wait for the
        ID they are interested in.

        :return: ID, status pairs of the currently executing commands
        """
        return self._command_statuses

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: CbfDevice) -> None:
        """Set up the command objects."""
        super().init_command_objects()

        # overriding base On/Off SubmittedSlowCommand register with FastCommand objects
        self.register_command_object(
            "On",
            self.OnCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )
        self.register_command_object(
            "Off",
            self.OffCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    # --------
    # Commands
    # --------

    @command(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype_out="DevVarLongStringArray"
    )
    @DebugIt()  # type: ignore[misc]  # "Untyped decorator makes function untyped"
    def Standby(self: CbfDevice) -> DevVarLongStringArrayType:
        """
        Put the device into standby mode.

        To modify behaviour for this command, modify the do() method of
        the command class.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            [
                "Standby command rejected; Mid.CBF does not currently implement standby state."
            ],
        )

    class OnCommand(FastCommand):
        """
        A class for the CbfDevice's on command.
        """

        def __init__(
            self: CbfDevice.OnCommand,
            *args,
            component_manager: BaseComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: CbfDevice.OnCommand,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.on()

    class OffCommand(FastCommand):
        """
        A class for the CbfDevice's off command.
        """

        def __init__(
            self: CbfDevice.OffCommand,
            *args,
            component_manager: BaseComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: CbfDevice.OffCommand,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.off()


# ----------
# Run server
# ----------


def main(*args: str, **kwargs: str) -> int:
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments

    :return: exit code
    """
    return cast(int, CbfDevice.run_server(args=args or None, **kwargs))


if __name__ == "__main__":
    main()
