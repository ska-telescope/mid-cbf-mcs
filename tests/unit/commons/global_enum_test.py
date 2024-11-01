import pytest

from ska_mid_cbf_mcs.commons.global_enum import get_coarse_channels

# Start and end Frequency of coarse channels in Hz
coarse_channel_boundaries = [
    (-99090432, 99090431),
    (99090432, 297271295),
    (297271296, 495452159),
    (495452160, 693633023),
    (693633024, 891813887),
    (891813888, 1089994751),
    (1089994752, 1288175615),
    (1288175616, 1486356479),
    (1486356480, 1684537343),
    (1684537344, 1882718207),
]


def test_get_coarse_channels_invalid_args():
    with pytest.raises(ValueError):
        get_coarse_channels(start_freq=1, end_freq=0, wb_shift=0)


def test_get_coarse_channels_valid():
    total_coarse_channels = len(coarse_channel_boundaries)
    for start_channel_index in range(0, total_coarse_channels):
        start_channel = coarse_channel_boundaries[start_channel_index]
        for end_channel_index in range(0, total_coarse_channels):
            if end_channel_index < start_channel_index:
                continue
            end_channel = coarse_channel_boundaries[end_channel_index]
            expected_number_of_channels = (
                end_channel_index - start_channel_index + 1
            )
            actual_coarse_channels = get_coarse_channels(
                start_channel[0], end_channel[1], 0
            )
            print(
                f"start index: {start_channel_index}, end index: {end_channel_index}"
            )
            print(actual_coarse_channels)
            assert expected_number_of_channels == len(actual_coarse_channels)
            assert actual_coarse_channels == list(
                range(start_channel_index, end_channel_index + 1)
            )
