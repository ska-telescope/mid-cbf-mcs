# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import tango
from ska_control_model import ObsState, ObsStateModel
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import SubmittedSlowCommand
from tango.server import attribute, command, device_property

from ska_mid_cbf_tdc_mcs.device.obs_device import CbfObsDevice
from ska_mid_cbf_tdc_mcs.subarray.subarray_component_manager import (
    CbfSubarrayComponentManager,
)

__all__ = ["CbfSubarray", "main"]


class CbfSubarray(CbfObsDevice):
    """
    CbfSubarray TANGO device class for the prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    CbfControllerAddress = device_property(
        dtype="str",
        doc="FQDN of CBF CController",
        default_value="mid_csp_cbf/sub_elt/controller",
    )

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    FspCorrSubarray = device_property(dtype=("str",))

    TalonBoard = device_property(dtype=("str",))

    VisSLIM = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevEnum",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
    )
    def frequencyBand(self: CbfSubarray) -> int:
        """
        Return frequency band assigned to this subarray.
        One of ["1", "2", "3", "4", "5a", "5b", ]

        :return: the frequency band
        :rtype: int
        """
        return self.component_manager.frequency_band

    @attribute(
        dtype=("str",),
        max_dim_x=197,
        doc="list of DISH/receptor string IDs assigned to subarray",
    )
    def receptors(self: CbfSubarray) -> list[str]:
        """
        Return list of receptors assigned to subarray

        :return: the list of receptor IDs
        :rtype: list[str]
        """
        receptors = list(self.component_manager.dish_ids)
        receptors.sort()
        return receptors

    @attribute(
        dtype=("int",),
        max_dim_x=197,
        doc="list of VCC integer IDs assigned to subarray",
    )
    def assignedVCCs(self: CbfSubarray) -> list[int]:
        """
        Return list of VCCs assigned to subarray

        :return: the list of VCC IDs
        :rtype: list[int]
        """
        return self.component_manager.vcc_ids

    @attribute(
        dtype=("int",),
        max_dim_x=27,
        doc="list of FSP integer IDs assigned to subarray",
    )
    def assignedFSPs(self: CbfSubarray) -> list[int]:
        """
        Return list of FSPs assigned to subarray

        :return: the list of FSP IDs
        :rtype: list[int]
        """
        return self.component_manager.fsp_ids

    @attribute(
        dtype=("int",),
        max_dim_x=197,
        doc="Frequency offset (k) of up to 197 receptors as an array of ints.",
    )
    def frequencyOffsetK(self: CbfSubarray) -> list[int]:
        """
        Return frequencyOffsetK attribute

        :return: array of integers reporting frequencyOffsetK of receptors in subarray
        :rtype: list[int]
        """
        return self.component_manager.frequency_offset_k

    @frequencyOffsetK.write
    def frequencyOffsetK(self: CbfSubarray, value: list[int]) -> None:
        """
        Set frequencyOffsetK attribute

        :param value: list of frequencyOffsetK values
        """
        self.component_manager.frequency_offset_k = value

    @attribute(
        dtype="str",
        memorized=True,
        hw_memorized=True,
        doc="the Dish ID - VCC ID mapping and frequency offset (k) in a json string",
    )
    def sysParam(self: CbfSubarray) -> str:
        """
        Return the sys param string in json format

        :return: the sys param string in json format
        :rtype: str
        """
        return self.component_manager._sys_param_str

    @sysParam.write
    def sysParam(self: CbfSubarray, value: str) -> None:
        """
        Set the sys param string in json format
        Should not be used by components external to Mid.CBF.
        To set the system parameters, refer to the CbfController Tango Commands:
        https://developer.skao.int/projects/ska-mid-cbf-tdc-mcs/en/latest/guide/interfaces/lmc_mcs_interface.html#cbfcontroller-tango-commands or the CbfController api docs at https://developer.skao.int/projects/ska-mid-cbf-tdc-mcs/en/latest/api/CbfController/index.html

        :param value: the sys param string in json format
        """
        self.component_manager.update_sys_param(value)

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype="str", doc="The last valid delay model received."
    )
    def lastDelayModel(self: CbfSubarray) -> str:
        """
        Read the last valid delay model received.

        :return: the current last_received_delay_model value
        """
        return self.component_manager.last_received_delay_model

    # --------------
    # Initialization
    # --------------

    def _init_state_model(self: CbfSubarray) -> None:
        """Set up the state model for the device."""
        super(CbfObsDevice, self)._init_state_model()

        # CbfSubarray uses the full observing state model
        self.obs_state_model = ObsStateModel(
            logger=self.logger,
            callback=self._update_obs_state,
        )

    def init_command_objects(self: CbfSubarray) -> None:
        """
        Sets up the command objects. Register the new Commands here.
        """
        super().init_command_objects()

        for command_name, method_name in [
            ("AddReceptors", "assign_vcc"),
            ("RemoveReceptors", "release_vcc"),
            ("RemoveAllReceptors", "release_all_vcc"),
            ("Restart", "restart"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name=command_name,
                    command_tracker=self._command_tracker,
                    component_manager=self.component_manager,
                    method_name=method_name,
                    logger=self.logger,
                ),
            )

    # Used by commands that needs resource manager in CspSubElementSubarray
    # base class (for example AddReceptors command).
    # The base class define len as len(resource_manager),
    # so we need to change that here. TODO - to clarify.
    def __len__(self: CbfSubarray) -> int:
        """
        Returns the number of resources currently assigned. Note that
        this also functions as a boolean method for whether there are
        any assigned resources: ``if len()``.

        :return: number of resources assigned
        :rtype: int
        """
        return len(self.component_manager.dish_ids)

    def create_component_manager(
        self: CbfSubarray,
    ) -> CbfSubarrayComponentManager:
        """
        Create and return a subarray component manager.

        :return: a subarray component manager
        """
        self.logger.debug("Entering CbfSubarray.create_component_manager()")

        return CbfSubarrayComponentManager(
            subarray_id=int(self.DeviceID),
            controller=self.CbfControllerAddress,
            vcc=self.VCC,
            fsp=self.FSP,
            fsp_corr_sub=self.FspCorrSubarray,
            talon_board=self.TalonBoard,
            vis_slim=self.VisSLIM,
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )

    # --------
    # Commands
    # --------

    class InitCommand(CbfObsDevice.InitCommand):
        """
        A class for the Subarray's init_device() "command".
        """

        def do(
            self: CbfSubarray.InitCommand,
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

            self._device._obs_state = ObsState.EMPTY
            self._device._commanded_obs_state = ObsState.EMPTY

            self._device.set_change_event("receptors", True)
            self._device.set_archive_event("receptors", True)
            self._device.set_change_event("sysParam", True)
            self._device.set_archive_event("sysParam", True)

            return (result_code, msg)

    # ---------------------
    # Long Running Commands
    # ---------------------

    # --- Resourcing Commands --- #

    @command(
        dtype_in=("str",),
        doc_in="List of DISH (receptor) IDs",
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @tango.DebugIt()
    def AddReceptors(
        self: CbfSubarray, argin: list[str]
    ) -> DevVarLongStringArrayType:
        """
        Assign input receptors to this subarray.
        Set subarray to ObsState.IDLE if no receptors were previously assigned,
        i.e. subarray was previously in ObsState.EMPTY.

        :param argin: list[str] of DISH IDs to add
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object("AddReceptors")
        result_code, command_id = command_handler(argin)
        return [[result_code], [command_id]]

    @command(
        dtype_in=("str",),
        doc_in="list of DISH/receptor IDs",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @tango.DebugIt()
    def RemoveReceptors(
        self: CbfSubarray, argin: list[str]
    ) -> DevVarLongStringArrayType:
        """
        Remove input from list of assigned receptors.
        Set subarray to ObsState.EMPTY if no receptors assigned.

        :param argin: list of DISH/receptor IDs to remove
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object("RemoveReceptors")
        result_code, command_id = command_handler(argin)
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @tango.DebugIt()
    def RemoveAllReceptors(self: CbfSubarray) -> DevVarLongStringArrayType:
        """
        Remove all assigned receptors.
        Set subarray to ObsState.EMPTY if no receptors assigned.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object("RemoveAllReceptors")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    # --- Scan Commands --- #

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the scan ID.",
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @tango.DebugIt()
    def Scan(self: CbfSubarray, argin: str) -> DevVarLongStringArrayType:
        """
        Start an observing scan.
        Overrides CbfObsDevice as subarray's scan input is a JSON string

        :param argin: JSON formatted string with the scan ID.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("Scan")
        result_code, command_id = command_handler(argin)
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @tango.DebugIt()
    def Restart(self: CbfSubarray) -> DevVarLongStringArrayType:
        """
        Restart the observing device from a FAULT/ABORTED obsState to EMPTY.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("Restart")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return CbfSubarray.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
