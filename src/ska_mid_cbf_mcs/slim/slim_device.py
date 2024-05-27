# -*- coding: utf-8 -*-
#
#
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
TANGO device class for controlling and monitoring the
Serial Lightweight Interconnect Mesh (SLIM)
"""

from __future__ import annotations

from typing import Optional

import tango

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import (
    FastCommand,
    ResultCode,
    SubmittedSlowCommand,
)
from ska_tango_base.control_model import (
    HealthState,
    PowerState,
    SimulationMode,
)
from ska_tango_base.faults import StateModelError
from tango import DebugIt
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.device.base_device import CbfDevice
from ska_mid_cbf_mcs.slim.slim_component_manager import SlimComponentManager

__all__ = ["Slim", "main"]


class Slim(CbfDevice):
    """
    TANGO device class for controlling and monitoring the SLIM
    """

    # PROTECTED REGION ID(Slim.class_variable) ENABLED START #
    MAX_NUM_LINKS = 16  # AA 0.5

    # PROTECTED REGION END #    //  Slim.class_variable

    # -----------------
    # Device Properties
    # -----------------
    Links = device_property(dtype=("str",))

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=str,
        label="Mesh configuration",
        doc="Mesh configuration in a YAML string. This is the string provided in Configure. Returns empty string if not already configured",
    )
    def meshConfiguration(self: Slim) -> str:
        """
        Returns the Mesh configuration in a YAML string. This is the string provided in Configure. Returns empty string if not already configured.

        :return: the Mesh configuration in a YAML string.
        """
        return self.component_manager.get_configuration_string()

    @attribute(
        dtype=(str,),
        max_dim_x=MAX_NUM_LINKS,
        label="Link FQDNs",
        doc="the Tango device FQDN of the active links.",
    )
    def linkFQDNs(self: Slim) -> list[str]:
        """
        Returns the Tango device FQDN of the active links.

        :return: a list of FQDNs.
        """
        return self.component_manager.get_link_fqdns()

    @attribute(
        dtype=(str,),
        max_dim_x=MAX_NUM_LINKS,
        label="Link Names",
        doc="Returns the names of the active links.",
    )
    def linkNames(self: Slim) -> list[str]:
        """
        Returns the names of the active links.

        :return: a list of link names.
        """
        return self.component_manager.get_link_names()

    @attribute(
        dtype=(HealthState,),
        max_dim_x=MAX_NUM_LINKS,
        label="Mesh health summary",
        doc="Returns a list with the health state of each link. True if OK. False if the link is in a bad state.",
    )
    def healthSummary(self: Slim) -> list[HealthState]:
        """
        Returns a list with the health state of each link.

        :return: a list of health states.
        """
        return self.component_manager.get_health_summary()

    @attribute(
        dtype=(float,),
        max_dim_x=MAX_NUM_LINKS,
        label="Bit error rate",
        doc="Returns the bit-error rate of each link in a list",
    )
    def bitErrorRate(self: Slim) -> list[float]:
        """
        Returns the bit-error rate of each link in a list.

        :return: the bit-error rate as a list of floats.
        """
        return self.component_manager.get_bit_error_rate()

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: Slim) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: Slim, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: Slim) -> None:
        # PROTECTED REGION ID(Slim.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Slim.always_executed_hook

    def delete_device(self: Slim) -> None:
        # PROTECTED REGION ID(Slim.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  Slim.delete_device

    def init_command_objects(self: Slim) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()

        self.register_command_object(
            "Configure",
            SubmittedSlowCommand(
                command_name="Configure",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="configure",
                logger=self.logger,
            ),
        )

        self.register_command_object(
            "Off",
            SubmittedSlowCommand(
                command_name="Off",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="off",
                logger=self.logger,
            ),
        )

        self.register_command_object(
            "SlimTest",
            self.SlimTestCommand(
                component_manager=self.component_manager,
                logger=self.logger,
            ),
        )

    # --------
    # Commands
    # --------

    def create_component_manager(self: Slim) -> SlimComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        :rtype: SlimComponentManager
        """
        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerState] = None

        # Simulation mode default true
        return SlimComponentManager(
            link_fqdns=self.Links,
            logger=self.logger,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the init_device() "command".
        """

        def do(self: Slim.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, message) = super().do()
            self._device.simulationMode = SimulationMode.TRUE

            return (result_code, message)

    class SlimTestCommand(FastCommand):
        """
        A command to test the mesh of SLIM Links.
        """

        def __init__(
            self: Slim.SlimTestCommand,
            *args: any,
            component_manager: SlimComponentManager,
            **kwargs: any,
        ) -> None:
            self.component_manager = component_manager
            super().__init__(*args, **kwargs)

        def do(self: Slim.SlimTestCommand) -> tuple[ResultCode, str]:
            """
            SLIM Test Command. Checks the BER and health status of the mesh's configured links.

            :return: A tuple containing a return code and a string
                message contaiing a report on the health of the Mesh or error message
                if exception is caught.
            :rtype: (ResultCode, str)
            """

            result_code, message = self.component_manager.slim_test()
            return (result_code, message)

    @command(
        dtype_in="DevString",
        doc_in="mesh configuration as a string in YAML format",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def Configure(self: Slim, argin: str) -> None:
        command_handler = self.get_command_object("Configure")
        result_code_message, command_id = command_handler(argin)
        return [[result_code_message], [command_id]]

    def is_Off_allowed(self: Slim) -> bool:
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple of a string containing a return code and message indicating the status of the command, as well as the SubmittedSlowCommand's command ID.",
    )
    @DebugIt()
    def Off(self: Slim) -> None:
        command_handler = self.get_command_object("Off")
        result_code_message, command_id = command_handler()
        return [[result_code_message], [command_id]]

    def is_SlimTest_allowed(self: Slim) -> bool:
        """
        Determined if SlimTest command is allowed

        :raises: CommandError: if DevState is not on
        :raises: StateModelError: if the Mesh has not been configured
        :return: if SlimTest is allowed
        :rtype: bool
        """
        if self.get_state() == tango.DevState.ON:
            if self.component_manager.mesh_configured:
                return True
            else:
                raise StateModelError(
                    "SLIM must be configured before SlimTest can be called"
                )
        return False

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    def SlimTest(self: Slim) -> None:
        handler = self.get_command_object("SlimTest")
        return_code, message = handler()
        return [[return_code], [message]]

    # ---------
    # Callbacks
    # ---------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return Slim.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
