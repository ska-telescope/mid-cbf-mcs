# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.
#
# Copyright (c) 2019 National Research Council of Canada
#
# """
# VccControllerSimulator Class
#
# This class is used to simulate the behaviour of the HPS VCC controller
# device when the Talon-DX hardware is not connected.
# """

from __future__ import annotations  # allow forward references in type hints

import tango
from tango import DevState

from ska_mid_cbf_mcs.vcc.vcc_band_simulator import VccBandSimulator

__all__ = ["VccControllerSimulator"]


class VccControllerSimulator:
    """
    VccControllerSimulator class used to simulate the behaviour of the HPS VCC
    controller device when the Talon-DX hardware is not connected.

    :param device_name: Identifier for the device instance
    :param vcc_band_1_and_2: VCC band simulator instance for the band 1 and 2 device
    :param vcc_band_3: VCC band simulator instance for the band 3 device
    :param vcc_band_4: VCC band simulator instance for the band 4 device
    :param vcc_band_5: VCC band simulator instance for the band 5 device
    """

    def __init__(
        self: VccControllerSimulator,
        device_name: str,
        vcc_band_1_and_2: VccBandSimulator,
        vcc_band_3: VccBandSimulator,
        vcc_band_4: VccBandSimulator,
        vcc_band_5: VccBandSimulator,
    ) -> None:
        self.device_name = device_name

        self._band_devices = [
            vcc_band_1_and_2,
            vcc_band_3,
            vcc_band_4,
            vcc_band_5,
        ]

        self._state = DevState.INIT

        self._frequency_band = 0

    # Properties that match the Tango attributes in the band devices

    @property
    def frequencyBand(self) -> int:
        """Return the frequency band attribute."""
        return self._frequency_band

    # Methods that match the Tango commands in the band devices
    def State(self: VccControllerSimulator) -> tango.DevState:
        """Get the current state of the device"""
        return self._state

    def ConfigureBand(
        self: VccControllerSimulator, frequency_band: int
    ) -> None:
        """
        Configure the band of this VCC.

        :param frequency_band: Frequency band
        """
        self._frequency_band = frequency_band

        freq_band_index_mapping = [0, 0, 1, 2, 3, 3]
        freq_band_index = freq_band_index_mapping[frequency_band]

        # Enable / disable the band devices
        for idx, band_device in enumerate(self._band_devices):
            if idx == freq_band_index:
                band_device.On()
            else:
                band_device.Disable()

    def Unconfigure(self: VccControllerSimulator) -> None:
        """Reset the configuration."""
        self._frequency_band = 0
        for band_device in self._band_devices:
            band_device.Unconfigure()
