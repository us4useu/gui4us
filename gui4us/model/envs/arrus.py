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


class ArrusStream(Stream):

    def __init__(self):
        self.callbacks = []

    def append_on_new_data_callback(self, callback: Callable):
        self.callbacks.append(callback)


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
        self.stream = ArrusStream()
        # Configure.
        if self.initial_voltage is not None:
            self.us4r.set_hv_voltage(self.initial_voltage)
        # NOTE: medium should be set before uploading the sequence.
        self.session.medium = self.medium
        self.metadata = self.session.upload(self.scheme)
        self.set_tgc(self.tgc_sampling_points, self.tgc_values)
        if not isinstance(self.metadata, Iterable):
            self.metadata = (self.metadata, )

    def start(self) -> None:
        self.session.start_scheme()

    def stop(self) -> None:
        self.session.stop_scheme()

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

    def set_tgc(self, z, value):
        # Medium, z -> time
        if self.medium:
            c = self.medium.speed_of_sound
            z = np.asarray(z)
            t = z/c*2
        else:
            t = z
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

