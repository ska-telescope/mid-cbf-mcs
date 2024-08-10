# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# fs_boundary_util.py
#
# determine the channels for a FSP given the starting frequency to take shift
# and channelization into account.
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

import json
import math

# CONSTS
##############################################################################

# For Band 1/2 the sample rate will be 3.96 Gsps (gigasample per second) +
# 1800 x k. k=0 has a sample rate of 3,960,000,000, k=1 has a sample rate of
# 3,960,001,800, etc.
SAMPLE_RATE_BASE = 3960000000

# Values from digitized BW
COMMON_SAMPLE_RATE = 220200960
VCC_OVERSAMPLING = 10 / 9
FS_BW = int(COMMON_SAMPLE_RATE / VCC_OVERSAMPLING)
HALF_FS_BW = FS_BW // 2

FINE_CHANNEL_WIDTH = 13440  # Hz
FINE_CHANNELS_PER_FSP = 14880
FINE_CHANNELS_PER_SDP_SPEAD_STREAM = 20  # 20 for AA0.5/1, 1 for AA2+

# HELPER FUNCTIONS
##############################################################################


def get_coarse_channels(
    start_freq: int, end_freq: int, wb_shift: int
) -> list[int]:
    """
    Determine the Frequency Slices needed for this processing region

    :param start_freq: Start frequency of the processing region (Hz)
    :param end_freq: End frequency of the processing region (Hz)
    :praam wb_shift: Wideband shift (Hz)
    :return: A list of frequency slice id's
    """

    # coarse_channel = floor [(Frequency + WB_shift + 99090432Hz) / 198180864 Hz]
    coarse_channel_low = math.floor(
        (start_freq - wb_shift + HALF_FS_BW) / FS_BW
    )
    coarse_channel_high = math.floor(
        (end_freq - wb_shift + HALF_FS_BW) / FS_BW
    )
    coarse_channels = list(range(coarse_channel_low, coarse_channel_high + 1))
    return coarse_channels


def _find_fine_channel(
    target_center_freq: int, channel_width: int, wideband_shift: int, fs: int
) -> int:
    """
    Find the fine channel closest to the target_center_freq frequency for the
    given channel width

    :param target_center_freq: Frequency of the center of the channel we
    want to locate
    :param channel_width: Width of a fine channel
    :param fs: Frequency Slice ID
    :return: The channel number (relative to the center of the FS) closest to
    the target frequency.
    """
    shifted_target_freq = target_center_freq - wideband_shift
    channel = None
    last = None
    for n in range(
        0, FINE_CHANNELS_PER_FSP // FINE_CHANNELS_PER_SDP_SPEAD_STREAM
    ):  # == 0 to 744
        n2 = (
            -FINE_CHANNELS_PER_FSP // 2
            + FINE_CHANNELS_PER_SDP_SPEAD_STREAM * n
        )
        center_f = _nominal_fs_spacing(fs) + channel_width * n2
        diff = abs(shifted_target_freq - center_f)
        if last is None or diff < last:
            channel = n2
            last = diff
        if diff > last:
            break
    if channel is None:
        raise ValueError("Failed to find a valid fine channel")
    return channel


# Used for getting the Center Frequency in Digitized Bandwidth
def _nominal_fs_spacing(fs_id: int) -> int:
    """
    Find the nomninal center frequency slice for a given frequency slice

    :param id: coarse frequency slice id
    :return: center frequency in digitized bandwidth of the frequency slice
    """
    return fs_id * FS_BW


def _k_dependent_fs_center(fs_id: int, k: int) -> int:
    """
    find the K-dpendent center frequency for a given frequency slice

    :param fs_id: the frequency slice id
    :param k: the channelisation coefficient
    :return: the k-dependent frequency slice center frequency (Hz)
    """
    # Center frequency of FS n = (sample rate / 20) x n
    sample_rate = SAMPLE_RATE_BASE + 1800 * k
    center_frequency = (sample_rate // 20) * fs_id
    return center_frequency


def _sum_of_channels(fs_infos: dict) -> int:
    """
    Calculate the sum of existing channels

    :param fs_info: Calculated frequency slice information (output of
                    calculate_fs_info function)
    :return: the sum of channels assigned to the fsps
    """
    total_channels = 0
    for fs in fs_infos:
        total_channels = total_channels + fs_infos[fs]["num_channels"]
    return total_channels


def _nearest_stream(start: int, end: int) -> int:
    """
    Determine the nearest end channel that will result in the number of
    channels being a multiple of the FINE_CHANNELS_PER_SDP_SPEAD_STREAM.

    Note: FINE_CHANNELS_PER_SDP_SPEAD_STREAM = 20 for AA0.50

    :param start: the starting channel id
    :param end: the last channel
    :return: the new end channel that results in the channel count being a mulitple of the FINE_CHANNELS_PER_SDP_SPEAD_STREAM
    """
    num_channels = end - start + 1
    remainder = num_channels % FINE_CHANNELS_PER_SDP_SPEAD_STREAM
    if remainder >= (FINE_CHANNELS_PER_SDP_SPEAD_STREAM // 2):
        neareset = end + (FINE_CHANNELS_PER_SDP_SPEAD_STREAM - remainder)
    else:
        neareset = end - remainder
    return neareset


def round_to_nearest(
    value: int, multiple: int = FINE_CHANNELS_PER_SDP_SPEAD_STREAM
) -> int:
    """
    Round to the nearest multiple

    :param value: the value to round
    :param multiple: the multiple to round to. default to the FINE_CHANNELS_PER_SDP_SPEAD_STREAM which is 20 for AA0.5
    :return: the rounded value
    """
    return multiple * round(value / multiple)


# MAIN ALGORITHM
##############################################################################

# example result:
"""
{
    "2": {
        "alignment_shift_freq": 125472,
        "b_width": 198105600,
        "end_ch": 7359,
        "end_ch_exact": 7363.464285714285,
        "end_ch_freq": 495392160,
        "start_ch_freq": 297174528,
        "fs_id": 2,
        "fsp_end_ch": 14799,
        "fsp_id": 1,
        "fsp_start_ch": 60,
        "num_channels": 14740,
        "sdp_channel_id": 0,
        "sdp_channel_id_end": 14739,
        "shift": 307200,
        "start_ch": -7380,
        "vcc_downshift_freq": 181728
    }
}
for output explaination, see documentation at:
https://confluence.skatelescope.org/display/SE/Processing+Regions+for+CORR+-+Identify+and+Select+Fine+Channels#ProcessingRegionsforCORRIdentifyandSelectFineChannels-ExampleCalculatedFrequencySliceBoundaryInformation
"""


def calculate_fs_info(
    fsp_ids: list,
    coarse_channels: list,
    start_freq: int,
    channel_width: int,
    num_channels: int,
    k_value: int,
    wideband_shift: int,
) -> dict:
    """
    determine the channelization information based on the calculations in
    https://confluence.skatelescope.org/pages/viewpage.action?pageId=265843120

    :param fsp_ids: list of available fsp's to assign fs channels to
    :param coarse_channels: list of coarse channels to get channels from
    :param start_freq: the center frequency (Hz) of the first channel
    :param channel_width: the width (Hz) of a fine channel
    :param num_channels: the number of channels in the processing region
    :param k_value: the channelization coefficient value
    :param wideband_shift: the wideband shift (Hz) to apply to the processing
                           region
    :return: structure

    """
    fs_infos = {}
    first_sdp_channel_id = 0
    for index, fs in enumerate(coarse_channels):
        # determine center frequency of first channel
        fs_info = {}
        fs_info["fs_id"] = fs
        fs_info["fsp_id"] = fsp_ids[index]

        # Determine major shift
        # vcc_downshift_freq = nominal_fsn_center_freq - k_dependent_fs_center_freq
        fs_info["vcc_downshift_freq"] = _nominal_fs_spacing(
            fs
        ) - _k_dependent_fs_center(fs, k_value)

        if index == 0:
            # need to base our start from the starting frequency
            fs_info["start_ch"] = round_to_nearest(
                _find_fine_channel(
                    start_freq, channel_width, wideband_shift, fs
                )
            )
            fs_info["start_ch_freq"] = (
                _nominal_fs_spacing(fs) + fs_info["start_ch"] * channel_width
            )

            # determine minor shift
            fs_info["alignment_shift_freq"] = (
                start_freq - wideband_shift - fs_info["start_ch_freq"]
            )
        else:
            # center frequency first ch FSn = one channel up from the previous
            fs_info["start_ch_freq"] = (
                fs_infos[fs - 1]["end_ch_freq"] + channel_width
            )

            # determine start channel
            fs_info["start_ch_exact"] = (
                fs_info["start_ch_freq"] - _nominal_fs_spacing(fs)
            ) / channel_width
            fs_info["start_ch"] = round_to_nearest(
                round(fs_info["start_ch_exact"])
            )

            nearest_to_start_ch = _nominal_fs_spacing(fs) + (
                fs_info["start_ch"] * channel_width
            )

            # Determine minor shift
            fs_info["alignment_shift_freq"] = (
                fs_info["start_ch_freq"] - nearest_to_start_ch
            )

        # Combine shift
        fs_info["shift"] = (
            fs_info["vcc_downshift_freq"] + fs_info["alignment_shift_freq"]
        )

        # determine end channel
        if index == (len(coarse_channels) - 1):
            # end channel is based off of the remaining channels we requested
            # for the processing region
            fs_info["end_ch"] = (
                num_channels
                - (_sum_of_channels(fs_infos) - fs_info["start_ch"])
                - 1
            )
        else:
            # We go to the end of the FS slice
            fs_info["end_ch_exact"] = (
                HALF_FS_BW - fs_info["alignment_shift_freq"]
            ) / channel_width
            fs_info["end_ch"] = round(fs_info["end_ch_exact"])

        # Change end channel so our number of channels will be a multiple of
        # the FINE_CHANNELS_PER_SDP_SPEAD_STREAM
        fs_info["end_ch"] = _nearest_stream(
            fs_info["start_ch"], fs_info["end_ch"]
        )

        # Determine number of channels
        fs_info["num_channels"] = fs_info["end_ch"] - fs_info["start_ch"] + 1

        fs_info["end_ch_freq"] = (
            (fs_info["end_ch"] * channel_width)
            + _nominal_fs_spacing(fs)
            + fs_info["alignment_shift_freq"]
        )
        # determine other things, (bandwidth, etc)
        fs_info["b_width"] = fs_info["num_channels"] * channel_width

        # determine first SDP channels
        # Sequential from 0 from all channels for all processed fs's
        fs_info["sdp_channel_id"] = first_sdp_channel_id
        first_sdp_channel_id += fs_info["num_channels"]
        fs_info["sdp_channel_id_end"] = first_sdp_channel_id - 1

        fs_info["fsp_start_ch"] = (
            fs_info["start_ch"] + FINE_CHANNELS_PER_FSP // 2
        )
        fs_info["fsp_end_ch"] = fs_info["end_ch"] + FINE_CHANNELS_PER_FSP // 2

        # sort the keys
        fs_info_Keys = list(fs_info.keys())
        fs_info_Keys.sort()
        sorted_fs_info = {i: fs_info[i] for i in fs_info_Keys}

        fs_infos.update({fs: sorted_fs_info})

    return fs_infos


# EXAMPLE INPUTS
##############################################################################
if __name__ == "__main__":
    fsp_ids = [1, 2, 3, 4, 5]
    START_FREQ = int(350e6)
    WB_SHIFT = int(
        52.7e6
    )  # positive means move the start of the coarse channel up by this many Hz.
    # WB_SHIFT = 0
    FINE_CHANNEL_COUNT = 58980
    # we can get K from sysinit. example in doc assumes k=1000
    K_VALUE = 1000

    # Derived from inputs
    TOTAL_BWIDTH = FINE_CHANNEL_COUNT * FINE_CHANNEL_WIDTH
    STREAMS = TOTAL_BWIDTH / FINE_CHANNELS_PER_SDP_SPEAD_STREAM
    END_FREQ = (
        (FINE_CHANNEL_COUNT * FINE_CHANNEL_WIDTH) + START_FREQ
    ) - FINE_CHANNEL_WIDTH

    print(f"With a wideband shift    : {WB_SHIFT} Hz")
    print(f"start_frequency          : {START_FREQ} Hz")
    print(f"center frequency of last : {END_FREQ} Hz")
    print(f"total bandwidth          : {TOTAL_BWIDTH} Hz")
    print(f"total streams            : {STREAMS}")

    coarse_channels = get_coarse_channels(START_FREQ, END_FREQ, WB_SHIFT)

    # Use fs_ids to validate we have enough FSP's for the bandwidth
    print(f"coarse_channels = {coarse_channels}")
    if len(fsp_ids) < len(coarse_channels):
        print(
            f"too few fsps, given: {fsp_ids}, but need for fs's {coarse_channels}"
        )
        # fsp_ids should match the number of coarse slices needed
        exit(1)

    results = calculate_fs_info(
        fsp_ids=fsp_ids,
        coarse_channels=coarse_channels,
        start_freq=START_FREQ,
        channel_width=FINE_CHANNEL_WIDTH,
        num_channels=FINE_CHANNEL_COUNT,
        k_value=K_VALUE,
        wideband_shift=WB_SHIFT,
    )

    sum_of_result_channels = 0
    expect_start_f = START_FREQ
    for coarse_ch, fs_info in results.items():
        sum_of_result_channels = (
            sum_of_result_channels + fs_info["num_channels"]
        )

        start_f = (
            WB_SHIFT
            + coarse_ch * FS_BW
            + fs_info["alignment_shift_freq"]
            + fs_info["start_ch"] * FINE_CHANNEL_WIDTH
        )
        end_f = (
            WB_SHIFT
            + coarse_ch * FS_BW
            + fs_info["alignment_shift_freq"]
            + fs_info["end_ch"] * FINE_CHANNEL_WIDTH
        )
        print(
            f'{coarse_ch:2}: start = ch {fs_info["fsp_start_ch"]/20:6} => {start_f:12} Hz (exp:{expect_start_f:12} Hz), end = ch {fs_info["fsp_end_ch"]/20:3.2f} => {end_f:12} Hz'
        )

        assert (fs_info["start_ch"]) % FINE_CHANNELS_PER_SDP_SPEAD_STREAM == 0
        assert (
            fs_info["end_ch"] + 1
        ) % FINE_CHANNELS_PER_SDP_SPEAD_STREAM == 0

        expect_start_f = end_f + FINE_CHANNEL_WIDTH

    print(f"total channels: {sum_of_result_channels}")
    assert sum_of_result_channels == FINE_CHANNEL_COUNT

    print(json.dumps(results, indent=4, sort_keys=True))
