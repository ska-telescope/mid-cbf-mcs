from enum import IntEnum
from math import floor

__all__ = ["const", "freq_band_dict", "FspModes"]


class Const:
    def __init__(self):
        self.MIN_INT_TIME = 1  # ADR-35: changed from 140 ms to 1 (factor)
        self.FREQUENCY_SLICE_BW = 200  # MHz
        self.SEARCH_WINDOW_BW = 300  # MHz
        self.FREQUENCY_BAND_1_RANGE = (0.35, 1.05)  # GHz
        self.FREQUENCY_BAND_2_RANGE = (0.95, 1.76)  # GHz
        self.FREQUENCY_BAND_3_RANGE = (1.65, 3.05)  # GHz
        self.FREQUENCY_BAND_4_RANGE = (2.80, 5.18)  # GHz
        self.FREQUENCY_BAND_5a_TUNING_BOUNDS = (5.85, 7.25)  # GHz
        self.FREQUENCY_BAND_5b_TUNING_BOUNDS = (9.55, 14.05)  # GHz
        self.BAND_5_STREAM_BANDWIDTH = 2.5  # GHz
        self.NUM_FINE_CHANNELS = 14880

        # Number of Fine channels per SPEAD stream;
        # TODO: NUM_CHANNELS_PER_SPEAD_STREAM = 20 for TDC (AA0.5, AA1) only; for Mid.CBF (AA2+) it will be set to 1
        self.NUM_CHANNELS_PER_SPEAD_STREAM = 20
        self.NUM_PHASE_BINS = 1024
        self.NUM_OUTPUT_LINKS = 80
        self.DELTA_F = 1800  # Hz

        # TODO - remove the consts in MHZ/GHz eventually
        self.FREQUENCY_SLICE_BW_HZ = 200 * 10**6
        self.SEARCH_WINDOW_BW_HZ = 300 * 10**6
        self.FREQUENCY_BAND_1_RANGE_HZ = (0.35 * 10**9, 1.05 * 10**9)
        self.FREQUENCY_BAND_2_RANGE_HZ = (0.95 * 10**9, 1.76 * 10**9)
        self.FREQUENCY_BAND_3_RANGE_HZ = (1.65 * 10**9, 3.05 * 10**9)
        self.FREQUENCY_BAND_4_RANGE_HZ = (2.80 * 10**9, 5.18 * 10**9)

        self.MAX_VCC = 197
        self.MAX_FSP = 27
        self.MAX_SUBARRAY = 16

        self.MAX_NUM_FS_LINKS = 16  # AA0.5
        self.MAX_NUM_VIS_LINKS = 4

        # TODO: update values as max capabilities increases
        self.DEFAULT_COUNT_VCC = 4
        self.DEFAULT_COUNT_FSP = 4
        self.DEFAULT_COUNT_SUBARRAY = 1

        self.DEFAULT_TIMEOUT = 4

        self.BER_PASS_THRESHOLD = 8.000e-11
        self.GBPS = 25.78125 * 64 / 66

        # Common sample rate for all receptor data streams, achieved after
        # Resampling & Delay Tracking  (RDT) [Hz]; applies for all function
        # modes except VLBI
        self.COMMON_SAMPLE_RATE = 220200960
        self.VCC_OVERSAMPLING_FACTOR = 10 / 9

        # Frequency Slice Bandwidth [Hz]
        self.FS_BW = int(
            self.COMMON_SAMPLE_RATE / self.VCC_OVERSAMPLING_FACTOR
        )
        self.HALF_FS_BW = self.FS_BW // 2

        # Fine channel width for the Correlation function mode [Hz]
        self.FINE_CHANNEL_WIDTH = 13440
        self.K_VALUE_RANGE = (1, 2222)


const = Const()


# TODO: use ObsMode
class FspModes(IntEnum):
    IDLE = 0
    CORR = 1
    PSS_BF = 2
    PST_BF = 3
    VLBI = 4


def freq_band_dict():
    band_info = {
        "1": {
            "band_index": 0,
            "base_dish_sample_rate_MHz": 3960,
            "sample_rate_const": 1,
            "total_num_FSs": 20,
            "num_samples_per_frame": 18,
            "num_frequency_slices": 4,
        },
        "2": {
            "band_index": 1,
            "base_dish_sample_rate_MHz": 3960,
            "sample_rate_const": 1,
            "total_num_FSs": 20,
            "num_samples_per_frame": 18,
            "num_frequency_slices": 5,
        },
        "3": {
            "band_index": 2,
            "base_dish_sample_rate_MHz": 3168,
            "sample_rate_const": 0.8,
            "total_num_FSs": 20,
            "num_samples_per_frame": 18,
            "num_frequency_slices": 7,
        },
        "4": {
            "band_index": 3,
            "base_dish_sample_rate_MHz": 5940,
            "sample_rate_const": 1.5,
            "total_num_FSs": 30,
            "num_samples_per_frame": 27,
            "num_frequency_slices": 12,
        },
        "5a": {
            "band_index": 4,
            "base_dish_sample_rate_MHz": 5940,
            "sample_rate_const": 1.5,
            "total_num_FSs": 60,
            "num_samples_per_frame": 27,  # FIXME with correct value
            "num_frequency_slices": 26,
        },
        "5b": {
            "band_index": 5,
            "base_dish_sample_rate_MHz": 5940,
            "sample_rate_const": 1.5,
            "total_num_FSs": 60,
            "num_samples_per_frame": 27,  # FIXME with correct value
            "num_frequency_slices": 26,
        },
    }
    return band_info


def scan_configuration_supported_value(parameter: str) -> any:
    """
    Returns the value that is supported by MCS of the given parameter.
    The return values could be one of or a combination of:

    - Dictionary if only specific values are supported, or there are multiple
         validation parameters

    - List if there is a range of specific values that is supported

    - Tuple if there is a min value and max value supported, inclusively

    - Bool if the parameter is not supported (in that case, False), or if the parameter is not one that
        is handled by this function (in this case, False)

    :return: One of the types listed above
    :rtype: dict | list | tuple | bool
    """

    supported_values = {
        "frequency": (0, 1981808640),
        "function_modes": {FspModes.IDLE, FspModes.CORR},
        "subarray_id": [1],
        "fsp_ids": (1, 4),
        "band_5_tuning": False,
        "frequency_band": {"1", "2"},
        "frequency_band_offset_stream1": False,
        "frequency_band_offset_stream2": False,
        "rfi_flagging_mask": False,
        "vlbi": False,
        "search_window": False,
        "processing_region": {
            FspModes.CORR: {
                "fsp_id": [1, 2, 3, 4],
                "channel_width": {13440},
                "channel_count": {"range": (1, 58982), "multiple": 20},
                "output_host": {"multiple": 20, "max_channel_per": 20},
                "output_port": {"increment": 20, "max_channel_per": 20},
                "output_link_map": {
                    "multiple": 20,
                    "max_channel_per": 20,
                    "values": [1],
                },
            }
        },
    }

    if parameter in supported_values:
        return supported_values[parameter]
    else:
        return False


mhz_to_hz = 1000000


"""
NOTES:

1) calculate the dish_sample_rate [Hz] as:
dish_sample_rate = base_dish_sample_rate_MH * mhz_to_hz + sample_rate_const * k * deltaF

where k (receptor dependent) is obtained from LMC via the CbfControl device.
deltaF is fixed at 1800Hz

2) calculate the input sample rate to the FSP, fs_sample_rate [Hz] as:
fs_sample_rate = dish_sample_rate * vcc_oversampling_factor / total_num_FSs

3) num_samples_per_frame is the parameter used as input
to the HPS VCC low level device, currently defined in DsVccBand1And2.h

4) For each band, by design, num_samples_per_frame is equal to
cc_oversampling_factor/total_num_FSs .

5) TODO: eventually, refactor to move the band frequency limits
defined in this file into the corresponding band_info
dictionary entries.
"""


def calculate_dish_sample_rate(
    freq_band_info: dict,
    freq_offset_k: int,
) -> int:
    """
    Calculate frequency slice sample rate

    :param freq_band_info: constants pertaining to a given frequency band
    :param freq_offset_k: DISH frequency offset k value
    :return: DISH sample rate
    """
    base_dish_sample_rate_MH = freq_band_info["base_dish_sample_rate_MHz"]
    sample_rate_const = freq_band_info["sample_rate_const"]

    return (base_dish_sample_rate_MH * mhz_to_hz) + (
        sample_rate_const * freq_offset_k * const.DELTA_F
    )


def get_coarse_channels(
    start_freq: int, end_freq: int, wb_shift: int
) -> list[int]:
    """
    Determine the coarse frequency Slices that contain the processing region

    :param start_freq: Start frequency of the processing region (Hz)
    :param end_freq: End frequency of the processing region (Hz)
    :praam wb_shift: Wideband shift (Hz)
    :return: A list of coarse frequency slice id's

    :raise ValueError: if start_freq is greater than end_freq
    """
    if start_freq > end_freq:
        raise ValueError("start_freq must be <= end_freq")

    # coarse_channel = floor [(Frequency + WB_shift + 99090432Hz) / 198180864 Hz]
    coarse_channel_low = floor(
        (start_freq - wb_shift + const.HALF_FS_BW) / const.FS_BW
    )
    coarse_channel_high = floor(
        (end_freq - wb_shift + const.HALF_FS_BW) / const.FS_BW
    )
    coarse_channels = list(range(coarse_channel_low, coarse_channel_high + 1))
    return coarse_channels


def get_end_frequency(
    start_freq: int, channel_width: int, channel_count: int
) -> int:
    """
    Determine the end frequency of the processing region (Hz)

    :param start_freq:  Start frequency of the processing region (Hz)
    :param channel_width: Width of a fine frequency channel (Hz)
    :param channel_count: Number of fine frequency channels
    :return: End frequency of the processing region (Hz)
    """

    end_freq = ((channel_count * channel_width) + start_freq) - channel_width
    return end_freq
