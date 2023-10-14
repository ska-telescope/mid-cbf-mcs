# -*- coding: utf-8 -*-
#
# This file is part of the SlimLink project
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
# PROTECTED REGION ID(SlimLink.additional_import) ENABLED START #
from ska_mid_cbf_mcs.slim_link.slim_link_component_manager import (
    SlimLinkComponentManager,
)

# PROTECTED REGION END #    //  SlimLink.additional_import

__all__ = ["SlimLink", "main"]


class SlimLink(SKABaseDevice):
    """
    TANGO device class for slim link device
    """

    # PROTECTED REGION ID(SlimLink.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  SlimLink.class_variable

    # -----------------
    # Device Properties
    # -----------------

    TxDeviceName = device_property(dtype="str")

    RxDeviceName = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    slim_link_is_active = attribute(
        dtype="bool",
        access=AttrWriteType.READ_WRITE,
        label="Indicator for whether link is active or inactive",
        doc="Indicator for whether link is active or inactive",
    )

    # TODO CIP-1768 determine enum_labels and how many attributes we need for the status
    slim_link_status = attribute(
        dtype="DevEnum",
        access=AttrWriteType.READ,
        label="Slim link status",
        doc="Slim link status from polling Tx-Rx HPS devices",
        enum_labels=[
            "1",
            "2",
            "3",
            "4",
        ],
    )
    
    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SlimLink.always_executed_hook

    def delete_device(self: SlimLink) -> None:
        # PROTECTED REGION ID(SlimLink.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SlimLink.delete_device

    def init_command_objects(self: SlimLink) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        # device_args = (self, self.op_state_model, self.logger)

        # self.register_command_object("On", self.OnCommand(*device_args))

        # self.register_command_object("Off", self.OffCommand(*device_args))

    # ----------
    # Callbacks
    # ----------

    # --------
    # Commands
    # --------

    def create_component_manager(self):
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return SlimLinkComponentManager(
            tx_device_name=self.TxDeviceName,
            rx_device_name=self.RxDeviceName,
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )
    
    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the SlimLink's init_device() "command".
        """

        def do(self: SlimLink.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            return super().do()

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.

        Initializes HPS device proxies and starts listening to
        attribute change events
        """

        def do(self: SlimLink.OnCommand) -> Tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.on()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.

        Stops listening to attribute change events
        """

        def do(self: SlimLink.OffCommand) -> Tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.off()


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(SlimLink.main) ENABLED START #
    return run((SlimLink,), args=args, **kwargs)
    # PROTECTED REGION END #    //  SlimLink.main


if __name__ == "__main__":
    main()
