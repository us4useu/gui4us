from dataclasses import dataclass
from typing import Sequence, Dict, Union, Tuple, Optional
from gui4us.model import StreamDataId


@dataclass(frozen=True)
class Layer2D:
    """
    2D image layer settings.

    Currently the only supported inputs are ``StreamDataId("default", i)``, where ``i`` is the pipeline
    output number.

    :param input: input id
    :param cmap: color map to use; see color map names available in matplotlib
    :param value_range: dynamic range to apply (min, max) pair
    """
    input: StreamDataId
    cmap: str
    value_range: tuple = None


@dataclass(frozen=True)
class Display2D:
    """
    2D display settings.

    :param title: display title
    :param layers: layers to display
    :param extents: physical extents: a tuple (min azimuth, max azimuth, min depth, max depth)
      Optional, if not provided, the extents will be determined from the metadata
      provided by the environemnt.
    :param ax_labels: axis labels to use; default: no labels
    """

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
    """
    Defines a location of a single display in the grid.

    :param rows: which rows should be occuped by the display
    :param columns: which columns should be occuped by the display
    :param display_id: display identifier
    """
    rows: Union[int, Tuple[int, int]]
    columns: Union[int, Tuple[int, int]]
    display_id: str = None


@dataclass(frozen=True)
class GridSpec:
    """
    Grid view layout specfication.

    This class allows to specify the non-standard way of arranging multiple
    displays presented in the GUI4us.

    Each display can occupy one or multiple cells in the grid.
    The cells occupied by which displays can be defined via the ``locations`` parameter.

    :param n_rows: number of rows
    :param n_columns: number of columns
    :param locations: grid cell - display assigments
    """
    n_rows: int
    n_columns: int
    locations: Sequence[DisplayLocation]


@dataclass(frozen=True)
class ViewCfg:
    """
    GUI4us view configuration.

    :param displays: displays to use
    :param layers: display grid layout; by default dispalys will be presented
      in a single row
    """
    displays: Sequence[Union[Display1D, Display2D]]
    grid_spec: Optional[GridSpec] = None
