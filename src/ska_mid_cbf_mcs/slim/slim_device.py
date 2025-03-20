# -*- coding: utf-8 -*-
#
#
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.


from __future__ import annotations

from ska_control_model import HealthState, PowerState, SimulationMode
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from tango import DebugIt
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.device.base_device import CbfDevice, CbfFastCommand
from ska_mid_cbf_mcs.slim.slim_component_manager import SlimComponentManager

__all__ = ["Slim", "main"]


class Slim(CbfDevice):
    """
    TANGO device class for controlling and monitoring the
    Serial Lightweight Interconnect Mesh (SLIM)
    """

    MAX_NUM_LINKS = 16  # AA 0.5

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
        max_dim_x=const.MAX_NUM_FS_LINKS,
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
        max_dim_x=const.MAX_NUM_FS_LINKS,
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
        max_dim_x=const.MAX_NUM_FS_LINKS,
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
        max_dim_x=const.MAX_NUM_FS_LINKS,
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

    # --------------
    # Initialization
    # --------------

    def create_component_manager(self: Slim) -> SlimComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        :rtype: SlimComponentManager
        """
        self.logger.debug("Entering create_component_manager()")
        return SlimComponentManager(
            link_fqdns=self.Links,
            logger=self.logger,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )

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
            "SlimTest",
            self.SlimTestCommand(
                component_manager=self.component_manager,
                logger=self.logger,
            ),
        )

    # -------------
    # Fast Commands
    # -------------

    class SlimTestCommand(CbfFastCommand):
        """
        A command to test the mesh of SLIM Links.
        """

        def is_allowed(self: Slim.SlimTestCommand) -> bool:
            """
            Determine if SlimTest command is allowed.

            :return: True if command is allowed, otherwise False
            """
            if self.component_manager.power_state != PowerState.ON:
                self.logger.warning(
                    "SLIM must be turned on before SlimTest can be called"
                )
                return False
            if not self.component_manager.mesh_configured:
                self.logger.warning(
                    "SLIM must be configured before SlimTest can be called"
                )
                return False
            return True

        def do(self: Slim.SlimTestCommand) -> tuple[ResultCode, str]:
            """
            SLIM Test Command. Checks the BER and health status of the mesh's configured links.

            :return: A tuple containing a return code and a string
                message containing a report on the health of the Mesh or error message
                if exception is caught.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                return self.component_manager.slim_test()
            return (ResultCode.REJECTED, "SLIM Test not allowed")

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    def SlimTest(self: Slim) -> None:
        handler = self.get_command_object("SlimTest")
        return_code, message = handler()
        return [[return_code], [message]]

    # ---------------------
    # Long Running Commands
    # ---------------------

    def is_On_allowed(
        self: Slim,
    ) -> bool:
        """
        Overwrite baseclass's is_On_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def On(
        self: Slim,
    ) -> DevVarLongStringArrayType:
        """
        Turn on SLIM.

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: DevVarLongStringArrayType
        """
        command_handler = self.get_command_object(command_name="On")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    def is_Off_allowed(
        self: Slim,
    ) -> bool:
        """
        Overwrite baseclass's is_Off_allowed method.
        """
        return True

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Off(
        self: Slim,
    ) -> DevVarLongStringArrayType:
        """
        Turn off SLIM.

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: DevVarLongStringArrayType
        """
        command_handler = self.get_command_object(command_name="Off")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    @command(
        dtype_in="DevString",
        doc_in="mesh configuration as a string in YAML format",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def Configure(self: Slim, argin: str) -> None:
        command_handler = self.get_command_object("Configure")
        result_code, command_id = command_handler(argin)
        return [[result_code], [command_id]]

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
