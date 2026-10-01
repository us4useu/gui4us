import math
import queue
import gui4us.cfg
import arrus
import arrus.logging
import arrus.utils.imaging
import arrus.medium

import gui4us.model.core
from gui4us.model import *
from gui4us.common import *
from arrus.ops.us4r import *
import dataclasses
from dataclasses import dataclass
import numpy as np
from typing import Iterable


def supports_arbitrary_subsequences(session) -> bool:
    """Whether ``Session.set_subsequences`` takes lists of (possibly non-consecutive) TX/RXs.

    The released ARRUS 0.14 selects contiguous ranges only (``slices=[slice(start, end)]``); the
    development branch with the us4OEM+ sequencer re-programming takes any increasing list
    (``subsequences=[[2, 3, 5, 8]]``).
    """
    import inspect
    try:
        parameters = inspect.signature(session.set_subsequences).parameters
    except (TypeError, ValueError, AttributeError):
        return False
    return "subsequences" in parameters


def supports_subsequence_double_buffering(session) -> bool:
    """Whether the next sub-sequence can be prepared while the scheme is running."""
    return callable(getattr(session, "prepare_subsequences", None))


def _as_contiguous_slice(ops):
    """``ops`` as a ``slice`` when it is one contiguous range of TX/RXs, else None."""
    if isinstance(ops, slice):
        return ops
    ops = [int(op) for op in ops]
    if not ops:
        return slice(0, 0)
    if ops == list(range(ops[0], ops[-1] + 1)):
        return slice(ops[0], ops[-1] + 1)
    return None


def _n_ops_per_sequence(scheme, metadata):
    """The number of TX/RXs of each TX/RX sequence of the scheme (None where it is not known).

    Counted from the scheme, not from the metadata: the metadata has one entry per pipeline
    OUTPUT (e.g. an ``Output()`` step in the middle of the pipeline adds one), not per sequence.
    """
    sequences = scheme.tx_rx_sequence
    if not isinstance(sequences, (list, tuple)):
        sequences = [sequences]
    counts = [len(seq.ops) if getattr(seq, "ops", None) is not None else None
              for seq in sequences]
    if len(counts) == 1 and counts[0] is None:
        # A simple sequence (e.g. LinSequence): ARRUS reports the TX/RXs it was converted to.
        first = next(iter(metadata)) if isinstance(metadata, Iterable) else metadata
        counts[0] = len(first.context.raw_sequence.ops)
    return counts


def _set_subsequences(session, ops, sri, array_id, n_ops_per_sequence, processing):
    """``session.set_subsequences`` for the given sequence, in the form the installed ARRUS takes.

    :param n_ops_per_sequence: the number of TX/RXs of each uploaded sequence (the released ARRUS
      needs an explicit range for every sequence; the ones not being limited run in full)
    """
    n_sequences = len(n_ops_per_sequence)
    sris = [None]*n_sequences
    sris[array_id] = sri
    if supports_arbitrary_subsequences(session):
        subsequences = [[] for _ in range(n_sequences)]
        subsequences[array_id] = ops
        return session.set_subsequences(subsequences=subsequences, sris=sris, processing=processing)
    selected = _as_contiguous_slice(ops)
    if selected is None:
        raise NotImplementedError(
            f"ARRUS {arrus.__version__} can only select a contiguous range of TX/RXs, got {list(ops)}. "
            f"Selecting arbitrary TX/RXs needs an ARRUS build with the us4OEM+ sub-sequence support.")
    # Explicit [start, stop) for every sequence; the other sequences keep running in full.
    if any(n is None for i, n in enumerate(n_ops_per_sequence) if i != array_id):
        raise NotImplementedError(
            f"ARRUS {arrus.__version__} needs the number of TX/RXs of every sequence to limit one "
            f"of them; use raw TxRxSequences for the other sequences.")
    slices = [slice(0, n) for n in n_ops_per_sequence]
    start, stop, _ = selected.indices(n_ops_per_sequence[array_id])
    slices[array_id] = slice(start, stop)
    return session.set_subsequences(slices, processing=processing, sris=sris)


class ArrusStream(Stream):

    def __init__(self, metadata, callbacks=None):
        # The callbacks are carried over when the stream is re-created (e.g. after selecting
        # a new sub-sequence), so the views/capture stay connected.
        self.callbacks = list(callbacks) if callbacks is not None else []
        self._metadata = metadata

    def append_on_new_data_callback(self, callback: Callable):
        self.callbacks.append(callback)

    def get_metadata(self):
        return self._metadata


@dataclass(frozen=True)
class Curve:
    """
    TGC curve defintion.

    :param points: depth points [m]
    :param values: curve values [dB]
    """
    points: Iterable[float]
    values: Iterable[float]


@dataclass(frozen=True)
class ArrusEnvConfiguration:
    """
    ARRUS environment configuration.

    The instance of this class should be returned by the factory function
    `configure`.

    :param scheme: arrus Scheme (TX/RX sequence and processing)
    :param tgc: tgc settings to apply
    :param medium: the assumed ARRUS medium
    :param voltage: initial voltage [V]
    """
    scheme: arrus.ops.us4r.Scheme
    tgc: Curve
    medium: Optional[arrus.medium.Medium] = None
    voltage: Optional[float] = 5  # [V]


def get_depth_range(depth_grid: Iterable[float]):
    """
    Returns depth range that covers a given grid of points.

    Currently, this function can be considered
    as a shortcut for (np.min(grid), np.max(grid)).
    """
    # +5e-3 to cover most of the use cases
    return np.min(depth_grid), np.max(depth_grid)+5e-3


class UltrasoundEnv(Env):
    """
    ARRUS ultrasound environment.

    This user class should provide a path to the .prototxt session configuration file
    and a factory function ``configure``, with the implementation of ultrasound
    environment, in particular: arrus Scheme(TX/RX sequence and processing in particular)
    and default settings like TX voltage.

    :param session_cfg: path to the session configuration file
    :param configure: ARRUS scheme factory function
    :param log_file_level: ARRUS logging level (output: file)
    :param log_file: output log file
    """

    LOG_FILE = "arrus.log"

    def __init__(self,
                 session_cfg: str,
                 configure: Callable[[arrus.Session], ArrusEnvConfiguration],
                 log_file_level=arrus.logging.INFO,
                 log_file: Optional[str] = None,
                 ):
        # Logging.
        log_file = log_file if log_file is not None else UltrasoundEnv.LOG_FILE
        self.log_file_level = log_file_level
        arrus.logging.add_log_file(log_file, log_file_level)

        # Start session
        self.session = arrus.Session(session_cfg)
        self.us4r = self.session.get_device("/Us4R:0")
        self.probe_model = self.us4r.get_probe_model()

        # Load configuration.
        if isinstance(configure, Callable):
            cfg = configure(self.session)
        else:
            raise ValueError("The scheme object should be callable.")

        # Initial values:
        self.scheme = cfg.scheme
        self.tgc_sampling_points = cfg.tgc.points
        self.tgc_values = cfg.tgc.values
        self.initial_voltage = cfg.voltage
        self.medium = cfg.medium

        # Set processing callback.
        # In order to do that, it is necessary to wrap the input pipeline
        # into the Processing class instance.
        if isinstance(self.scheme.processing, arrus.utils.imaging.Pipeline):
            pipeline = self.scheme.processing
            self.scheme = dataclasses.replace(
                    self.scheme,
                    processing=arrus.utils.imaging.Processing(pipeline))
        
        arrus_version = arrus.__version__
        arrus_version_major_minor = tuple(int(v) for v in arrus_version.split(".")[:2])
        print(arrus_version_major_minor)

        if arrus_version_major_minor <= (0, 10):
            self.scheme.processing.callback = self._on_new_data_arrus010
        else:
            self.scheme.processing.callback = self._on_new_data

        # TODO replace the below with settings read via arrus
        self._us4r_actions = {
            "TGC": lambda value: self.set_tgc(self.tgc_sampling_points, value),
            "Voltage": lambda value: self.us4r.set_hv_voltage(int(value)),
        }
        # Configure.
        if self.initial_voltage is not None:
            # int: the ARRUS (SWIG) binding rejects float voltages
            self.us4r.set_hv_voltage(int(self.initial_voltage))
        # NOTE: medium should be set before uploading the sequence.
        self.session.medium = self.medium
        self._is_running = False
        self.metadata = self.session.upload(self.scheme)
        self.stream = ArrusStream(metadata=self.metadata)
        # The number of TX/RXs of each uploaded sequence (the full ones, before any sub-sequence).
        self._n_ops_per_sequence = _n_ops_per_sequence(self.scheme, self.metadata)
        self.set_tgc(self.tgc_sampling_points, self.tgc_values)
        if not isinstance(self.metadata, Iterable):
            self.metadata = (self.metadata, )

    def start(self) -> None:
        self.session.start_scheme()
        self._is_running = True

    def stop(self) -> None:
        self.session.stop_scheme()
        self._is_running = False

    def close(self) -> None:
        self.stop()
        self.session.close()

    def set(self, action: SetAction):
        if action.name not in self._us4r_actions:
            self.scheme.processing.set_parameter(action.name, action.value)
        else:
            self._us4r_actions[action.name](action.value)

    def get_settings(self) -> Sequence[SettingDef]:
        parameters = self.scheme.processing.get_parameters()

        def _convert_to_gui4us_space(arrus_space):
            return gui4us.model.Box(
                **arrus_space.__dict__
            )

        arrus_processing_parameters = []
        for name, definition in parameters.items():
            initial_value = self.scheme.processing.get_parameter(name)
            arrus_processing_parameters.append(
                SettingDef(
                    name=name,
                    space=_convert_to_gui4us_space(definition.space),
                    initial_value=initial_value,
                ),
            )
        # Sort by name
        arrus_processing_parameters = sorted(
            arrus_processing_parameters,
            key=lambda setting: setting.name
        )
        if self.medium is not None:
            tgc_space = Box(
                shape=(len(self.tgc_sampling_points),),
                dtype=np.float32,
                low=14,
                high=54,
                name=[f"{i*1e3:.0f} [mm]"
                    for i in self.tgc_sampling_points],
                unit=["dB"]*len(self.tgc_sampling_points)
            )
        else:
            # Seconds
            tgc_space = Box(
                shape=(len(self.tgc_sampling_points),),
                dtype=np.float32,
                low=14,
                high=54,
                name=[f"{i*1e6:.0f} [us]"
                    for i in self.tgc_sampling_points],
                unit=["dB"]*len(self.tgc_sampling_points)
            )

        parameters = arrus_processing_parameters
        if self.initial_voltage is not None:
            parameters += [SettingDef(
                name="Voltage",
                space=Box(
                    shape=(1,),
                    dtype=np.float32,
                    low=5,
                    high=90  # Read from us4R object
                ),
                initial_value=self.initial_voltage,
                step=5
            ), ]
        return parameters + [
            SettingDef(
                name="TGC",
                space=tgc_space,
                initial_value=self.tgc_values,
            ),
        ]

    def set_subsequence(self, ops, sri=None, array_id: int = 0):
        """Runs only the given TX/RXs of the uploaded sequence.

        A thin wrapper around ``arrus.Session.set_subsequences`` that keeps this environment
        consistent afterwards: the scheme is stopped while the sequencer is re-programmed, the
        processing pipeline is reused (so this stream's callback survives), the metadata is
        refreshed and the acquisition is resumed when it was running.

        Call it through the controller so that it runs on the environment thread::

            gui.call("set_subsequence", [2, 3, 5, 8, 13])

        :param ops: the TX/RX ordinal numbers to run (increasing), or a slice
        :param sri: sequence repetition interval to apply [s]
        :param array_id: which uploaded TX/RX sequence to limit
        :return: the new stream metadata collection
        """
        was_running = self._is_running
        if was_running:
            self.stop()
        metadata = _set_subsequences(self.session, ops, sri, array_id,
                                     self._n_ops_per_sequence, self.scheme.processing)
        self.metadata = metadata
        if not isinstance(self.metadata, Iterable):
            self.metadata = (self.metadata, )
        self.stream = ArrusStream(metadata=self.metadata,
                                  callbacks=self.stream.callbacks)
        if was_running:
            self.start()
        return self.get_stream_metadata()

    def prepare_subsequence(self, ops, sri=None, array_id: int = 0):
        """Prepares the TX/RXs to run, without stopping the scheme.

        NOTE: with the scheme running, the prepared TX/RXs are used starting from the SECOND :meth:`run` after
        this call (the next run still acquires the current TX/RXs).

        A thin wrapper around ``arrus.Session.prepare_subsequences`` (the sequencer double-buffering): the
        MANUAL work mode is required, and the new TX/RXs must produce data of the same shape as the current
        ones (e.g. the same number of TX/RXs). The processing pipeline is updated by ARRUS on the next run.
        When the scheme is stopped, this is the same as :meth:`set_subsequence`.

        Call it through the controller: ``gui.call("prepare_subsequence", [2, 3, 5])``.
        """
        if not self._is_running:
            return self.set_subsequence(ops, sri=sri, array_id=array_id)
        if not supports_subsequence_double_buffering(self.session):
            raise NotImplementedError(
                f"Preparing a sub-sequence while the scheme is running (sequencer double-buffering) is not "
                f"available in ARRUS {arrus.__version__}; stop the scheme and use set_subsequence instead.")
        n_sequences = self._get_number_of_sequences()
        subsequences = [[] for _ in range(n_sequences)]
        sris = [None]*n_sequences
        subsequences[array_id] = ops
        sris[array_id] = sri
        # NOTE: the output data shape does not change, the stream (and its metadata) is kept.
        self.session.prepare_subsequences(subsequences=subsequences, sris=sris,
                                          processing=self.scheme.processing)
        return self.get_stream_metadata()

    def run(self, sync: bool = False, timeout=None) -> None:
        """Triggers the scheme (MANUAL work mode: a single acquisition); starts it, when stopped."""
        self.session.run(sync=sync, timeout=timeout)
        self._is_running = True

    def _get_number_of_sequences(self) -> int:
        sequences = self.scheme.tx_rx_sequence
        if isinstance(sequences, Iterable):
            return len(sequences)
        return 1

    def set_tgc(self, z, value):
        # Medium, z -> time
        if self.medium:
            c = self.medium.speed_of_sound
            z = np.asarray(z)
            t = z/c*2
        else:
            t = z
        # Plain Python floats: the ARRUS (SWIG) binding rejects numpy.float32 elements, which
        # is what a setting coming from the web/notebook control panel is converted to.
        t = [float(v) for v in np.ravel(t)]
        value = [float(v) for v in np.ravel(value)]
        self.us4r.set_tgc((t, value))

    def get_stream(self) -> Stream:
        return self.stream

    def get_stream_metadata(self) -> MetadataCollection:
        image_metadata = {}
        for i, m in enumerate(self.metadata):
            spacing = m.data_description.spacing
            extents = []
            if spacing is not None:
                for coords in spacing.coordinates:
                    extents.append((np.min(coords), np.max(coords)))
                extents = tuple(extents)
            else:
                # Use the pixel units
                for ax_dimension in m.input_shape:
                    extents.append((0, ax_dimension))
                extents=tuple(extents)
            im = ImageMetadata(
                shape=m.input_shape,
                dtype=m.dtype,
                extents=extents
            )
            image_metadata[StreamDataId("default", i)] = im
        return MetadataCollection(image_metadata)

    def _on_new_data(self, input_elements):
        try:
            output_data = []

            if not isinstance(input_elements, Iterable):
                input_elements = (input_elements,)
            for input_element in input_elements:
                for array in input_element.arrays:
                    output_data.append(array[:])
                input_element.release()
            output_data = tuple(output_data)
            for cb in self.stream.callbacks:
                cb(output_data)
        except Exception as e:
            print(e)
        except:
            print("Unknown exception")

    def _on_new_data_arrus010(self, input_elements):
        try:
            output_data = []
            for input_element in input_elements:
                output_data.append(input_element.data[:])
                input_element.release()
            output_data = tuple(output_data)
            for cb in self.stream.callbacks:
                cb(output_data)
        except Exception as e:
            print(e)
        except:
            print("Unknown exception")

