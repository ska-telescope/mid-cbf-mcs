# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.
#
# """
# HpsFspControllerSimulator Class
#
# This class is used to simulate the behaviour of the HPS FSP controller
# device when the Talon-DX hardware is not connected.
# """

from __future__ import annotations  # allow forward references in type hints

import tango

from ska_mid_cbf_mcs.commons.global_enum import FspModes

__all__ = ["HpsFspControllerSimulator"]


class HpsFspControllerSimulator:
    """
    VccControllerSimulator class used to simulate the behaviour of the HPS FSP
    controller device when the Talon-DX hardware is not connected.

    :param device_name: Identifier for the device instance

    """

    def __init__(
        self: HpsFspControllerSimulator,
        device_name: str,
    ) -> None:
        self.device_name = device_name

        self._state = tango.DevState.INIT
        self._function_mode = FspModes.IDLE.value

    # Methods that match the Tango commands in the band devices
    def State(self: HpsFspControllerSimulator) -> tango.DevState:
        """Get the current state of the device"""
        return self._state

    def SetFunctionMode(
        self: HpsFspControllerSimulator, f_mode: tango.DevEnum
    ) -> None:
        """
        Sets the function mode to be processed on this device.

        :param f_mode: string containing the function mode
        """
        pass
