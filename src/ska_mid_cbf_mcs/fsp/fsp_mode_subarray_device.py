# -*- coding: utf-8 -*-
#
# This file is part of the FspCorrSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

# """

# """ FspModeSubarray Tango device prototype

# FspModeSubarray TANGO device class for the FspModeSubarray prototype
# Parrent class for the various FSP Modes to inherit
# """
from __future__ import annotations

import os

from ska_control_model import HealthState, ObsState, ResultCode
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.device.base_device import CbfFastCommand
from ska_mid_cbf_mcs.device.obs_device import CbfObsDevice

file_path = os.path.dirname(os.path.abspath(__file__))

__all__ = ["FspModeSubarray", "main"]


class FspModeSubarray(CbfObsDevice):
    """
    FspModeSubarray TANGO device class for the FspModeSubarray prototype
    Abstract class for the various FSP Modes to inherit
    """

    # -----------------
    # Device Properties
    # -----------------

    LRCTimeout = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=("uint16",),
        max_dim_x=197,
        doc="Assigned VCC IDs",
    )
    def vccIDs(self: FspModeSubarray) -> list[int]:
        """
        Read the vccIDs attribute; FSP deals with VCC, not DISH (receptor) IDs.

        :return: the list of assigned VCC IDs
        :rtype: list[int]
        """
        return self.component_manager.vcc_ids

    @attribute(
        dtype="str", doc="The last valid FSP scan configuration sent to HPS."
    )
    def lastHpsScanConfiguration(self: FspModeSubarray) -> str:
        """
        Read the last valid FSP scan configuration of the device sent to HPS.

        :return: the current last_hps_scan_configuration value
        """
        return self.component_manager.last_hps_scan_configuration

    @attribute(
        dtype="str",
        doc="Differential off-boresight beam delay model",
    )
    def delayModel(self: FspModeSubarray) -> str:
        """
        Read the delayModel attribute.

        :return: the delayModel attribute.
        :rtype: string
        """
        return self.component_manager.delay_model

    @attribute(
        dtype=HealthState,
        doc="HealthState of the FSP Function Mode Subarray device",
    )
    def healthState(self: FspModeSubarray) -> HealthState:
        """
        Read the healthState attribute.

        :return: the healthState attribute.
        :rtype: string
        """
        self.component_manager.update_health_state_from_hps()
        return self._health_state

    # --------------
    # Initialization
    # --------------
    class InitCommand(CbfObsDevice.InitCommand):
        """
        A class for the FspCorrSubarray's init_device() "command".
        """

        def do(
            self: FspModeSubarray.InitCommand,
            *args: any,
            **kwargs: any,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, msg) = super().do(*args, **kwargs)

            self._device.set_change_event("delayModel", True)
            self._device.set_archive_event("delayModel", True)

            return (result_code, msg)

    def init_command_objects(self: FspModeSubarray) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        self.register_command_object(
            "UpdateDelayModel",
            self.UpdateDelayModelCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    # -------------
    # Fast Commands
    # -------------

    class UpdateDelayModelCommand(CbfFastCommand):
        """
        A class for the Fsp's UpdateDelayModel() command.
        """

        def is_allowed(self: FspModeSubarray.UpdateDelayModelCommand) -> bool:
            """
            Determine if UpdateDelayModel command is allowed.

            :return: True if command is allowed, otherwise False
            """
            if not self.component_manager.is_communicating:
                return False

            obs_state = self.component_manager.obs_state
            if obs_state not in [ObsState.READY, ObsState.SCANNING]:
                self.logger.warning(
                    f"Ignoring delay model received in {obs_state} (must be READY or SCANNING)."
                )
                return False

            return True

        def do(
            self: FspModeSubarray.UpdateDelayModelCommand,
            argin: str,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for UpdateDelayModel() command functionality.

            :param argin: the delay model data
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                return self.component_manager.update_delay_model(argin)
            return (ResultCode.REJECTED, "UpdateDelayModel not allowed")

    @command(
        dtype_in="str",
        dtype_out="DevVarLongStringArray",
        doc_in="Delay Model, per receptor per polarization per timing beam",
    )
    def UpdateDelayModel(
        self: FspModeSubarray, argin: str
    ) -> DevVarLongStringArrayType:
        """
        Update the FSP's delay model (serialized JSON object)

        :param argin: the delay model data
        """
        command_handler = self.get_command_object("UpdateDelayModel")
        result_code, message = command_handler(argin)
        return [[result_code], [message]]

    # ---------------------
    # Long Running Commands
    # ---------------------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    raise TypeError(
        "FspModeSubarray is an Abstract Class; This server cannot be ran."
    )


if __name__ == "__main__":
    main()
