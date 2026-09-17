"""ViewSession -- the host independent view-model shared by the web and Jupyter views.

It is the only new object that talks to the controller. A browser (through the FastAPI server)
and a notebook (through anywidget) both drive this same class, which is why the two front ends
cannot drift apart in behaviour.
"""

import os
import pickle
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

import gui4us.cfg
from gui4us.controller.buffer import CaptureBuffer
from gui4us.controller.env import EnvController
from gui4us.logging import get_logger
from gui4us.model import Box, MetadataCollection, SettingDef
from gui4us.utils import load_cfg
from gui4us.view.frames import FrameEncoder, LayerSpec, create_layers
from gui4us.view.protocol import Frame

#: Hardware states, as reported to the front end.
STATE_STOPPED = "stopped"
STATE_STARTED = "started"

#: Capture buffer states (the same ones the Qt capture component uses).
CAPTURE_EMPTY = "empty"
CAPTURE_CAPTURING = "capturing"
CAPTURE_CAPTURED = "captured"


class ViewSession:
    """Everything a front end needs from a single environment.

    :param env: the environment controller to drive
    :param view_cfg: display configuration (``display.py``)
    :param capture_capacity: default number of frames a capture holds (``app.py``)
    :param max_fps: upper bound on the frame rate pushed to the front end
    """

    def __init__(self, env: EnvController, view_cfg: gui4us.cfg.ViewCfg,
                 capture_capacity: int = 100, max_fps: float = 30.0):
        self.logger = get_logger(type(self))
        self.env = env
        self.view_cfg = view_cfg
        self.capture_capacity = capture_capacity
        self.min_frame_interval = 1.0/max_fps if max_fps else 0.0

        metadata_promise = self.env.get_stream_metadata()
        self.metadata: MetadataCollection = metadata_promise.get_result()
        self.settings: Sequence[SettingDef] = self.env.get_settings().get_result()
        self.layers: List[LayerSpec] = create_layers(view_cfg, self.metadata)
        self.encoder = FrameEncoder(self.layers)

        self._state_lock = threading.Lock()
        self._hardware_state = STATE_STOPPED
        self._capture_state = CAPTURE_EMPTY
        self._capture_buffer: Optional[CaptureBuffer] = None
        self._capture_metadata = None
        self._capture_done = threading.Event()
        self._frame_callbacks: List[Callable[[Frame], Any]] = []
        self._state_callbacks: List[Callable[[Dict[str, Any]], Any]] = []
        #: Only the newest frame is kept: a slow client must never block acquisition.
        self._latest = deque(maxlen=1)
        self._last_sent = 0.0

        self.env.get_stream().append_on_new_data_callback(self._on_new_data)

    # ------------------------------------------------------------------ descriptor
    def view_descriptor(self) -> Dict[str, Any]:
        """The JSON description of this view: what to render and what can be controlled."""
        return {
            "type": "descriptor",
            "layers": [layer.to_dict() for layer in self.layers],
            "displays": self._displays_descriptor(),
            "settings": [self._setting_descriptor(s) for s in self.settings],
            "capture": {"capacity": self.capture_capacity},
            "state": self.state(),
        }

    def _displays_descriptor(self) -> List[Dict[str, Any]]:
        displays: List[Dict[str, Any]] = []
        seen = {}
        for layer in self.layers:
            if layer.display_id not in seen:
                seen[layer.display_id] = {
                    "id": layer.display_id,
                    "title": layer.title,
                    "kind": layer.kind,
                    "ax_labels": list(layer.ax_labels) if layer.ax_labels else None,
                    "extents": [list(e) for e in layer.extents] if layer.extents else None,
                    "n_layers": 0,
                }
                displays.append(seen[layer.display_id])
            seen[layer.display_id]["n_layers"] += 1
        return displays

    @staticmethod
    def _setting_descriptor(setting: SettingDef) -> Dict[str, Any]:
        space = setting.space
        descriptor: Dict[str, Any] = {
            "name": setting.name,
            "step": _to_jsonable(setting.step),
            "initial_value": _to_jsonable(setting.initial_value),
            "shape": list(space.shape) if space.shape is not None else None,
            "dtype": str(space.dtype),
            "unit": _to_jsonable(space.unit),
            "component_names": _to_jsonable(space.name),
            "kind": "scalar" if space.is_scalar() else ("vector" if space.is_vector()
                                                        else "other"),
        }
        if isinstance(space, Box):
            descriptor["low"] = _to_jsonable(space.low)
            descriptor["high"] = _to_jsonable(space.high)
        return descriptor

    # ------------------------------------------------------------------ state
    def state(self) -> Dict[str, Any]:
        with self._state_lock:
            capture_size = (self._capture_buffer.get_current_size()
                            if self._capture_buffer is not None else 0)
            capacity = (self._capture_buffer.capacity
                        if self._capture_buffer is not None else self.capture_capacity)
            return {
                "hardware": self._hardware_state,
                "capture": {
                    "state": self._capture_state,
                    "size": capture_size,
                    "capacity": capacity,
                },
            }

    def on_state(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        self._state_callbacks.append(callback)

    def _notify_state(self) -> None:
        state = {"type": "state", **self.state()}
        for callback in list(self._state_callbacks):
            try:
                callback(state)
            except Exception as e:  # noqa: BLE001 - one broken client must not stop the rest
                self.logger.exception(e)

    # ------------------------------------------------------------------ frames
    def on_frame(self, callback: Callable[[Frame], Any]) -> None:
        """Registers a callback receiving every (throttled) encoded frame."""
        self._frame_callbacks.append(callback)

    def latest_frame(self) -> Optional[Frame]:
        """The most recent encoded frame, or None when nothing has arrived yet."""
        return self._latest[-1] if self._latest else None

    def _on_new_data(self, data) -> None:
        """Stream callback -- runs on the acquisition thread."""
        try:
            if self._capture_state == CAPTURE_CAPTURING:
                self._append_to_capture(data)
            now = time.time()
            if self.min_frame_interval and (now-self._last_sent) < self.min_frame_interval:
                return
            self._last_sent = now
            frame = self.encoder.encode(data)
            self._latest.append(frame)
            for callback in list(self._frame_callbacks):
                try:
                    callback(frame)
                except Exception as e:  # noqa: BLE001
                    self.logger.exception(e)
        except Exception as e:  # noqa: BLE001 - never propagate into the acquisition thread
            self.logger.exception(e)

    # ------------------------------------------------------------------ actions
    def start(self) -> None:
        """Starts the acquisition. Blocks until the environment has actually started."""
        _wait(self.env.start())
        with self._state_lock:
            self._hardware_state = STATE_STARTED
        self._notify_state()

    def stop(self) -> None:
        """Stops (freezes) the acquisition. Blocks until the environment has stopped."""
        _wait(self.env.stop())
        with self._state_lock:
            self._hardware_state = STATE_STOPPED
        self._notify_state()

    def set_setting(self, name: str, value) -> None:
        setting = self._find_setting(name)
        value = np.asarray(value, dtype=setting.space.dtype)
        if setting.space.is_scalar():
            value = value.reshape(1)
        _wait(self.env.set(setting.create_set_action(value)))

    def _find_setting(self, name: str) -> SettingDef:
        for setting in self.settings:
            if setting.name == name:
                return setting
        raise ValueError(f"Unknown setting: {name}")

    # ------------------------------------------------------------------ capture
    def capture_start(self, n_frames: Optional[int] = None) -> None:
        """Starts (or restarts) a capture of ``n_frames`` raw frames."""
        with self._state_lock:
            capacity = int(n_frames) if n_frames else self.capture_capacity
            self._capture_buffer = CaptureBuffer(capacity)
            self._capture_metadata = self.env.get_stream().get_metadata()
            self._capture_state = CAPTURE_CAPTURING
            self._capture_done.clear()
        self._notify_state()

    def _append_to_capture(self, data) -> None:
        buffer = self._capture_buffer
        if buffer is None:
            return
        # The RAW arrays are stored, not the 8-bit display frames: a notebook must get exactly
        # what the environment produced.
        buffer.append(tuple(np.copy(a) for a in data))
        if buffer.is_ready():
            with self._state_lock:
                self._capture_state = CAPTURE_CAPTURED
                self._capture_done.set()
        self._notify_state()

    def capture_wait(self, timeout: Optional[float] = None) -> bool:
        """Blocks until the capture is complete. Returns False on timeout."""
        return self._capture_done.wait(timeout)

    def captured_arrays(self) -> List[Tuple[np.ndarray, ...]]:
        """The captured frames: one tuple of raw arrays per frame."""
        if self._capture_buffer is None:
            return []
        return [d for d in self._capture_buffer.data if d is not None]

    @property
    def captured_metadata(self):
        return self._capture_metadata

    def capture_clear(self) -> None:
        with self._state_lock:
            self._capture_buffer = None
            self._capture_metadata = None
            self._capture_state = CAPTURE_EMPTY
            self._capture_done.clear()
        self._notify_state()

    def capture_save(self, path: str) -> str:
        """Saves the captured buffer; the format follows the Qt view's (a pickle)."""
        if self._capture_buffer is None:
            raise ValueError("Nothing has been captured yet.")
        if not os.path.splitext(path)[1]:
            path = f"{path}.pkl"
        with open(path, "wb") as f:
            pickle.dump({"data": self.captured_arrays(),
                         "metadata": self._capture_metadata}, f)
        return path

    def capture_bytes(self) -> bytes:
        """The captured buffer serialised for download by the browser."""
        if self._capture_buffer is None:
            raise ValueError("Nothing has been captured yet.")
        return pickle.dumps({"data": self.captured_arrays(),
                             "metadata": self._capture_metadata})

    # ------------------------------------------------------------------ lifecycle
    def close(self) -> None:
        try:
            self.env.close()
        except Exception as e:  # noqa: BLE001
            self.logger.exception(e)


def _wait(promise):
    """Waits for a controller promise and re-raises the error it carries, if any.

    The environment runs on its own thread; without this, a failure to start the hardware or
    to apply a setting would only show up in the log.
    """
    if promise is None:
        return None
    error = promise.get_error()
    if error is not None:
        raise error
    return promise.get_result()


def _to_jsonable(value):
    """numpy scalars/arrays -> plain Python, so that the descriptor is JSON serialisable."""
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def create_session(cfg_path: str, env_id: str = "main",
                   max_fps: float = 30.0) -> ViewSession:
    """Builds an EnvController and a ViewSession from a GUI4us configuration directory.

    The directory holds the same ``env.py``/``app.py``/``display.py`` files the Qt view uses.
    """
    display_cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
    app_cfg = load_cfg(os.path.join(cfg_path, "app.py"), "app")
    env = EnvController(env_id, cfg_path)
    return ViewSession(
        env=env,
        view_cfg=display_cfg.VIEW_CFG,
        capture_capacity=getattr(app_cfg, "CAPTURE_BUFFER_SIZE", 100),
        max_fps=max_fps,
    )
