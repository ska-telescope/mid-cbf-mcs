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
CbfObsDevice

Generic observing device for Mid.CBF
"""

from __future__ import annotations

from typing import cast

from ska_csp_lmc_base.obs.obs_device import CspSubElementObsDevice
from tango.server import attribute

__all__ = ["CbfObsDevice", "main"]


INPUT_QUEUE_SIZE_LIMIT = 32


class CbfObsDevice(CspSubElementObsDevice):
    """
    A generic base observing device for Mid.CBF.
    Extends the CspSubElementObsDevice to override certain key values.
    """

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=INPUT_QUEUE_SIZE_LIMIT
    )
    def longRunningCommandsInQueue(self: CbfObsDevice) -> list[str]:
        """
        Read the long running commands in the queue.

         Keep track of which commands are in the queue.
         Pop off from front as they complete.

        :return: tasks in the queue
        """
        return self._commands_in_queue

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=INPUT_QUEUE_SIZE_LIMIT
    )
    def longRunningCommandIDsInQueue(self: CbfObsDevice) -> list[str]:
        """
        Read the IDs of the long running commands in the queue.

        Every client that executes a command will receive a command ID as response.
        Keep track of IDs in the queue. Pop off from front as they complete.

        :return: unique ids for the enqueued commands
        """
        return self._command_ids_in_queue

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=INPUT_QUEUE_SIZE_LIMIT * 2  # 2 per command
    )
    def longRunningCommandStatus(self: CbfObsDevice) -> list[str]:
        """
        Read the status of the currently executing long running commands.

        ID, status pair of the currently executing command.
        Clients can subscribe to on_change event and wait for the
        ID they are interested in.

        :return: ID, status pairs of the currently executing commands
        """
        return self._command_statuses

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=INPUT_QUEUE_SIZE_LIMIT * 2  # 2 per command
    )
    def longRunningCommandProgress(self: CbfObsDevice) -> list[str]:
        """
        Read the progress of the currently executing long running command.

        ID, progress of the currently executing command.
        Clients can subscribe to on_change event and wait
        for the ID they are interested in.

        :return: ID, progress of the currently executing command.
        """
        return self._command_progresses


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
    return cast(int, CbfObsDevice.run_server(args=args or None, **kwargs))


if __name__ == "__main__":
    main()
