# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""
CbfSubarray
Sub-element subarray device for Mid.CBF
"""
from __future__ import annotations

import copy
import json

import tango
from ska_control_model import ObsStateModel, ResultCode
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import SubmittedSlowCommand
from ska_telmodel.schema import validate as telmodel_validate
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.device.obs_device import CbfObsDevice
from ska_mid_cbf_mcs.subarray.subarray_component_manager import (
    CbfSubarrayComponentManager,
)

__all__ = ["CbfSubarray", "main"]


class CbfSubarray(CbfObsDevice):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    CbfControllerAddress = device_property(
        dtype="str",
        doc="FQDN of CBF CController",
        default_value="mid_csp_cbf/sub_elt/controller",
    )

    SW1Address = device_property(dtype="str")

    SW2Address = device_property(dtype="str")

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    FspCorrSubarray = device_property(dtype=("str",))

    TalonBoard = device_property(dtype=("str",))

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevEnum",
        label="Frequency band",
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
        label="receptors",
        doc="list of DISH/receptor string IDs assigned to subarray",
    )
    def receptors(self: CbfSubarray) -> list[str]:
        """
        Return list of receptors assigned to subarray

        :return: the list of receptor IDs
        :rtype: list[str]
        """
        return list(self.component_manager.dish_ids)

    @attribute(
        dtype=("int",),
        max_dim_x=197,
        label="VCCs",
        doc="list of VCC integer IDs assigned to subarray",
    )
    def assignedVCCs(self: CbfSubarray) -> list[int]:
        """
        Return list of VCCs assigned to subarray

        :return: the list of VCC IDs
        :rtype: list[int]
        """
        return list(self.component_manager.vcc_ids)

    @attribute(
        dtype=("int",),
        max_dim_x=197,
        label="Frequency offset (k)",
        doc="Frequency offset (k) of all 197 receptors as an array of ints.",
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
        label="sys_param",
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
        https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/guide/interfaces/lmc_mcs_interface.html#cbfcontroller-tango-commands or the CbfController api docs at https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/api/CbfController/index.html

        :param value: the sys param string in json format
        """
        self.component_manager.update_sys_param(value)

    # ---------------
    # General methods
    # ---------------

    def _init_state_model(self: CbfSubarray) -> None:
        """Set up the state model for the device."""
        super(CbfObsDevice, self)._init_state_model()

        # subarray instantiates full observing state model
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
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
        )

    # ---------
    # Callbacks
    # ---------

    # None at this time

    # --------
    # Commands
    # --------

    #  Resourcing Commands  #

    @command(
        dtype_in="DevString",
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
        result_code_message, command_id = command_handler(argin)
        return [[result_code_message], [command_id]]

    class RemoveReceptorsCommand(
        CspSubElementSubarray.ReleaseResourcesCommand
    ):
        """
        A class for CbfSubarray's RemoveReceptors() command.
        Equivalent to the ReleaseResourcesCommand in ADR-8.
        """

        def do(
            self: CbfSubarray.RemoveReceptorsCommand, argin: list[str]
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for RemoveReceptors() command functionality.

            :param argin: The receptors to be released
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            return component_manager.release_vcc(argin)

        def validate_input(
            self: CbfSubarray.RemoveReceptorsCommand, argin: list[str]
        ) -> Tuple[bool, str]:
            """
            Validate DISH/receptor IDs.

            :param argin: The list of DISH/receptor IDs to remove.

            :return: A tuple containing a boolean indicating if the configuration
                is valid and a string message. The message is for information
                purpose only.
            :rtype: (bool, str)
            """
            return DISHUtils.are_Valid_DISH_Ids(argin)

    @command(
        dtype_in=("str",),
        doc_in="list of DISH/receptor IDs",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def RemoveReceptors(
        self: CbfSubarray, argin: list[str]
    ) -> Tuple[ResultCode, str]:
        """
        Remove input from list of assigned receptors.
        Set subarray to ObsState.EMPTY if no receptors assigned.

        :param argin: list of DISH/receptor IDs to remove
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("RemoveReceptors")

        (valid, msg) = command.validate_input(argin)
        if not valid:
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "RemoveReceptors command input failed",
                tango.ErrSeverity.ERR,
            )

        self.logger.info(msg)
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class RemoveAllReceptorsCommand(
        CspSubElementSubarray.ReleaseAllResourcesCommand
    ):
        """
        A class for CbfSubarray's RemoveAllReceptors() command.
        """

        def do(
            self: CbfSubarray.RemoveAllReceptorsCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for RemoveAllReceptors() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            return component_manager.release_all_vcc()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @tango.DebugIt()
    def RemoveAllReceptors(self: CbfSubarray) -> Tuple[ResultCode, str]:
        """
        Remove all assigned receptors.
        Set subarray to ObsState.EMPTY if no receptors assigned.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        command = self.get_command_object("RemoveAllReceptors")
        (return_code, message) = command()
        return [[return_code], [message]]

    #  Scan Commands   #

    class ConfigureScanCommand(CspSubElementSubarray.ConfigureScanCommand):
        """
        A class for CbfSubarray's ConfigureScan() command.
        """

        def do(
            self: CbfSubarray.ConfigureScanCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target

            full_configuration = json.loads(argin)
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
            # set band5Tuning to [0,0] if not specified
            if "band_5_tuning" not in common_configuration:
                common_configuration["band_5_tuning"] = [0, 0]
            if "frequency_band_offset_stream1" not in common_configuration:
                configuration["frequency_band_offset_stream1"] = 0
            if "frequency_band_offset_stream2" not in common_configuration:
                configuration["frequency_band_offset_stream2"] = 0
            if "rfi_flagging_mask" not in configuration:
                configuration["rfi_flagging_mask"] = {}

            # Configure components
            full_configuration["common"] = copy.deepcopy(common_configuration)
            full_configuration["cbf"] = copy.deepcopy(configuration)
            (result_code, message) = component_manager.configure_scan(
                json.dumps(full_configuration)
            )

            return (result_code, message)

        def validate_input(
            self: CbfSubarray.ConfigureScanCommand, argin: str
        ) -> Tuple[bool, str]:
            """
            Validate scan configuration.

            :param argin: The configuration as JSON formatted string.

            :return: A tuple containing a boolean indicating if the configuration
                is valid and a string message. The message is for information
                purpose only.
            :rtype: (bool, str)
            """
            # try to deserialize input string to a JSON object
            try:
                full_configuration = json.loads(argin)
                common_configuration = copy.deepcopy(
                    full_configuration["common"]
                )
                configuration = copy.deepcopy(full_configuration["cbf"])
            except json.JSONDecodeError:  # argument not a valid JSON object
                msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
                return (False, msg)

            # Validate full_configuration against the telescope model
            try:
                telmodel_validate(
                    version=full_configuration["interface"],
                    config=full_configuration,
                    strictness=2,
                )
                self.logger.info("Scan configuration is valid!")
            except ValueError as e:
                msg = f"Scan configuration validation against the telescope model failed with the following exception:\n {str(e)}."
                self.logger.error(msg)

            # Validate frequencyBandOffsetStream1.
            if "frequency_band_offset_stream1" not in configuration:
                configuration["frequency_band_offset_stream1"] = 0
            if (
                abs(int(configuration["frequency_band_offset_stream1"]))
                <= const.FREQUENCY_SLICE_BW * 10**6 / 2
            ):
                pass
            else:
                msg = (
                    "Absolute value of 'frequencyBandOffsetStream1' must be at most half "
                    "of the frequency slice bandwidth. Aborting configuration."
                )
                return (False, msg)

            # Validate frequencyBandOffsetStream2.
            if "frequency_band_offset_stream2" not in configuration:
                configuration["frequency_band_offset_stream2"] = 0
            if (
                abs(int(configuration["frequency_band_offset_stream2"]))
                <= const.FREQUENCY_SLICE_BW * 10**6 / 2
            ):
                pass
            else:
                msg = (
                    "Absolute value of 'frequencyBandOffsetStream2' must be at most "
                    "half of the frequency slice bandwidth. Aborting configuration."
                )
                return (False, msg)

            # Validate band5Tuning, frequencyBandOffsetStream2 if frequencyBand is 5a or 5b.
            if common_configuration["frequency_band"] in ["5a", "5b"]:
                # band5Tuning is optional
                if "band_5_tuning" in common_configuration:
                    pass
                    # check if streamTuning is an array of length 2
                    try:
                        assert len(common_configuration["band_5_tuning"]) == 2
                    except (TypeError, AssertionError):
                        msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                        return (False, msg)

                    stream_tuning = [
                        *map(float, common_configuration["band_5_tuning"])
                    ]
                    if common_configuration["frequency_band"] == "5a":
                        if all(
                            [
                                const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0]
                                <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1]
                                for i in [0, 1]
                            ]
                        ):
                            pass
                        else:
                            msg = (
                                "Elements in 'band5Tuning must be floats between"
                                f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0]} and "
                                f"{const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1]} "
                                f"(received {stream_tuning[0]} and {stream_tuning[1]})"
                                " for a 'frequencyBand' of 5a. "
                                "Aborting configuration."
                            )
                            return (False, msg)
                    else:  # configuration["frequency_band"] == "5b"
                        if all(
                            [
                                const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0]
                                <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1]
                                for i in [0, 1]
                            ]
                        ):
                            pass
                        else:
                            msg = (
                                "Elements in 'band5Tuning must be floats between"
                                f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0]} and "
                                f"{const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1]} "
                                f"(received {stream_tuning[0]} and {stream_tuning[1]})"
                                " for a 'frequencyBand' of 5b. "
                                "Aborting configuration."
                            )
                            return (False, msg)
                else:
                    # set band5Tuning to zero for the rest of the test. This won't
                    # change the argin in function "configureScan(argin)"
                    common_configuration["band_5_tuning"] = [0, 0]

            # At this point, validate FSP, VCC, subscription parameters
            full_configuration["common"] = copy.deepcopy(common_configuration)
            full_configuration["cbf"] = copy.deepcopy(configuration)
            component_manager = self.target
            return component_manager.validate_input(
                json.dumps(full_configuration)
            )

    def is_ConfigureScan_allowed(self):
        """
        Check if command `ConfigureScan` is allowed in the current device state.

        :return: ``True`` if the command is allowed
        :rtype: boolean
        """
        command = self.get_command_object("ConfigureScan")
        return command.is_allowed(raise_if_disallowed=True)

    @command(
        dtype_in="str",
        doc_in="Scan configuration",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @tango.DebugIt()
    def ConfigureScan(self: CbfSubarray, argin: str) -> Tuple[ResultCode, str]:
        # """
        """Change state to CONFIGURING.
        Configure attributes from input JSON. Subscribe events. Configure VCC, VCC subarray, FSP, FSP Subarray.
        publish output links.

        :param argin: The configuration as JSON formatted string.
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        command = self.get_command_object("ConfigureScan")

        (valid, msg) = command.validate_input(argin)
        if not valid:
            self.component_manager.raise_configure_scan_fatal_error(msg)
        self.logger.info(msg)
        # store the configuration on command success
        self._last_scan_configuration = argin

        self.logger.debug(f"obsState == {self.obsState}")

        (result_code, message) = command(argin)

        self.logger.debug(f"obsState == {self.obsState}")
        return [[result_code], [message]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return CbfSubarray.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
