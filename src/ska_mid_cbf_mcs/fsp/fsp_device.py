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
from ska_control_model import SimulationMode
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import FastCommand, SubmittedSlowCommand
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.device.base_device import CbfDevice
from ska_mid_cbf_mcs.fsp.fsp_component_manager import FspComponentManager

__all__ = ["Fsp", "main"]


class Fsp(CbfDevice):
    """
    Fsp TANGO device class for the prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    FspCorrSubarray = device_property(dtype=("str",))

    HpsFspControllerAddress = device_property(dtype="str")

    HpsFspCorrControllerAddress = device_property(dtype="str")

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
        dtype=("uint16",),
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

    @attribute(
        dtype="str",
        doc="Differential off-boresight beam delay model",
    )
    def delayModel(self: Fsp) -> str:
        """
        Read the delayModel attribute.

        :return: the delayModel attribute.
        :rtype: string
        """
        return self.component_manager.delay_model

    # --------------
    # Initialization
    # --------------

    def init_command_objects(self: Fsp) -> None:
        """
        Sets up the command objects
        """
        super(CbfDevice, self).init_command_objects()

        self.register_command_object(
            "SetFunctionMode",
            SubmittedSlowCommand(
                command_name="SetFunctionMode",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="set_function_mode",
                logger=self.logger,
            ),
        )

        self.register_command_object(
            "AddSubarrayMembership",
            self.AddSubarrayMembershipCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

        self.register_command_object(
            "RemoveSubarrayMembership",
            self.RemoveSubarrayMembershipCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

        self.register_command_object(
            "UpdateDelayModel",
            self.UpdateDelayModelCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    def create_component_manager(self: Fsp) -> FspComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")
        # NOTE: using component manager default of SimulationMode.TRUE,
        # as self._simulation_mode at this point during init_device()
        # SimulationMode.FALSE

        return FspComponentManager(
            fsp_id=self.DeviceID,
            fsp_corr_subarray_fqdns_all=self.FspCorrSubarray,
            hps_fsp_controller_fqdn=self.HpsFspControllerAddress,
            hps_fsp_corr_controller_fqdn=self.HpsFspCorrControllerAddress,
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
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

            # Setting initial simulation mode to True
            self._device._simulation_mode = SimulationMode.TRUE

            return (result_code, message)

    def is_AddSubarrayMembership_allowed(self: Fsp) -> bool:
        """
        Determine if AddSubarrayMembership is allowed
        (allowed if FSP state is ON).

        :return: if AddSubarrayMembership is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    class AddSubarrayMembershipCommand(FastCommand):
        """
        A class for the Fsp's AddSubarrayMembership command.
        """

        def __init__(
            self: Fsp.AddSubarrayMembershipCommand,
            *args,
            component_manager: FspComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: Fsp.AddSubarrayMembershipCommand, sub_id: int
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for AddSubarrayMembership command functionality.

            :param sub_id: an integer representing the subarray affiliation

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.add_subarray_membership(sub_id)

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
        result_code, message = command_handler(sub_id)
        return [[result_code], [message]]

    def is_RemoveSubarrayMembership_allowed(self: Fsp) -> bool:
        """
        Determine if RemoveSubarrayMembership is allowed
        (allowed if FSP state is ON).

        :return: if RemoveSubarrayMembership is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    class RemoveSubarrayMembershipCommand(FastCommand):
        """
        A class for the Fsp's RemoveSubarrayMembership command.
        """

        def __init__(
            self: Fsp.RemoveSubarrayMembershipCommand,
            *args,
            component_manager: FspComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: Fsp.RemoveSubarrayMembershipCommand, sub_id: int
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for RemoveSubarrayMembership command functionality.

            :param sub_id: an integer representing the subarray affiliation

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.remove_subarray_membership(sub_id)

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
        result_code, message = command_handler(sub_id)
        return [[result_code], [message]]

    # TODO: is this command needed?
    # If not also remove the get_fsp_corr_config_id method
    @command(
        dtype_out="DevString",
        doc_out="returns configID for all the fspCorrSubarray",
    )
    def getConfigID(self: Fsp) -> str:
        """
        Get the configID for all the fspCorrSubarray

        :return: the configID
        :rtype: str
        """
        return self.component_manager.get_fsp_corr_config_id()

    class UpdateDelayModelCommand(FastCommand):
        """
        A class for the Fsp's UpdateDelayModel() command.
        """

        def __init__(
            self: Fsp.UpdateDelayModelCommand,
            *args,
            component_manager: FspComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: Fsp.UpdateDelayModelCommand, argin: str
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for UpdateDelayModel() command functionality.

            :param argin: the delay model data
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.update_delay_model(argin)

    def is_UpdateDelayModel_allowed(self: Fsp) -> bool:
        """
        Determine if UpdateDelayModelis allowed
        (allowed if FSP state is ON and ObsState is
        READY OR SCANNINNG).

        :return: if UpdateDelayModel is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in="str",
        dtype_out="DevVarLongStringArray",
        doc_in="Delay Model, per receptor per polarization per timing beam",
    )
    def UpdateDelayModel(self: Fsp, argin: str) -> DevVarLongStringArrayType:
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

    def is_On_allowed(self: Fsp) -> bool:
        """
        Overriding the base class is_On_allowed so that the command may be queued,
        relying on the component manager equivalent method instead.
        """
        return True

    def is_Off_allowed(self: Fsp) -> bool:
        """
        Overriding the base class is_Off_allowed so that the command may be queued,
        relying on the component manager equivalent method instead.
        """
        return True

    def is_SetFunctionMode_allowed(self: Fsp) -> bool:
        """
        Determine if SetFunctionMode is allowed
        (allowed if FSP state is ON).

        :return: if SetFunctionMode is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in="str",
        dtype_out="DevVarLongStringArray",
        doc_in="FSP function mode",
    )
    def SetFunctionMode(
        self: Fsp, function_mode: str
    ) -> DevVarLongStringArrayType:
        """
        Set the Fsp Function Mode, either IDLE, CORR, PSS-BF, PST-BF, or VLBI
        If IDLE set the pss, pst, corr and vlbi devicess to DISABLE. OTherwise,
        turn one of them ON according to argin, and all others DISABLE.

        :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: DevVarLongStringArrayType

        """
        command_handler = self.get_command_object(
            command_name="SetFunctionMode"
        )
        result_code_message, command_id = command_handler(function_mode)
        return [[result_code_message], [command_id]]

    # ----------
    # Callbacks
    # ----------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return Fsp.run_server(args=args, **kwargs)


if __name__ == "__main__":
    main()
