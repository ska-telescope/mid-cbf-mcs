# -*- coding: utf-8 -*-
#
# This file is part of the FspPssSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: Ryam Voigt Ryan.Voigt@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada

FspPssSubarray Tango device prototype

FspPssSubarray TANGO device class for the FspPssSubarray prototype
"""
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple, Optional

# tango imports
import tango
from tango import DebugIt
from tango.server import run
from tango.server import Device
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(FspPssSubarray.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

from ska_tango_base.control_model import HealthState, AdminMode, ObsState, PowerMode
from ska_tango_base import CspSubElementObsDevice
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.fsp.fsp_pss_subarray_component_manager import FspPssSubarrayComponentManager
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

# PROTECTED REGION END #    //  FspPssSubarray.additionnal_import

__all__ = ["FspPssSubarray", "main"]

class FspPssSubarray(CspSubElementObsDevice):
    """
    FspPssSubarray TANGO device class for the FspPssSubarray prototype
    """
    # PROTECTED REGION ID(FspPssSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPssSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(
        dtype='uint16'
    )

    FspID = device_property(
        dtype='uint16'
    )

    CbfControllerAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Controller",
        default_value="mid_csp_cbf/controller/main"
    )

    # TODO: CbfSubarrayAddress prop not being used
    CbfSubarrayAddress = device_property(
        dtype='str',
        doc="FQDN of CBF Subarray"
    )

    VCC = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    receptors = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ,
        max_dim_x=197,
        label="Receptors",
        doc="List of receptors assigned to subarray",
    )
    searchBeams = attribute(
        dtype=('str',),
        access=AttrWriteType.READ,
        max_dim_x=192,
        label="SearchBeams",
        doc="List of searchBeams assigned to fspsubarray",
    )
    searchWindowID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ,
        max_dim_x=2,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    searchBeamID = attribute(
        dtype=('uint16',),
        access=AttrWriteType.READ,
        max_dim_x=192,
        label="ID for 300MHz Search Window",
        doc="Identifier of the Search Window to be used as input for beamforming on this FSP.",
    )

    outputEnable = attribute(
        dtype='bool',
        access=AttrWriteType.READ,
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: FspPssSubarray) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.obs_state_model, self.logger)
        self.register_command_object(
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the Vcc's init_device() "command".
        """

        def do(
            self: FspPssSubarray.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            device = self.target

            # Make a private copy of the device properties:
            device._subarray_id = device.SubID
            device._fsp_id = device.FspID

            # initialize attribute values
            device._receptors = []
            device._search_beams = []
            device._search_window_id = 0
            device._search_beam_id = []
            device._output_enable = 0
            device._scan_id = 0
            device._config_id = ""

            # device proxy for connection to CbfController
            device._proxy_cbf_controller = CbfDeviceProxy(
                fqdn=device.CbfControllerAddress,
                logger=device.logger
            )
            device._controller_max_capabilities = dict(
                pair.split(":") for pair in 
                device._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
            )

            # Connect to all VCC devices turned on by CbfController:
            device._count_vcc = int(device._controller_max_capabilities["VCC"])
            device._fqdn_vcc = list(device.VCC)[:device._count_vcc]
            device._proxies_vcc = [
                CbfDeviceProxy(
                    logger=device.logger, 
                    fqdn=address) for address in device._fqdn_vcc
            ]

            message = "FspPssSubarry Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

        # PROTECTED REGION END #    //  FspPssSubarray.init_device

    def always_executed_hook(self: FspPssSubarray) -> None:
        # PROTECTED REGION ID(FspPssSubarray.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""
        pass
        # PROTECTED REGION END #    //  FspPssSubarray.always_executed_hook
    
    def create_component_manager(self: FspPssSubarray) -> FspPssSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return FspPssSubarrayComponentManager( 
            self.logger,
            self.push_change_event,
            self._communication_status_changed,
            self._component_power_mode_changed,
        )

    def delete_device(self: FspPssSubarray) -> None:
        # PROTECTED REGION ID(FspPssSubarray.delete_device) ENABLED START #
        """Hook to delete device."""
        pass
        # PROTECTED REGION END #    //  FspPssSubarray.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptors(self: FspPssSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPssSubarray.receptors_read) ENABLED START #
        """
            Read the receptors attribute.

            :return: the receptors attribute.
            :rtype: List[int]
        """
        return self._receptors
        # PROTECTED REGION END #    //  FspPssSubarray.receptors_read

    def read_searchBeams(self: FspPssSubarray) -> List[str]:
        # PROTECTED REGION ID(FspPssSubarray.searchBeams_read) ENABLED START #
        """
            Read the searchBeams attribute. 

            :return: the searchBeams attribute.
            :rtype: List[str]
        """
        return self._search_beams
        # PROTECTED REGION END #    //  FspPssSubarray.searchBeams_read

    def read_searchBeamID(self: FspPssSubarray) -> List[int]:
        # PROTECTED REGION ID(FspPssSubarray.read_searchBeamID ENABLED START #
        """
            Read the searchBeamID attribute. 

            :return: the searchBeamID attribute.
            :rtype: List[int]
        """
        return self._search_beam_id
        # PROTECTED REGION END #    //  FspPssSubarray.read_searchBeamID

    def read_searchWindowID(self: FspPssSubarray) -> List[int]:
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_searchWindowID) ENABLED START #
        """
            Read the searchWindowID attribute. 

            :return: the searchWindowID attribute.
            :rtype: List[int]
        """
        return self._search_window_id
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_searchWindowID

    def read_outputEnable(self: FspPssSubarray) -> bool:
        # PROTECTED REGION ID(CbfSubarrayPssConfig.read_outputEnable) ENABLED START #
        """
            Read the outputEnable attribute. Used to enable/disable 
            transmission of the output products.

            :return: the outputEnable attribute.
            :rtype: bool
        """
        return self._output_enable
        # PROTECTED REGION END #    //  CbfSubarrayPssConfig.read_outputEnable

    # --------
    # Commands
    # --------

    def _add_receptors(
        self: FspPssSubarray, 
        argin: List[int]
        ) -> None:
        """
            Add specified receptors to the subarray.

            :param argin: ids of receptors to add. 
        """
        self.logger.debug("_AddReceptors")
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                subarrayID = self._proxies_vcc[vccID - 1].subarrayMembership

                # only add receptor if it belongs to the CBF subarray
                if subarrayID != self._subarray_id:
                    errs.append("Receptor {} does not belong to subarray {}.".format(
                        str(receptorID), str(self._subarray_id)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)
                    else:
                        # TODO: this is not true if more receptors can be 
                        #       specified for the same search beam
                        log_msg = "Receptor {} already assigned to current FSP subarray.".format(
                            str(receptorID))
                        self.logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "AddReceptors execution",
                                           tango.ErrSeverity.ERR)
        # PROTECTED REGION END #    //  FspPssSubarray.AddReceptors

    def _remove_receptors(
        self: FspPssSubarray, 
        argin: List[int]
        )-> None:
        """
            Remove specified receptors from the subarray.

            :param argin: ids of receptors to remove. 
        """
        self.logger.debug("_remove_receptors")
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self.logger.warn(log_msg)

    def _remove_all_receptors(self: FspPssSubarray) -> None:
        """ Remove all receptors from the subarray."""
        self._remove_receptors(self._receptors[:])

    # --------
    # Commands
    # --------

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the FspPssSubarray's ConfigureScan() command.
        """

        """Input a serilized JSON object. """

        def do(
            self: FspPssSubarray.ConfigureScanCommand,
            argin: str,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string.
            :type argin: str

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            device = self.target

            argin = json.loads(argin)

            # Configure receptors.
            self.logger.debug("_receptors = {}".format(device._receptors))
            # TODO: Why are we overwriting the device property fsp ID
            #       with the argument in the ConfigureScan json file
            if device._fsp_id != argin["fsp_id"]:
                device.logger.warning(
                    "The Fsp ID from ConfigureScan {} does not equal the Fsp ID from the device properties {}"
                    .format(device._fsp_id, argin["fsp_id"]))
            device._fsp_id = argin["fsp_id"]
            device._search_window_id = int(argin["search_window_id"])

            self.logger.debug("_search_window_id = {}".format(device._search_window_id))

            for searchBeam in argin["search_beam"]:

                if len(searchBeam["receptor_ids"]) != 1:
                    # TODO - to add support for multiple receptors
                    msg = "Currently only 1 receptor per searchBeam is supported"
                    self.logger.error(msg) 
                    return (ResultCode.FAILED, msg)

                device._add_receptors(map(int, searchBeam["receptor_ids"]))
                self.logger.debug("device._receptors = {}".format(device._receptors))
                device._search_beams.append(json.dumps(searchBeam))

                device._search_beam_id.append(int(searchBeam["search_beam_id"]))
            
            # TODO: _output_enable is not currently set

            # TODO - possibly move validation of params to  
            #        validate_input()
            # (result_code, msg) = self.validate_input(argin) # TODO

            result_code = ResultCode.OK # TODO  - temp - remove
            msg = "Configure command completed OK" # TODO temp, remove

            if result_code == ResultCode.OK:
                # store the configuration on command success
                device._last_scan_configuration = argin
                msg = "Configure command completed OK"

            return(result_code, msg)

        def validate_input(self, argin):
            """
            Validate the configuration parameters against allowed values, as needed.

            :param argin: The JSON formatted string with configuration for the device.
            :type argin: 'DevString'
            :return: A tuple containing a return code and a string message.
            :rtype: (ResultCode, str)
            """
            device = self.target
            return (ResultCode.OK, "ConfigureScan arguments validation successfull") 

    @command(
    dtype_in='DevString',
    doc_in="JSON formatted string with the scan configuration.",
    dtype_out='DevVarLongStringArray',
    doc_out="A tuple containing a return code and a string message indicating status. "
            "The message is for information purpose only.",
    )

    @DebugIt()
    def ConfigureScan(
            self: FspPssSubarray, 
            argin: str
        ) -> Tuple[ResultCode, str]:
        # PROTECTED REGION ID(Vcc.ConfigureScan) ENABLED START #
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.
        :type argin: 'DevString'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]

    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the FspPssSubarray's GoToIdle command.
        """

        def do(
            self: FspPssSubarray.GoToIdleCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for GoToIdle() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")

            device = self.target

            # initialize attribute values
            device._search_beams = []
            device._search_window_id = 0
            device._search_beam_id = []
            device._output_enable = 0
            device._scan_id = 0
            device._config_id = ""

            device._remove_all_receptors()

            if device.state_model.obs_state == ObsState.IDLE:
                return (ResultCode.OK, 
                "GoToIdle command completed OK. Device already IDLE")

            return (ResultCode.OK, "GoToIdle command completed OK")
    
    # ----------
    # Callbacks
    # ----------

    def _component_configured(
        self: FspPssSubarray,
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
        self: FspPssSubarray, 
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
    
    def _component_obsfault(self: FspPssSubarray) -> None:
        """
        Handle notification that the component has obsfaulted.

        This is a callback hook.
        """
        self.obs_state_model.perform_action("component_obsfault")


    def _communication_status_changed(
        self: FspPssSubarray,
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
        self: FspPssSubarray,
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

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPssSubarray.main) ENABLED START #
    return run((FspPssSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPssSubarray.main


if __name__ == '__main__':
    main()