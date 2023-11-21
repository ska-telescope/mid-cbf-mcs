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

from typing import List, Optional, Tuple

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResponseCommand, ResultCode
from ska_tango_base.control_model import PowerMode
from tango.server import attribute, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.slim.mesh_manager import MeshManager
from ska_mid_cbf_mcs.slim.slim_common import SLIMConst

__all__ = ["SLIMMesh", "main"]


class SLIMMesh(SKABaseDevice):
    """
    TANGO device class for controlling and monitoring the SLIM mesh
    """

    # PROTECTED REGION ID(SLIMMesh.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  SLIMMesh.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=str,
        label="Mesh configuration",
        doc="Mesh configuration in a YAML string. This is the string provided in Configure. Returns empty string if not already configured",
    )
    def MeshConfiguration(self: SLIMMesh) -> str:
        """
        Read the FPGA bitstream version of the Talon-DX board.

        :return: the FPGA bitstream version
        """
        res = self.component_manager.get_configuration_string()
        return res

    @attribute(
        dtype=(bool,),
        max_dim_x=SLIMConst.MAX_NUM_LINKS,
        label="Mesh status summary",
        doc="Returns a list of status of each link. True if OK. False if the link is in a bad state.",
    )
    def MeshStatusSummary(self: SLIMMesh) -> List[bool]:
        """
        Returns a list of status of each link. True if OK. False if the link is in a bad state.

        :return: a list of link status
        """
        res = self.component_manager.get_status_summary()
        return res

    @attribute(
        dtype=(float,),
        max_dim_x=SLIMConst.MAX_NUM_LINKS,
        label="Bit error rate",
        doc="Returns the bit error rate of each link in a list",
    )
    def BitErrorRate(self: SLIMMesh) -> List[float]:
        """
        Returns the bit error rate of each link in a list

        :return: the bit error rate as a list of float
        """
        res = self.component_manager.get_bit_error_rate()
        return res

    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: SLIMMesh) -> None:
        # PROTECTED REGION ID(SLIMMesh.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SLIMMesh.always_executed_hook

    def delete_device(self: SLIMMesh) -> None:
        # PROTECTED REGION ID(SLIMMesh.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SLIMMesh.delete_device

    def init_command_objects(self: SLIMMesh) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object(
            "Configure", self.ConfigureCommand(*device_args)
        )

    # --------
    # Commands
    # --------

    def create_component_manager(self: SLIMMesh) -> MeshManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return MeshManager(
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

        def do(self: SLIMMesh.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            return super().do()

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.
        """

        def do(self: SLIMMesh.OnCommand) -> Tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.on()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.
        """

        def do(self: SLIMMesh.OffCommand) -> Tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.off()

    class ConfigureCommand(ResponseCommand):
        """
        The command class for the Configure command.
        """

        def do(
            self: SLIMMesh.ConfigureCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Configure command. Configures the SLIM mesh as provided in the input string.

            :param argin: mesh configuration as a string in YAML format
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            self.logger.info("Entering SLIMMesh.ConfigureCommand")
            (result_code, message) = self.target.component_manager.configure(
                argin
            )
            if result_code == ResultCode.OK:
                self.logger.info("Mesh Configure completed successfully")
            elif result_code == ResultCode.FAILED:
                self.logger.error(message)

            return (result_code, message)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(SLIMMesh.main) ENABLED START #
    return run((SLIMMesh,), args=args, **kwargs)
    # PROTECTED REGION END #    //  SLIMMesh.main


if __name__ == "__main__":
    main()
