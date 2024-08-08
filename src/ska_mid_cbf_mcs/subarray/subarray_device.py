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
from typing import List, Optional, Tuple

# tango imported to enable use of @tango.DebugIt. If
# DebugIt is imported using "from tango import DebugIt"
# then docs will not generate
import tango

# Tango imports
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode
from ska_tango_base.csp.subarray.subarray_device import CspSubElementSubarray
from ska_telmodel.schema import validate as telmodel_validate
from tango import AttrWriteType
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# SKA imports
from ska_mid_cbf_mcs.subarray.subarray_component_manager import (
    CbfSubarrayComponentManager,
)

# Additional import
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #


# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


class CbfSubarray(CspSubElementSubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """

    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #
    def init_command_objects(self: CbfSubarray) -> None:
        """
        Sets up the command objects. Register the new Commands here.
        """
        super().init_command_objects()

        device_args = (
            self.component_manager,
            self.op_state_model,
            self.obs_state_model,
            self.logger,
        )

        self.register_command_object(
            "AddReceptors", self.AddReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveReceptors", self.RemoveReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveAllReceptors", self.RemoveAllReceptorsCommand(*device_args)
        )

    # PROTECTED REGION END #    //  CbfSubarray.class_variable

    # ----------
    # Helper functions
    # ----------

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

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(dtype="uint16")

    CbfControllerAddress = device_property(
        dtype="str",
        doc="FQDN of CBF CController",
        default_value="mid_csp_cbf/sub_elt/controller",
    )

    PssConfigAddress = device_property(dtype="str")

    PstConfigAddress = device_property(dtype="str")

    SW1Address = device_property(dtype="str")

    SW2Address = device_property(dtype="str")

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    FspCorrSubarray = device_property(dtype=("str",))

    FspPssSubarray = device_property(dtype=("str",))

    FspPstSubarray = device_property(dtype=("str",))

    TalonBoard = device_property(dtype=("str",))

    VisSLIM = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    frequencyBand = attribute(
        dtype="DevEnum",
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
    )

    receptors = attribute(
        dtype=("str",),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="receptors",
        doc="List of DISH/receptor string IDs assigned to subarray",
    )

    assignedVCCs = attribute(
        dtype=("int",),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="VCCs",
        doc="List of VCC integer IDs assigned to subarray",
    )

    frequencyOffsetK = attribute(
        dtype=("int",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency offset (k)",
        doc="Frequency offset (k) of all 197 receptors as an array of ints.",
    )

    sysParam = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="sys_param",
        doc="the Dish ID - VCC ID mapping and frequency offset (k) in a json string",
    )

    simulationMode = attribute(
        dtype=SimulationMode,
        access=AttrWriteType.READ_WRITE,
        label="Simulation Mode",
        doc="Simulation Mode",
    )

    # ---------------
    # General methods
    # ---------------

    class InitCommand(CspSubElementSubarray.InitCommand):
        """
        A class for the CbfSubarray's init_device() "command".
        """

        def do(self: CbfSubarray.InitCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.
            Initialize the attributes and the properties of the CbfSubarray.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)

            """
            # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
            (result_code, message) = super().do()

            device = self.target

            # TODO remove when upgrading base class from 0.11.3
            device.set_change_event("healthState", True, True)

            device.write_simulationMode(True)

            return (result_code, message)

    def create_component_manager(
        self: CbfSubarray,
    ) -> CbfSubarrayComponentManager:
        """
        Create and return a subarray component manager.

        :return: a subarray component manager
        """
        self.logger.info("Entering CbfSubarray.create_component_manager()")
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        self._simulation_mode = SimulationMode.TRUE

        return CbfSubarrayComponentManager(
            subarray_id=int(self.SubID),
            controller=self.CbfControllerAddress,
            vcc=self.VCC,
            fsp=self.FSP,
            fsp_corr_sub=self.FspCorrSubarray,
            fsp_pss_sub=self.FspPssSubarray,
            fsp_pst_sub=self.FspPstSubarray,
            talon_board=self.TalonBoard,
            vis_slim=self.VisSLIM,
            logger=self.logger,
            simulation_mode=self._simulation_mode,
            push_change_event_callback=self.push_change_event,
            component_resourced_callback=self._component_resourced,
            component_configured_callback=self._component_configured,
            component_scanning_callback=self._component_scanning,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
            component_obs_fault_callback=self._component_obsfault,
        )

    def always_executed_hook(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        """Hook to delete device."""
        # PROTECTED REGION END #    //  CbfSubarray.delete_device

    # ---------
    # Callbacks
    # ---------

    def _component_resourced(self: CbfSubarray, resourced: bool) -> None:
        """
        Handle notification that the component has started or stopped resourcing.

        This is callback hook.

        :param configured: whether this component is configured
        :type configured: bool
        """
        if resourced:
            self.obs_state_model.perform_action("component_resourced")
        else:
            self.obs_state_model.perform_action("component_unresourced")

    def _component_configured(self: CbfSubarray, configured: bool) -> None:
        """
        Handle notification that the component has started or stopped configuring.

        This is callback hook.

        :param configured: whether this component is configured
        :type configured: bool
        """
        if configured:
            self.obs_state_model.perform_action("component_configured")
        else:
            self.obs_state_model.perform_action("component_unconfigured")

    def _component_scanning(self: CbfSubarray, scanning: bool) -> None:
        """
        Handle notification that the component has started or stopped scanning.

        This is a callback hook.

        :param scanning: whether this component is scanning
        :type scanning: bool
        """
        self.logger.debug(f"_component_scanning({scanning})")
        if scanning:
            self.obs_state_model.perform_action("component_scanning")
        else:
            self.obs_state_model.perform_action("component_not_scanning")

    def _communication_status_changed(
        self: CbfSubarray, communication_status: CommunicationStatus
    ) -> None:
        """
        Handle change in communications status between component manager and component.

        This is a callback hook, called by the component manager when
        the communications status changes. It is implemented here to
        drive the op_state.

        :param communication_status: the status of communications
            between the component manager and its component.
        """
        self._communication_status = communication_status

        if communication_status == CommunicationStatus.DISABLED:
            self.op_state_model.perform_action("component_disconnected")
        elif communication_status == CommunicationStatus.NOT_ESTABLISHED:
            self.op_state_model.perform_action("component_unknown")
        elif (
            communication_status == CommunicationStatus.ESTABLISHED
            and self._component_power_mode is not None
        ):
            self._component_power_mode_changed(self._component_power_mode)
        else:  # self._component_power_mode is None
            pass  # wait for a power mode update

    def _component_power_mode_changed(
        self: CbfSubarray, power_mode: PowerMode
    ) -> None:
        """
        Handle change in the power mode of the component.

        This is a callback hook, called by the component manager when
        the power mode of the component changes. It is implemented here
        to drive the op_state.

        :param power_mode: the power mode of the component.
        """
        self._component_power_mode = power_mode

        if self._communication_status == CommunicationStatus.ESTABLISHED:
            action_map = {
                PowerMode.OFF: "component_off",
                PowerMode.STANDBY: "component_standby",
                PowerMode.ON: "component_on",
                PowerMode.UNKNOWN: "component_unknown",
            }
            self.op_state_model.perform_action(action_map[power_mode])

    def _component_fault(self: CbfSubarray, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")

    def _component_obsfault(self: CbfSubarray, faulty: bool) -> None:
        """
        Handle notification that the component has obsfaulted.

        This is a callback hook.
        """
        self.component_manager.obs_faulty = faulty
        if faulty:
            self.obs_state_model.perform_action("component_obsfault")
            self.set_status("The device is in FAULT state")

    # ------------------
    # Attributes methods
    # ------------------

    def write_simulationMode(self: CbfSubarray, value: SimulationMode) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulation mode of {value}")
        super().write_simulationMode(value)
        self.component_manager._simulation_mode = value

    def read_simulationMode(self: CbfSubarray) -> SimulationMode:
        self.logger.info(
            f"Reading Simulation Mode of value {self.component_manager._simulation_mode}"
        )
        return self.component_manager._simulation_mode

    def read_frequencyBand(self: CbfSubarray) -> int:
        # PROTECTED REGION ID(CbfSubarray.frequencyBand_read) ENABLED START #
        """
        Return frequency band assigned to this subarray.
        One of ["1", "2", "3", "4", "5a", "5b", ]

        :return: the frequency band
        :rtype: int
        """
        return self.component_manager.frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def read_receptors(self: CbfSubarray) -> List[str]:
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        """
        Return list of receptors assigned to subarray

        :return: the list of receptor IDs
        :rtype: List[str]
        """
        return self.component_manager.dish_ids
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read

    def read_assignedVCCs(self: CbfSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarray.assignedVCCs_read) ENABLED START #
        """
        Return list of VCCs assigned to subarray

        :return: the list of VCC IDs
        :rtype: List[int]
        """
        return self.component_manager.vcc_ids
        # PROTECTED REGION END #    //  CbfSubarray.assignedVCCs_read

    def read_frequencyOffsetK(self: CbfSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarray.frequencyOffsetK_read) ENABLED START #
        """Return frequencyOffsetK attribute: array of integers reporting receptors in subarray"""
        return self.component_manager.frequency_offset_k
        # PROTECTED REGION END #    //  CbfSubarray.frequencyOffsetK_read

    def write_frequencyOffsetK(self: CbfSubarray, value: List[int]) -> None:
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_write) ENABLED START #
        """Set frequencyOffsetK attribute"""
        self.component_manager.frequency_offset_k = value
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_write

    def read_sysParam(self: CbfSubarray) -> str:
        # PROTECTED REGION ID(CbfSubarray.sysParam_read) ENABLED START #
        """
        Return the sys param string in json format

        :return: the sys param string in json format
        :rtype: str
        """
        return self.component_manager._sys_param_str
        # PROTECTED REGION END #    //  CbfSubarray.sysParam_read

    def write_sysParam(self: CbfSubarray, value: str) -> None:
        # PROTECTED REGION ID(CbfSubarray.sysParam_write) ENABLED START #
        """
        Set the sys param string in json format
        Should not be used by components external to Mid.CBF.
        To set the system parameters, refer to the CbfController Tango Commands at https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/guide/interfaces/lmc_mcs_interface.html#cbfcontroller-tango-commands or the CbfController api docs at https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/api/CbfController/index.html

        :param value: the sys param string in json format
        """
        self.component_manager.update_sys_param(value)
        # PROTECTED REGION END #    //  CbfSubarray.sysParam_write

    # --------
    # Commands
    # --------

    #  Receptor Related Commands  #

    class RemoveReceptorsCommand(
        CspSubElementSubarray.ReleaseResourcesCommand
    ):
        """
        A class for CbfSubarray's RemoveReceptors() command.
        Equivalent to the ReleaseResourcesCommand in ADR-8.
        """

        def do(
            self: CbfSubarray.RemoveReceptorsCommand, argin: List[str]
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
            self: CbfSubarray.RemoveReceptorsCommand, argin: List[str]
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
        doc_in="List of DISH/receptor IDs",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def RemoveReceptors(
        self: CbfSubarray, argin: List[str]
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
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
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
        # PROTECTED REGION END #    //  CbfSubarray.RemoveAllReceptors

    class AddReceptorsCommand(CspSubElementSubarray.AssignResourcesCommand):
        """
        A class for CbfSubarray's AddReceptors() command.
        """

        def do(
            self: CbfSubarray.AddReceptorsCommand, argin: List[str]
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for AddReceptors() command functionality.

            :param argin: The receptors to be assigned
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            return component_manager.assign_vcc(argin)

        def validate_input(
            self: CbfSubarray.AddReceptorsCommand, argin: List[str]
        ) -> Tuple[bool, str]:
            """
            Validate DISH/receptor ID.

            :param argin: The list of DISH/receptor IDs to add.

            :return: A tuple containing a boolean indicating if the configuration
                is valid and a string message. The message is for information
                purpose only.
            :rtype: (bool, str)
            """
            return DISHUtils.are_Valid_DISH_Ids(argin)

    @command(
        dtype_in=("str",),
        doc_in="List of DISH/receptor IDs",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @tango.DebugIt()
    def AddReceptors(
        self: CbfSubarray, argin: List[str]
    ) -> Tuple[ResultCode, str]:
        """
        Assign input receptors to this subarray.
        Set subarray to ObsState.IDLE if no receptors were previously assigned.

        :param argin: list of DISH/receptors to add
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("AddReceptors")

        (valid, msg) = command.validate_input(argin)
        if not valid:
            self._logger.error(msg)
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "AddReceptors command input failed",
                tango.ErrSeverity.ERR,
            )
        self.logger.info(msg)

        (return_code, message) = command(argin)
        return [[return_code], [message]]

    #  Configure Related Commands   #

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
            if "cbf" in full_configuration:
                full_configuration["cbf"] = copy.deepcopy(configuration)
            else:
                full_configuration["midcbf"] = copy.deepcopy(configuration)
            
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
                # Pre 4.0
                if "cbf" in full_configuration:
                    configuration = copy.deepcopy(full_configuration["cbf"])
                # Post .0
                elif "midcbf"in full_configuration:
                    configuration = copy.deepcopy(full_configuration["midcbf"])
                else:
                    msg = "cbf/midcbf configuration not find in the given Scan Configuration"
                    return (False, msg)
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
            if "cbf" in full_configuration:
                full_configuration["cbf"] = copy.deepcopy(configuration)
            else:
                full_configuration["midcbf"] = copy.deepcopy(configuration)
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
        # PROTECTED REGION ID(CbfSubarray.ConfigureScan) ENABLED START #
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

    class GoToIdleCommand(CspSubElementSubarray.GoToIdleCommand):
        """A class for the CbfSubarray's GoToIdle command."""

        def __init__(
            self, target, op_state_model, obs_state_model, logger=None
        ):
            """
            Initialise a new GoToIdleCommand instance.

            :param target: the object that this base command acts upon. For
                example, the device's component manager.
            :type target: object
            :param op_state_model: the op state model that this command
                uses to check that it is allowed to run
            :type op_state_model: :py:class:`OpStateModel`
            :param obs_state_model: the observation state model that
                 this command uses to check that it is allowed to run,
                 and that it drives with actions.
            :type obs_state_model: :py:class:`SubarrayObsStateModel`
            :param logger: the logger to be used by this Command. If not
                provided, then a default module logger will be used.
            :type logger: a logger that implements the standard library
                logger interface
            """
            super().__init__(
                target=target,
                op_state_model=op_state_model,
                obs_state_model=obs_state_model,
                logger=logger,
            )

        def do(self):
            """
            Stateless hook for GoToIdle() command functionality.

            :return: A tuple containing a return code and a string
                  message indicating status. The message is for
                  information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            return component_manager.go_to_idle()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="A tuple containing a return code and a string  message indicating status."
        "The message is for information purpose only.",
    )
    def GoToIdle(self):
        # PROTECTED REGION ID(CbfSubarray.GoToIdle) ENABLED START #
        """
        Transit the subarray from READY to IDLE obsState.

        :return: 'DevVarLongStringArray' A tuple containing a return
            code and a string message indicating status. The message is
            for information purpose only.
        """
        # NOTE: ska-tango-base class also deletes self._last_scan_configuration
        # here, but we are choosing to preserve it even in IDLE state should there
        # be a need to check it

        command = self.get_command_object("GoToIdle")
        (return_code, message) = command()
        return [[return_code], [message]]

    class ScanCommand(CspSubElementSubarray.ScanCommand):
        """
        A class for CbfSubarray's Scan() command.
        """

        def do(
            self: CbfSubarray.ScanCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Scan() command functionality.

            :param argin: The scan ID as JSON formatted string.
            :type argin: str
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            (result_code, msg) = component_manager.scan(argin)
            return (result_code, msg)

    class EndScanCommand(CspSubElementSubarray.EndScanCommand):
        """
        A class for CbfSubarray's EndScan() command.
        """

        def do(self: CbfSubarray.EndScanCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for EndScan() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            (result_code, msg) = component_manager.end_scan()
            return (result_code, msg)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == "__main__":
    main()
