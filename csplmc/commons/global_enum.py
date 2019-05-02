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

