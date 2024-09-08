from dataclasses import dataclass
from typing import Sequence, Dict, Union, Tuple, Optional
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
class Display1D:
    """
    :param labels: curve labels
    """
    title: str
    input: StreamDataId
    ax_labels: tuple = None
    value_range: tuple = None
    labels: Sequence[str] = None


@dataclass(frozen=True)
class DisplayLocation:
    rows: Union[int, Tuple[int, int]]
    columns: Union[int, Tuple[int, int]]
    display_id: str = None


@dataclass(frozen=True)
class GridSpec:
    n_rows: int
    n_columns: int
    locations: Sequence[DisplayLocation]


@dataclass(frozen=True)
class ViewCfg:
    displays: Sequence[Union[Display1D, Display2D]]
    grid_spec: Optional[GridSpec] = None
