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


class Model:
    def __init__(self, cfg_path):
        self._settings = self.load_settings_module(cfg_path)

        self._settings = {**self._settings, **{
            "min_voltage": _PROBE_MIN_TX_VOLTAGE,  # [V]
            "max_voltage": _PROBE_MAX_TX_VOLTAGE,  # [V]
            "tgc_step": _TGC_SAMPLING_STEP,  # [m]
            "min_tgc": _MIN_TGC,  # [dB]
            "max_tgc": _MAX_TGC,  # [dB]
        }}

        # General settings
        self._sampling_frequency = _SAMPLING_FREQUENCY
        self._initial_voltage = self._settings["tx_voltage"]
        self._dynamic_range_min = self._settings["dynamic_range_min"]
        self._dynamic_range_max = self._settings["dynamic_range_max"]
        self._tgc_start = self._settings["tgc_start"]
        self._tgc_slope = self._settings["tgc_slope"]
        self._img_start_depth = self._settings.get(
            "img_start_depth", _IMG_START_DEPTH)

    def load_settings_module(self, settings_path):
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def start(self):
        pass

    @property
    def settings(self):
        return self._settings

    def get_bmode(self):
        raise ValueError("Abstract class")

    def get_rf(self):
        raise ValueError("Abstract class")

    def set_tgc_curve(self, tgc_curve: np.ndarray):
        raise ValueError("Abstract class")

    def set_dr_min(self, dr_min: float):
        raise ValueError("Abstract class")

    def set_dr_max(self, dr_max: float):
        raise ValueError("Abstract class")

    def set_tx_voltage(self, voltage: float):
        raise ValueError("Abstract class")

    def close(self):
        raise ValueError("Abstract class")


def compute_tgc_curve_linear(oz_min, oz_max, tgc_start, tgc_slope,
                             tgc_sampling_step):
    tgc_sampling_depths = np.arange(oz_min, oz_max, step=tgc_sampling_step)
    tgc_curve = tgc_slope * (tgc_sampling_depths - oz_min) + tgc_start
    return tgc_sampling_depths, tgc_curve


def interpolate_to_device_tgc(input_sampling_depths, input_tgc_values,
                              end_sample, downsampling_factor, fs, c):
    output_sampling_depths = np.arange(
        start=round(150/downsampling_factor), stop=end_sample,
        step=round(75/downsampling_factor))/fs*c
    return np.interp(output_sampling_depths, input_sampling_depths,
                     input_tgc_values)


class ArrusModel(Model):

    def __init__(self, settings: dict):
        super().__init__(settings)
        arrus.logging.add_log_file("arrus.log", arrus.logging.DEBUG)

        self._session = arrus.Session("us4r.prototxt")
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
        self._tgc_sampling_depths, tgc_curve = compute_tgc_curve_linear(
            oz_min, oz_max,
            tgc_start=self._settings["tgc_start"],
            tgc_slope=self._settings["tgc_slope"],
            tgc_sampling_step=_TGC_SAMPLING_STEP)
        actual_tgc_curve = interpolate_to_device_tgc(
            self._tgc_sampling_depths, tgc_curve, self._rx_sample_range[1],
            self._downsampling_factor,
            self._sampling_frequency/self._downsampling_factor,
            self._speed_of_sound)

        # Update settings with the TGC curve
        self._settings["tgc_curve"] = tgc_curve
        self._settings["tgc_sampling_depths"] = self._tgc_sampling_depths

        # Determine sequence
        self._scheme = self._cf

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
        actual_tgc_curve = interpolate_to_device_tgc(
            self._tgc_sampling_depths, tgc_curve, self._rx_sample_range[1],
            self._downsampling_factor,
            self._sampling_frequency/self._downsampling_factor,
            self._speed_of_sound)
        self._us4r.set_tgc(actual_tgc_curve)

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


class MockedModel(Model):

    def __init__(self, lri_data, settings: dict):
        super().__init__(settings)
        self._rf_data = lri_data
        _, _, n_pix_ox, n_pix_oz = lri_data.shape
        self._rf_data_source = CineloopDataSource(self._rf_data)
        self._bmode_data = np.sum(self._rf_data, axis=1)
        self._bmode_data = 20 * np.log10(np.abs(self._bmode_data))
        self._bmode_data = np.transpose(self._bmode_data, (0, 2, 1))
        self._bmode_data_source = CineloopDataSource(self._bmode_data)

        self._settings = {**self._settings, **{
            "image_extent_ox": [-19e-3, 19e-3],
            "image_extent_oz": [10e-3, 45e-3],
            "n_pix_ox": n_pix_ox,
            "n_pix_oz": n_pix_oz
        }}
        # Compute TGC samples, for a given TGC step.
        tgc_sampling_depths, tgc_curve = compute_tgc_curve_linear(
            oz_min=self._settings["image_extent_oz"][0],
            oz_max=self._settings["image_extent_oz"][1],
            tgc_start=self._settings["tgc_start"],
            tgc_slope=self._settings["tgc_slope"],
            tgc_sampling_step=self._settings["tgc_step"]
        )
        self._settings["tgc_sampling_depths"] = tgc_sampling_depths
        self._settings["tgc_curve"] = tgc_curve
        self._dr_min = self._settings["dynamic_range_min"]
        self._dr_max = self._settings["dynamic_range_max"]

    def start(self):
        print("Starting")

    @property
    def settings(self):
        return self._settings

    def get_bmode(self):
        bmode = self._bmode_data_source.get()
        dr_min = self._dr_min
        dr_max = self._dr_max
        bmode = np.clip(bmode, dr_min, dr_max)
        return (bmode, dr_min, dr_max)

    def get_rf(self):
        return self._rf_data_source.get()

    def set_tgc_curve(self, tgc_curve: np.ndarray):
        print(f"Setting TGC: {tgc_curve}")

    def set_dr_min(self, dr_min: float):
        self._dr_min = dr_min

    def set_dr_max(self, dr_max: float):
        self._dr_max = dr_max

    def set_tx_voltage(self, voltage: float):
        print(f"Setting TX voltage: {voltage}")

    def close(self):
        print("Closing model")
