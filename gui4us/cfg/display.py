from dataclasses import dataclass
from typing import Sequence, Dict


@dataclass(frozen=True)
class Layer2D:
    value_range: tuple
    cmap: str
    input: object


@dataclass(frozen=True)
class Display2D:
    title: str
    layers: Sequence[Layer2D]


@dataclass(frozen=True)
class ViewCfg:
    display_cfg: Dict[str, Display2D]
