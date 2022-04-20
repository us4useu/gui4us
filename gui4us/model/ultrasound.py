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
import traceback



class UltrasoundEnv:
    pass


class CaptureBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self._counter = 0
        self._data = [None]*self.capacity

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
        # LOGGING.
        self.log_file = self.cfg.log_file
        if self.log_file is None:
            self.log_file = HardwareEnv.DEFAULT_LOG_FILE
        self.log_file_level = getattr(arrus.logging, self.cfg.log_file_level,
                                      None)
        if self.log_file_level is None:
            raise ValueError(f"Unknown log file level: "
                             f"{self.cfg.log_file_level}")
        arrus.logging.add_log_file(self.log_file, self.log_file_level)
        # START AND CONFIGURE NEW SESSION.
        self.session = arrus.Session(self.cfg.session_cfg)
        self.us4r = self.session.get_device("/Us4R:0")
        self.probe_model = self.us4r.get_probe_model()
        scheme = Scheme(
            tx_rx_sequence=self.cfg.tx_rx_sequence,
            rx_buffer_size=self.cfg.rx_buffer_size,
            output_buffer=DataBufferSpec(type="FIFO",
                                         n_elements=self.cfg.host_buffer_size),
            work_mode=self.cfg.work_mode,
            processing=Processing(self.cfg.pipeline, callback=self._on_new_data)
        )
        self.metadata = self.session.upload(scheme)
        if not isinstance(self.metadata, Iterable):
            self.metadata = (self.metadata, )
        # PREPARE SETTINGS.
        # NOTE: the below code should replaced soon by the possibility to
        # read settable session parameters.
        # TGC: determine sampling points based on the provided configuration
        # TODO there should be a function in arrus that allows to determine
        # TGC sampling points for a given tgc sampling step
        # TODO consider using grid determined by RF sampling depth
        _, self.img0_oz_grid, _, _ = self._determine_image_metadata(ordinal=0)
        self.tgc_sampling = self._get_tgc_sampling_points(self.cfg)
        self.device_tgc_sampling_points = self._get_device_tgc_sampling_points(
            metadata=self.metadata[0])
        # Prepare initial configuration.
        self.settings = self.create_settings()
        for setting in self.settings:
            self.set(setting.id, setting.init_value)
        # OUTPUTS
        # Set environment observation outputs.
        self.outputs = {
            "main_events": Output(),
            "capture_buffer_events": Output()
        }
        for i in range(len(self.metadata)):
            self.outputs[f"out_{i}"] = Output()
        self.is_capturing = False
        self.capture_buffer = CaptureBuffer(self.cfg.capture_buffer_capacity)

    def get_image_metadata(self, ordinal):
        image_metadata = self._determine_image_metadata(ordinal)
        x_grid, z_grid, units, ids = image_metadata
        return ImageMetadata(
            shape=self.metadata[ordinal].input_shape,
            dtype=self.metadata[ordinal].dtype,
            extents=self._get_image_extent((z_grid, x_grid)),
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

    def clear_capture(self):
        self.is_capturing = False

    def stop_capture(self):
        """
        Stop manually capturing data.
        """
        self.is_capturing = False
        print("Stopping capture")
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
        n_tgc_samples = len(self.tgc_sampling)
        tgc_sampling_label = tuple(str(v*1e3) for v in self.tgc_sampling)
        return [
            Setting(
                id="tx_voltage",
                data_type="int",
                # TODO determine based on the probe definition
                domain=ContinuousRange(5, 90,
                                       default_step=self.cfg.tx_voltage_step),
                init_value=self.cfg.tx_voltage,
                unit="V",
                shape=(1, )
            ),
            Setting(
                id="tgc",
                data_type="float",
                # TODO determine based on the LNA and PGA values
                domain=ContinuousRange(14, 54, default_step=self.cfg.tgc_step),
                init_value=self._convert_tgc_to_ndarray(self.cfg.tgc_curve),
                unit="dB",
                shape=(n_tgc_samples, ),
                label=tgc_sampling_label
            )
        ]

    def get_settings(self):
        return self.settings

    def set_tx_voltage(self, value):
        self.us4r.set_hv_voltage(value)

    def set_tgc(self, value):
        """
        :param value: a list of values
        """
        # y (values)
        # TODO the below conversion and parameters should be done in arrus
        value = self._convert_tgc_to_ndarray(value)
        tgc_curve = np.interp(self.device_tgc_sampling_points,
                              self.tgc_sampling, value)
        self.us4r.set_tgc(tgc_curve)

    def _convert_tgc_to_ndarray(self, value):
        if isinstance(value, gui4us.cfg.LinearFunction):
            intercept = value.intercept
            slope = value.slope
            return intercept + slope*self.tgc_sampling
        elif isinstance(value, Iterable):
            return np.asarray(value)
        elif not isinstance(value, (int, float)):
            # Treat it as a single integer value
            return np.asarray([value]*len(self.tgc_sampling))
        else:
            raise ValueError("Unhandled type of tgc curve instance: "
                             f"{type(value)}")

    def _get_tgc_sampling_points(self, cfg):
        oz_min, oz_max = np.min(self.img0_oz_grid), np.max(self.img0_oz_grid)
        return np.arange(oz_min, oz_max, step=cfg.tgc_sampling)

    def _get_device_tgc_sampling_points(self, metadata):
        # TODO verify every tx/rx has the same position
        seq = metadata.context.raw_sequence
        downsampling_factor = seq.ops[0].rx.downsampling_factor
        end_sample = seq.ops[0].rx.sample_range[1]
        fs = metadata.context.device.sampling_frequency
        c = metadata.context.sequence.speed_of_sound
        return np.arange(
            start=round(150/downsampling_factor),
            stop=end_sample,
            step=round(75/downsampling_factor))/fs*c

    def _determine_image_metadata(self, ordinal):
        # TODO the output grid dimensions should be a part of the arrus metadata
        if isinstance(self.cfg.pipeline, arrus.utils.imaging.Pipeline)\
                and ordinal == 0:
            grid_steps = [step for step in self.cfg.pipeline.steps
                          if hasattr(step, "x_grid") and hasattr(step, "z_grid")
                          ]
            if len(grid_steps) > 0:
                grid_step = grid_steps[-1]
                return grid_step.x_grid, \
                       grid_step.z_grid, \
                       ("m", "m"), \
                       ("OZ", "OX")

        # otherwise: very simple fallback option: treat the data as raw
        # channel data
        input_shape = self.metadata[ordinal].input_shape
        if len(input_shape) != 2:
            raise ValueError("The pipeline's output should be a 2D image!")
        pitch = self.metadata[ordinal].context.device.probe.model.pitch
        fs = self.metadata[ordinal].data_description.sampling_frequency
        n_points_x, n_points_z = input_shape
        x_grid = np.arange(0, n_points_x)*pitch
        z_grid = np.arange(0, n_points_z)/fs
        return x_grid, z_grid, ("s", "m"), ("OZ", "OX")

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
                output = self.outputs[f"out_{i}"]
                for callback in output.callbacks:
                    callback(element.data)
                    if is_capturing:
                        out_data.append(element.data.copy())
                    element.release()
            if is_capturing:
                self.capture_buffer.append(out_data)
                capture_buffer_output = self.outputs["capture_buffer_events"]
                if self.capture_buffer.is_ready():
                    self.stop_capture()
                else:
                    for callback in capture_buffer_output.callbacks:
                        callback((self.capture_buffer.get_current_size(), False))
        except Exception as e:
            print(e)
            print(traceback.format_exc())
        except:
            print("Unknown exception")


