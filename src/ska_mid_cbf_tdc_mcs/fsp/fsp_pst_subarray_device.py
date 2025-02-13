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
import os

from ska_control_model import SimulationMode

# PyTango imports
from tango.server import attribute, device_property, run

from ska_mid_cbf_tdc_mcs.fsp.fsp_mode_subarray_device import FspModeSubarray
from ska_mid_cbf_tdc_mcs.fsp.fsp_pst_subarray_component_manager import (
    FspPstSubarrayComponentManager,
)

file_path = os.path.dirname(os.path.abspath(__file__))

__all__ = ["FspPstSubarray", "main"]


class FspPstSubarray(FspModeSubarray):
    """
    FspPstSubarray TANGO device class for the FspPstSubarray prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    HpsFspPstControllerAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

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

        return self.component_manager._timing_beam_id

    # TODO: SimulationMode override to be removed once MCS PST Function Mode is fully implemented
    # Currently setting FSP PST Subarray to SimulationMode.TRUE to allow 8 VCC
    # 4 FSP configurations (CIP-2815 Part 1)
    @attribute(
        dtype=SimulationMode,
        memorized=True,
        hw_memorized=True,
        doc="Reports the simulation mode of the device. \nSome devices may implement "
        "both modes, while others will have simulators that set simulationMode "
        "to True while the real devices always set simulationMode to False.",
    )
    def simulationMode(self: FspPstSubarray) -> SimulationMode:
        """
        :return: the current simulation mode
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: FspPstSubarray, value: SimulationMode) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(
            "MCS FSP PST Subarray Current Only Allowed in SimulationMode.TRUE"
        )
        value = SimulationMode.TRUE
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    # --------------
    # Initialization
    # --------------

    def create_component_manager(
        self: FspPstSubarray,
    ) -> FspPstSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        return FspPstSubarrayComponentManager(
            hps_fsp_mode_controller_fqdn=self.HpsFspPstControllerAddress,
            lrc_timeout=int(self.LRCTimeout),
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
    return run((FspPstSubarray,), args=args, **kwargs)


if __name__ == "__main__":
    main()
