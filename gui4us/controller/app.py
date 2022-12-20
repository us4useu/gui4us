import threading
import queue
import threading
import pickle

from gui4us.logging import get_logger
from gui4us.model.app import *
from gui4us.controller.event import *
from gui4us.controller.task import *
from gui4us.controller.env import *
from gui4us.utils import load_cfg
from gui4us.controller.buffer import *


class AppController:
    def __init__(self, cfg_path: str):
        self._env_controllers: Dict[EnvId, EnvController] = {}
        self.logger = get_logger(type(self))
        self._state_lock = threading.Lock()
        self.cfg = load_cfg(os.path.join(cfg_path, "app.py"), "gui4us_app")
        # Settings:
        self.capture_buffer_size = self.cfg.CAPTURE_BUFFER_SIZE
        self.capture_buffer: CaptureBuffer = None

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        with self._state_lock:
            for k, env in self._env_controllers.items():
                env.close()

    def start(self):
        pass

    def start_capture(self):
        """
        Starts data capture on the only env.
        """
        with self._state_lock:
            if len(self._env_controllers) != 1:
                raise ValueError("Capture buffer currently works only with "
                                 "a single environment.")
            if self.capture_buffer is not None:
                raise ValueError("Some capture buffer already exists, close "
                                 "the existing one before starting "
                                 "a new capture.")
            _, env = next(iter(self._env_controllers.items()))
            self.capture_buffer = CaptureBuffer(self.capture_buffer_size)

    def save_capture(self, path: str):
        with self._state_lock:
            # TODO metadata?
            pickle.dump({"data": self.capture_buffer.data}, open(path, "wb"))

    def clear_capture(self):
        with self._state_lock:
            self.capture_buffer = None

    def add_env(self, id: EnvId, env_cfg_path: str):
        with self._state_lock:
            if id in self._env_controllers:
                raise ValueError(f"Env {id} already exists.")
            # Load configuration file.
            env_controller = EnvController(id, env_cfg_path)
            self._env_controllers[id] = env_controller
            env_controller.get_stream().append_on_new_data_callback(
                self._app_default_callback
            )
            return env_controller

    def _app_default_callback(self, data):
        """
        Default APP callback, to be called for the first environment.
        """
        # TODO lock?
        if self.capture_buffer is not None:
            if not self.capture_buffer.is_ready():
                self.capture_buffer.append(data)

