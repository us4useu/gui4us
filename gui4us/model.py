import numpy as np
import arrus
import queue
import scipy.signal
import time
import importlib
import sys


# APEX probe + us4R-Lite specific parameters
# TODO read the below information using ARRUS
_PROBE_MIN_TX_VOLTAGE = 5  # [V]
_PROBE_MAX_TX_VOLTAGE = 50  # [V]
_MIN_TGC = 14
_MAX_TGC = 54
_TGC_SAMPLING_STEP = 5e-3  # [m]
_SAMPLING_FREQUENCY = 65e6


class DataSource:

    def get(self):
        raise ValueError("NYI")


class CineloopDataSource(DataSource):

    def __init__(self, collection):
        self.collection = collection
        self._counter = 0

    def get(self):
        result = self.collection[self._counter]
        self._counter = (self._counter + 1) % len(self.collection)
        return result


class ArrusModel(Model):

    def __init__(self, settings_path: str):
        super().__init__(settings_path)
        arrus.logging.add_log_file("arrus.log", arrus.logging.DEBUG)
        self._session = arrus.Session(self.settings.SESSION_CFG_PATH)
        self._us4r = self._session.get_device("/Us4R:0")
        self._probe_model = self._us4r.get_probe_model()
        x_grid, z_grid = self._compute_image_grid()
        # Update settings with image extent
        self._settings["image_extent_ox"] = [np.min(x_grid), np.max(x_grid)]
        self._settings["image_extent_oz"] = [np.min(z_grid), np.max(z_grid)]
        self._settings["n_pix_ox"] = len(x_grid)
        self._settings["n_pix_oz"] = len(z_grid)
        # Compute TGC curve
        oz_min, oz_max = self._settings["image_extent_oz"]
        # Update settings with the TGC curve
        self._settings["tgc_curve"] = tgc_curve
        self._settings["tgc_sampling_depths"] = self._tgc_sampling_depths
        # Determine sequence
        self._scheme = self.settings.SCHEME
        self._dr_min = self._settings["dynamic_range_min"]
        self._dr_max = self._settings["dynamic_range_max"]

    def start(self):
        # Set initial values
        self.set_tx_voltage(self._initial_voltage)
        # Upload sequence on the us4r-lite device.
        self._buffer, self._const_metadata = self._session.upload(self._scheme)
        self._session.start_scheme()

    def get_bmode(self):
        bmode = self._bmode_queue.get()
        dr_min = self._dr_min
        dr_max = self._dr_max
        bmode = np.clip(bmode, dr_min, dr_max)
        return bmode, dr_min, dr_max

    def get_rf(self):
        return self._rf_queue.get()

    def set_tgc_curve(self, tgc_curve: np.ndarray):
        actual_tgc_curve = self._interpolate_to_device_tgc(
            self._tgc_sampling_depths, tgc_curve)
        self._us4r.set_tgc(actual_tgc_curve)

    def _interpolate_to_device_tgc(self, sampling_depths, tgc_values):
        seq = self._scheme.tx_rx_sequence
        downsampling_factor=seq.downsampling_factor
        _, end_sample = seq.rx_sample_range
        c = seq.speed_of_sound
        fs = self._us4r.sampling_frequency
        out_sampling_depths = np.arange(
            start=round(150 / downsampling_factor), stop=end_sample,
            step=round(75 / downsampling_factor)) / fs * c
        return np.interp(out_sampling_depths, sampling_depths, tgc_values)

    def set_dr_min(self, dr_min: float):
        self._dr_min = dr_min

    def set_dr_max(self, dr_max: float):
        self._dr_max = dr_max

    def set_tx_voltage(self, voltage: float):
        self._us4r.set_hv_voltage(voltage)

    def close(self):
        self._session.stop_scheme()

    def _compute_image_grid(self):
        # OZ
        c = self._speed_of_sound
        fs = _SAMPLING_FREQUENCY/self._downsampling_factor
        max_depth = (c/fs)*self._rx_sample_range[1]/2
        z_grid = np.arange(self._img_start_depth, max_depth,
                           step=_IMG_PIXEL_STEP)
        # OX
        n_elements = self._probe_model.n_elements
        pitch = self._probe_model.pitch
        ox_l = -(n_elements-1)/2*pitch
        ox_r = (n_elements-1)/2*pitch
        x_grid = np.arange(ox_l, ox_r, step=_IMG_PIXEL_STEP)
        return x_grid, z_grid



