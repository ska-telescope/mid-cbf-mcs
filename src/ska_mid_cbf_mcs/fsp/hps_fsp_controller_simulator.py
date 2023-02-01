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
from ska_mid_cbf_mcs.fsp.hps_fsp_corr_controller_simulator import (
    HpsFspCorrControllerSimulator,
)

__all__ = ["HpsFspControllerSimulator"]


class HpsFspControllerSimulator:
    """
    HpsFspControllerSimulator class used to simulate the behaviour of the
    HPS FSP controller device when the Talon-DX hardware is not connected.

    :param device_name: Identifier for the device instance

    """

    def __init__(
        self: HpsFspControllerSimulator,
        device_name: str,
        fsp_corr_controller: HpsFspCorrControllerSimulator,
    ) -> None:
        self.device_name = device_name

        self._state = tango.DevState.INIT
        self._function_mode = FspModes.IDLE.value
        self._fsp_corr_controller = fsp_corr_controller

    # Methods that match the Tango commands in the band devices
    def State(self: HpsFspControllerSimulator) -> tango.DevState:
        """Get the current state of the device"""
        return self._state

    def SetFspFunctionMode(
        self: HpsFspControllerSimulator, f_mode: FspModes
    ) -> None:
        """
        Sets the function mode to be processed on this FPGA board.

        :param f_mode: string containing the function mode
        """

        """
        From Confluence design page "description of updates":
        Sets the function mode.
        Connect to  the DsFsp<Func>Controller devices
        Set to ON the DsFsp<Func>Controller corresponding to the given function mode
        Set to DESABLE the other DsFsp<Func>Controller devices
        """

        # TODO: figure out what to call on the DsFsp<Func>Controller
        # since there is no ON command. Should it just
        # set state to ON as below?
        if f_mode == "IDLE":
            self._function_mode = FspModes.IDLE.value
            # set all the DsFsp<>Controllers state to tango.DevState.DISABLE
            self._fsp_corr_controller.SetState(tango.DevState.DISABLE)
        elif f_mode == "CORR":
            self._function_mode = FspModes.CORR.value
            # set the DsFspCorrController state to tango.DevState.ON
            self._fsp_corr_controller.SetState(tango.DevState.ON)
            # set the others to tango.DevState.DISABLE
        elif f_mode == "PSS_BF":
            self._function_mode = FspModes.PSS_BF.value
            # set the DsFspPssController state to tango.DevState.ON
            # set the others to tango.DevState.DISABLE
            self._fsp_corr_controller.SetState(tango.DevState.DISABLE)
        elif f_mode == "PST_BF":
            self._function_mode = FspModes.PST_BF.value
            # set the DsFspPstController state to tango.DevState.ON
            # set the others to tango.DevState.DISABLE
            self._fsp_corr_controller.SetState(tango.DevState.DISABLE)
        elif f_mode == "VLBI":
            self._function_mode = FspModes.VLBI.value
            # set the DsFspVlbiController state to tango.DevState.ON
            # set the others to tango.DevState.DISABLE
            self._fsp_corr_controller.SetState(tango.DevState.DISABLE)
        else:
            # error
            pass
