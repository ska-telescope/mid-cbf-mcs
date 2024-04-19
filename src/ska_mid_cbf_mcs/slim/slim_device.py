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

from typing import List, Optional

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tango_base.control_model import (
    HealthState,
    PowerState,
    SimulationMode,
)
from tango import DebugIt
from tango.server import attribute, command, device_property, run

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
        res = self.component_manager.get_configuration_string()
        return res

    @attribute(
        dtype=(str,),
        max_dim_x=MAX_NUM_LINKS,
        label="Link FQDNs",
        doc="the Tango device FQDN of the active links.",
    )
    def linkFQDNs(self: Slim) -> List[str]:
        """
        Returns the Tango device FQDN of the active links.

        :return: a list of FQDNs.
        """
        res = self.component_manager.get_link_fqdns()
        return res

    @attribute(
        dtype=(str,),
        max_dim_x=MAX_NUM_LINKS,
        label="Link Names",
        doc="Returns the names of the active links.",
    )
    def linkNames(self: Slim) -> List[str]:
        """
        Returns the names of the active links.

        :return: a list of link names.
        """
        res = self.component_manager.get_link_names()
        return res

    @attribute(
        dtype=(HealthState,),
        max_dim_x=MAX_NUM_LINKS,
        label="Mesh health summary",
        doc="Returns a list with the health state of each link. True if OK. False if the link is in a bad state.",
    )
    def healthSummary(self: Slim) -> List[HealthState]:
        """
        Returns a list with the health state of each link.

        :return: a list of health states.
        """
        res = self.component_manager.get_health_summary()
        return res

    @attribute(
        dtype=(float,),
        max_dim_x=MAX_NUM_LINKS,
        label="Bit error rate",
        doc="Returns the bit-error rate of each link in a list",
    )
    def bitErrorRate(self: Slim) -> List[float]:
        """
        Returns the bit-error rate of each link in a list.

        :return: the bit-error rate as a list of floats.
        """
        res = self.component_manager.get_bit_error_rate()
        return res

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
            self._device.simulationMode = True

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

    # ---------
    # Callbacks
    # ---------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.

    # ------------------
    # Attributes methods
    # ------------------

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


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Slim.main) ENABLED START #
    return run((Slim,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Slim.main


if __name__ == "__main__":
    main()
