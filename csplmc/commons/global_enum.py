from enum import IntEnum, unique

@unique
class HealthState(IntEnum):
    OK       = 0
    DEGRADED = 1
    FAILED   = 2
    UNKNOWN  = 3

@unique
class AdminMode(IntEnum):
    ONLINE      = 0
    OFFLINE     = 1
    MAINTENANCE = 2
    NOTFITTED   = 3

@unique
class ControlMode(IntEnum):
    REMOTE = 0
    LOCAL  = 1

@unique
class ObsMode(IntEnum):
    IDLE             = 0
    IMAGING          = 1
    PULSARSEARCH     = 2
    PULSARTIMING     = 3
    DYNAMICSPECTRUM  = 4
    TRANSIENTSEARCH  = 5
    VLBI             = 6
    CALIBRATION      = 7

@unique
class ObsState(IntEnum):
    IDLE        = 0
    CONFIGURING = 1
    READY       = 2
    SCANNING    = 3
    PAUSED      = 4
    ABORTED     = 5
    FAULT       = 6


# Temporary class. These values should be retrieved from their respective devices.
class Const:
    def __init__(self):
        self.MIN_INT_TIME = 140  # ms
        self.FREQUENCY_SLICE_BW = 200  # MHz
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
