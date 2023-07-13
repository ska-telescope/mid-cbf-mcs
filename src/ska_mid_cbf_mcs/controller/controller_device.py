# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
CbfController
Sub-element controller device for Mid.CBf
"""

from __future__ import annotations  # allow forward references in type hints

from typing import List, Optional, Tuple

import tango
from ska_tango_base import SKABaseDevice, SKAController
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.controller.controller_component_manager import (
    ControllerComponentManager,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)

__all__ = ["CbfController", "main"]


class CbfController(SKAController):

    """
    CbfController TANGO device class.
    Primary point of contact for monitoring and control of Mid.CBF. Implements state and mode indicators, and a set of state transition commmands.
    """

    # PROTECTED REGION ID(CbfController.class_variable) ENABLED START #

    # PROTECTED REGION END #    //  CbfController.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CbfSubarray = device_property(dtype=("str",))

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    TalonLRU = device_property(dtype=("str",))

    TalonDxConfigPath = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    commandProgress = attribute(
        dtype="uint16",
        label="Command progress percentage",
        max_value=100,
        min_value=0,
        polling_period=3000,
        abs_change=5,
        rel_change=2,
        doc="Percentage progress implemented for commands that result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
    )

    receptorToVcc = attribute(
        dtype=("str",),
        max_dim_x=197,
        label="Receptor-VCC map",
        polling_period=3000,
        doc='Maps receptors IDs to VCC IDs, in the form "receptorID:vccID"',
    )

    vccToReceptor = attribute(
        dtype=("str",),
        max_dim_x=197,
        label="VCC-receptor map",
        polling_period=3000,
        doc='Maps VCC IDs to receptor IDs, in the form "vccID:receptorID"',
    )

    subarrayconfigID = attribute(
        dtype=("str",),
        max_dim_x=16,
        label="Subarray config IDs",
        polling_period=3000,
        doc="ID of subarray configuration. empty string if subarray is not configured for a scan.",
    )

    reportVCCState = attribute(
        dtype=("DevState",),
        max_dim_x=197,
        label="VCC state",
        polling_period=3000,
        doc="Report the state of the VCC capabilities as an array of DevState",
    )

    reportVCCHealthState = attribute(
        dtype=("uint16",),
        max_dim_x=197,
        label="VCC health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of VCC capabilities as an array of unsigned short.\nEx:\n[0,0,0,2,0...3]",
    )

    reportVCCAdminMode = attribute(
        dtype=("uint16",),
        max_dim_x=197,
        label="VCC admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the VCC capabilities as an array of unsigned short.\nFor ex.:\n[0,0,0,...1,2]",
    )

    reportVCCSubarrayMembership = attribute(
        dtype=("uint16",),
        max_dim_x=197,
        label="VCC subarray membership",
        # no polling period so it reads the true value and not the one in cache
        doc="Report the subarray membership of VCCs (each can only belong to a single subarray), 0 if not assigned.",
    )

    reportFSPState = attribute(
        dtype=("DevState",),
        max_dim_x=27,
        label="FSP state",
        polling_period=3000,
        doc="Report the state of the FSP capabilities.",
    )

    reportFSPHealthState = attribute(
        dtype=("uint16",),
        max_dim_x=27,
        label="FSP health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the FSP capabilities.",
    )

    reportFSPAdminMode = attribute(
        dtype=("uint16",),
        max_dim_x=27,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the FSP capabilities as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    reportFSPSubarrayMembership = attribute(
        dtype=(("uint16",),),
        max_dim_x=16,
        max_dim_y=27,
        label="FSP subarray membership",
        polling_period=3000,
        abs_change=1,
        doc="Report the subarray membership of FSPs (each can only belong to at most 16 subarrays), 0 if not assigned.",
    )

    frequencyOffsetK = attribute(
        dtype=("int",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency offset (k)",
        doc="Frequency offset (k) of all 197 receptors as an array of ints.",
    )

    frequencyOffsetDeltaF = attribute(
        dtype=("int",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=197,
        label="Frequency offset (delta f)",
        doc="Frequency offset (delta f) of all 197 receptors as an array of ints.",
    )

    reportSubarrayState = attribute(
        dtype=("DevState",),
        max_dim_x=16,
        label="Subarray state",
        polling_period=3000,
        doc="Report the state of the Subarray",
    )

    reportSubarrayHealthState = attribute(
        dtype=("uint16",),
        max_dim_x=16,
        label="Subarray health status",
        polling_period=3000,
        abs_change=1,
        doc="Report the health status of the Subarray.",
    )

    reportSubarrayAdminMode = attribute(
        dtype=("uint16",),
        max_dim_x=16,
        label="FSP admin mode",
        polling_period=3000,
        abs_change=1,
        doc="Report the administration mode of the Subarray as an array of unsigned short.\nfor ex:\n[0,0,2,..]",
    )

    simulationMode = attribute(
        dtype=SimulationMode,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        doc="Reports the simulation mode of the device. \nSome devices may implement "
        "both modes, while others will have simulators that set simulationMode "
        "to True while the real devices always set simulationMode to False.",
    )

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: CbfController) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object("On", self.OnCommand(*device_args))

        self.register_command_object("Off", self.OffCommand(*device_args))

        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

    def get_num_capabilities(
        self: CbfController,
    ) -> None:
        # self._max_capabilities inherited from SKAController
        # check first if property exists in DB
        """Get number of capabilities for _init_Device.
        If property not found in db, then assign a default amount(197,27,16)"""

        if self._max_capabilities:
            return self._max_capabilities
        else:
            self.logger.warning("MaxCapabilities device property not defined")

    class InitCommand(SKAController.InitCommand):
        def _get_num_capabilities(
            self: CbfController.InitCommand,
        ) -> None:
            # self._max_capabilities inherited from SKAController
            # check first if property exists in DB
            """Get number of capabilities for _init_Device.
            If property not found in db, then assign a default amount(197,27,16)
            """

            device = self.target

            device.write_simulationMode(True)

            if device._max_capabilities:
                try:
                    device._count_vcc = device._max_capabilities["VCC"]
                except KeyError:  # not found in DB
                    self.logger.warning(
                        "VCC capabilities not defined; defaulting to 197."
                    )
                    device._count_vcc = 197

                try:
                    device._count_fsp = device._max_capabilities["FSP"]
                except KeyError:  # not found in DB
                    self.logger.warning(
                        "FSP capabilities not defined; defaulting to 27."
                    )
                    device._count_fsp = 27

                try:
                    device._count_subarray = device._max_capabilities[
                        "Subarray"
                    ]
                except KeyError:  # not found in DB
                    self.logger.warning(
                        "Subarray capabilities not defined; defaulting to 16."
                    )
                    device._count_subarray = 16
            else:
                self.logger.warning(
                    "MaxCapabilities device property not defined - \
                    using default value"
                )

        def do(
            self: CbfController.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
            :return: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")
            message = "Entering InitCommand()"
            self.logger.info(message)

            super().do()

            device = self.target

            # initialize attribute values
            device._command_progress = 0

            device._storage_logging_level = tango.LogLevel.LOG_DEBUG
            device._element_logging_level = tango.LogLevel.LOG_DEBUG
            device._central_logging_level = tango.LogLevel.LOG_DEBUG

            # defines self._count_vcc, self._count_fsp, and self._count_subarray
            self._get_num_capabilities()

            # initialize dicts with maps receptorID <=> vccID
            # TODO: vccID == receptorID for now, for testing purposes
            device._receptor_to_vcc = []
            device._vcc_to_receptor = []
            for vccID in range(1, device._count_vcc + 1):
                receptorID = vccID
                device._receptor_to_vcc.append(f"{receptorID}:{vccID}")
                device._vcc_to_receptor.append(f"{vccID}:{receptorID}")

            # # initialize attribute values
            device._command_progress = 0

            message = "CbfController Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self: CbfController) -> None:
        # PROTECTED REGION ID(CbfController.always_executed_hook) ENABLED START #
        """
        Hook to be executed before any command.
        """
        # PROTECTED REGION END #    //  CbfController.always_executed_hook

    def create_component_manager(
        self: CbfController,
    ) -> ControllerComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        # Create the Talon-DX component manager and initialize simulation
        # mode to on
        self._simulation_mode = SimulationMode.TRUE
        self._talondx_component_manager = TalonDxComponentManager(
            self.TalonDxConfigPath, self._simulation_mode, self.logger
        )

        return ControllerComponentManager(
            get_num_capabilities=self.get_num_capabilities,
            vcc_fqdns_all=self.VCC,
            fsp_fqdns_all=self.FSP,
            subarray_fqdns_all=self.CbfSubarray,
            talon_lru_fqdns_all=self.TalonLRU,
            talondx_component_manager=self._talondx_component_manager,
            talondx_config_path=self.TalonDxConfigPath,
            logger=self.logger,
            push_change_event=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )

    def delete_device(self: CbfController) -> None:
        """Unsubscribe to events, turn all the subarrays, VCCs and FSPs off"""
        # PROTECTED REGION ID(CbfController.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  CbfController.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self: CbfController) -> int:
        # PROTECTED REGION ID(CbfController.commandProgress_read) ENABLED START #
        """Return commandProgress attribute: percentage progress implemented for
        commands that result in state/mode transitions for a large number of
        components and/or are executed in stages (e.g power up, power down)"""
        return self._command_progress
        # PROTECTED REGION END #    //  CbfController.commandProgress_read

    def read_receptorToVcc(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.receptorToVcc_read) ENABLED START #
        """Return 'receptorID:vccID'"""
        return self._receptor_to_vcc
        # PROTECTED REGION END #    //  CbfController.receptorToVcc_read

    def read_vccToReceptor(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.vccToReceptor_read) ENABLED START #
        """Return receptorToVcc attribute: 'vccID:receptorID'"""
        return self._vcc_to_receptor
        # PROTECTED REGION END #    //  CbfController.vccToReceptor_read

    def read_subarrayconfigID(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.subarrayconfigID_read) ENABLED START #
        """Return subarrayconfigID atrribute: ID of subarray config.
        Used for debug purposes. empty string if subarray is not configured for a scan
        """
        return self.component_manager.subarray_config_ID
        # PROTECTED REGION END #    //  CbfController.subarrayconfigID_read

    def read_reportVCCState(self: CbfController) -> List[tango.DevState]:
        # PROTECTED REGION ID(CbfController.reportVCCState_read) ENABLED START #
        """Return reportVCCState attribute: the state of the VCC capabilities as an array of DevState"""
        return self.component_manager.report_vcc_state
        # PROTECTED REGION END #    //  CbfController.reportVCCState_read

    def read_reportVCCHealthState(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportVCCHealthState_read) ENABLED START #
        """
        Return reportVCCHealthState attribute: health status of VCC capabilities
        as an array of unsigned short. Ex: [0,0,0,2,0...3]
        """
        return self.component_manager.report_vcc_health_state
        # PROTECTED REGION END #    //  CbfController.reportVCCHealthState_read

    def read_reportVCCAdminMode(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportVCCAdminMode_read) ENABLED START #
        """
        Return reportVCCAdminMode attribute: report the administration mode
        of the VCC capabilities as an array of unsigned short. For ex.: [0,0,0,...1,2]
        """
        return self.component_manager.report_vcc_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportVCCAdminMode_read

    def read_reportVCCSubarrayMembership(self: CbfController) -> List[int]:
        """Return reportVCCSubarrayMembership attribute: report the subarray membership of VCCs
        (each can only belong to a single subarray), 0 if not assigned."""
        # PROTECTED REGION ID(CbfController.reportVCCSubarrayMembership_read) ENABLED START #
        return self.component_manager.report_vcc_subarray_membership
        # PROTECTED REGION END #    //  CbfController.reportVCCSubarrayMembership_read

    def read_reportFSPState(self: CbfController) -> List[tango.DevState]:
        # PROTECTED REGION ID(CbfController.reportFSPState_read) ENABLED START #
        """Return reportFSPState attribute: state of all the FSP capabilities in the form of array"""
        return self.component_manager.report_fsp_state
        # PROTECTED REGION END #    //  CbfController.reportFSPState_read

    def read_reportFSPHealthState(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportFSPHealthState_read) ENABLED START #
        """Return reportFspHealthState attribute: Report the health status of the FSP capabilities"""
        return self.component_manager.report_fsp_health_state
        # PROTECTED REGION END #    //  CbfController.reportFSPHealthState_read

    def read_reportFSPAdminMode(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportFSPAdminMode_read) ENABLED START #
        """
        Return reportFSPAdminMode attribute: Report the administration mode
        of the FSP capabilities as an array of unsigned short. for ex: [0,0,2,..]
        """
        return self.component_manager.report_fsp_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportFSPAdminMode_read

    def read_reportFSPSubarrayMembership(
        self: CbfController,
    ) -> List[List[int]]:
        # PROTECTED REGION ID(CbfController.reportFSPSubarrayMembership_read) ENABLED START #
        """Return reportVCCSubarrayMembership attribute: Report the subarray membership
        of FSPs (each can only belong to at most 16 subarrays), 0 if not assigned.
        """
        return self.component_manager.report_fsp_subarray_membership
        # PROTECTED REGION END #    //  CbfController.reportFSPSubarrayMembership_read

    def read_frequencyOffsetK(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_read) ENABLED START #
        """Return frequencyOffsetK attribute: array of integers reporting receptors in subarray"""
        return self.component_manager.frequency_offset_k
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_read

    def write_frequencyOffsetK(self: CbfController, value: List[int]) -> None:
        # PROTECTED REGION ID(CbfController.frequencyOffsetK_write) ENABLED START #
        """Set frequencyOffsetK attribute"""
        if len(value) == self._count_vcc:
            self.component_manager.update_freq_offset_k(value)
        else:
            log_msg = (
                "Skipped writing to frequencyOffsetK attribute "
                + f"(expected {self._count_vcc} arguments, but received {len(value)}."
            )
            self.logger.warning(log_msg)
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetK_write

    def read_frequencyOffsetDeltaF(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.frequencyOffsetDeltaF_read) ENABLED START #
        """Return frequencyOffsetDeltaF attribute: Frequency offset (delta f)
        of all 197 receptors as an array of ints."""
        return self.component_manager.frequency_offset_delta_f
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetDeltaF_read

    def write_frequencyOffsetDeltaF(
        self: CbfController, value: List[int]
    ) -> None:
        # PROTECTED REGION ID(CbfController.frequencyOffsetDeltaF_write) ENABLED START #
        """Set the frequencyOffsetDeltaF attribute"""
        if len(value) == self._count_vcc:
            self.component_manager.update_freq_offset_deltaF(value)
        else:
            log_msg = (
                "Skipped writing to frequencyOffsetDeltaF attribute "
                + f"(expected {self._count_vcc} arguments, but received {len(value)}."
            )
            self.logger.warning(log_msg)
        # PROTECTED REGION END #    //  CbfController.frequencyOffsetDeltaF_write

    def read_reportSubarrayState(self: CbfController) -> List[tango.DevState]:
        # PROTECTED REGION ID(CbfController.reportSubarrayState_read) ENABLED START #
        """Return reportSubarrayState attribute: report the state of the Subarray with an array of DevState"""
        return self.component_manager.report_subarray_state
        # PROTECTED REGION END #    //  CbfController.reportSubarrayState_read

    def read_reportSubarrayHealthState(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportSubarrayHealthState_read) ENABLED START #
        """Return reportSubarrayHealthState attribute: subarray healthstate in an array of unsigned short"""
        return self.component_manager.report_subarray_health_state
        # PROTECTED REGION END #    //  CbfController.reportSubarrayHealthState_read

    def read_reportSubarrayAdminMode(self: CbfController) -> List[int]:
        # PROTECTED REGION ID(CbfController.reportSubarrayAdminMode_read) ENABLED START #
        """
        Return reportSubarrayAdminMode attribute: Report the administration mode
        of the Subarray as an array of unsigned short. for ex: [0,0,2,..]
        """
        return self.component_manager.report_subarray_admin_mode
        # PROTECTED REGION END #    //  CbfController.reportSubarrayAdminMode_read

    def write_simulationMode(
        self: CbfController, value: SimulationMode
    ) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
        super().write_simulationMode(value)
        self._talondx_component_manager.simulation_mode = value

    # --------
    # Commands
    # --------

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the CbfController's On() command.
        """

        def do(
            self: CbfController.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = self.target.component_manager.on()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.ON)

            self.logger.info(message)
            return (result_code, message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the CbfController's Off() command.
        """

        def do(
            self: CbfController.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = self.target.component_manager.off()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.OFF)

            self.logger.info(message)
            return (result_code, message)

    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the CbfController's Standby() command.
        """

        def do(
            self: CbfController.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.
            Turn off subarray, vcc, fsp, turn CbfController to standby

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = self.target.component_manager.standby()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.STANDBY)

            self.logger.info(message)
            return (result_code, message)

    # ----------
    # Callbacks
    # ----------
    def _communication_status_changed(
        self: CbfController,
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

    def _component_power_mode_changed(
        self: CbfController,
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

    def _component_fault(self: CbfController, faulty: bool) -> None:
        """
        Handle component fault

        :param faulty: whether the component has faulted.
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfController.main) ENABLED START #
    return run((CbfController,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfController.main


if __name__ == "__main__":
    main()
