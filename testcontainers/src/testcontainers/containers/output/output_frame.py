from dataclasses import dataclass
from enum import Enum, auto


class OutputType(Enum):
    STDOUT = auto()
    STDERR = auto()
    END = auto()


@dataclass
class OutputFrame:
    output_type: OutputType
    bytes: bytearray
