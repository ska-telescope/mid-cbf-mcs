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
from importlib.abc import ResourceLoader  # allow forward references in type hints
from logging import log
from typing import Any, Dict, List, Tuple, Optional
import json
import copy

# Tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import DevState, AttrWriteType, AttrQuality
# Additional import
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #

# SKA imports
from ska_mid_cbf_mcs.subarray.subarray_component_manager import CbfSubarrayComponentManager
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.attribute_proxy import CbfAttributeProxy
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import ObsState, AdminMode, HealthState, PowerMode
from ska_tango_base.csp.subarray.subarray_device import CspSubElementSubarray
from ska_tango_base.commands import ResultCode, BaseCommand, ResponseCommand

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

        device_args = (self, self.op_state_model, self.obs_state_model, self.logger)

        self.register_command_object(
            "AddReceptors",
            self.AddReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveReceptors",
            self.RemoveReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "RemoveAllReceptors",
            self.RemoveAllReceptorsCommand(*device_args)
        )
        self.register_command_object(
            "ConfigureScan",
            self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "Scan",
            self.ScanCommand(*device_args)
        )
        self.register_command_object(
            "EndScan",
            self.EndScanCommand(*device_args)
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
        return len(self.component_manager.receptors)


    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16',
    )

    CbfControllerAddress = device_property(
        dtype='str',
        doc="FQDN of CBF CController",
        default_value="mid_csp_cbf/sub_elt/controller"
    )

    PssConfigAddress = device_property(
        dtype='str'
    )

    PstConfigAddress = device_property(
        dtype='str'
    )

    SW1Address = device_property(
        dtype='str'
    )

    SW2Address = device_property(
        dtype='str'
    )

    VCC = device_property(
        dtype=('str',)
    )

    FSP = device_property(
        dtype=('str',)
    )

    FspCorrSubarray = device_property(
        dtype=('str',)
    )

    FspPssSubarray = device_property(
        dtype=('str',)
    )

    FspPstSubarray = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="receptor_ids",
        doc="List of receptors assigned to subarray",
    )


    vccState = attribute(
        dtype=('DevState',),
        max_dim_x=197,
        label="VCC state",
        polling_period=1000,
        doc="Report the state of the assigned VCCs as an array of DevState",
    )

    vccHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=197,
        label="VCC health status",
        polling_period=1000,
        abs_change=1,
        doc="Report the health state of assigned VCCs as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    fspState = attribute(
        dtype=('DevState',),
        max_dim_x=27,
        label="FSP state",
        polling_period=1000,
        doc="Report the state of the assigned FSPs",
    )

    fspHealthState = attribute(
        dtype=('uint16',),
        max_dim_x=27,
        label="FSP health status",
        polling_period=1000,
        abs_change=1,
        doc="Report the health state of the assigned FSPs.",
    )

    fspList = attribute(
        dtype=(('uint16',),),
        max_dim_x=4,
        max_dim_y=27,
        label="List of FSP's used by subarray",
        doc="fsp[1][x] = CORR [2][x] = PSS [1][x] = PST [1][x] = VLBI",
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

            # TODO: remove
            # device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            # device._element_logging_level = tango.LogLevel.LOG_DEBUG
            # device._central_logging_level = tango.LogLevel.LOG_DEBUG

            return (result_code, message)


    def create_component_manager(self: CbfSubarray) -> CbfSubarrayComponentManager:
        """
        Create and return a subarray component manager.
        
        :return: a subarray component manager
        """
        self.logger.debug("Entering create_component_manager()")
        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return CbfSubarrayComponentManager(
            subarray_id=int(self.get_name()[-2:]),
            controller=self.CbfControllerAddress,
            vcc=self.VCC,
            fsp=self.FSP,
            fsp_corr_sub=self.FspCorrSubarray,
            fsp_pss_sub=self.FspPssSubarray,
            fsp_pst_sub=self.FspPstSubarray,
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            component_configured_callback=self._component_configured,
            component_resourced_callback=self._component_resourced,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault
        )


    def always_executed_hook(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        """Hook to delete device."""
        pass
        # PROTECTED REGION END #    //  CbfSubarray.delete_device


    # ---------
    # Callbacks
    # ---------

    def _component_resourced(
        self: CbfSubarray,
        resourced: bool
    ) -> None:
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


    def _component_configured(
        self: CbfSubarray,
        configured: bool
    ) -> None:
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


    def _component_scanning(
        self: CbfSubarray, 
        scanning: bool
    ) -> None:
        """
        Handle notification that the component has started or stopped scanning.

        This is a callback hook.

        :param scanning: whether this component is scanning
        :type scanning: bool
        """
        if scanning:
            self.obs_state_model.perform_action("component_scanning")
        else:
            self.obs_state_model.perform_action("component_not_scanning")


    def _communication_status_changed(
        self: CbfSubarray,
        communication_status: CommunicationStatus,
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
        elif communication_status == CommunicationStatus.ESTABLISHED \
            and self._component_power_mode is not None:
            self._component_power_mode_changed(self._component_power_mode)
        else:  # self._component_power_mode is None
            pass  # wait for a power mode update


    def _component_power_mode_changed(
        self: CbfSubarray,
        power_mode: PowerMode,
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
            self.obs_state_model.perform_action("component_obsfault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")


    # ------------------
    # Attributes methods
    # ------------------

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

    def read_receptors(self: CbfSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        """
        Return list of receptors assgined to subarray
        
        :return: the list of receptors
        :rtype: List[int]
        """
        return self.component_manager.receptors
        # PROTECTED REGION END #    //  CbfSubarray.receptors_read

    def write_receptors(self: CbfSubarray, value: List[int]) -> None:
        # PROTECTED REGION ID(CbfSubarray.receptors_write) ENABLED START #
        """
        Set receptors of this array to the input value. 
        Input should be an array of int
        
        :param value: the list of receptors
        """
        self.RemoveAllReceptors()
        self.AddReceptors(value)
        # PROTECTED REGION END #    //  CbfSubarray.receptors_write

    def read_vccState(self: CbfSubarray) -> Dict[str, DevState]:
        # PROTECTED REGION ID(CbfSubarray.vccState_read) ENABLED START #
        """
        Return the attribute vccState: array of DevState
        
        :return: the list of VCC states
        :rtype: Dict[str, DevState]
        """
        return self.component_manager.vcc_state.values()
        # PROTECTED REGION END #    //  CbfSubarray.vccState_read

    def read_vccHealthState(self: CbfSubarray) -> Dict[str, HealthState]:
        # PROTECTED REGION ID(CbfSubarray.vccHealthState_read) ENABLED START #
        """
        returns vccHealthState attribute: an array of unsigned short
        
        :return: the list of VCC health states
        :rtype: Dict[str, HealthState]
        """
        return self.component_manager.vcc_health_state.values()
        # PROTECTED REGION END #    //  CbfSubarray.vccHealthState_read

    def read_fspState(self: CbfSubarray) -> Dict[str, DevState]:
        # PROTECTED REGION ID(CbfSubarray.fspState_read) ENABLED START #
        """
        Return the attribute fspState: array of DevState
        
        :return: the list of FSP states
        :rtype: Dict[str, DevState]
        """
        return self.component_manager.fsp_state.values()
        # PROTECTED REGION END #    //  CbfSubarray.fspState_read

    def read_fspHealthState(self: CbfSubarray) -> Dict[str, HealthState]:
        # PROTECTED REGION ID(CbfSubarray.fspHealthState_read) ENABLED START #
        """
        returns fspHealthState attribute: an array of unsigned short
        
        :return: the list of FSP health states
        :rtype: Dict[str, HealthState]
        """
        return self.component_manager.fsp_health_state.values()
        # PROTECTED REGION END #    //  CbfSubarray.fspHealthState_read

    def read_fspList(self: CbfSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(CbfSubarray.fspList_read) ENABLED START #
        """
        return fspList attribute 
        2 dimentional array the fsp used by all the subarrays
        
        :return: the array of FSP IDs
        :rtype: List[List[int]]
        """
        return self.component_manager.fsp_list
        # PROTECTED REGION END #    //  CbfSubarray.fspList_read


    # --------
    # Commands
    # --------

    ##################  Receptors Related Commands  ###################

    class RemoveReceptorsCommand(CspSubElementSubarray.ReleaseResourcesCommand):
        """
        A class for CbfSubarray's RemoveReceptors() command.
        Equivalent to the ReleaseResourcesCommand in ADR-8.
        """
        def do(
            self: CbfSubarray.RemoveReceptorsCommand,
            argin: List[int]
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for RemoveReceptors() command functionality.

            :param argin: The receptors to be released
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return_code = ResultCode.OK
            msg = "RemoveReceptors command completed OK"

            for receptorID in argin:
                # check for invalid receptorID
                if not 0 < receptorID <= const.MAX_VCC:
                    msg = f"Invalid receptor ID {receptorID}. Skipping."
                    self.logger.warning(msg)
                else:
                    (result_code, msg) = device.component_manager.remove_receptor(receptorID)
                    if result_code == ResultCode.FAILED:
                        return_code = ResultCode.FAILED
                        device.logger.warning(msg)

            device.logger.info(msg)
            return (return_code, msg)

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    def RemoveReceptors(
        self: CbfSubarray,
        argin: List[int]
    ) -> Tuple[ResultCode, str]:
        """
        Remove from list of receptors. Turn Subarray to ObsState = EMPTY if no receptors assigned.
        Uses RemoveReceptorsCommand class.

        :param argin: list of receptor IDs to remove
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("RemoveReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]


    class RemoveAllReceptorsCommand(CspSubElementSubarray.ReleaseAllResourcesCommand):
        """
        A class for CbfSubarray's RemoveAllReceptors() command.
        """
        def do(
            self: CbfSubarray.RemoveAllReceptorsCommand
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for RemoveAllReceptors() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return device.component_manager.remove_all_receptors()

    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )
    @DebugIt()
    def RemoveAllReceptors(self: CbfSubarray) -> Tuple[ResultCode, str]:
        # PROTECTED REGION ID(CbfSubarray.RemoveAllReceptors) ENABLED START #
        """
        Remove all receptors. Turn Subarray OFF if no receptors assigned

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
        # NOTE: doesn't inherit CspSubElementSubarray._ResourcingCommand 
        # because will give error on len(self.target); TODO: to resolve
        """
        A class for CbfSubarray's AddReceptors() command.
        """
        def do(
            self: CbfSubarray.AddReceptorsCommand,
            argin: List[int]
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for AddReceptors() command functionality.

            :param argin: The receptors to be assigned
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            return_code = ResultCode.OK
            msg = "AddReceptorsCommand completed OK"

            for receptorID in argin:
                # check for invalid receptorID
                if not 0 < receptorID <= const.MAX_VCC:
                    msg = f"Invalid receptor ID {receptorID}. Skipping."
                    self.logger.warning(msg)
                else:
                    (result_code, msg) = device.component_manager.add_receptor(receptorID)
                    if result_code == ResultCode.FAILED:
                        return_code = ResultCode.FAILED
                        device.logger.warning(msg)

            device.logger.info(msg)
            return (return_code, msg)

    @command(
        dtype_in=('uint16',),
        doc_in="List of receptor IDs",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')"
    )

    @DebugIt()
    def AddReceptors(
        self: CbfSubarray,
        argin: List[int]
    ) -> Tuple[ResultCode, str]:
        """
        Assign Receptors to this subarray. 
        Turn subarray to ObsState = IDLE if previously no receptor is assigned.

        :param argin: list of receptors to add
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("AddReceptors")
        (return_code, message) = command(argin)
        return [[return_code], [message]]  

    ############  Configure Related Commands   ##############

    class ConfigureScanCommand(CspSubElementSubarray.ConfigureCommand):
        """
        A class for CbfSubarray's ConfigureScan() command.
        """
        def do(
            self: CbfSubarray.ConfigureScanCommand,
            argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            # Call this just to release all FSPs and unsubscribe to events.
            (result_code, msg) = device.component_manager.deconfigure()
            if result_code == ResultCode.FAILED:
                return (result_code, msg)

            full_configuration = json.loads(argin)
            common_configuration = copy.deepcopy(full_configuration["common"])
            configuration = copy.deepcopy(full_configuration["cbf"])
            # set band5Tuning to [0,0] if not specified
            if "band_5_tuning" not in common_configuration: 
                common_configuration["band_5_tuning"] = [0,0]
            if "frequency_band_offset_stream_1" not in common_configuration: 
                configuration["frequency_band_offset_stream_1"] = 0
            if "frequency_band_offset_stream_2" not in common_configuration: 
                configuration["frequency_band_offset_stream_2"] = 0
            if "rfi_flagging_mask" not in configuration: 
                configuration["rfi_flagging_mask"] = {}

            # Configure components
            full_configuration["common"] = copy.deepcopy(common_configuration)
            full_configuration["cbf"] = copy.deepcopy(configuration)
            (result_code, message) = device.component_manager.configure_scan(json.dumps(full_configuration))

            if result_code == ResultCode.OK:
                # store the configuration on command success
                device._last_scan_configuration = argin

            return (result_code, message)


        def validate_input(
            self: CbfSubarray.ConfigureScanCommand,
            argin: str
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
                common_configuration = copy.deepcopy(full_configuration["common"])
                configuration = copy.deepcopy(full_configuration["cbf"])
            except json.JSONDecodeError:  # argument not a valid JSON object
                msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
                return (False, msg)

            # Validate frequencyBandOffsetStream1.
            if "frequency_band_offset_stream_1" not in configuration:
                configuration["frequency_band_offset_stream_1"] = 0
            if abs(int(configuration["frequency_band_offset_stream_1"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream1' must be at most half " \
                        "of the frequency slice bandwidth. Aborting configuration."
                return (False, msg)

            # Validate frequencyBandOffsetStream2.
            if "frequency_band_offset_stream_2" not in configuration:
                configuration["frequency_band_offset_stream_2"] = 0
            if abs(int(configuration["frequency_band_offset_stream_2"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
                pass
            else:
                msg = "Absolute value of 'frequencyBandOffsetStream2' must be at most " \
                        "half of the frequency slice bandwidth. Aborting configuration."
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

                    stream_tuning = [*map(float, common_configuration["band_5_tuning"])]
                    if common_configuration["frequency_band"] == "5a":
                        if all(
                                [const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0] <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1] for i in [0, 1]]
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
                                [const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0] <= stream_tuning[i]
                                <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1] for i in [0, 1]]
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
            return self.target.component_manager.validate_input(json.dumps(full_configuration))


    @command(
        dtype_in='str',
        doc_in="Scan configuration",
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )
    @DebugIt()
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

        (return_code, message) = command(argin)
        return [[return_code], [message]]


    class ScanCommand(CspSubElementSubarray.ScanCommand):
        """
        A class for CbfSubarray's Scan() command.
        """
        def do(
            self: CbfSubarray.ScanCommand,
            argin: str
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
            device = self.target
            scan = json.loads(argin)
            (result_code, msg) =  device.component_manager.scan(scan["scan_id"])
            
            if result_code == ResultCode.STARTED:
                device._component_scanning(True)
            
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
            device = self.target

            (result_code, msg) =  device.component_manager.end_scan()
            
            if result_code == ResultCode.OK:
                device._component_scanning(False)

            return (result_code, msg)


    # # TODO: Remove GoToIdleCommand in favour of Base
    # class GoToIdleCommand(CspSubElementSubarray.EndCommand):
    #     """
    #     A class for CspSubElementSubarray's GoToIdle() command.
    #     """
    #     def do(self: CbfSubarray.GoToIdleCommand) -> Tuple[ResultCode, str]:
    #         """
    #         Stateless hook for GoToIdle() command functionality.
            
    #         :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #         :rtype: (ResultCode, str)
    #         """
    #         return super().do()

    # @command(
    #     dtype_out='DevVarLongStringArray',
    #     doc_out="(ReturnType, 'informational message')",
    # )
    # def GoToIdle(self: CbfSubarray) -> Tuple[ResultCode, str]:
    #     """
    #     deconfigure a scan, set ObsState to IDLE

    #     :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #     :rtype: (ResultCode, str)
    #     """
    #     command = self.get_command_object("GoToIdle")
    #     (return_code, message) = command()
    #     return [[return_code], [message]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == '__main__':
    main()