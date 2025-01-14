# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for modifying gain"""

from __future__ import annotations  # allow forward references in type hints

import logging

import numpy as np
import scipy
import yaml

from ska_mid_cbf_tdc_mcs.commons.global_enum import const, freq_band_dict

VCC_IR_PATH = "mnt/vcc_param/OS_Prototype_FIR_CH20.yml"

DEFAULT_GAIN = 1.0
MIN_GAIN = 0.0
MAX_GAIN = 4.005


def get_vcc_ripple_correction(
    freq_band: str,
    logger: logging.Logger,
    vcc_freq_slice: int = None,
) -> list:
    """
    Applies VCC Gain ripple correction to a list of gains.
    Based on https://gitlab.com/ska-telescope/ska-mid-cbf-signal-verification/-/blob/main/images/ska-mid-cbf-signal-verification/hardware_testing_notebooks/talon_pyro/talon_FSP.py

    :return: list of new gain values
    """
    if vcc_freq_slice is None:
        logger.warning(
            f"No frequency slice provided, setting all gains to default value {DEFAULT_GAIN}"
        )
        return [
            [DEFAULT_GAIN, DEFAULT_GAIN] for _ in range(const.FINE_CHANNELS)
        ]

    # Load VCC frequency band info
    try:
        freq_band_info = freq_band_dict()[freq_band]
    except KeyError as ke:
        logger.error(f"Invalid frequency band {freq_band}; {ke}")
    logger.debug(f"VCC frequency band info: {freq_band_info}")
    input_sample_rate = freq_band_info["base_dish_sample_rate_MHz"] * 1000000
    # TODO: Check some of the frame sizes says FIXME on them
    input_frame_size = freq_band_info["num_samples_per_frame"]
    frequency_slice_sample_rate = input_sample_rate // input_frame_size

    # Assuming frequency shifting is applied in the resampler, calculate shift
    scf0_fsft = vcc_freq_slice * (
        frequency_slice_sample_rate - const.COMMON_SAMPLE_RATE
    )
    # Calculate normalized actual center frequency of secondary channelizer
    fc0 = np.linspace(-1, 1 - 2 / const.FINE_CHANNELS, num=const.FINE_CHANNELS)
    actual_center_frequency = fc0 * const.COMMON_SAMPLE_RATE / 2 - scf0_fsft
    normalized_center_frequency = (
        actual_center_frequency
        / frequency_slice_sample_rate
        / input_frame_size
    )

    # Evaluate VCC frequency response data
    with open(f"{VCC_IR_PATH}", "r") as file:
        vcc_ir = yaml.safe_load(file)
    vcc_ir_coeff = vcc_ir["h"]
    _, fr_values = scipy.signal.freqz(
        vcc_ir_coeff, a=1, worN=2 * np.pi * normalized_center_frequency
    )

    # Calculate 16k fine-channelizer gain correction factors
    gain_factors = np.clip(
        DEFAULT_GAIN / abs(fr_values), a_min=MIN_GAIN, a_max=MAX_GAIN
    )
    # TODO: what is this alternate version for?
    # gain_factors = np.clip(
    #     0.99 / abs(fr_values), 0, 1
    # )  # NOTE: The 0.99 factor avoids the saturation of gain correction factors

    # Initialize the Imaging Channel gain array with length of FINE_CHANNELS
    default_gains = [DEFAULT_GAIN for _ in range(const.FINE_CHANNELS)]
    vcc_gain_corrections = [
        gain * factor for gain, factor in zip(default_gains, gain_factors)
    ]

    # Duplicate values for both polarizations
    vcc_gains_pol = [[gc, gc] for gc in vcc_gain_corrections]

    # FFT-shift to match registers.
    center_channel = const.FINE_CHANNELS // 2
    vcc_gain_corrections = (
        vcc_gains_pol[center_channel:] + vcc_gains_pol[:center_channel]
    )

    return vcc_gain_corrections
