# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# fine_channel_partitioner.py
#
# functions to divide the fine channels of a processing region into frequency
# slices according to given coarse channels
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

import json

from ska_mid_cbf_mcs.commons.global_enum import (
    calculate_dish_sample_rate,
    const,
    freq_band_dict,
    get_coarse_channels,
    get_end_frequency,
)

# HELPER FUNCTIONS
##############################################################################


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
        0, const.NUM_FINE_CHANNELS // const.NUM_CHANNELS_PER_SPEAD_STREAM
    ):  # == 0 to 744
        n2 = (
            -const.NUM_FINE_CHANNELS // 2
            + const.NUM_CHANNELS_PER_SPEAD_STREAM * n
        )
        center_f = _nominal_fs_center_freq(fs) + channel_width * n2
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
def _nominal_fs_center_freq(fs_id: int) -> int:
    """
    Find the nomninal center frequency slice for a given frequency slice

    :param id: coarse frequency slice id
    :return: center frequency in digitized bandwidth of the frequency slice
    """
    return fs_id * const.FS_BW


def _get_dish_sample_rate(freq_band_info: dict, k: int) -> dict:
    dish_sample_rate = calculate_dish_sample_rate(freq_band_info, k)
    return dish_sample_rate


def _dish_dependent_fs_center_freq(fs_id: int, total_num_fs_for_band: int, dish_sample_rate: dict) -> int:
    """
    find the dish-dependent center frequency for a given frequency slice

    :param fs_id: the frequency slice id
    :param k: non-negative integer used in the calculation of the dish sample rate.
    :return: the k-dependent frequency slice center frequency (Hz)
    """
    # Center frequency of FS n = (sample rate / 20) x n
    center_frequency = (
        dish_sample_rate // total_num_fs_for_band
    ) * fs_id
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


def _find_end_channel_for_spead_stream(start: int, end: int) -> int:
    """
    Determine the nearest end channel that will result in the number of
    channels being a multiple of the const.NUM_CHANNELS_PER_SPEAD_STREAM.

    :param start: the starting channel id
    :param end: the last channel
    :return: the new end channel that results in the channel count being a
             multiple of the const.NUM_CHANNELS_PER_SPEAD_STREAM
    """
    num_channels = end - start + 1
    remainder = num_channels % const.NUM_CHANNELS_PER_SPEAD_STREAM
    if remainder >= (const.NUM_CHANNELS_PER_SPEAD_STREAM // 2):
        neareset = end + (const.NUM_CHANNELS_PER_SPEAD_STREAM - remainder)
    else:
        neareset = end - remainder
    return neareset


def _round_to_nearest(
    value: int, nearest: int = const.NUM_CHANNELS_PER_SPEAD_STREAM
) -> int:
    """
    Round the value to the nearest multiple.

    :param value: the value to round
    :param nearest: the multiple to round to. default to the const.NUM_CHANNELS_PER_SPEAD_STREAM
    :return: the rounded value
    """
    return nearest * round(value / nearest)


# MAIN ALGORITHM
##############################################################################
def partition_spectrum_to_frequency_slices(
    fsp_ids: list[int],
    start_freq: int,
    channel_width: int,
    channel_count: int,
    k_value: int,
    wideband_shift: int,
    band_name: str,
) -> dict:
    """
    determine the channelization information based on the calculations in
    https://confluence.skatelescope.org/pages/viewpage.action?pageId=265843120

    :param fsp_ids: list of available fsp's to assign fs channels to
    :param start_freq: the center frequency (Hz) of the first channel
    :param channel_width: the width (Hz) of a fine channel
    :param channel_count: the number of channels in the processing region
    :param k_value: the channelization coefficient value
    :param wideband_shift: the wideband shift (Hz) to apply to the processing region
    :param band_name: the name of the frequency band
    :return: structure with information about fsp boundaries, see:
        https://confluence.skatelescope.org/display/SE/Processing+Regions+for+CORR+-+Identify+and+Select+Fine+Channels#ProcessingRegionsforCORRIdentifyandSelectFineChannels-ExampleCalculatedFrequencySliceBoundaryInformation

    example output:
    {
        "1": {    # the fsp_id
            "alignment_shift_freq": 125472,
            "b_width": 198105600,
            "end_ch": 7359,
            "end_ch_exact": 7363.464285714285,
            "end_ch_freq": 495392160,
            "fs_id": 2,
            "fsp_end_ch": 14799,
            "fsp_id": 1,
            "fsp_start_ch": 60,
            "num_channels": 14740,
            "sdp_start_channel_id": 0,
            "sdp_end_channel_id": 14739,
            "start_ch": -7380,
            "start_ch_exact": -7383,
            "start_ch_freq": 297174528,
            "total_shift_freq": 307200,
            "vcc_downshift_freq": 181728
        }
    }
    """

    if channel_width is None:
        raise ValueError("channel_width cannot be None")
    if channel_width <= 0:
        raise ValueError("channel_width cannot be negative or zero")
    if channel_count is None:
        raise ValueError("channel_count cannot be None")
    if channel_count <= 0:
        raise ValueError("channel_count cannot be negative")
    if k_value is None:
        raise ValueError("k_value cannot be None")
    if k_value < const.K_VALUE_RANGE[0] or k_value > const.K_VALUE_RANGE[1]:
        raise ValueError(
            f"k_value must be between {const.K_VALUE_RANGE[0]} - {const.K_VALUE_RANGE[1]}"
        )
    if fsp_ids is None:
        raise ValueError("fsp_ids cannot be None")
    if len(fsp_ids) == 0:
        raise ValueError("fsp_ids cannot be empty")
    band_names = list(freq_band_dict().keys())
    if band_name not in band_names:
        raise ValueError(f"band_name not in {band_names}")

    end_freq = ((channel_count * channel_width) + start_freq) - channel_width
    coarse_channels = get_coarse_channels(
        start_freq=start_freq, end_freq=end_freq, wb_shift=wideband_shift
    )
    if len(fsp_ids) < len(coarse_channels):
        raise ValueError(
            "Too few FSP's assigned for required processing region"
        )

    freq_band_info = freq_band_dict()[band_name]
    dish_sample_rate = _get_dish_sample_rate(freq_band_info, k_value)

    fs_infos = {}
    first_sdp_channel_id = 0
    for index, fs in enumerate(coarse_channels):
        fs_info = {}
        fs_info["fs_id"] = fs
        fs_info["fsp_id"] = fsp_ids[index]

        # Determine major shift
        # vcc_downshift_freq = nominal_fsn_center_freq - k_dependent_fs_center_freq
        fs_info["vcc_downshift_freq"] = _nominal_fs_center_freq(
            fs
        ) - _dish_dependent_fs_center_freq(fs, freq_band_info["total_num_FSs"], dish_sample_rate)

        if index == 0:
            # determine center frequency of first coarse channel
            # need to base our start from the starting frequency
            fs_info["start_ch"] = _round_to_nearest(
                _find_fine_channel(
                    start_freq, channel_width, wideband_shift, fs
                )
            )
            fs_info["start_ch_freq"] = (
                _nominal_fs_center_freq(fs) + fs_info["start_ch"] * channel_width
            )

            # determine minor shift
            fs_info["alignment_shift_freq"] = (
                start_freq - wideband_shift - fs_info["start_ch_freq"]
            )
        else:
            # center frequency first ch FSn = one channel up from the previous
            fs_info["start_ch_freq"] = (
                fs_infos[fsp_ids[index] - 1]["end_ch_freq"] + channel_width
            )

            # determine start channel
            fs_info["start_ch_exact"] = (
                fs_info["start_ch_freq"] - _nominal_fs_center_freq(fs)
            ) / channel_width
            # round to nearest group of const.NUM_CHANNELS_PER_SPEAD_STREAM
            fs_info["start_ch"] = _round_to_nearest(
                round(fs_info["start_ch_exact"])
            )

            nearest_to_start_ch = _nominal_fs_center_freq(fs) + (
                fs_info["start_ch"] * channel_width
            )

            # Determine minor shift
            fs_info["alignment_shift_freq"] = (
                fs_info["start_ch_freq"] - nearest_to_start_ch
            )

        # Combine shift
        fs_info["total_shift_freq"] = (
            fs_info["vcc_downshift_freq"] + fs_info["alignment_shift_freq"]
        )

        # determine end channel
        if index == (len(coarse_channels) - 1):
            # end channel is based off of the remaining channels we requested
            # for the processing region
            fs_info["end_ch"] = (
                channel_count
                - (_sum_of_channels(fs_infos) - fs_info["start_ch"])
                - 1
            )
        else:
            # We go to the end of the FS slice
            fs_info["end_ch_exact"] = (
                const.HALF_FS_BW - fs_info["alignment_shift_freq"]
            ) / channel_width
            fs_info["end_ch"] = round(fs_info["end_ch_exact"])

        # Change end channel so our number of channels will be a multiple of
        # the const.NUM_CHANNELS_PER_SPEAD_STREAM
        fs_info["end_ch"] = _find_end_channel_for_spead_stream(
            fs_info["start_ch"], fs_info["end_ch"]
        )

        # Determine number of channels
        fs_info["num_channels"] = fs_info["end_ch"] - fs_info["start_ch"] + 1

        fs_info["end_ch_freq"] = (
            (fs_info["end_ch"] * channel_width)
            + _nominal_fs_center_freq(fs)
            + fs_info["alignment_shift_freq"]
        )
        # determine other things, (bandwidth, etc)
        fs_info["b_width"] = fs_info["num_channels"] * channel_width

        # determine first SDP channels
        # Sequential from 0 from all channels for all processed fs's
        fs_info["sdp_start_channel_id"] = first_sdp_channel_id
        first_sdp_channel_id += fs_info["num_channels"]
        fs_info["sdp_end_channel_id"] = first_sdp_channel_id - 1

        fs_info["fsp_start_ch"] = (
            fs_info["start_ch"] + const.NUM_FINE_CHANNELS // 2
        )
        fs_info["fsp_end_ch"] = (
            fs_info["end_ch"] + const.NUM_FINE_CHANNELS // 2
        )

        # sort the keys
        fs_info_Keys = list(fs_info.keys())
        fs_info_Keys.sort()
        sorted_fs_info = {i: fs_info[i] for i in fs_info_Keys}

        fs_infos.update({fsp_ids[index]: sorted_fs_info})

    return fs_infos


# EXAMPLE INPUTS
##############################################################################
if __name__ == "__main__":
    fsp_ids = [5, 6, 7, 8, 9]
    START_FREQ = int(297271296)
    # WB_SHIFT = int(
    #    52.7e6
    # )  # positive means move the start of the coarse channel up by this many Hz.
    WB_SHIFT = 0
    FINE_CHANNEL_COUNT = 44740
    # we can get K from sysinit. example in doc assumes k=1000
    K_VALUE = 1000

    # Derived from inputs
    TOTAL_BWIDTH = FINE_CHANNEL_COUNT * const.FINE_CHANNEL_WIDTH
    STREAMS = TOTAL_BWIDTH / const.NUM_CHANNELS_PER_SPEAD_STREAM
    END_FREQ = get_end_frequency(
        START_FREQ, const.FINE_CHANNEL_WIDTH, FINE_CHANNEL_COUNT
    )

    print(f"With a wideband shift    : {WB_SHIFT} Hz")
    print(f"start_frequency          : {START_FREQ} Hz")
    print(f"center frequency of last : {END_FREQ} Hz")
    print(f"total bandwidth          : {TOTAL_BWIDTH} Hz")
    print(f"total streams            : {STREAMS}")

    coarse_channels = get_coarse_channels(
        START_FREQ, END_FREQ, WB_SHIFT
    )

    # Use fs_ids to validate we have enough FSP's for the bandwidth
    print(f"coarse_channels = {coarse_channels}")
    if len(fsp_ids) < len(coarse_channels):
        print(
            f"too few fsps, given: {fsp_ids}, but need for fs's {coarse_channels}"
        )
        # fsp_ids should match the number of coarse slices needed
        exit(1)

    results = partition_spectrum_to_frequency_slices(
        fsp_ids=fsp_ids,
        start_freq=START_FREQ,
        channel_width=const.FINE_CHANNEL_WIDTH,
        channel_count=FINE_CHANNEL_COUNT,
        k_value=K_VALUE,
        wideband_shift=WB_SHIFT,
        band_name="1",
    )

    sum_of_result_channels = 0
    expect_start_f = START_FREQ
    for fsp_id, fs_info in results.items():
        coarse_ch = fs_info["fs_id"]
        sum_of_result_channels = (
            sum_of_result_channels + fs_info["num_channels"]
        )

        start_f = (
            WB_SHIFT
            + coarse_ch * const.FS_BW
            + fs_info["alignment_shift_freq"]
            + fs_info["start_ch"] * const.FINE_CHANNEL_WIDTH
        )
        end_f = (
            WB_SHIFT
            + coarse_ch * const.FS_BW
            + fs_info["alignment_shift_freq"]
            + fs_info["end_ch"] * const.FINE_CHANNEL_WIDTH
        )
        print(
            f'fsp_id:{fsp_id} {coarse_ch:2}: start = ch {fs_info["fsp_start_ch"]/20:6} => {start_f:12} Hz (exp:{expect_start_f:12} Hz), end = ch {fs_info["fsp_end_ch"]/20:3.2f} => {end_f:12} Hz'
        )

        assert (fs_info["start_ch"]) % const.NUM_CHANNELS_PER_SPEAD_STREAM == 0
        assert (
            fs_info["end_ch"] + 1
        ) % const.NUM_CHANNELS_PER_SPEAD_STREAM == 0

        expect_start_f = end_f + const.FINE_CHANNEL_WIDTH

    print(f"total channels: {sum_of_result_channels}")
    assert sum_of_result_channels == FINE_CHANNEL_COUNT

    print(json.dumps(results, indent=4, sort_keys=True))
