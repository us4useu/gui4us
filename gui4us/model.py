import numpy as np
import arrus
import queue
import scipy.signal
import time

from arrus.ops.us4r import (
    Scheme,
    Pulse,
    DataBufferSpec
)
from arrus.ops.imaging import (
    PwiSequence
)
from arrus.utils.imaging import (
    Pipeline,
    Transpose,
    BandpassFilter,
    Decimation,
    QuadratureDemodulation,
    EnvelopeDetection,
    LogCompression,
    Enqueue,
    ReconstructLri,
    Mean,
    Squeeze,
    FirFilter
)
from arrus.utils.us4r import (
    RemapToLogicalOrder
)
from arrus.utils.gui import (
    Display2D
)


# DEFAULT PWI sequence parameters
_TX_ANGLES = np.linspace(-10, 10, 11).tolist()  # [deg]
_TX_FREQUENCY = 6e6
_TX_N_PERIODS = 2
_TX_INVERSE = False
_PRI = 300e-6
_SRI = 50e-3
_RX_SAMPLE_START = 0
_RX_SAMPLE_END = 4096
_DOWNSAMPLING_FACTOR = 1
_IMG_START_DEPTH = 5e-3  # [m]
_IMG_PIXEL_STEP = 0.1e-3  # [m]

# APEX probe + us4R-Lite specific parameters
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
    def __init__(self, settings: dict):
        self._settings = settings.copy()

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

        # Sequence settings
        self._sequence_settings = self._settings["sequence"]
        # Required
        self._speed_of_sound = self._sequence_settings["speed_of_sound"]
        # Optional:
        self._tx_angles = self._sequence_settings.get("angles", _TX_ANGLES)
        self._rx_sample_range = (
            self._sequence_settings.get("rx_sample_range_start",
                                        _RX_SAMPLE_START),
            self._sequence_settings.get("rx_sample_range_end", _RX_SAMPLE_END),
        )
        self._tx_frequency = self._sequence_settings.get(
            "tx_frequency", _TX_FREQUENCY)
        self._tx_n_periods = self._sequence_settings.get(
            "tx_n_periods", _TX_N_PERIODS)
        self._tx_inverse = self._sequence_settings.get(
            "tx_inverse", _TX_INVERSE)
        self._pri = self._sequence_settings.get("pri", _PRI)
        self._sri = self._sequence_settings.get("pri", _SRI)
        # non-modifiable:
        self._downsampling_factor = _DOWNSAMPLING_FACTOR

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
        self._sequence = PwiSequence(
            angles=np.asarray(self._tx_angles)*np.pi/180,
            pulse=Pulse(
                center_frequency=self._tx_frequency,
                n_periods=self._tx_n_periods,
                inverse=self._tx_inverse),
            rx_sample_range=self._rx_sample_range,
            downsampling_factor=self._downsampling_factor,
            speed_of_sound=self._speed_of_sound,
            pri=self._pri, sri=self._sri,
            tgc_curve=actual_tgc_curve)

        # TODO use dequeue instead? is it thread safe?
        self._bmode_queue = queue.Queue(1)
        self._rf_queue = queue.Queue(1)

        self._fir_filter_taps = scipy.signal.firwin(64, np.array(
            [0.5, 1.5]) * self._tx_frequency, pass_zero=False,
            fs=self._sampling_frequency/self._downsampling_factor)

        self._scheme = Scheme(
            tx_rx_sequence=self._sequence,
            rx_buffer_size=2,
            output_buffer=DataBufferSpec(type="FIFO", n_elements=4),
            work_mode="HOST",
            processing=Pipeline(
                steps=(
                    RemapToLogicalOrder(),
                    Enqueue(self._rf_queue, block=False, ignore_full=True),
                    Transpose(axes=(0, 2, 1)),
                    FirFilter(self._fir_filter_taps),
                    QuadratureDemodulation(),
                    Decimation(decimation_factor=4, cic_order=2),
                    ReconstructLri(x_grid=x_grid, z_grid=z_grid),
                    Mean(axis=0),
                    EnvelopeDetection(),
                    Transpose(),
                    LogCompression(),
                    Enqueue(self._bmode_queue, block=False, ignore_full=True)
                ),
                placement="/GPU:0"
            )
        )
        # initial dynamic range
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
