# TODO: outputs: avoid hash computation for performance? (split into two collections?)


import queue
import gui4us.cfg
import numpy as np
import datetime
import pickle
import arrus.logging
import arrus.utils.imaging
from gui4us.settings import *
from gui4us.common import *
from arrus.ops.us4r import *
from arrus.utils.imaging import (
    Processing,
    Pipeline
)
from collections.abc import Iterable


class UltrasoundEnv:
    pass


class CaptureBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self._counter = 0
        self._data = []*self.capacity

    def append(self, data):
        if self.is_ready():
            raise queue.Full()
        self._data[self._counter] = data
        self._counter += 1

    def is_ready(self):
        return self.capacity == self._counter

    def get_current_size(self):
        return self._counter

    @property
    def data(self):
        return self._data


class Output:

    def __init__(self):
        self.callbacks = []

    def add_callback(self, func):
        self.callbacks.append(func)


class HardwareEnv(UltrasoundEnv):

    DEFAULT_LOG_FILE = "arrus.log"

    def __init__(self, cfg: gui4us.cfg.HardwareEnvironment):
        self.cfg = cfg
        self.log_file = self.cfg.log_file
        if self.log_file is None:
            self.log_file = HardwareEnv.DEFAULT_LOG_FILE
        self.log_file_level = getattr(arrus.logging, self.cfg.log_file_level,
                                      None)
        if self.log_file_level is None:
            raise ValueError(f"Unknown log file level: {self.log_file_level}")
        arrus.logging.add_log_file(self.log_file, self.log_file_level)
        self.session = arrus.Session(self.cfg.session_cfg)
        self.us4r = self.session.get_device("/Us4R:0")
        self.probe_model = self.us4r.get_probe_model()
        scheme = Scheme(
            tx_rx_sequence=self.cfg.tx_rx_sequence,
            work_mode=self.cfg.work_mode,
            processing=Processing(self.cfg.pipeline, callback=self._on_new_data)
        )
        self.metadata = self.session.upload(scheme)
        if not isinstance(self.metadata, Iterable):
            self.metadata = (self.metadata, )
        self.n_tgc_samples = self._get_number_of_tgc_samples(self.cfg.tx_rx_sequence)

        self.capture_buffer = CaptureBuffer(self.cfg.capture_buffer_capacity)
        # Do initial configuration of the system
        self.settings = self.create_settings()
        # Image dimensions
        self.img0_ox_grid, self.img0_oz_grid, _, _ = self._determine_image_metadata(ordinal=0)
        # TGC
        # determine tgc curve sampling points.
        for setting in self.settings:
            self.set(setting.id, setting.init_value)
        self.is_capturing = False  # TODO state_graph
        self.outputs = {
            "main_events": Output(),
            "capture_buffer_events": Output()
        }
        for i in range(len(self.metadata)):
            self.outputs[i] = Output()

    def get_image_metadata(self, ordinal):
        image_metadata = self._determine_image_metadata(ordinal)
        x_grid, z_grid, units, ids = image_metadata
        return ImageMetadata(
            shape=self.metadata[ordinal].input_shape,
            dtype=self.metadata[ordinal].dtype,
            extents=self._get_image_extent((x_grid, z_grid)),
            units=units,
            ids=ids)

    def start(self):
        self.session.start_scheme()

    def stop(self):
        self.session.stop_scheme()

    def close(self):
        self.session.stop_scheme()
        self.session.close()

    def set(self, key: str, value: object):
        method = getattr(self, f"set_{key}")
        method(value)

    def start_capture(self):
        self.capture_buffer = CaptureBuffer(self.cfg.capture_buffer_capacity)
        self.is_capturing = True

    def stop_capture(self):
        """
        Stop manually capturing data.
        """
        self.is_capturing = False
        for callback in self.outputs["capture_buffer_events"].callbacks:
            callback((self.capture_buffer.get_current_size(), True))

    def save_capture(self, filepath):
        if self.capture_buffer.get_current_size() == 0:
            raise ValueError("Cannot save empty buffer")
        pickle.dump({"metadata": self.metadata,
                     "data": self.capture_buffer.data},
                    open(filepath, "wb"))

    def set_output_callback(self, output_key, func):
        self.outputs[output_key].add_callback(func)

    def create_settings(self):
        return [
            Setting(
                id="tx_voltage",
                data_type="int",
                domain=ContinuousRange(0, 90, default_step=5),
                init_value=self.cfg.initial_tx_voltage,
                unit="V",
            ),
            Setting(
                id="gain",
                data_type="float",
                domain=ContinuousRange(14, 54, default_step=1),
                init_value=self.cfg.initial_gain,
                unit="dB"
            )
        ]

    def get_settings(self):
        return self.settings

    def set_tx_voltage(self, value):
        self.us4r.set_hv_voltage(value)

    def set_gain(self, value):
        tgc_curve = [value]*self.n_tgc_samples
        self.us4r.set_tgc(tgc_curve)

    def _get_number_of_tgc_samples(self, tx_rx_sequence):
        start, end = tx_rx_sequence.rx_sample_range
        return round(end/(75/tx_rx_sequence.downsampling_factor))

    def _determine_image_metadata(self, ordinal):
        # TODO the output grid dimensions should be a part of the metadata
        # returned by arrus package
        if isinstance(self.cfg.pipeline, arrus.utils.imaging.Pipeline)\
                and ordinal == 0:
            # Try to find ScanConverter or LRI reconstruction step
            # Very simple logic that should be replaced with some
            grid_steps = [step for step in self.cfg.pipeline.steps
                          if hasattr(step, "x_grid") and hasattr(step, "z_grid")
                          ]
            if len(grid_steps) > 1:
                grid_step = grid_steps[-1]
                return grid_step.x_grid, grid_step.z_grid, ("m", "m"), ("OX", "OZ")

        # otherwise: very simple fallback option
        input_shape = self.metadata[ordinal].input_shape
        if len(input_shape) != 2:
            raise ValueError("The pipeline's output should be a 2D image!")
        n_points_x, n_points_z = input_shape
        x_grid = np.arange(0, n_points_x)
        z_grid = np.arange(0, n_points_z)
        return x_grid, z_grid, ("", ""), ("", "")

    def _get_image_extent(self, imaging_grids):
        ox_grid, oz_grid = imaging_grids
        return ((np.min(ox_grid), np.max(ox_grid)),
                (np.min(oz_grid), np.max(oz_grid)))

    def _on_new_data(self, elements):
        try:
            is_capturing = self.is_capturing
            if is_capturing:
                out_data = []
            for i, element in enumerate(elements):
                output = self.outputs[i]
                for callback in output.callbacks:
                    callback(element.data)
                    if is_capturing:
                        out_data.append(element.data.copy())
                    element.release()
            if is_capturing:
                capture_buffer_output = self.outputs["capture_buffer_events"]
                for callback in capture_buffer_output.callbacks:
                    callback((self.capture_buffer.capacity,
                              self.capture_buffer.is_ready()))
        except Exception as e:
            print(f"Exception: {type(e)}")
        except:
            print("Unknown exception")


