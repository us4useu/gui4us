import numpy as np
from arrus.utils.imaging import *

from gui4us.common import ImageMetadata
from gui4us.model import *
from gui4us.logging import get_logger

DATA_SHAPE_1 = (100, 100)
DATA_SHAPE_2 = (50, 100)


class DummyStream(Stream):

    def __init__(self):
        self.thread = threading.Thread(target=self._produce_data)
        self._is_running = False
        self.callbacks = []

    def append_on_new_data_callback(self, callback: Callable):
        self.callbacks.append(callback)

    def stop(self):
        self._is_running = False
        self.thread.join()

    def start(self):
        self._is_running = True
        self.thread.start()

    def _produce_data(self):
        while self._is_running:
            data1 = np.random.rand(*DATA_SHAPE_1).astype(np.float32)
            data2 = np.random.rand(*DATA_SHAPE_2)
            for c in self.callbacks:
                c((data1, data2))


class DummyEnv(Env):

    def __init__(self, n_outputs=1):
        self.logger = get_logger(type(self))
        self.stream = DummyStream()
        self._state_lock = threading.Lock()
        self.n_outputs = n_outputs

    def get_settings(self) -> Sequence[SettingDef]:
        return [
            SettingDef(
                name="range1",
                space=Box(
                    shape=(1,),
                    dtype=np.float32,
                    low=0,
                    high=100
                ),
                initial_value=10,
                step=5
            ),
            SettingDef(
                name="TGC",
                space=Box(
                    shape=(10,),
                    dtype=np.float32,
                    low=14,
                    high=54,
                    name=[f"{i} [mm]" for i in range(10)],
                    unit=["dB"]*10
                ),
                initial_value=[20]*10,
                step=1
            ),
        ]

    def start(self) -> None:
        with self._state_lock:
            self.stream.start()

    def stop(self) -> None:
        with self._state_lock:
            self.stream.stop()

    def close(self) -> None:
        self.stop()

    def set(self, action: SetAction) -> None:
        print(f"Got action: {action}")

    def get_stream(self) -> Stream:
        return self.stream

    def get_stream_metadata(self) -> MetadataCollection:
        return MetadataCollection({
            StreamDataId("default", 0): ImageMetadata(
                shape=DATA_SHAPE_1,
                dtype=np.float32,
                ids=("OZ", "OX"),
                units=("m", "m"),
                extents=((0, 10), (-5, 5))
            ),
            StreamDataId("default", 1): ImageMetadata(
                shape=DATA_SHAPE_2,
                dtype=np.float32,
                ids=("OZ", "OY"),
                units=("m", "m"),
                extents=((0, 5), (-5, 5))
            )
        })


ENV = DummyEnv()
