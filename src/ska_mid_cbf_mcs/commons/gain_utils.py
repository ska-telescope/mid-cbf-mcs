# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for modifying gain"""

from __future__ import annotations  # allow forward references in type hints

from ska_mid_cbf_mcs.commons.global_enum import const
import numpy
import scipy
import yaml

class GAINUtils:
    """
    Utilities for modifying and correcting the vcc gain.
    """

    def __init__(self: DISHUtils, mapping) -> None:
        """
        Initialize a new instance.

        :param mapping: todo
        """

    @staticmethod
    def get_vcc_ripple_correction(self) -> dict:
        """
        Applies VCC Gain ripple correction to a dictionary of gains

        :return: dictionary of new gain values
        """

        vcc_gain_corrections = []
        # The below source code was based off talon_FSP.py:vcc_gain_corrections 
        # from ska-mid-cbf-signal-verification
        with open("OS_Prototype_FIR_CH20.yml", "r") as f:
            vcc_fir_prototype = yaml.safe_load(f)

        fir_proto = vcc_fir_prototype["h"]

        # TODO how to get vcc frequency slice?
        VCC_frequency_slice = None

        if VCC_frequency_slice is None:
            return {chan: 1.0 for chan in range(16384)}

        frequency_slice_sample_rate = (
            const.INPUT_SAMPLE_RATE // const.INPUT_FRAME_SIZE
        )

        # The Normalized Center Frequencies of the Secondry Channelizer
        fc0 = numpy.linspace(-1, 1 - 2 / const.FINE_CHANNELS, num=const.FINE_CHANNELS)

        # Assuming Frequency Shifting is Applied in the ReSampler
        SCFO_Fsft = (VCC_frequency_slice + 1) * (
            frequency_slice_sample_rate - const.COMMON_SAMPLE_RATE
        )

        # The Actual Center Frequencies of the Secondry Channelizer
        actual_center_frequency = fc0 * const.COMMON_SAMPLE_RATE / 2 - SCFO_Fsft
        # Converting again to Normalized Frequencies
        normalized_frequency = actual_center_frequency / frequency_slice_sample_rate / const.INPUT_FRAME_SIZE

        # Evaluating the Gain of the Frequency response of the VCC Channelizer
        _, H = scipy.signal.freqz(fir_proto, a=1, worN=2 * numpy.pi * normalized_frequency)

        # The Gain Correction Factors
        GC_Vec = numpy.clip(
            0.99 / abs(H), 0, 1
        )  # NOTE: The 0.99 factor avoids the saturation of gain correction factors

        # Initiating the Gain Correction Dictionary
        # chan = (np.arange(0,16383, dtype=int) + 8192) % 16384
        channels = numpy.arange(0, 16383, dtype=int)
        vcc_gain_corrections = dict(zip(channels, GC_Vec))

        log_msg = f"vcc_gain_corrections: {vcc_gain_corrections}"
        self._logger.info(log_msg)

        return vcc_gain_corrections