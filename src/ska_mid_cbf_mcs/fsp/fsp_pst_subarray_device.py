# -*- coding: utf-8 -*-
#
# This file is part of the FspPstSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Mid.CBF MCS

"""
from __future__ import annotations  # allow forward references in type hints

# Additional import
# PROTECTED REGION ID(FspPstSubarray.additionnal_import) ENABLED START #
import os

# PyTango imports
from tango.server import attribute, device_property, run

from ska_mid_cbf_mcs.fsp.fsp_mode_subarray_device import FspModeSubarray
from ska_mid_cbf_mcs.fsp.fsp_pst_subarray_component_manager import (
    FspPstSubarrayComponentManager,
)

file_path = os.path.dirname(os.path.abspath(__file__))


# PROTECTED REGION END #  //  FspPstSubarray.additionnal_import

__all__ = ["FspPstSubarray", "main"]


class FspPstSubarray(FspModeSubarray):
    """
    FspPstSubarray TANGO device class for the FspPstSubarray prototype
    """

    # PROTECTED REGION ID(FspPstSubarray.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPstSubarray.class_variable

    # -----------------
    # Device Properties
    # -----------------

    SubID = device_property(dtype="uint16")

    FspID = device_property(dtype="uint16")

    CbfControllerAddress = device_property(
        dtype="str", default_value="mid_csp_cbf/controller/main"
    )

    CbfSubarrayAddress = device_property(dtype="str")

    VCC = device_property(dtype=("str",))

    # To Add in Chart
    HpsFspPstControllerAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="bool",
        label="Enable Output",
        doc="Enable/disable transmission of output products.",
    )
    def outputEnable(self: FspPstSubarray) -> bool:
        """
        Read the outputEnable attribute. Used to enable/disable
        transmission of the output products.

        :return: the outputEnable attribute.
        :rtype: bool
        """

        return self.component_manager.output_enable

    @attribute(
        dtype=("str",),
        max_dim_x=16,
        label="TimingBeams",
        doc="List of timing beams assigned to FSP PST Subarray.",
    )
    def timingBeams(self: FspPstSubarray) -> list[str]:
        """
        Read the timingBeams attribute.  List of timing beams assigned to
        the FSP PST Subarray

        :return: list of timing beams assigned to the FSP PST Subarray
        :rtype: List[int]
        """

        return self.component_manager.timing_beams

    @attribute(
        dtype=("uint16",),
        max_dim_x=16,
        label="TimingBeamID",
        doc="Identifiers of timing beams assigned to FSP PST Subarray",
    )
    def timingBeamID(self: FspPstSubarray) -> list[int]:
        """
        Read the list of Timing Beam IDs assigned to the FSP PST Subarray.

        :return: the timingBeamID attribute. List of ints
        :rtype: List[int]
        """

        return self.component_manager.timing_beam_id

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: FspPstSubarray) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

    # --------------
    # Initialization
    # --------------

    # Not used right now.  PST does not implement additional commands.
    # Reference FspCorrSubarray for future implementations
    class InitCommand(FspModeSubarray.InitCommand):
        """
        A class for the FspPstSubarray's init_device() "command".
        """

    def create_component_manager(
        self: FspPstSubarray,
    ) -> FspPstSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        return FspPstSubarrayComponentManager(
            hps_fsp_pst_controller_fqdn=self.HpsFspPstControllerAddress,
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._admin_mode_perform_action,
        )


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPstSubarray.main) ENABLED START #
    return run((FspPstSubarray,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPstSubarray.main


if __name__ == "__main__":
    main()
