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
from gui4us.model.model import Environment
from gui4us.model.common import get_image_extent


class Output:
    def __init__(self):
        self.callbacks = []

    def add_callback(self, func):
        self.callbacks.append(func)


class HardwareEnv(Environment):
    DEFAULT_LOG_FILE = "arrus.log"

    def __init__(self, cfg: gui4us.cfg.HardwareEnvironment, data_buffer: DataBuffer):
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
        self.session = arrus.Session(self.cfg.session_cfg, medium=cfg.medium)
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
            self.metadata = (self.metadata,)
        # PREPARE SETTINGS.
        # NOTE: the below code should replaced soon by the possibility to
        # read settable session parameters.
        # TGC: determine sampling points based on the provided configuration
        # TODO there should be a function in arrus that allows to determine
        # TGC sampling points for a given tgc sampling step
        # TODO consider using grid determined by RF sampling depth
        z_grid = self._determine_image_z_grid(0, self.cfg)
        self.tgc_sampling = self._get_tgc_sampling_points(z_grid, self.cfg)
        self.device_tgc_sampling_points = self._get_device_tgc_sampling_points(
            metadata=self.metadata[0], medium=cfg.medium)
        # Prepare initial configuration.
        self.settings = self.create_settings()
        for setting in self.settings:
            self.set(setting.id, setting.init_value)
        self.output_buffer = data_buffer

    def set_capturer(self, capturer):
        self.capturer = capturer
        self.capturer.set_metadata(self.metadata)

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
        self.session.start_scheme()

    def stop(self):
        self.session.stop_scheme()

    def close(self):
        self.session.stop_scheme()
        self.session.close()

    def set(self, key: str, value: object):
        method = getattr(self, f"set_{key}")
        method(value)

    def create_settings(self):
        # TODO move this to arrus.session.get_parameters
        n_tgc_samples = len(self.tgc_sampling)
        tgc_sampling_label = tuple(str(v * 1e3) for v in self.tgc_sampling)
        return [
            Setting(
                id="tx_voltage",
                data_type="int",
                # TODO determine based on the probe definition
                domain=ContinuousRange(5, 60,
                                       default_step=self.cfg.tx_voltage_step),
                init_value=self.cfg.tx_voltage,
                unit="V",
                shape=(1,)
            ),
            Setting(
                id="tgc",
                data_type="float",
                # TODO determine based on the LNA and PGA values
                domain=ContinuousRange(14, 54, default_step=self.cfg.tgc_step),
                init_value=self._convert_tgc_to_ndarray(self.cfg.tgc_curve),
                unit="dB",
                shape=(n_tgc_samples,),
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
            return intercept + slope * self.tgc_sampling
        elif isinstance(value, Iterable):
            return np.asarray(value)
        elif not isinstance(value, (int, float)):
            # Treat it as a single integer value
            return np.asarray([value] * len(self.tgc_sampling))
        else:
            raise ValueError("Unhandled type of tgc curve instance: "
                             f"{type(value)}")

    def _get_tgc_sampling_points(self, z_grid, cfg):
        oz_min, oz_max = np.min(z_grid), np.max(z_grid)
        return np.arange(oz_min, oz_max, step=cfg.tgc_sampling)

    def get_speed_of_sound(self, metadata, cfg):
        if hasattr(metadata.context.sequence, "speed_of_sound"):
            return metadata.context.sequence.speed_of_sound
        else:
            if cfg.medium is None:
                raise ValueError("The speed of sound must be provided at as a part of "
                                 "TX/RX sequence description or as a description "
                                 "of medium.")
            else:
                return cfg.medium.speed_of_sound

    def _get_device_tgc_sampling_points(self, metadata, medium):
        # TODO verify every tx/rx has the same position
        seq = metadata.context.raw_sequence
        downsampling_factor = seq.ops[0].rx.downsampling_factor
        end_sample = seq.ops[0].rx.sample_range[1]
        fs = metadata.context.device.sampling_frequency
        c = self.get_speed_of_sound(metadata, self.cfg)
        return np.arange(
            start=round(400 / downsampling_factor),
            stop=end_sample,
            step=round(150 / downsampling_factor)) / fs * c / 2

    def _determine_image_z_grid(self, ordinal, cfg):
        grid = self.metadata[ordinal].data_description.grid
        fs = self.metadata[ordinal].data_description.sampling_frequency
        n_samples = self.metadata[ordinal].input_shape[-2]  # Rows
        if grid is None:
            # determine basing on the max depth and sampling frequency
            grid = arrus.metadata.RegularGridDescriptor(
                start=0, step=1, n=n_samples,
                unit=arrus.metadata.Units.PIXELS)
        if grid.unit == arrus.metadata.Units.PIXELS:
            grid = arrus.metadata.RegularGridDescriptor(
                start=0, step=1 / fs, n=n_samples,
                unit=arrus.metadata.Units.SECONDS
            )
        if grid.unit == arrus.metadata.Units.SECONDS:
            c = self.get_speed_of_sound(self.metadata[0], cfg)
            return grid.points * c / 2
        else:
            return grid.points

    def _get_image_extent(self, imaging_grids):
        ox_grid, oz_grid = imaging_grids
        return ((np.min(ox_grid), np.max(ox_grid)),
                (np.min(oz_grid), np.max(oz_grid)))

    def _on_new_data(self, elements):
        try:
            out_data = []
            for element in elements:
                out_data.append(element.data.copy())
                element.release()

            if self.capturer.is_capturing:
                self.capturer.append(out_data)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
        except:
            print("Unknown exception")
