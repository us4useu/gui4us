import queue
import numpy as np
from dataclasses import dataclass
import typing
import multiprocessing as mp


EventQueue = mp.Queue


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
    ids: tuple = None


class DataBuffer:

    def __init__(self, size=0):
        self.size = size
        self.queue = mp.Queue(self.size)

    def get(self):
        return self.queue.get()

    def put(self, data):
        self.queue.put(data)

    def try_put(self, data):
        try:
            self.queue.put_nowait(data)
        except queue.Full:
            pass




