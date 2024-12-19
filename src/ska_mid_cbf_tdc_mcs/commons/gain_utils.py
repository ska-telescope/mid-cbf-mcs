# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for modifying gain"""

from __future__ import annotations  # allow forward references in type hints

import logging

import numpy
import scipy
import yaml

from ska_mid_cbf_tdc_mcs.commons.global_enum import const, freq_band_dict

VCC_PARAM_PATH = "mnt/vcc_param/"


class GAINUtils:
    """
    Utilities for modifying and correcting the vcc gain.
    """

    def __init__(self: GAINUtils) -> None:
        """
        Initialize a new instance.

        :param mapping: todo
        """

    @staticmethod
    def get_vcc_ripple_correction(
        freq_band: str,
        logger: logging.Logger,
        vcc_frequency_slice=None,
    ) -> dict:
        """
        Applies VCC Gain ripple correction to a dictionary of gains

        :return: dictionary of new gain values
        """

        vcc_gain_corrections = []
        # The below source code was based off talon_FSP.py:vcc_gain_corrections
        # from ska-mid-cbf-signal-verification
        with open(f"{VCC_PARAM_PATH}OS_Prototype_FIR_CH20.yml", "r") as file:
            vcc_fir_prototype = yaml.safe_load(file)

        fir_proto = vcc_fir_prototype["h"]

        # TODO how to get vcc frequency slice? 0 is default
        # Stored in test_config.yaml
        # fs_transport_cfg:
        # switch_map:
        # 0 : 5
        # vcc_frequency_slice = 0

        if vcc_frequency_slice is None:
            return {chan: 1.0 for chan in range(16384)}
        logger.info(f"Here is the frequency band build attribute: {freq_band}")
        _freq_band_dict = freq_band_dict()
        logger.info(
            f"Here is the frequency band gain attribute: {_freq_band_dict[freq_band]}"
        )
        input_sample_rate = (
            _freq_band_dict[freq_band]["base_dish_sample_rate_MHz"] * 1000000
        )
        # TODO: Check some of the frame sizes says FIXME on them
        input_frame_size = _freq_band_dict[freq_band]["num_samples_per_frame"]

        frequency_slice_sample_rate = input_sample_rate // input_frame_size

        # The Normalized Center Frequencies of the Secondry Channelizer
        fc0 = numpy.linspace(
            -1, 1 - 2 / const.FINE_CHANNELS, num=const.FINE_CHANNELS
        )

        # Assuming Frequency Shifting is Applied in the ReSampler
        scf0_fsft = vcc_frequency_slice * (
            frequency_slice_sample_rate - const.COMMON_SAMPLE_RATE
        )
        # The Actual Center Frequencies of the Secondry Channelizer
        actual_center_frequency = (
            fc0 * const.COMMON_SAMPLE_RATE / 2 - scf0_fsft
        )

        # Converting again to Normalized Frequencies
        normalized_frequency = (
            actual_center_frequency
            / frequency_slice_sample_rate
            / input_frame_size
        )
        # Evaluating the Gain of the Frequency response of the VCC Channelizer
        _, H = scipy.signal.freqz(
            fir_proto, a=1, worN=2 * numpy.pi * normalized_frequency
        )
        # The Gain Correction Factors
        # TODO: This is different than Will's version he sent in Slack
        vcc_gain_corrections = numpy.clip(1.0 / abs(H), 0, 4.005)
        # vcc_gain_corrections = numpy.clip(
        #     0.99 / abs(H), 0, 1
        # )  # NOTE: The 0.99 factor avoids the saturation of gain correction factors
        # Initiating the Gain Correction Dictionary
        # chan = (np.arange(0,16383, dtype=int) + 8192) % 16384

        return vcc_gain_corrections
