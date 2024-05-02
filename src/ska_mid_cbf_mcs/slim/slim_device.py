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

import time
from typing import List, Optional, Tuple

# tango imports
import tango
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResponseCommand, ResultCode
from ska_tango_base.control_model import HealthState, PowerMode, SimulationMode
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.slim.slim_component_manager import SlimComponentManager

__all__ = ["Slim", "main"]


class Slim(SKABaseDevice):
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

        device_args = (self, self.logger)

        self.register_command_object(
            "Configure", self.ConfigureCommand(*device_args)
        )

        self.register_command_object(
            "SlimMeshTest",
            self.SlimMeshTestCommand(*device_args),
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
        self._component_power_mode: Optional[PowerMode] = None

        # Simulation mode default true
        return SlimComponentManager(
            link_fqdns=self.Links,
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
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

            device = self.target
            device.write_simulationMode(True)

            return (result_code, message)

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.
        """

        def do(self: Slim.OnCommand) -> Tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            return component_manager.on()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.
        """

        def do(self: Slim.OffCommand) -> Tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            component_manager = self.target
            return component_manager.off()

    class ConfigureCommand(ResponseCommand):
        """
        The command class for the Configure command.
        """

        def is_allowed(self: Slim.ConfigureCommand) -> bool:
            """
            Determine if Configure is allowed
            (allowed when Devstate is ON).

            :return: if Configure is allowed
            :rtype: bool
            """
            if self.target.get_state() == tango.DevState.ON:
                return True
            return False

        def do(
            self: Slim.ConfigureCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Configure command. Configures the SLIM as provided in the input string.

            :param argin: mesh configuration as a string in YAML format.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                component_manager = self.target.component_manager
                (result_code, message) = component_manager.configure(argin)
                if result_code == ResultCode.OK:
                    self.logger.info("Mesh Configure completed successfully")
                elif result_code == ResultCode.FAILED:
                    self.logger.error(message)
                return (result_code, message)
            else:
                return (
                    ResultCode.FAILED,
                    "Device is off. Failed to issue Configure command.",
                )

    class SlimMeshTestCommand(ResponseCommand):
        """
        A command to test the mesh of SLIM Tx Rx Links
        """

        def do(self: Slim.SlimMeshTestCommand) -> Tuple[ResultCode, str]:
            """
            SLIM Mesh Test Command.  Checks the BER and Health Status of the mesh with the already configured links.

            :return: A tuple containing a return code and a string
                message contaiing a report on the health of the Mesh or error message
                if exception is caught.
            :rtype: (ResultCode, str)
            """

            if self.target.get_state() == tango.DevState.ON:
                component_manager = self.target.component_manager
                t_sleep = 2
                # TODO Change test_length to something longer when BaseClass Updates are completed
                # Currently there is no way to prevent the 3sec default timeout for commands
                test_length = 2
                self.logger.info(f"Sleeping for {test_length}s")
                for slept_time in range(0, test_length, t_sleep):
                    time.sleep(t_sleep)
                    self.logger.info(
                        f"Sleep Time Remaining: {test_length - slept_time}"
                    )

                # Prints the connection status and Bit Error Rate of the devices on the mesh
                (
                    result_code,
                    message,
                ) = component_manager.slim_mesh_links_ber_check_summary()
                if result_code != ResultCode.OK:
                    return (result_code, message)

                # Logs Health Summary of Mesh Links
                (result_code, message) = component_manager.slim_table()
                if result_code != ResultCode.OK:
                    return (result_code, message)
                return (ResultCode.OK, "SLIM Mesh Test Completed")

            else:
                self.logger.info(
                    "Device is off. Failed to issue Configure command."
                )
                return (
                    ResultCode.FAILED,
                    "Device is off. Failed to issue Configure command.",
                )

    @command(
        dtype_in="DevString",
        doc_in="mesh configuration as a string in YAML format",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def Configure(self: Slim, argin: str) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(Slim.Configure) ENABLED START #
        handler = self.get_command_object("Configure")
        return_code, message = handler(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  Slim.Configure

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    def SlimMeshTest(self: Slim) -> None:
        if self.component_manager.is_communicating is not True:
            return [
                [ResultCode.FAILED],
                ["The Mesh is currently not communicating and/or configured"],
            ]
        handler = self.get_command_object("SlimMeshTest")
        return_code, message = handler()
        return [[return_code], [message]]

    # ---------
    # Callbacks
    # ---------

    def _communication_status_changed(
        self: Slim, communication_status: CommunicationStatus
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
        self: Slim, power_mode: PowerMode
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

    def _component_fault(self: Slim, faulty: bool) -> None:
        """
        Handle component fault

        :param faulty: True if component is faulty.
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")

    # ------------------
    # Attributes methods
    # ------------------

    def write_simulationMode(self: Slim, value: SimulationMode) -> None:
        """
        Overrides the base class implementation. Additionally set the
        simulation mode of link devices to the same value.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        super().write_simulationMode(value)
        self.component_manager._simulation_mode = value

    def read_simulationMode(self: Slim) -> SimulationMode:
        """
        Reads simulation mode. Overrides the base class implementation.
        """
        return self.component_manager._simulation_mode


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Slim.main) ENABLED START #
    return run((Slim,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Slim.main


if __name__ == "__main__":
    main()
