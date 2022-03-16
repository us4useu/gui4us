from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Layer2D:
    value_range: tuple
    cmap: str
    input: object


@dataclass(frozen=True)
class Display2D:
    title: str
    layers: Sequence[Layer2D]
