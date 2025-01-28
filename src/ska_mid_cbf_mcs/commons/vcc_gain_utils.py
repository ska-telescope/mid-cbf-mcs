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

from ska_mid_cbf_mcs.commons.global_enum import (
    calculate_dish_sample_rate,
    const,
    freq_band_dict,
)

# YAML file containing the finite impulse response (FIR) data for a VCC
VCC_FIR_PATH = "mnt/vcc_param/VCC_FIR.yml"

DEFAULT_GAIN = 1.0
MIN_GAIN = 0.0
MAX_GAIN = 4.005


def get_vcc_ripple_correction(
    freq_band: str,
    scfo_fsft: int,
    freq_offset_k: int,
) -> list[float]:
    """
    Applies VCC Gain ripple correction to a list of gains.
    Based on https://gitlab.com/ska-telescope/ska-mid-cbf-signal-verification/-/blob/main/images/ska-mid-cbf-signal-verification/hardware_testing_notebooks/talon_pyro/talon_FSP.py

    :param freq_band: the frequency band of the VCC
    :param scfo_fsft: the frequency shift of the RDT required due to Sample Clock
        Frequency Offset (SCFO) sampling
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
        start=-1,
        stop=1 - 2 / const.TOTAL_FINE_CHANNELS,
        num=const.TOTAL_FINE_CHANNELS,
    )
    actual_center_frequency = fc0 * const.COMMON_SAMPLE_RATE / 2 - scfo_fsft
    normalized_center_frequency = (
        actual_center_frequency
        / frequency_slice_sample_rate
        / input_frame_size
    )

    # Evaluate VCC frequency response data
    with open(f"{VCC_FIR_PATH}", "r") as file:
        vcc_fir = yaml.safe_load(file)
    vcc_fir_coeff = vcc_fir["h"]
    _, fr_values = scipy.signal.freqz(
        vcc_fir_coeff, a=1, worN=2 * np.pi * normalized_center_frequency
    )

    # Calculate 16k fine-channelizer gain correction factors
    vcc_gain_corrections = np.clip(
        DEFAULT_GAIN / abs(fr_values), a_min=MIN_GAIN, a_max=MAX_GAIN
    ).tolist()

    # FFT-shift to match registers.
    vcc_gains_copy = list(vcc_gain_corrections)
    center_channel = const.TOTAL_FINE_CHANNELS // 2
    vcc_gain_corrections = (
        vcc_gains_copy[center_channel:] + vcc_gains_copy[:center_channel]
    )

    return vcc_gain_corrections
