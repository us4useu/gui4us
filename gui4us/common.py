import queue
import numpy as np
from dataclasses import dataclass
import typing


EventQueue = queue.Queue


@dataclass(frozen=True)
class ImageMetadata:
    """
    :param shape: (number of pixels OZ, number of pixels OX)
    :param dtype: image data type, acceptable: float32
    :param extent: (extent_oz, extent_ox), in the given units, extent is a pair
       (min, max)
    :param units: (height units, width units)
    :param id: (height label id, width label id)
    """
    shape: tuple
    dtype: str
    extents: tuple
    units: tuple
    ids: tuple




