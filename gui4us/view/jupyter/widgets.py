"""GUI4us Jupyter widgets.

Each widget wraps one of the components from ``ui/src/components`` -- the same ones the web
application uses -- and connects it to a :class:`gui4us.view.session.ViewSession` running
in the notebook kernel. Because the session is in-process, captured data is available as plain
numpy arrays in the notebook (see :class:`NotebookView.captured`).
"""

import pathlib
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from gui4us.logging import get_logger
from gui4us.view.jupyter.bundler import bundle
from gui4us.view.session import ViewSession, create_session

LOGGER = get_logger(__name__)

#: Vite output (`npm run build:widgets`), preferred when present.
_BUILT_WIDGETS = pathlib.Path(__file__).resolve().parent/"static"
#: Component sources, used by the no-Node fallback bundler.
_UI_SRC = pathlib.Path(__file__).resolve().parents[3]/"ui"/"src"


def _load_esm(name: str) -> str:
    """The widget's ES module: the Vite bundle if it was built, else a source bundle."""
    built = _BUILT_WIDGETS/f"{name}.js"
    if built.is_file():
        return built.read_text(encoding="utf-8")
    entry = _UI_SRC/"widgets"/f"{name}.js"
    if not entry.is_file():
        raise FileNotFoundError(
            f"Neither a built widget ({built}) nor its sources ({entry}) were found. "
            f"Reinstall gui4us or run `npm run build:widgets` in ui/.")
    return bundle(entry)


def _import_anywidget():
    try:
        import anywidget  # noqa: F401
        import traitlets  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "The GUI4us notebook view needs anywidget: pip install 'gui4us[jupyter]'") from e
    return anywidget, traitlets


class _SessionWidget:
    """Mixin: connects an anywidget to a ViewSession.

    Frames are pushed into a binary traitlet, control messages travel as custom messages; both
    map 1:1 onto what the WebSocket transport does, so the JS side is unchanged.
    """

    def _attach(self, session: ViewSession, send_frames: bool = False,
                max_fps: float = 20.0) -> None:
        self._session = session
        self._send_frames = send_frames
        self._frame_interval = 1.0/max_fps if max_fps else 0.0
        self._last_frame_sent = 0.0
        self.descriptor = session.view_descriptor()
        self.state = session.state()
        session.on_state(self._on_session_state)
        if send_frames:
            session.on_frame(self._on_session_frame)
        self.on_msg(self._on_client_message)

    # -- session -> front end
    def _on_session_state(self, state: Dict[str, Any]) -> None:
        try:
            self.state = {k: v for k, v in state.items() if k != "type"}
        except Exception as e:  # noqa: BLE001 - a dead comm must not break acquisition
            LOGGER.debug(f"Could not push the state to the widget: {e}")

    def _on_session_frame(self, frame) -> None:
        now = time.time()
        if self._frame_interval and (now-self._last_frame_sent) < self._frame_interval:
            return
        self._last_frame_sent = now
        try:
            self.frame = frame.to_bytes()
        except Exception as e:  # noqa: BLE001
            LOGGER.debug(f"Could not push a frame to the widget: {e}")

    # -- front end -> session
    def _on_client_message(self, widget, content, buffers) -> None:
        try:
            message_type = content.get("type")
            if message_type == "action":
                name = content["name"]
                if name == "start":
                    self._session.start()
                elif name == "stop":
                    self._session.stop()
                elif name == "capture":
                    self._session.capture_start(content.get("n_frames"))
                elif name == "clear":
                    self._session.capture_clear()
                elif name == "save":
                    self._session.capture_save(content["path"])
                else:
                    raise ValueError(f"Unknown action: {name}")
            elif message_type == "set_setting":
                self._session.set_setting(content["name"], content["value"])
        except Exception as e:  # noqa: BLE001 - report to the front end, keep the kernel alive
            LOGGER.exception(e)
            self.send({"type": "error", "message": str(e)})


def _make_widget_class(name: str, esm_name: str, extra_traits=None):
    """Builds an AnyWidget subclass for one component (done lazily: anywidget is optional)."""
    anywidget, traitlets = _import_anywidget()

    attributes = {
        "_esm": _load_esm(esm_name),
        "descriptor": traitlets.Dict({}).tag(sync=True),
        "state": traitlets.Dict({}).tag(sync=True),
        "frame": traitlets.Bytes(b"").tag(sync=True),
    }
    if extra_traits:
        attributes.update(extra_traits(traitlets))
    return type(name, (anywidget.AnyWidget, _SessionWidget), attributes)


def StreamDisplay(session: ViewSession, display_id: Optional[str] = None,
                  height: int = 320, max_fps: float = 20.0):
    """A live ultrasound display (``<g4u-stream-view>``) for one display of the view."""
    cls = _make_widget_class(
        "StreamDisplay", "display",
        lambda traitlets: {
            "display_id": traitlets.Unicode("").tag(sync=True),
            "height": traitlets.Int(320).tag(sync=True),
        })
    widget = cls()
    displays = session.view_descriptor()["displays"]
    widget.display_id = display_id or (displays[0]["id"] if displays else "")
    widget.height = height
    widget._attach(session, send_frames=True, max_fps=max_fps)
    return widget


def ControlPanel(session: ViewSession):
    """The environment settings (``<g4u-control-panel>``)."""
    widget = _make_widget_class("ControlPanel", "controls")()
    widget._attach(session)
    return widget


def ActionsPanel(session: ViewSession):
    """Start/Freeze (``<g4u-actions-panel>``)."""
    widget = _make_widget_class("ActionsPanel", "actions")()
    widget._attach(session)
    return widget


def CapturePanel(session: ViewSession):
    """Capture/Save buttons (``<g4u-capture-panel>``)."""
    widget = _make_widget_class("CapturePanel", "capture")()
    widget._attach(session)
    return widget


class NotebookView:
    """The GUI4us view for a notebook: displays, controls, actions and capture.

    ::

        from gui4us.view.jupyter import NotebookView

        view = NotebookView("/path/to/cfg")   # the same cfg directory the Qt view uses
        view                                  # displays the whole panel
        view.start()

        view.capture(50)                      # or press "Capture" in the UI
        frames = view.captured                # list[tuple[np.ndarray, ...]] -- raw arrays

    The individual widgets are also available (``view.display``, ``view.control_panel``,
    ``view.actions``, ``view.capture_panel``) and can be arranged with ipywidgets as needed.
    """

    def __init__(self, cfg_path: Optional[str] = None, session: Optional[ViewSession] = None,
                 display_id: Optional[str] = None, height: int = 320, max_fps: float = 20.0):
        if session is None:
            if cfg_path is None:
                raise ValueError("Provide either cfg_path or session.")
            session = create_session(cfg_path, max_fps=max_fps)
        self.session = session
        self.display = StreamDisplay(session, display_id=display_id, height=height,
                                     max_fps=max_fps)
        self.control_panel = ControlPanel(session)
        self.actions = ActionsPanel(session)
        self.capture_panel = CapturePanel(session)

    # ------------------------------------------------------------------ actions
    def start(self) -> None:
        """Starts the hardware (the same as pressing Start)."""
        self.session.start()

    def stop(self) -> None:
        """Freezes the acquisition."""
        self.session.stop()

    def capture(self, n_frames: Optional[int] = None, timeout: Optional[float] = None,
                wait: bool = True) -> List[Tuple[np.ndarray, ...]]:
        """Captures ``n_frames`` raw frames into the notebook.

        :param n_frames: number of frames; defaults to the configured capacity
        :param timeout: how long to wait for the buffer to fill [s]
        :param wait: when False, returns immediately (poll :attr:`captured` / the panel)
        :return: the captured frames, one tuple of arrays per frame
        """
        self.session.capture_start(n_frames)
        if not wait:
            return []
        if not self.session.capture_wait(timeout):
            LOGGER.warning("The capture did not complete within the timeout; "
                           "returning what has been captured so far.")
        return self.captured

    @property
    def captured(self) -> List[Tuple[np.ndarray, ...]]:
        """The captured frames as raw numpy arrays (empty before the first capture)."""
        return self.session.captured_arrays()

    @property
    def captured_metadata(self):
        """The stream metadata that goes with :attr:`captured`."""
        return self.session.captured_metadata

    def captured_array(self, output: int = 0) -> np.ndarray:
        """The captured frames of one stream output, stacked into a single array."""
        frames = self.captured
        if not frames:
            return np.empty((0, ))
        return np.stack([frame[output] for frame in frames])

    def save(self, path: str) -> str:
        """Saves the captured buffer (pickle, the format the Qt view writes)."""
        return self.session.capture_save(path)

    def close(self) -> None:
        self.session.close()

    # ------------------------------------------------------------------ display
    def widget(self):
        """The default layout: controls on the left, the display on the right."""
        import ipywidgets

        sidebar = ipywidgets.VBox(
            [self.actions, self.capture_panel, self.control_panel],
            layout=ipywidgets.Layout(width="22rem"))
        self.display.layout = ipywidgets.Layout(width="100%", min_height=f"{self.display.height}px")
        return ipywidgets.HBox([sidebar, self.display],
                               layout=ipywidgets.Layout(width="100%"))

    def _repr_mimebundle_(self, **kwargs):
        return self.widget()._repr_mimebundle_(**kwargs)
