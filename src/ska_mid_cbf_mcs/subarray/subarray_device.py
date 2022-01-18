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
from __future__ import annotations  # allow forward references in type hints
from logging import log
from typing import Any, Dict, List, Tuple

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
from ska_mid_cbf_mcs.subarray.subarray_component_manager import SubarrayComponentManager
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.attribute_proxy import CbfAttributeProxy
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.control_model import ObsState, AdminMode, HealthState
from ska_tango_base import SKASubarray, SKABaseDevice
from ska_tango_base.commands import ResultCode

# PROTECTED REGION END #    //  CbfSubarray.additionnal_import

__all__ = ["CbfSubarray", "main"]


def validate_ip(ip: str) -> bool:
    """
    Validate IP address format.

    :param ip: IP address to be evaluated

    :return: whether or not the IP address format is valid
    :rtype: bool
    """
    splitip = ip.split('.')
    if len(splitip) != 4:
        return False
    for ipparts in splitip:
        if not ipparts.isdigit():
            return False
        ipval = int(ipparts)
        if ipval < 0 or ipval > 255:
            return False
    return True


class CbfSubarray(SKASubarray):
    """
    CBFSubarray TANGO device class for the CBFSubarray prototype
    """

    # PROTECTED REGION ID(CbfSubarray.class_variable) ENABLED START #
    def init_command_objects(self: CbfSubarray) -> None:
        """
        Sets up the command objects. Register the new Commands here.
        """
        super().init_command_objects()
        device_args = (self, self.state_model, self.logger)
        # resource_args = (self.resource_manager, self.state_model, self.logger) 
        # only use resource_args if we want to have separate resource_manager object

        # self.register_command_object(
        #     "On",
        #     self.OnCommand(*device_args)
        # )
        self.register_command_object(
            "Off",
            self.OffCommand(*device_args)
        )
        #TODO: is this command needed (vs ConfigureScan)
        # self.register_command_object(
        #     "Configure",
        #     self.ConfigureCommand(*device_args)
        # )
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
        self.register_command_object(
            "GoToIdle",
            self.GoToIdleCommand(*device_args)
        )
        
    # ----------
    # Helper functions
    # ----------


    # PROTECTED REGION END #    //  CbfSubarray.class_variable


    # Used by commands that needs resource manager in SKASubarray 
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

        return len(self.component_manager._receptors)


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

    configID = attribute(
        dtype='str',
        access=AttrWriteType.READ,
        label="Config ID",
        doc="config ID",
    )

    scanID = attribute(
        dtype='uint',
        access=AttrWriteType.READ,
        label="Scan ID",
        doc="Scan ID",
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

    latestScanConfig = attribute(
        dtype='DevString',
        label="lastest Scan Configuration",
        doc="for storing lastest scan configuration",
    )


    # ---------------
    # General methods
    # ---------------
    class InitCommand(SKASubarray.InitCommand):
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
            # SKASubarray.init_device(self)
            # PROTECTED REGION ID(CbfSubarray.init_device) ENABLED START #
            # self.set_state(DevState.INIT)
            (result_code, message) = super().do()

            device=self.target
            
            device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            device._element_logging_level = tango.LogLevel.LOG_DEBUG
            device._central_logging_level = tango.LogLevel.LOG_DEBUG

            device.component_manager = device.create_component_manager()

            return (ResultCode.OK, "InitCommand successful.")


    def create_component_manager(self: CbfSubarray) -> SubarrayComponentManager:
        """
        Create and return a subarray component manager.
        
        :return: a subarray component manager
        """
        self.logger.debug("Entering create_component_manager()")

        return SubarrayComponentManager(
            subarray=self.get_name(),
            controller=self.CbfControllerAddress,
            vcc=self.VCC,
            fsp=self.FSP,
            fsp_corr_sub=self.FspCorrSubarray,
            fsp_pss_sub=self.FspPssSubarray,
            fsp_pst_sub=self.FspPstSubarray,
            logger=self.logger,
            connect=False
        )


    def always_executed_hook(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.always_executed_hook) ENABLED START #
        """methods always executed before any TANGO command is executed"""
        if not self.component_manager._connected:
            self.component_manager.start_communicating()
        # PROTECTED REGION END #    //  CbfSubarray.always_executed_hook

    def delete_device(self: CbfSubarray) -> None:
        # PROTECTED REGION ID(CbfSubarray.delete_device) ENABLED START #
        """
        Hook to delete device. 
        TODO: Set State to DISABLE, remove all receptors, go to ObsState IDLE
        """
        pass
        # PROTECTED REGION END #    //  CbfSubarray.delete_device

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
        return self.component_manager._frequency_band
        # PROTECTED REGION END #    //  CbfSubarray.frequencyBand_read

    def read_configID(self: CbfSubarray) -> str:
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """
        Return attribute configID
        
        :return: the configuration ID
        :rtype: str
        """
        return self.component_manager._config_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def read_scanID(self: CbfSubarray) -> int:
        # PROTECTED REGION ID(CbfSubarray.configID_read) ENABLED START #
        """
        Return attribute scanID
        
        :return: the scan ID
        :rtype: int
        """
        return self.component_manager._scan_ID
        # PROTECTED REGION END #    //  CbfSubarray.configID_read

    def read_receptors(self: CbfSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarray.receptors_read) ENABLED START #
        """
        Return list of receptors assgined to subarray
        
        :return: the list of receptors
        :rtype: List[int]
        """
        return self.component_manager._receptors
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
        return list(self.component_manager._vcc_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccState_read

    def read_vccHealthState(self: CbfSubarray) -> Dict[str, HealthState]:
        # PROTECTED REGION ID(CbfSubarray.vccHealthState_read) ENABLED START #
        """
        returns vccHealthState attribute: an array of unsigned short
        
        :return: the list of VCC health states
        :rtype: Dict[str, HealthState]
        """
        return list(self.component_manager._vcc_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.vccHealthState_read

    def read_fspState(self: CbfSubarray) -> Dict[str, DevState]:
        # PROTECTED REGION ID(CbfSubarray.fspState_read) ENABLED START #
        """
        Return the attribute fspState: array of DevState
        
        :return: the list of FSP states
        :rtype: Dict[str, DevState]
        """
        return list(self.component_manager._fsp_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspState_read

    def read_fspHealthState(self: CbfSubarray) -> Dict[str, HealthState]:
        # PROTECTED REGION ID(CbfSubarray.fspHealthState_read) ENABLED START #
        """
        returns fspHealthState attribute: an array of unsigned short
        
        :return: the list of FSP health states
        :rtype: Dict[str, HealthState]
        """
        return list(self.component_manager._fsp_health_state.values())
        # PROTECTED REGION END #    //  CbfSubarray.fspHealthState_read

    def read_fspList(self: CbfSubarray) -> List[List[int]]:
        # PROTECTED REGION ID(CbfSubarray.fspList_read) ENABLED START #
        """
        return fspList attribute 
        2 dimentional array the fsp used by all the subarrays
        
        :return: the array of FSP IDs
        :rtype: List[List[int]]
        """
        return self.component_manager._fsp_list
        # PROTECTED REGION END #    //  CbfSubarray.fspList_read

    def read_latestScanConfig(self: CbfSubarray) -> str:
        # PROTECTED REGION ID(CbfSubarray.latestScanConfig_read) ENABLED START #
        """
        Return the latestScanConfig attribute.
        
        :return: the latest scan configuration string
        :rtype: str
        """
        return self.component_manager._latest_scan_config
        # PROTECTED REGION END #    //  CbfSubarray.latestScanConfig_read

    # --------
    # Commands
    # --------

    # class OnCommand(SKASubarray.OnCommand):
    #     """
    #     A class for the SKASubarray's On() command.
    #     """
    #     def do(self):
    #         """
    #         Stateless hook for On() command functionality.

    #         :return: A tuple containing a return code and a string
    #             message indicating status. The message is for
    #             information purpose only.
    #         :rtype: (ResultCode, str)
    #         """
    #         return super().do()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the SKASubarray's Off() command.
        """
        def do(self: CbfSubarray.OffCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code,message) = super().do()
            device = self.target
            device.logger.info(f"Subarray ObsState is {device._obs_state}")

            return (result_code, message)


    ##################  Receptors Related Commands  ###################

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

    class RemoveReceptorsCommand(SKASubarray.ReleaseResourcesCommand):
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
            #(result_code,message) = super().do(argin)
            device = self.target

            (result_code, message) = device.component_manager.remove_receptors(argin)
            device.logger.info(message)
            return (result_code, message)


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

    class RemoveAllReceptorsCommand(SKASubarray.ReleaseAllResourcesCommand):
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
            # (result_code,message) = super().do()

            device = self.target
            device.logger.debug("Entering RemoveAllReceptors()")

            (result_code, message) = device.component_manager.remove_receptors(
                device.component_manager._receptors[:]
            )
            device.logger.info(message)
            return (result_code, message)

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

    
    class AddReceptorsCommand(SKASubarray.AssignResourcesCommand):
        # NOTE: doesn't inherit SKASubarray._ResourcingCommand 
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

            (result_code, message) = device.component_manager.add_receptors(argin)
            device.logger.info(message)
            return (result_code, message)


    ############  Configure Related Commands   ##############

    class ConfigureScanCommand(SKASubarray.ConfigureCommand):
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

            (result_code, message) = device.component_manager.configure_scan(argin)
            device.logger.info(message)
            return (result_code, message)

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
        (return_code, message) = command(argin)
        return [[return_code], [message]]    

    class ScanCommand(SKASubarray.ScanCommand):
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

            (result_code, message) = device.component_manager.scan(argin)
            device.logger.info(message)
            return (result_code, message)


    class EndScanCommand(SKASubarray.EndScanCommand):
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
            (result_code, message) = super().do()

            device = self.target
            device.logger.info(message)

            if result_code == ResultCode.OK:
                (result_code, message) = device.component_manager.end_scan()
                device.logger.info(message)

            return (result_code, message)


    @command(
        dtype_out='DevVarLongStringArray',
        doc_out="(ReturnType, 'informational message')",
    )
    def GoToIdle(self: CbfSubarray) -> Tuple[ResultCode, str]:
        """
        deconfigure a scan, set ObsState to IDLE

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        
        command = self.get_command_object("GoToIdle")
        (return_code, message) = command()
        return [[return_code], [message]]

    class GoToIdleCommand(SKASubarray.EndCommand):
        """
        A class for SKASubarray's GoToIdle() command.
        """
        def do(self: CbfSubarray.GoToIdleCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for GoToIdle() command functionality.
            
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            
            device = self.target
            device.logger.debug("Entering GoToIdleCommand()")

            (result_code, message) = device.component_manager.go_to_idle()
            device.logger.info(message)
            return (result_code, message)

    ############### abort, restart and reset #####################

    class AbortCommand(SKASubarray.AbortCommand):
        """
        A class for SKASubarray's Abort() command.
        """
        def do(self: CbfSubarray.AbortCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Abort() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, message) = super().do()

            device = self.target
            device.logger.info(message)

            if result_code == ResultCode.OK:
                (result_code, message) = device.component_manager.abort()
                device.logger.info(message)

            return (result_code, message)

    
    # RestartCommand already registered in SKASubarray, so no "def restart" needed
    class RestartCommand(SKASubarray.RestartCommand):
        """
        A class for CbfSubarray's Restart() command.
        """
        def do(self: CbfSubarray.RestartCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Restart() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target

            (result_code, message) = device.component_manager.restart()
            device.logger.info(message)
            return (result_code, message)


    class ObsResetCommand(SKASubarray.ObsResetCommand):
        """
        A class for CbfSubarray's ObsReset() command.
        """
        def do(self: CbfSubarray.ObsResetCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ObsReset() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            device = self.target
            
            (result_code, message) = device.component_manager.obs_reset()
            device.logger.info(message)
            return (result_code, message)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfSubarray.main) ENABLED START #
    return run((CbfSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfSubarray.main


if __name__ == '__main__':
    main()