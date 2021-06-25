from enum import IntEnum, unique

# TODO - Temporary class. These values should be retrieved 
#        from their respective devices (?)
class Const:
    def __init__(self):
        self.MIN_INT_TIME = 1  #ADR-35: changed from 140 ms to 1 (factor)
        self.FREQUENCY_SLICE_BW = 200  # MHz
        self.SEARCH_WINDOW_BW   = 300  # MHz
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
        self.FREQUENCY_SLICE_BW_HZ = 200 * 10 ** 6
        self.SEARCH_WINDOW_BW_HZ   = 300 * 10 ** 6 
        self.FREQUENCY_BAND_1_RANGE_HZ = (0.35* 10**9, 1.05 * 10**9)
        self.FREQUENCY_BAND_2_RANGE_HZ = (0.95* 10**9, 1.76 * 10**9)
        self.FREQUENCY_BAND_3_RANGE_HZ = (1.65* 10**9, 3.05 * 10**9)
        self.FREQUENCY_BAND_4_RANGE_Hz = (2.80* 10**9, 5.18 * 10**9)

const = Const()

def freq_band_dict():
    freq_band_labels = ["1", "2", "3", "4", "5a", "5b"]
    freq_bands = dict(zip(freq_band_labels, range(len(freq_band_labels))))
    return freq_bands
