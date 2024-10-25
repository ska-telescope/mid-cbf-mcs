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

# """ FspModeSubarray Tango device prototype

# FspModeSubarray TANGO device class for the FspModeSubarray prototype
# Parrent class for the various FSP Modes to inherit
# """
from __future__ import annotations

import os

from tango.server import attribute

from ska_mid_cbf_mcs.device.obs_device import CbfObsDevice

file_path = os.path.dirname(os.path.abspath(__file__))

__all__ = ["FspModeSubarray", "main"]


class FspModeSubarray(CbfObsDevice):
    """
    FspModeSubarray TANGO device class for the FspModeSubarray prototype
    Abstract class for the various FSP Modes to inherit
    """

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=("uint16",),
        max_dim_x=197,
        doc="Assigned VCC IDs",
    )
    def vccIDs(self: FspModeSubarray) -> list[int]:
        """
        Read the vccIDs attribute; FSP deals with VCC, not DISH (receptor) IDs.

        :return: the list of assigned VCC IDs
        :rtype: list[int]
        """
        return self.component_manager.vcc_ids

    # -------------
    # Fast Commands
    # -------------

    # ---------------------
    # Long Running Commands
    # ---------------------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    raise TypeError(
        "FspModeSubarray is an Abstract Class; This server cannot be ran."
    )


if __name__ == "__main__":
    main()
