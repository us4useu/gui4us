import threading
import time
import cupy as cp
from gui4us.model.common import get_image_extent

from gui4us.common import ImageMetadata, DataBuffer
from gui4us.model.model import Environment
from gui4us.cfg.environment import DatasetEnvironment
import arrus.metadata


class DatasetEnv(Environment):

    def __init__(self, cfg: DatasetEnvironment, data_buffer: DataBuffer):
        self.data, self.metadata = cfg.input["data"], cfg.input["metadata"]
        self.cfg = cfg
        self.input_nr = self.cfg.input_nr
        if self.cfg.pipeline is not None and self.input_nr is None:
            # use output 0 by default
            self.input_nr = 0
        if self.input_nr is not None:
            data = list(zip(*self.data))
            self.data = data[cfg.input_nr]
            self.metadata = [self.metadata[cfg.input_nr]]
        # Initialize Pipeline.
        self.pipeline = self.cfg.pipeline
        if self.pipeline is not None:
            if len(self.metadata) > 1:
                raise ValueError("Only a single input element can be fed "
                                 "to the provided Pipeline")
            print(self.metadata[0].input_shape)
            print(self.data[0].shape)
            self.metadata = self.pipeline.prepare(self.metadata[0])
        self.data_acq_thread = threading.Thread(target=self._main_loop)
        self.output = data_buffer
        self.is_working = False
        self.capturer = None

    def set_capturer(self, capturer):
        self.capturer = capturer
        self.capturer.set_metadata(self.metadata)

    def get_n_outputs(self):
        return len(self.metadata)

    def get_output_metadata(self, ordinal) -> ImageMetadata:
        output_grids = self.metadata[ordinal].data_description.grid
        if output_grids is None:
            # Fallback option: treat all the values as the raw delays
            output_grids = [
                arrus.metadata.RegularGridDescriptor(0, 1, n=i, unit=arrus.metadata.Units.PIXELS)
                for i in self.metadata[ordinal].input_shape
            ]
        extents = get_image_extent(output_grids)
        units = [grid.unit for grid in output_grids]
        return ImageMetadata(
            shape=self.metadata[ordinal].input_shape,
            dtype=self.metadata[ordinal].dtype,
            extents=extents,
            units=tuple(units))

    def start(self):
        self.is_working = True
        self.data_acq_thread.start()

    def stop(self):
        if self.is_working:
            self.is_working = False
            self.data_acq_thread.join()

    def close(self):
        self.stop()

    def get_settings(self):
        return {}

    def set(self, key: str, value: object):
        pass

    def _main_loop(self):
        i = 0
        size = len(self.data)
        while self.is_working:
            d = self.data[i]
            i = (i+1) % size

            if self.pipeline is not None:
                d = self.pipeline.process(cp.asarray(d))
                d = [v.get() for v in d]
            if not isinstance(d, tuple) and not isinstance(d, list):
                d = [d]
            d = tuple(d)
            self.output.put(d)
            if self.capturer.is_capturing:
                self.capturer.append(d)
            # Here should be the release.
            time.sleep(1/self.cfg.max_frame_rate)







