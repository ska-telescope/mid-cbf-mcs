# -*- coding: utf-8 -*-
#
# This file is part of the FspCorrSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

# """

# """ FspCorrSubarray Tango device prototype

# FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
# """

""" Mid.CBF MCS

"""
from __future__ import annotations

import os

import tango
from tango.server import attribute, device_property, run

from ska_mid_cbf_tdc_mcs.device.base_device import CbfFastCommand
from ska_mid_cbf_tdc_mcs.device.obs_device import CbfObsDevice
from ska_mid_cbf_tdc_mcs.fsp.fsp_corr_subarray_component_manager import (
    FspCorrSubarrayComponentManager,
)
from ska_mid_cbf_mcs.fsp.fsp_mode_subarray_device import FspModeSubarray

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(FspModeSubarray):
    """
    FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    HpsFspCorrControllerAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=tango.DevEnum,
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
        doc="Frequency band; an int in the range [0, 5]",
    )
    def frequencyBand(self: FspCorrSubarray) -> tango.DevEnum:
        """
        Read the frequencyBand attribute.

        :return: the frequency band
        :rtype: tango.DevEnum
        """
        return self.component_manager.frequency_band

    @attribute(
        dtype="int",
        doc="Frequency slice ID",
    )
    def frequencySliceID(self: FspCorrSubarray) -> int:
        """
        Read the frequencySliceID attribute.

        :return: the frequencySliceID attribute.
        :rtype: int
        """
        return self.component_manager.frequency_slice_id

    # --------------
    # Initialization
    # --------------

    def create_component_manager(
        self: FspCorrSubarray,
    ) -> FspCorrSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        return FspCorrSubarrayComponentManager(
            hps_fsp_corr_controller_fqdn=self.HpsFspCorrControllerAddress,
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


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return run((FspCorrSubarray,), args=args, **kwargs)


if __name__ == "__main__":
    main()
