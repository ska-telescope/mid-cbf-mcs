# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for gain correction of VCC frequency response"""

from __future__ import annotations  # allow forward references in type hints

import numpy as np
import scipy
import yaml

from ska_mid_cbf_tdc_mcs.commons.global_enum import (
    calculate_dish_sample_rate,
    const,
    freq_band_dict,
)

VCC_IR_PATH = "mnt/vcc_param/OS_Prototype_FIR_CH20.yml"

DEFAULT_GAIN = 1.0
MIN_GAIN = 0.0
MAX_GAIN = 4.005


def get_vcc_ripple_correction(
    freq_band: str,
    scf0_fsft: int,
    freq_offset_k: int,
) -> list:
    """
    Applies VCC Gain ripple correction to a list of gains.
    Based on https://gitlab.com/ska-telescope/ska-mid-cbf-signal-verification/-/blob/main/images/ska-mid-cbf-signal-verification/hardware_testing_notebooks/talon_pyro/talon_FSP.py

    :param freq_band: the frequency band of the VCC
    :param scf0_fsft: the frequency shift of the RDT required due to SCFO sampling
    :param freq_offset_k: the frequency offset k value
    :return: list of new gain values
    """

    # Load VCC band info to calculate FS sample rate
    freq_band_info = freq_band_dict()[freq_band]
    input_sample_rate = calculate_dish_sample_rate(
        freq_band_info=freq_band_info, freq_offset_k=freq_offset_k
    )
    input_frame_size = freq_band_info["num_samples_per_frame"]
    frequency_slice_sample_rate = input_sample_rate // input_frame_size

    # Calculate normalized actual center frequency of secondary channelizer
    fc0 = np.linspace(
        -1, 1 - 2 / const.NUM_FINE_CHANNELS, num=const.NUM_FINE_CHANNELS
    )
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

    # Initialize the Imaging Channel gain array with length of NUM_FINE_CHANNELS
    default_gains = [DEFAULT_GAIN for _ in range(const.NUM_FINE_CHANNELS)]
    vcc_gain_corrections = [
        gain * factor for gain, factor in zip(default_gains, gain_factors)
    ]

    # FFT-shift to match registers.
    vcc_gains_copy = list(vcc_gain_corrections)
    center_channel = const.NUM_FINE_CHANNELS // 2
    vcc_gain_corrections = (
        vcc_gains_copy[center_channel:] + vcc_gains_copy[:center_channel]
    )

    return vcc_gain_corrections
