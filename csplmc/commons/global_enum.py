from enum import Enum, unique

@unique
class HealthState(Enum):
    OK       = 0
    DEGRADED = 1
    FAILED   = 2
    UNKNOWN  = 3

@unique
class AdminMode(Enum):
    ONLINE      = 0
    OFFLINE     = 1
    MAINTENANCE = 2
    NOTFITTED   = 3
    RESERVED    = 4

@unique
class ControlMode(Enum):
    REMOTE = 0
    LOCAL  = 1

@unique
class ObsMode(Enum):
    IDLE             = 0
    IMAGING          = 1
    PULSARSEARCH    = 2
    PULSARTIMING    = 3
    DYNAMICSPECTRUM = 4
    TRANSIENTSEARCH = 5
    VLBI             = 6
    CALIBRATION      = 7

@unique
class ObsState(Enum):
    IDLE        = 0
    CONFIGURING = 1
    READY       = 2
    SCANNING    = 3
    PAUSED      = 4
    ABORTED     = 5
    FAULT       = 6
