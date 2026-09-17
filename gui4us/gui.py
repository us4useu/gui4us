"""The programmatic GUI4us API.

:class:`Gui4us` is GUI4us used as a library: a script (or a notebook) creates one with the three
configuration objects that a configuration directory would otherwise provide -- the display
configuration (``display.py``), the environment (``env.py``) and the application settings
(``app.py``) -- and then acquires, displays and captures data through it::

    from gui4us import AppCfg, Gui4us
    from gui4us.cfg import Display2D, Layer2D, ViewCfg
    from gui4us.model import StreamDataId
    from gui4us.model.envs.arrus import ArrusEnvConfiguration, Curve, UltrasoundEnv

    def configure(session):
        return ArrusEnvConfiguration(scheme=scheme, tgc=Curve(points, values), voltage=10)

    gui = Gui4us(
        env=lambda: UltrasoundEnv(session_cfg="/opt/us4us/us4r.prototxt", configure=configure),
        display=ViewCfg(displays={"B-mode": Display2D(
            title="B-mode", layers=(Layer2D(input=StreamDataId("default", 0), cmap="gray",
                                            value_range=(20, 80)), ))}),
        app=AppCfg(capture_buffer_size=100, view="web"),
    )
    with gui:
        gui.start()
        frames = gui.capture(10)   # -> list[tuple[np.ndarray, ...]] in the script
        gui.run()                  # blocking: the configured view

It is a facade over the existing layers -- ``EnvController`` for the environment and
``ViewSession`` for everything a view needs -- so scripts, the Qt window, the web server and
the notebook widgets all drive the same objects.
"""

import threading
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

import gui4us.cfg
from gui4us.cfg.app import AppCfg
from gui4us.controller.env import EnvController
from gui4us.logging import get_logger
from gui4us.model import Env, EnvId, SettingDef, Stream
from gui4us.view.session import ViewSession

EnvSource = Union[Env, Callable[[], Env]]


class Gui4us:
    """GUI4us as a Python object.

    :param env: the environment: an :class:`gui4us.model.Env` instance or a callable returning
      one (the callable is invoked on the environment thread, which then owns the hardware)
    :param display: display configuration, i.e. what ``display.py`` provides as ``VIEW_CFG``
    :param app: application settings; ``None`` means :class:`gui4us.cfg.AppCfg` defaults
    :param env_id: environment identifier (for logs and multi-environment setups)
    """

    def __init__(self, env: EnvSource, display: gui4us.cfg.ViewCfg,
                 app: Optional[AppCfg] = None, env_id: EnvId = "main"):
        self.logger = get_logger(type(self))
        self.app_cfg = app if app is not None else AppCfg()
        self.view_cfg = display
        self._closed = False
        self._view_thread: Optional[threading.Thread] = None
        self._server = None

        self.env_controller = EnvController(env_id, env=env)
        self.session = ViewSession(
            env=self.env_controller,
            view_cfg=self.view_cfg,
            capture_capacity=self.app_cfg.capture_buffer_size,
            max_fps=self.app_cfg.max_fps,
        )

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_cfg(cls, cfg_path: str, env_id: EnvId = "main") -> "Gui4us":
        """Builds a Gui4us from a configuration DIRECTORY (``env.py``/``display.py``/``app.py``).

        This is what the ``gui4us`` command line does; scripts normally pass the configuration
        objects to the constructor instead.
        """
        import os

        from gui4us.utils import load_cfg

        display_cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
        app_module = load_cfg(os.path.join(cfg_path, "app.py"), "app")
        env_module = load_cfg(os.path.join(cfg_path, "env.py"), f"env_{env_id}")
        return cls(env=env_module.ENV, display=display_cfg.VIEW_CFG,
                   app=AppCfg.from_module(app_module), env_id=env_id)

    # ------------------------------------------------------------------ environment
    @property
    def env(self) -> EnvController:
        """The environment controller (all calls are serialised on its thread)."""
        return self.env_controller

    @property
    def settings(self) -> Sequence[SettingDef]:
        """The settings the environment exposes."""
        return self.session.settings

    @property
    def metadata(self):
        """The stream metadata (a :class:`gui4us.model.MetadataCollection`)."""
        return self.session.metadata

    def start(self) -> "Gui4us":
        """Starts the acquisition."""
        self.session.start()
        return self

    def stop(self) -> "Gui4us":
        """Stops (freezes) the acquisition."""
        self.session.stop()
        return self

    def set(self, name: str, value) -> None:
        """Sets an environment setting, e.g. ``gui.set("Voltage", 20)``."""
        self.session.set_setting(name, value)

    def get(self, name: str):
        """The initial value of a setting (as declared by the environment)."""
        for setting in self.settings:
            if setting.name == name:
                return setting.initial_value
        raise ValueError(f"Unknown setting: {name}")

    def call(self, method: str, *args, **kwargs):
        """Calls an environment specific method on the environment thread.

        For example, with the ARRUS environment::

            gui.call("set_subsequence", [2, 3, 5, 8, 13])

        :return: whatever the method returned
        """
        promise = self.env_controller.call(method, *args, **kwargs)
        error = promise.get_error()
        if error is not None:
            raise error
        return promise.get_result()

    # ------------------------------------------------------------------ data
    def get_stream(self) -> Stream:
        """The raw data stream of the environment."""
        return self.env_controller.get_stream()

    def on_new_data(self, callback: Callable[[Tuple[np.ndarray, ...]], Any]) -> None:
        """Registers a callback for every acquired frame (raw arrays, acquisition thread)."""
        self.get_stream().append_on_new_data_callback(callback)

    def capture(self, n_frames: Optional[int] = None, timeout: Optional[float] = None,
                wait: bool = True) -> List[Tuple[np.ndarray, ...]]:
        """Captures ``n_frames`` frames and returns them as numpy arrays.

        The frames are exactly what the environment produced (the display's value range and
        colour map are not applied).

        :param n_frames: number of frames; ``None`` uses ``AppCfg.capture_buffer_size``
        :param timeout: how long to wait [s]; ``None`` waits indefinitely
        :param wait: when False, starts the capture and returns immediately
        """
        self.session.capture_start(n_frames)
        if not wait:
            return []
        if not self.session.capture_wait(timeout):
            self.logger.warning("The capture did not complete within the timeout; returning "
                                "the frames captured so far.")
        return self.captured

    @property
    def captured(self) -> List[Tuple[np.ndarray, ...]]:
        """The frames of the last capture."""
        return self.session.captured_arrays()

    def captured_array(self, output: int = 0) -> np.ndarray:
        """The last capture for one stream output, stacked into a single array."""
        frames = self.captured
        if not frames:
            return np.empty((0, ))
        return np.stack([frame[output] for frame in frames])

    @property
    def captured_metadata(self):
        return self.session.captured_metadata

    def save(self, path: str) -> str:
        """Saves the last capture (a pickle with ``data`` and ``metadata``)."""
        return self.session.capture_save(path)

    # ------------------------------------------------------------------ views
    def run(self, view: Optional[str] = None, **kwargs) -> int:
        """Runs a view; blocks until it is closed.

        :param view: "qt", "web" or None (no view -- returns immediately);
          defaults to ``AppCfg.view``
        """
        view = view if view is not None else self.app_cfg.view
        if view is None or view == "none":
            return 0
        if view == "qt":
            return self._run_qt(**kwargs)
        if view == "web":
            return self.serve(background=False, **kwargs)
        raise ValueError(f"Unknown view: {view}")

    def _run_qt(self, **kwargs) -> int:
        import matplotlib
        matplotlib.use("QtAgg")
        from gui4us.view.view import start_view_app_for

        title = self.app_cfg.title or f"gui4us {gui4us.__version__}"
        return start_view_app_for(env=self.env_controller, view_cfg=self.view_cfg,
                                  capture_buffer_capacity=self.app_cfg.capture_buffer_size,
                                  title=title, **kwargs)

    def serve(self, host: Optional[str] = None, port: Optional[int] = None,
              background: bool = False, **kwargs):
        """Serves the browser view.

        :param background: when True, the server runs in a daemon thread and the call returns
          the thread, so that a script can keep working (this is how a live demo shows its data
          while its own loop runs)
        """
        from gui4us.view.web.server import create_app, serve_app

        host = host if host is not None else self.app_cfg.host
        port = port if port is not None else self.app_cfg.port
        app = create_app(self.session)
        return serve_app(app, host=host, port=port, background=background, **kwargs)

    def widget(self, **kwargs):
        """The notebook view of this instance (an ipywidgets layout)."""
        return self.notebook_view(**kwargs).widget()

    def notebook_view(self, **kwargs):
        """A :class:`gui4us.view.jupyter.NotebookView` bound to this instance."""
        from gui4us.view.jupyter import NotebookView

        if not hasattr(self, "_notebook_view"):
            self._notebook_view = NotebookView(session=self.session, **kwargs)
        return self._notebook_view

    def _repr_mimebundle_(self, **kwargs):
        # Displaying the object in a notebook shows the widgets.
        return self.notebook_view()._repr_mimebundle_(**kwargs)

    # ------------------------------------------------------------------ lifecycle
    def close(self) -> None:
        """Stops the acquisition and closes the environment."""
        if self._closed:
            return
        self._closed = True
        try:
            self.session.close()
        finally:
            self.logger.info("Closed.")

    def __enter__(self) -> "Gui4us":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
