from dataclasses import dataclass
from typing import Sequence, Dict, Union
from gui4us.model import StreamDataId


@dataclass(frozen=True)
class Layer2D:
    """
    :param extent: image dimensions, a pair (oz_extent, ox_extent),
        each (min, max)
    """
    input: StreamDataId
    cmap: str
    value_range: tuple = None


@dataclass(frozen=True)
class Display2D:
    title: str
    layers: Sequence[Layer2D]
    extents: tuple = None
    ax_labels: tuple = None


@dataclass(frozen=True)
class Display3D:
    title: str
    input: StreamDataId


@dataclass(frozen=True)
class ViewCfg:
    displays: Dict[str, Union[Display2D, Display3D]]
