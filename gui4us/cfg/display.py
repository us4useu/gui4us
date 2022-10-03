from dataclasses import dataclass
from typing import Sequence, Dict


@dataclass(frozen=True)
class Layer2D:
    """
    :param extent: image dimensions, a pair (oz_extent, ox_extent),
        each (min, max)
    """
    cmap: str
    input: object
    value_range: tuple = None
    extent: tuple = None
    ax_labels: tuple = None
    units: tuple = None


@dataclass(frozen=True)
class Display2D:
    title: str
    layers: Sequence[Layer2D]


@dataclass(frozen=True)
class ViewCfg:
    displays: Dict[str, Display2D]
