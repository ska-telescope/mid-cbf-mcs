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

# """ FspCorrSubarray Tango device prototype

# FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
# """
from __future__ import annotations

import os

import tango
from ska_control_model import ObsState, ResultCode
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.device.base_device import CbfFastCommand
from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager import (
    FspCorrSubarrayComponentManager,
)
from ska_mid_cbf_mcs.fsp.fsp_mode_subarray_device import FspModeSubarray

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(FspModeSubarray):
    """
    FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    HpsFspCorrControllerAddress = device_property(dtype="str")

    LRCTimeout = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="str",
        doc="Differential off-boresight beam delay model",
    )
    def delayModel(self: FspCorrSubarray) -> str:
        """
        Read the delayModel attribute.

        :return: the delayModel attribute.
        :rtype: string
        """
        return self.component_manager.delay_model

    @attribute(
        dtype=("uint16",),
        max_dim_x=197,
        doc="Assigned VCC IDs",
    )
    def vccIDs(self: FspCorrSubarray) -> list[int]:
        """
        Read the vccIDs attribute; FSP deals with VCC, not DISH (receptor) IDs.

        :return: the list of assigned VCC IDs
        :rtype: list[int]
        """
        return self.component_manager.vcc_ids

    @attribute(
        dtype=tango.DevEnum,
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
        doc="Frequency band; an int in the range [0, 5]",
    )
    def frequencyBand(self: FspCorrSubarray) -> tango.DevEnum:
        """
        Read the frequencyBand attribute.

        :return: the frequency band
        :rtype: tango.DevEnum
        """
        return self.component_manager.frequency_band

    @attribute(
        dtype="int",
        doc="Frequency slice ID",
    )
    def frequencySliceID(self: FspCorrSubarray) -> int:
        """
        Read the frequencySliceID attribute.

        :return: the frequencySliceID attribute.
        :rtype: int
        """
        return self.component_manager.frequency_slice_id

    @attribute(
        dtype="str", doc="The last valid FSP scan configuration sent to HPS."
    )
    def lastHpsScanConfiguration(self: FspCorrSubarray) -> str:
        """
        Read the last valid FSP scan configuration of the device sent to HPS.

        :return: the current last_hps_scan_configuration value
        """
        return self.component_manager.last_hps_scan_configuration

    # --------------
    # Initialization
    # --------------

    class InitCommand(FspModeSubarray.InitCommand):
        """
        A class for the FspCorrSubarray's init_device() "command".
        """

        def do(
            self: FspCorrSubarray.InitCommand,
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

    def init_command_objects(self: FspCorrSubarray) -> None:
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

    def create_component_manager(
        self: FspCorrSubarray,
    ) -> FspCorrSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        return FspCorrSubarrayComponentManager(
            hps_fsp_corr_controller_fqdn=self.HpsFspCorrControllerAddress,
            lrc_timeout=int(self.LRCTimeout),
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )

    # -------------
    # Fast Commands
    # -------------

    class UpdateDelayModelCommand(CbfFastCommand):
        """
        A class for the Fsp's UpdateDelayModel() command.
        """

        def is_allowed(self: FspCorrSubarray.UpdateDelayModelCommand) -> bool:
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
            self: FspCorrSubarray.UpdateDelayModelCommand,
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
        self: FspCorrSubarray, argin: str
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
    return run((FspCorrSubarray,), args=args, **kwargs)


if __name__ == "__main__":
    main()
