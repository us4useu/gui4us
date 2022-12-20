import numpy as np
from arrus.utils.imaging import *

from gui4us.common import ImageMetadata
from gui4us.model import *
from gui4us.logging import get_logger

DATA_SHAPE = (100, 100)


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
            data = np.random.rand(*DATA_SHAPE).astype(np.float32)
            for c in self.callbacks:
                c(data)


class DummyEnv(Env):

    def __init__(self):
        self.logger = get_logger(type(self))
        self.stream = DummyStream()
        self._state_lock = threading.Lock()

    def get_settings(self) -> Sequence[SettingDef]:
        return [
            SettingDef(
                name="range",
                space=Box(
                    shape=(1,),
                    dtype=np.float32,
                    low=0,
                    high=100
                ),
                initial_value=10,
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

    def set(self, action: Action) -> None:
        print(f"Got action: {action}")

    def get_stream(self) -> Stream:
        return self.stream

    def get_stream_metadata(self) -> MetadataCollection:
        return MetadataCollection({
            StreamDataId("default", 0): ImageMetadata(
                shape=DATA_SHAPE,
                dtype=np.float32
            )
        })


ENV = DummyEnv()
