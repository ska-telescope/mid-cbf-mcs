# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import tango
from ska_control_model import SimulationMode
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tango_base.utils import convert_dict_to_list
from tango.server import attribute, command, device_property

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
    Implements state and mode indicators, and a set of state transition commands.
    """

    # -----------------
    # Device Properties
    # -----------------

    # --- Subdevice FQDNs --- #

    CbfSubarray = device_property(dtype=("str",))

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    TalonLRU = device_property(dtype=("str",))

    TalonBoard = device_property(dtype=("str",))

    PowerSwitch = device_property(dtype=("str",))

    FsSLIM = device_property(dtype=("str"))

    VisSLIM = device_property(dtype=("str"))

    # --- Configuration file paths --- #

    TalonDxConfigPath = device_property(dtype=("str"))

    HWConfigPath = device_property(dtype=("str"))

    FsSLIMConfigPath = device_property(dtype=("str"))

    VisSLIMConfigPath = device_property(dtype=("str"))

    # --- General properties --- #

    LRCTimeout = device_property(dtype=("str"))

    MaxCapabilities = device_property(dtype=("str",))

    # ----------
    # Attributes
    # ----------

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
        return self.component_manager.last_init_sys_param

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
        return self.component_manager.source_init_sys_param

    @attribute(
        dtype=(str,),
        label="Dish ID to VCC mapping",
        doc="Dish ID to VCC mapping. The string is in the format 'dishID:vccID'.",
    )
    def dishToVcc(self: CbfController) -> list[str]:
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
        dtype=(str,),
        label="VCC to Dish mapping",
        doc="VCC to Dish mapping. The string is in the format 'vccID:dishID'.",
    )
    def vccToDish(self: CbfController) -> list[str]:
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
        dtype=(str,),
        max_dim_x=20,
        doc=(
            "Maximum number of instances of each capability type,"
            " e.g. 'VCC:4', 'FSP:4', 'Subarray:1'."
        ),
    )
    def maxCapabilities(self: CbfController) -> list[str]:
        """
        Read maximum number of instances of each capability type, as defined in charts.
        By default, these include VCC, FSP, and Subarray.

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
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: CbfController, value: SimulationMode) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self._talondx_component_manager.simulation_mode = value
        self.component_manager.simulation_mode = value

    @attribute(
        dtype="DevBoolean",
        label="Restrictive Validation of Supported Configurations",
        doc="Flag to indicate if a restrictive validation is requested for "
        "supported configurations, such as with Scan Configurations. "
        "Defaults to True.  Setting the flag to False can cause unexpected "
        "behaviour with the system.",
    )
    def validateSupportedConfiguration(self: CbfController) -> bool:
        """
        Reads and return the value in the validateSupportedConfiguration

        :return: the value in validateSupportedConfiguration
        :rtype: bool
        """
        return self.component_manager.validate_supported_configuration

    @validateSupportedConfiguration.write
    def validateSupportedConfiguration(
        self: CbfController, value: bool
    ) -> None:
        """
        Setting this flag to false allows the user to bypass validation that
        ensures the inputs are currently supported by the system.

        The option to bypass validation is intended for testing purposes only.
        Using unsupported configurations may result in unexpected system behaviour."

        A warning level log is created when the flag is set to False.

        :param value: Set the flag to True/False
        """
        if value is False:
            msg = (
                "Setting validateSupportedConfiguration to False. "
                "Using unsupported configurations may result in "
                "unexpected system behaviour."
            )
            self.logger.warning(msg)

        self.component_manager.validate_supported_configuration = value

    # --------------
    # Initialization
    # --------------

    def init_command_objects(self: CbfController) -> None:
        """
        Sets up the command objects
        """
        # Registers Off and On commands
        super().init_command_objects()

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

    def _get_max_capabilities(self: CbfController) -> dict[str, int]:
        """
        Get maximum number of capabilities for VCC, FSP and Subarray. If property not found in db, then assign a default amount.

        :return: dictionary of maximum number of capabilities with capability type as key and max capability instances as value
        """
        capabilities = ["VCC", "FSP", "Subarray"]
        max_capabilities = {}

        if self.MaxCapabilities:
            for max_capability in self.MaxCapabilities:
                (
                    capability_type,
                    max_capability_instances,
                ) = max_capability.split(":")
                max_capabilities[capability_type] = int(
                    max_capability_instances
                )

            for capability in capabilities:
                if capability not in max_capabilities:
                    raise tango.DevFailed(
                        f"{capability} capabilities not defined; MaxCapabilities device property must be updated in charts"
                    )
        else:
            raise tango.DevFailed(
                "MaxCapabilities device property not defined"
            )

        return max_capabilities

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
            lrc_timeout=int(self.LRCTimeout),
            logger=self.logger,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )

        fqdn_dict = {
            "VCC": self.VCC,
            "FSP": self.FSP,
            "CbfSubarray": self.CbfSubarray,
            "TalonLRU": self.TalonLRU,
            "TalonBoard": self.TalonBoard,
            "PowerSwitch": self.PowerSwitch,
            "FsSLIM": [self.FsSLIM],
            "VisSLIM": [self.VisSLIM],
        }

        config_path_dict = {
            "TalonDxConfigPath": self.TalonDxConfigPath,
            "HWConfigPath": self.HWConfigPath,
            "FsSLIMConfigPath": self.FsSLIMConfigPath,
            "VisSLIMConfigPath": self.VisSLIMConfigPath,
        }

        # Initialize the _max_capabilities variable for the component manager.
        self._max_capabilities = self._get_max_capabilities()

        return ControllerComponentManager(
            fqdn_dict=fqdn_dict,
            config_path_dict=config_path_dict,
            max_capabilities=self._max_capabilities,
            talondx_component_manager=self._talondx_component_manager,
            logger=self.logger,
            lrc_timeout=int(self.LRCTimeout),
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
        A class for the CbfController's Init() command.
        """

        def do(
            self: CbfController.InitCommand,
            *args: any,
            **kwargs: any,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string message indicating status.
                     The message is for information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, msg) = super().do(*args, **kwargs)

            self._device._command_progress = 0

            return (result_code, msg)

    # ---------------------
    # Long Running Commands
    # ---------------------

    def is_On_allowed(self: CbfController) -> bool:
        """
        Overwrite base class's is_On_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @tango.DebugIt()
    def On(
        self: CbfController,
    ) -> DevVarLongStringArrayType:
        """
        Turn the device on.

        :return: A tuple containing a return code and a string message indicating status.
                 The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object(command_name="On")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    def is_Off_allowed(self: CbfController) -> bool:
        """
        Overwrite baseclass's is_On_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @tango.DebugIt()
    def Off(
        self: CbfController,
    ) -> DevVarLongStringArrayType:
        """
        Turn the device off.

        :return: A tuple containing a return code and a string message indicating status.
                 The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command_handler = self.get_command_object(command_name="Off")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

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
        doc_out="tuple containing a return code and a string message indicating the status of the command.",
    )
    @tango.DebugIt()
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
        result_code, command_id = command_handler(argin)
        return [[result_code], [command_id]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return CbfController.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
