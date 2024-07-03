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
from __future__ import annotations

import os

import tango
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.device.obs_device import CbfObsDevice
from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager import (
    FspCorrSubarrayComponentManager,
)

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(CbfObsDevice):
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
        dtype=("uint16",),
        max_dim_x=197,
        doc="Assigned VCC IDs",
    )
    def vccIDs(self: FspCorrSubarray) -> list[int]:
        """
        Read the vccIDs attribute; FSP deals with VCC, not DISH (receptor) IDs.

        :return: the list of assigned VCC IDs
        :rtype: List[int]
        """
        return self.component_manager.vcc_ids

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
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
        )

    # -------------
    # Fast Commands
    # -------------

    # TODO - currently not used
    def is_getLinkAndAddress_allowed(self: FspCorrSubarray) -> bool:
        """
        Determine if getLinkAndAddress is allowed
        (allowed if destination addresses are received,
        meaning outputLinkMap also received (checked in subarray validate scan)).

        :return: if getLinkAndAddress is allowed
        :rtype: bool
        """
        if self._vis_destination_address["outputHost"] == []:
            return False
        return True

    @command(
        dtype_in="DevULong",
        doc_in="channel ID",
        dtype_out="DevString",
        doc_out="output link and destination addresses in JSON",
    )
    def getLinkAndAddress(self: FspCorrSubarray, argin: int) -> str:
        """
        Get output link and destination addresses in JSON based on a channel ID.

        :param argin: the channel id.

        :return: the output link and destination addresses in JSON.
        :rtype: str
        """
        if argin < 0 or argin > 14479:
            msg = "channelID should be between 0 to 14479"
            tango.Except.throw_exception(
                "Command failed",
                msg,
                "getLinkAndAddress",
                tango.ErrSeverity.ERR,
            )
            return

        result = {
            "outputLink": 0,
            "outputHost": "",
            "outputPort": 0,
        }
        # Get output link by finding the first element[1] that's greater than argin
        link = 0
        for element in self._output_link_map:
            if argin >= element[0]:
                link = element[1]
            else:
                break
        result["outputLink"] = link
        # Get 3 addresses by finding the first element[1] that's greater than argin
        host = ""
        for element in self._vis_destination_address["outputHost"]:
            if argin >= element[0]:
                host = element[1]
            else:
                break
        result["outputHost"] = host

        # Port is different. the array is given as [[start_channel, start_value, increment],[start_channel, start_value, increment],.....]
        # value = start_value + (channel - start_channel)*increment
        triple = []  # find the triple with correct start_value
        for element in self._vis_destination_address["outputPort"]:
            if argin >= element[0]:
                triple = element
            else:
                break

        result["outputPort"] = triple[1] + (argin - triple[0]) * triple[2]

        return str(result)

    # ---------------------
    # Long Running Commands
    # ---------------------

    # ----------
    # Callbacks
    # ----------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return run((FspCorrSubarray,), args=args, **kwargs)


if __name__ == "__main__":
    main()
