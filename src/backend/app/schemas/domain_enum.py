from enum import Enum

class DomainType(str, Enum):
    TIME = "time"
    FREQUENCY = "frequency"
    TIME_FREQUENCY = "time_frequency"
    QUALITY = "quality"
