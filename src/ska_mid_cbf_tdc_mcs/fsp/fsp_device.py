# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Copyright (c) 2019 National Research Council of Canada
# """

from __future__ import annotations

from typing import Any

import tango
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import SubmittedSlowCommand
from tango.server import attribute, command, device_property

from ska_mid_cbf_tdc_mcs.device.base_device import CbfDevice
from ska_mid_cbf_tdc_mcs.fsp.fsp_component_manager import FspComponentManager

__all__ = ["Fsp", "main"]


class Fsp(CbfDevice):
    """
    Fsp TANGO device class for the prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    FspCorrSubarray = device_property(dtype=("str",))

    FspPstSubarray = device_property(dtype=("str",))

    HpsFspControllerAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        abs_change=1,
        dtype="DevEnum",
        doc="Function mode; an int in the range [0, 4]",
        enum_labels=["IDLE", "CORRELATION", "PSS", "PST", "VLBI"],
    )
    def functionMode(self: Fsp) -> tango.DevEnum:
        """
        Read the functionMode attribute.

        :return: a DevEnum representing the mode.
        :rtype: tango.DevEnum
        """
        return self.component_manager.function_mode

    @attribute(
        abs_change=1,
        dtype=[int],
        max_dim_x=16,
        doc="Subarray membership",
    )
    def subarrayMembership(self: Fsp) -> list[int]:
        """
        Read the subarrayMembership attribute.

        :return: an array of affiliations of the FSP.
        :rtype: list[int]
        """
        return self.component_manager.subarray_membership

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: Fsp) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        for command_name, method_name in [
            ("SetFunctionMode", "set_function_mode"),
            ("AddSubarrayMembership", "add_subarray_membership"),
            ("RemoveSubarrayMembership", "remove_subarray_membership"),
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

    def create_component_manager(self: Fsp) -> FspComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        return FspComponentManager(
            fsp_id=self.DeviceID,
            all_fsp_corr_subarray_fqdn=self.FspCorrSubarray,
            all_fsp_pst_subarray_fqdn=self.FspPstSubarray,
            hps_fsp_controller_fqdn=self.HpsFspControllerAddress,
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )

    # -------------
    # Fast Commands
    # -------------

    class InitCommand(CbfDevice.InitCommand):
        """
        A class for the Fsp's init_device() "command".
        """

        def do(
            self: Fsp.InitCommand,
            *args: Any,
            **kwargs: Any,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = super().do(*args, **kwargs)

            self._device.set_change_event("functionMode", True)
            self._device.set_archive_event("functionMode", True)
            self._device.set_change_event("subarrayMembership", True)
            self._device.set_archive_event("subarrayMembership", True)

            return (result_code, message)

    # ---------------------
    # Long Running Commands
    # ---------------------

    def is_SetFunctionMode_allowed(self: Fsp) -> bool:
        """
        Returns True; SetFunctionMode must be allowed in DISABLED state for AA0.5 approach (CIP-2550)
        """
        return True

    @command(
        dtype_in="str",
        dtype_out="DevVarLongStringArray",
        doc_in="FSP function mode",
    )
    def SetFunctionMode(
        self: Fsp, function_mode: str
    ) -> DevVarLongStringArrayType:
        """
        Set the FSP function mode to either IDLE, CORR, PSS-BF, PST-BF, or VLBI.
        If IDLE, set the PSS, PST, CORR, and VLBI devices to DISABLE. Else,
        turn ON the target function_mode, and DISABLE all others.

        :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: DevVarLongStringArrayType

        """
        command_handler = self.get_command_object(
            command_name="SetFunctionMode"
        )
        result_code, command_id = command_handler(function_mode)
        return [[result_code], [command_id]]

    @command(
        dtype_in="uint16",
        dtype_out="DevVarLongStringArray",
        doc_in="Subarray ID",
    )
    def AddSubarrayMembership(
        self: Fsp, sub_id: int
    ) -> DevVarLongStringArrayType:
        """
        Add a subarray to the subarrayMembership list.

        :param argin: an integer representing the subarray affiliation
        """
        command_handler = self.get_command_object(
            command_name="AddSubarrayMembership"
        )
        result_code, command_id = command_handler(sub_id)
        return [[result_code], [command_id]]

    @command(
        dtype_in="uint16",
        dtype_out="DevVarLongStringArray",
        doc_in="Subarray ID",
    )
    def RemoveSubarrayMembership(
        self: Fsp, sub_id: int
    ) -> DevVarLongStringArrayType:
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing
        (no subarray is using this FSP), set function mode to empty.

        :param argin: an integer representing the subarray affiliation
        """
        command_handler = self.get_command_object(
            command_name="RemoveSubarrayMembership"
        )
        result_code, command_id = command_handler(sub_id)
        return [[result_code], [command_id]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return Fsp.run_server(args=args, **kwargs)


if __name__ == "__main__":
    main()
