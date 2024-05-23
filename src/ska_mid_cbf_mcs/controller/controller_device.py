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

from typing import Any, List, Optional, Tuple

import tango
from ska_tango_base import SKAController
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tango_base.control_model import PowerState, SimulationMode
from ska_tango_base.utils import convert_dict_to_list
from tango import AttrWriteType, DebugIt, DevState
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.controller.controller_component_manager import (
    ControllerComponentManager,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)
from ska_mid_cbf_mcs.device.base_device import CbfDevice

__all__ = ["CbfController", "main"]


class CbfController(CbfDevice):

    """
    CbfController TANGO device class.

    Primary point of contact for monitoring and control of Mid.CBF.
    Implements state and mode indicators, and a set of state transition commmands.
    """

    # -----------------
    # Device Properties
    # -----------------

    CbfSubarray = device_property(dtype=("str",))

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    TalonLRU = device_property(dtype=("str",))

    TalonBoard = device_property(dtype=("str",))

    PowerSwitch = device_property(dtype=("str",))

    FsSLIM = device_property(dtype=("str"))

    VisSLIM = device_property(dtype=("str"))

    TalonDxConfigPath = device_property(dtype=("str"))

    HWConfigPath = device_property(dtype=("str"))

    FsSLIMConfigPath = device_property(dtype=("str"))

    VisSLIMConfigPath = device_property(dtype=("str"))

    LruTimeout = device_property(dtype=("str"))

    MaxCapabilities = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="uint16",
        max_value=100,
        min_value=0,
        polling_period=3000,
        abs_change=5,
        rel_change=2,
        doc="Percentage progress implemented for commands that result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
    )
    def commandProgress(self: CbfController) -> int:
        """
        Read the commandProgress attribute: the percentage progress implemented for
        commands that result in state/mode transitions for a large number of
        components and/or are executed in stages (e.g power up, power down)

        :return: the commandProgress attribute
        :rtype: int
        """
        return self._command_progress

    @attribute(
        dtype="str",
        label="Dish ID to VCC and frequency offset k mapping",
        doc="Maps Dish ID to VCC and frequency offset k. The string is in JSON format.",
    )
    def sysParam(self: CbfController) -> str:
        """
        :return: the mapping from Dish ID to VCC and frequency offset k. The string is in JSON format.
        :rtype: str
        """
        return self.component_manager._init_sys_param

    @attribute(
        dtype="str",
        label="The location of the file containing Dish ID to VCC and frequency offset k mapping.",
        doc="Source and file path to the file to be retrieved through the Telescope Model. The string is in JSON format.",
    )
    def sourceSysParam(self: CbfController) -> str:
        """
        :return: the location of the json file that contains the mapping from Dish ID to VCC
                 and frequency offset k, to be retrieved using the Telescope Model.
        :rtype: str
        """
        return self.component_manager._source_init_sys_param

    @attribute(
        dtype="DevVarLongStringArray",
        label="Dish ID to VCC mapping",
        doc="Dish ID to VCC mapping. The string is in the format 'dishID:vccID'.",
    )
    def dishToVcc(self: CbfController) -> List[str]:
        """
        Return dishToVcc attribute: 'dishID:vccID'
        """
        if self.component_manager.dish_utils is None:
            return []
        out_str = [
            f"{r}:{v}"
            for r, v in self.component_manager.dish_utils.dish_id_to_vcc_id.items()
        ]
        return out_str

    @attribute(
        dtype="DevVarLongStringArray",
        label="VCC to Dish mapping",
        doc="VCC to Dish mapping. The string is in the format 'vccID:dishID'.",
    )
    def vccToDish(self: CbfController) -> List[str]:
        """
        Return dishToVcc attribute: 'vccID:dishID'
        """
        if self.component_manager.dish_utils is None:
            return []
        out_str = [
            f"{v}:{r}"
            for r, v in self.component_manager.dish_utils.dish_id_to_vcc_id.items()
        ]
        return out_str

    @attribute(
        dtype="DevVarLongStringArray",
        max_dim_x=20,
        doc=(
            "Maximum number of instances of each capability type,"
            " e.g. 'CORRELATOR:512', 'PSS-BEAMS:4'."
        ),
    )
    def maxCapabilities(self: CbfController) -> list[str]:
        """
        Read maximum number of instances of each capability type.

        :return: list of maximum number of instances of each capability type
        """
        return convert_dict_to_list(self._max_capabilities)

    @attribute(
        dtype=SimulationMode,
        memorized=True,
        hw_memorized=True,
        doc="Reports the simulation mode of the device. \nSome devices may implement "
        "both modes, while others will have simulators that set simulationMode "
        "to True while the real devices always set simulationMode to False.",
    )
    def simulationMode(self: CbfController) -> SimulationMode:
        """
        :return: the current simulation mode
        """
        return self._talondx_component_manager.simulation_mode

    @simulationMode.write
    def simulationMode(self: CbfController, value: SimulationMode) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self._talondx_component_manager.simulation_mode = value

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: CbfController) -> None:
        """
        Sets up the command objects
        """
        super(SKAController, self).init_command_objects()
        self.register_command_object(
            "InitSysParam",
            SubmittedSlowCommand(
                command_name="InitSysParam",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="init_sys_param",
                logger=self.logger,
            ),
        )

    def create_component_manager(
        self: CbfController,
    ) -> ControllerComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        self._talondx_component_manager = TalonDxComponentManager(
            talondx_config_path=self.TalonDxConfigPath,
            hw_config_path=self.HWConfigPath,
            simulation_mode=self._simulation_mode,
            logger=self.logger,
        )

        # TODO: Clear unused and add base class params
        return ControllerComponentManager(
            get_num_capabilities=self.get_num_capabilities,
            vcc_fqdns_all=self.VCC,
            fsp_fqdns_all=self.FSP,
            subarray_fqdns_all=self.CbfSubarray,
            talon_lru_fqdns_all=self.TalonLRU,
            talon_board_fqdns_all=self.TalonBoard,
            power_switch_fqdns_all=self.PowerSwitch,
            fs_slim_fqdn=self.FsSLIM,
            vis_slim_fqdn=self.VisSLIM,
            lru_timeout=int(self.LruTimeout),
            talondx_component_manager=self._talondx_component_manager,
            talondx_config_path=self.TalonDxConfigPath,
            hw_config_path=self.HWConfigPath,
            fs_slim_config_path=self.FsSLIMConfigPath,
            vis_slim_config_path=self.VisSLIMConfigPath,
            logger=self.logger,
            push_change_event=self.push_change_event,
        )

    # --------
    # Commands
    # --------

    class InitCommand(SKAController.InitCommand):
        """
        A class for the CbfController's Init() command.
        """

        def _get_max_capabilities(
            self: CbfController.InitCommand,
        ) -> None:
            """
            Get maximum number of capabilities for _init_Device.
            """
            device = self._device
            device._max_capabilities = {}

            if device.MaxCapabilities:
                for max_capability in device.MaxCapabilities:
                    (
                        capability_type,
                        max_capability_instances,
                    ) = max_capability.split(":")
                    device._max_capabilities[capability_type] = int(
                        max_capability_instances
                    )

        def _get_num_capabilities(
            self: CbfController.InitCommand,
        ) -> None:
            """
            Get number of capabilities for _init_Device.
            If property not found in db, then assign a default amount(197,27,16)
            """

            device = self._device
            # TODO: Confirm removal of this line
            # device.write_simulationMode(True)

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
            *args: Any,
            **kwargs: Any,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
            :return: (ResultCode, str)
            """
            (result_code, msg) = super().do(*args, **kwargs)

            self._device._simulation_mode = SimulationMode.TRUE

            # initialize attribute values
            self._device._command_progress = 0

            # initialize max capabilities
            self._get_max_capabilities()

            # defines self._count_vcc, self._count_fsp, and self._count_subarray
            self._get_num_capabilities()

            # # initialize attribute values
            self._device._command_progress = 0

            return (result_code, msg)

    def is_On_allowed(self: CbfController) -> bool:
        """
        Overwrite baseclass's is_On_allowed method.
        """
        return True

    def On(
        self: CbfController,
    ) -> DevVarLongStringArrayType:
        """
        Turn the device on.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object(command_name="On")
        result_code_message, command_id = command_handler()
        return [result_code_message], [command_id]

    def is_Off_allowed(self: CbfController) -> bool:
        """
        Overwrite baseclass's is_On_allowed method.
        """
        return True

    def Off(
        self: CbfController,
    ) -> DevVarLongStringArrayType:
        """
        Turn the device off.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object(command_name="Off")
        result_code_message, command_id = command_handler()
        return [result_code_message], [command_id]

    def is_InitSysParam_allowed(self: CbfController) -> bool:
        """
        Determine if InitSysParamCommand is allowed (allowed when state is OFF).

        :return: if InitSysParamCommand is allowed
        :rtype: bool
        """
        return True

    @command(
        dtype_in="DevString",
        dtype_out="DevVarLongStringArray",
        doc_in="the Dish ID - VCC ID mapping and frequency offset (k) in a json string",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    def InitSysParam(
        self: CbfController, argin: str
    ) -> DevVarLongStringArrayType:
        """
        This command sets the Dish ID - VCC ID mapping and k values

        :param argin: the Dish ID - VCC ID mapping and frequency offset (k) in a json string.
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object(command_name="InitSysParam")
        result_code_message, command_id = command_handler(argin)
        return [result_code_message], [command_id]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return CbfController.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
