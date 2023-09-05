from enum import Enum

__all__ = ["const", "freq_band_dict", "FspModes"]


# TODO - Temporary class. These values should be retrieved
#        from their respective devices (?)
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
        self.NUM_CHANNEL_GROUPS = 20
        self.NUM_PHASE_BINS = 1024
        self.NUM_OUTPUT_LINKS = 80

        # TODO - remove the consts in MHZ/GHz eventually
        self.FREQUENCY_SLICE_BW_HZ = 200 * 10**6
        self.SEARCH_WINDOW_BW_HZ = 300 * 10**6
        self.FREQUENCY_BAND_1_RANGE_HZ = (0.35 * 10**9, 1.05 * 10**9)
        self.FREQUENCY_BAND_2_RANGE_HZ = (0.95 * 10**9, 1.76 * 10**9)
        self.FREQUENCY_BAND_3_RANGE_HZ = (1.65 * 10**9, 3.05 * 10**9)
        self.FREQUENCY_BAND_4_RANGE_HZ = (2.80 * 10**9, 5.18 * 10**9)

        self.DEFAULT_OUTPUT_HOST = [[0, "192.168.0.1"]]
        self.DEFAULT_OUTPUT_MAC = [[0, "06-00-00-00-00-01"]]
        self.DEFAULT_OUTPUT_PORT = [[0, 9000, 1]]

        self.MAX_VCC = 4

        self.MAX_SUBARRAY = 16

        self.DEFAULT_COUNT_VCC = 197
        self.DEFAULT_COUNT_FSP = 27
        self.DEFAULT_COUNT_SUBARRAY = 16


const = Const()


class FspModes(Enum):
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
        },
        "2": {
            "band_index": 1,
            "base_dish_sample_rate_MHz": 3960,
            "sample_rate_const": 1,
            "total_num_FSs": 20,
            "num_samples_per_frame": 18,
        },
        "3": {
            "band_index": 2,
            "base_dish_sample_rate_MHz": 3168,
            "sample_rate_const": 0.8,
            "total_num_FSs": 20,
            "num_samples_per_frame": 18,
        },
        "4": {
            "band_index": 3,
            "base_dish_sample_rate_MHz": 5940,
            "sample_rate_const": 1.5,
            "total_num_FSs": 30,
            "num_samples_per_frame": 27,
        },
        "5a": {
            "band_index": 4,
            "base_dish_sample_rate_MHz": 5940,
            "sample_rate_const": 1.5,
            "total_num_FSs": 60,
            "num_samples_per_frame": 27,  # FIXME with correct value
        },
        "5b": {
            "band_index": 5,
            "base_dish_sample_rate_MHz": 5940,
            "sample_rate_const": 1.5,
            "total_num_FSs": 60,
            "num_samples_per_frame": 27,  # FIXME with correct value
        },
    }
    return band_info


# The VCC-OSPPFB oversampling factor:
vcc_oversampling_factor = 10 / 9

mhz_to_hz = 1000000

"""
NOTES:

1) calculate the dish_sample_rate [Hz] as:
dish_sample_rate = base_dish_sample_rate_MH * mhz_to_hz + sample_rate_const * k * deltaF

where k (receptor dependent) and deltaF [Hz] are obtained from LMC via the CbfControl device.

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
