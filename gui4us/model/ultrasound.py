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


class UltrasoundEnv:
    pass


class CaptureBuffer:
    def __init__(self, size):
        self.size = size
        self._counter = 0
        self._data = []

    def append(self, data):
        if self.is_ready():
            raise queue.Full()
        self._data.append(data)
        self._counter += 1

    def is_ready(self):
        return self.size == self._counter

    def __len__(self):
        return

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
                                      default=None)
        if self.log_file_level is None:
            raise ValueError(f"Unknown log file level: {self.log_file_level}")
        arrus.logging.add_log_file(self.log_file, self.log_file_level)
        self.session = arrus.Session(self.cfg.session_cfg)
        self.us4r = self.session.get_device("/Us4R:0")
        self.probe_model = self.us4r.get_probe_model()

        scheme = Scheme(
            tx_rx_sequence=self.cfg.tx_rx_sequence,
            work_mode=self.cfg.work_mode,
            processing=Processing(self.cfg.pipeline, callback=self.__on_new_data)
        )

        self.metadata = self.session.upload(scheme)
        self.capture_buffer = CaptureBuffer(self.cfg.capture_buffer_capacity)
        # Do initial configuration of the system
        self.settings = self.create_settings()
        # Image dimensions
        self.img0_ox_grid, self.img0_oz_grid, _, _ = self.__determine_image_metadata(ordinal=0)
        # TGC
        # determine tgc curve sampling points.
        self.tgc_curve_sampling_depths = self.__determine_tgc_sampling_depths(
            (self.img0_ox_grid, self.img0_oz_grid)
        )
        for setting in self.settings:
            self.set(setting.id, setting.init_value)
        self.is_capturing = False  # TODO state_graph
        self.outputs = [Output()]*(self.metadata+1) # n pipeline outputs + 1 for the capture data
        self.capture_buffer_ordinal = -1 # the last one

    def get_image_metadata(self, ordinal):
        image_metadata = self.__determine_image_metadata(ordinal)
        x_grid, z_grid, units, ids = image_metadata[0]

        return ImageMetadata(
            shape=self.metadata[ordinal].input_shape,
            dtype=self.metadata[ordinal].dtype,
            extents=self.__get_image_extent((x_grid, z_grid)),
            units=units,
            ids=ids
        )

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
        self.is_capturing = False
        for callback in self.outputs[self.capture_buffer_ordinal].callbacks:
            callback((self.capture_buffer.size, True))

    def save_capture(self, filepath):
        if len(self.capture_buffer) == 0:
            raise ValueError("Cannot save empty buffer")
        pickle.dump({"metadata": self.metadata,
                     "data": self.capture_buffer.data},
                    open(filepath, "wb"))

    def set_output_callback(self, output_number: int, func):
        self.callbacks[output_number].append(func)

    def set_capture_state_callback(self, func):
        self.capture_state_callbacks.append(func)

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
                init_value=self.cfg.initial_tgc_curve,
                unit="dB"
            )
        ]

    def set_tx_voltage(self, voltage: int):
        self.us4r.set_hv_voltage(voltage)

    def set_tgc_curve(self, tgc_curve):
        if self.cfg.n_tgc_curve_points == 1:
            # single scalar value
            tgc_curve = [tgc_curve, tgc_curve]
        actual_tgc_curve = self.__interpolate_to_device_tgc(tgc_curve)
        self.us4r.set_tgc(actual_tgc_curve)

    def __determine_tgc_sampling_depths(self, imaging_grids):
        n_tgc_curve_points = self.cfg.n_tgc_curve_points
        if n_tgc_curve_points == 1:
            n_tgc_curve_points = 2
        _, oz_extent = self.__get_image_extent(imaging_grids)
        oz_min, oz_max = oz_extent
        return np.linspace(start=oz_min, stop=oz_max, num=n_tgc_curve_points)

    def __interpolate_to_device_tgc(self, tgc_curve):
        # TODO speed of sound should be determined based on the medium object
        c = self.cfg.scheme.tx_rx_sequence.speed_of_sound
        # TODO should be determined based on raw_sequence parameters
        downsampling_factor = self.cfg.scheme.tx_rx_sequence.downsampling_factor
        fs = self.us4r.sampling_frequency
        end_sample = self.cfg.scheme.tx_rx_sequence.rx_sample_range[1]

        in_sampling_depths = self.tgc_curve_sampling_depths
        output_sampling_depths = np.arange(
            start=round(150/downsampling_factor), stop=end_sample,
            step=round(75/downsampling_factor))/fs*c
        return np.interp(output_sampling_depths, in_sampling_depths,
                     tgc_curve)

    def __determine_image_metadata(self, ordinal):
        # TODO the output grid dimensions should be a part of the metadata
        # returned by arrus package
        scheme = self.cfg.scheme
        if isinstance(scheme.processing, arrus.utils.imaging.Pipeline)\
                and ordinal == 0:
            # Try to find ScanConverter or LRI reconstruction step
            # Very simple logic that should be replaced with some
            grid_steps = [step for step in scheme.processing.steps
                          if hasattr(step, "x_grid") and hasattr(step, "z_grid")
                          ]
            grid_step = grid_steps[-1]
            return grid_step.x_grid, grid_step.z_grid, ("m", "m"), ("OX", "OZ")
        else:
            # Very simple fallback option
            input_shape = self.metadata[ordinal].input_shape
            if len(input_shape) != 2:
                raise ValueError("The pipeline's output should be a 2D image!")
            n_points_x, n_points_z = input_shape
            x_grid = np.arange(0, n_points_x)
            z_grid = np.arange(0, n_points_z)
            return x_grid, z_grid, ("", ""), ("", "")

    def __get_image_extent(self, imaging_grids):
        ox_grid, oz_grid = imaging_grids
        return ((np.min(ox_grid), np.max(ox_grid)),
                (np.min(oz_grid), np.max(oz_grid)))

    def __on_new_data(self, elements):
        try:
            for i, element in enumerate(elements):
                for callback in self.outputs[i].callbacks:
                    callback(element.data)
                    element.release()
        except Exception as e:
            print(f"Exception: {type(e)}")
        except:
            print("Unknown exception")


