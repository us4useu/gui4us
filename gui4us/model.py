import numpy as np
import arrus
import queue
import scipy.signal
from collections import deque

from arrus.ops.us4r import (
    Scheme,
    Pulse,
    DataBufferSpec
)
from arrus.ops.imaging import (
    StaSequence
)
from arrus.utils.imaging import (
    Pipeline,
    Operation,
    Transpose,
    Enqueue,
    FirFilter,
    Sum,
    Squeeze,
    Lambda,
    SelectFrames
)
from arrus.utils.us4r import (
    RemapToLogicalOrder
)

# DEFAULT PWI sequence parameters
_TX_FREQUENCY = 6e6
_TX_N_PERIODS = 2
_TX_INVERSE = False
_PRI = 300e-6
_SRI = 50e-3
_RX_SAMPLE_START = 0
_RX_SAMPLE_END = 4096
_DOWNSAMPLING_FACTOR = 1
_IMG_START_DEPTH = 0e-3  # [m]
_IMG_PIXEL_STEP = 0.1e-3  # [m]

# APEX probe + us4R-Lite specific parameters
_PROBE_MIN_TX_VOLTAGE = 5  # [V]
_PROBE_MAX_TX_VOLTAGE = 90  # [V]
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
        self._tgc_start = self._settings["tgc_start"]
        self._img_start_depth = self._settings.get("img_start_depth", _IMG_START_DEPTH)

        # Sequence settings
        self._sequence_settings = self._settings["sequence"]
        # Required
        self._speed_of_sound = self._sequence_settings["speed_of_sound"]
        # Optional:
        self._rx_sample_range = (
            self._sequence_settings.get("rx_sample_range_start",_RX_SAMPLE_START),
            self._sequence_settings.get("rx_sample_range_end", _RX_SAMPLE_END),
        )
        self._tx_frequency = self._sequence_settings.get(
            "tx_frequency", _TX_FREQUENCY)
        self._tx_n_periods = self._sequence_settings.get(
            "tx_n_periods", _TX_N_PERIODS)
        self._tx_inverse = self._sequence_settings.get(
            "tx_inverse", _TX_INVERSE)
        self._pri = self._sequence_settings.get("pri", _PRI)
        self._sri = self._sequence_settings.get("sri", _SRI)
        # non-modifiable:
        self._downsampling_factor = _DOWNSAMPLING_FACTOR

    def start(self):
        pass

    @property
    def settings(self):
        return self._settings

    def get_rf_sum(self):
        raise ValueError("Abstract class")

    def get_defect_mask(self):
        raise ValueError("Abstract class")

    def get_rf(self):
        raise ValueError("Abstract class")

    def set_gain_value(self, gain_value: float):
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
        # Liczba probek wszerz, wzdluz
        self._settings["n_pix_ox"] = len(x_grid)
        self._settings["n_pix_oz"] = len(z_grid)

        # Compute TGC curve
        oz_min, oz_max = self._settings["image_extent_oz"]
        self._tgc_sampling_depths, tgc_curve = compute_tgc_curve_linear(
            oz_min, oz_max,
            tgc_start=self._settings["tgc_start"], tgc_slope=0,
            tgc_sampling_step=_TGC_SAMPLING_STEP)

        # Determine sequence
        self._sequence = StaSequence(
            tx_aperture_center_element=np.arange(0, 32),
            rx_aperture_center_element=16,
            rx_aperture_size=32,
            pulse=Pulse(
                center_frequency=self._tx_frequency,
                n_periods=self._tx_n_periods,
                inverse=self._tx_inverse),
            rx_sample_range=self._rx_sample_range,
            downsampling_factor=self._downsampling_factor,
            speed_of_sound=self._speed_of_sound,
            pri=self._pri, sri=self._sri,
            tgc_start=self._settings["tgc_start"],
            tgc_slope=0)

        self._rf_sum_queue = queue.Queue(1)
        self._rf_queue = queue.Queue(1)

        import cupy as cp

        class ComputeDefectMask(Operation):

            def __init__(self, threshold1=0.50, threshold2=0.65):
                self.threshold1 = threshold1
                self.threshold2 = threshold2
                self.output_data_queue = deque()
                self._max_amplitude1 = (2**14-1)*self.threshold1
                self._max_amplitude2 = (2**14-1)*self.threshold2
                self._output_mask = None

            def _prepare(self, const_metadata):
                print(const_metadata.input_shape)
                self._output_mask = cp.zeros(const_metadata.input_shape, dtype=const_metadata.dtype)
                return const_metadata

            def _process(self, data):
                self._output_mask = data.copy()
                level0 = self._output_mask <= self._max_amplitude1
                level1 = cp.logical_and(self._output_mask > self._max_amplitude1, self._output_mask <= self._max_amplitude2)
                level2 = self._output_mask > self._max_amplitude2
                self._output_mask[level0] = 0
                self._output_mask[level1] = 1
                self._output_mask[level2] = 2
                mask = cp.max(self._output_mask, axis=0)
                self.output_data_queue.append(mask.get())
                return data

        self._compute_defect_mask_op = ComputeDefectMask()

        self._fir_filter_taps = scipy.signal.firwin(
            64, np.array([0.5, 1.5]) * self._tx_frequency, pass_zero=False,
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
                    self._compute_defect_mask_op,
                    Sum(axis=0),
                    # SelectFrames([31]),
                    Squeeze(),
                    Enqueue(self._rf_sum_queue, block=False, ignore_full=True)),
                placement="/GPU:0"))

    def start(self):
        # Set initial values
        self.set_tx_voltage(self._initial_voltage)
        # Upload sequence on the us4r-lite device.
        self._buffer, self._const_metadata = self._session.upload(self._scheme)
        self._session.start_scheme()

    def get_rf_sum(self):
        return self._rf_sum_queue.get()

    def get_defect_mask(self):
        return self._compute_defect_mask_op.output_data_queue.pop()

    def get_rf(self):
        return self._rf_queue.get()

    def set_gain_value(self, gain_value):
        oz_min, oz_max = self._settings["image_extent_oz"]
        tgc_samples, tgc_curve = compute_tgc_curve_linear(
            oz_min, oz_max,
            gain_value, 0, _TGC_SAMPLING_STEP)
        actual_tgc_curve = interpolate_to_device_tgc(
            self._tgc_sampling_depths, tgc_curve, self._rx_sample_range[1],
            self._downsampling_factor,
            self._sampling_frequency/self._downsampling_factor,
            self._speed_of_sound)
        self._us4r.set_tgc(actual_tgc_curve)

    def set_tx_voltage(self, voltage: float):
        self._us4r.set_hv_voltage(voltage)

    def close(self):
        self._session.stop_scheme()

    def _compute_image_grid(self):
        # OZ
        c = self._speed_of_sound
        fs = _SAMPLING_FREQUENCY/self._downsampling_factor
        max_depth = (c/fs)*self._rx_sample_range[1]/2
        start_sample, end_sample = self._rx_sample_range
        z_grid = np.linspace(self._img_start_depth, max_depth, end_sample-start_sample)
        # OX
        n_elements = 32
        pitch = self._probe_model.pitch
        ox_l = -(n_elements-1)/2*pitch
        ox_r = (n_elements-1)/2*pitch
        x_grid = np.linspace(ox_l, ox_r, n_elements)
        return x_grid, z_grid

