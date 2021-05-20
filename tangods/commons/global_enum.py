from enum import IntEnum, unique

# Temporary class. These values should be retrieved from their respective devices.
class Const:
    def __init__(self):
        self.MIN_INT_TIME = 140  # ms
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

const = Const()

def freq_band_dict():
    freq_band_labels = ["1", "2", "3", "4", "5a", "5b"]
    freq_bands = dict(zip(freq_band_labels, range(len(freq_band_labels))))
    return freq_bands
