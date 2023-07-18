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


class ArrusStream(Stream):

    def __init__(self):
        self.callbacks = []

    def append_on_new_data_callback(self, callback: Callable):
        self.callbacks.append(callback)


@dataclass(frozen=True)
class Curve:
    points: Iterable[float]
    values: Iterable[float]


@dataclass(frozen=True)
class ArrusEnvConfiguration:
    medium: arrus.medium.Medium
    scheme: arrus.ops.us4r.Scheme
    tgc: Curve
    voltage: float = 5  # [V]


def get_depth_range(depth_grid: Iterable[float]):
    """
    Returns depth range that covers a given grid of points.

    Currently this function can be considered
    as a shortcut for (np.min(grid), np.max(grid)).
    """
    return (np.min(depth_grid), np.max(depth_grid))


class UltrasoundEnv(Env):

    LOG_FILE = "arrus.log"

    def __init__(self,
                 session_cfg: str,
                 configure: Callable[[arrus.Session], ArrusEnvConfiguration],
                 log_file_level=arrus.logging.INFO,
                 log_file: Optional[str] = None
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
                    processing=arrus.utils.imaging.Processing(pipeline=pipeline))
            
        self.scheme.processing.callback = self._on_new_data

        # TODO replace the below with settings read via arrus
        self._us4r_actions = {
            "TGC": lambda value: self.set_tgc(self.tgc_sampling_points, value),
            "Voltage": self.us4r.set_hv_voltage
        }
        self.stream = ArrusStream()
        # Configure.
        self.us4r.set_hv_voltage(self.initial_voltage)
        # NOTE: medium should be set before uploading the sequence.
        self.session.medium = self.medium
        self.metadata = self.session.upload(self.scheme)
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
        return arrus_processing_parameters + [
            SettingDef(
                name="Voltage",
                space=Box(
                    shape=(1,),
                    dtype=np.float32,
                    low=5,
                    high=90  # Read from us4R object
                ),
                initial_value=self.initial_voltage,
                step=5
            ),
            SettingDef(
                name="TGC",
                space=Box(
                    shape=(len(self.tgc_sampling_points),),
                    dtype=np.float32,
                    low=14,
                    high=54,
                    name=[f"{i*1e3:.0f} [mm]"
                          for i in self.tgc_sampling_points],
                    unit=["dB"]*len(self.tgc_sampling_points)
                ),
                initial_value=self.tgc_values,
            ),
        ]

    def set_tgc(self, z, value):
        # Medium, z -> time
        c = self.medium.speed_of_sound
        z = np.asarray(z)
        t = z/c*2
        self.us4r.set_tgc((t, value))

    def get_stream(self) -> Stream:
        return self.stream

    def get_stream_metadata(self) -> MetadataCollection:
        x_grid, z_grid = self._determine_image_grid()
        oxz_extent = np.array([np.min(z_grid), np.max(z_grid),
                               np.min(x_grid), np.max(x_grid)])*1e3

        image_metadata = {}
        print(self.metadata)
        for i, m in enumerate(self.metadata):
            print(m)
            im = ImageMetadata(
                shape=m.input_shape,
                dtype=m.dtype,
                ids=("OX", "OZ"),
                units=("mm", "mm"),
                extents=((oxz_extent[0], oxz_extent[1]),
                         (oxz_extent[2], oxz_extent[3]))
            )
            image_metadata[StreamDataId("default", i)] = im
        return MetadataCollection(image_metadata)

    def _on_new_data(self, input_elements):
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

    def _determine_image_grid(self):
        # TODO the output grid dimensions should be a part of the arrus metadata
        if isinstance(self.scheme.processing, arrus.utils.imaging.Processing):
            pipeline = self.scheme.processing.pipeline
        else:
            pipeline = self.scheme.processing
        grid_steps = [step for step in pipeline.steps
                      if hasattr(step, "x_grid") and hasattr(step, "z_grid")
                      ]
        if len(grid_steps) > 0:
            grid_step = grid_steps[-1]
            return grid_step.x_grid, grid_step.z_grid
        else:
            raise ValueError("The processing should contain imaging step.")



