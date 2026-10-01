"""Runs the web view as a desktop application: the server in the background + a native window showing it.

The window, in order of preference:

1. an embedded web engine window (pywebview: WebView2 on Windows, Qt WebEngine or WebKitGTK on Linux, WebKit on
   macOS); closing the window stops the application,
2. a Chromium/Chrome/Edge window in the "app" mode (no tabs, no address bar),
3. the default web browser.

For 2 and 3 the application runs until Ctrl+C (the browser process is not owned by gui4us). When there is no
display (e.g. over SSH), only the server is started (the same as ``headless=True``).
"""
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Optional

from gui4us.logging import get_logger

LOGGER = get_logger(__name__)

#: The window size [px].
WINDOW_SIZE = (1400, 900)

_APP_MODE_BROWSERS = (
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "microsoft-edge", "msedge",
    "brave-browser",
)


def get_local_url(host: str, port: int) -> str:
    """The URL of the server as seen from this machine."""
    if host in ("0.0.0.0", "::", ""):
        host = "127.0.0.1"
    return f"http://{host}:{port}"


def has_display() -> bool:
    """Whether a window can be opened (on Linux: an X11 or Wayland display is available)."""
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def wait_for_server(url: str, timeout: float = 30.0, server_thread=None) -> bool:
    """Waits until the server responds (any HTTP status)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server_thread is not None and not server_thread.is_alive():
            return False
        try:
            urllib.request.urlopen(f"{url}/api/state", timeout=1.0).close()
            return True
        except urllib.error.HTTPError:
            return True  # the server is up
        except (urllib.error.URLError, OSError):
            time.sleep(0.1)
    return False


def run_app(app, host: str = "127.0.0.1", port: int = 7777, title: str = "gui4us",
            headless: bool = False, window: str = "auto", log_level: str = "info") -> int:
    """
    Serves the FastAPI application and shows it in a window; blocks until the window is closed (or Ctrl+C).

    :param headless: only serve (connect with a browser to ``http://host:port``)
    :param window: "auto" (embedded engine, then the app-mode browser, then the default browser),
      "webview" (embedded engine only), "browser" (the default browser)
    """
    from gui4us.view.web.server import serve_app

    if not headless and not has_display():
        LOGGER.warning("No display available (DISPLAY/WAYLAND_DISPLAY not set): running headless.")
        headless = True
    stop_requested = threading.Event()
    stop_handler = _StopSignalHandler(on_stop=lambda: _request_stop(stop_requested))
    server_thread = serve_app(app, host=host, port=port, background=True, log_level=log_level)
    url = get_local_url(host, port)
    try:
        if not wait_for_server(url, server_thread=server_thread):
            LOGGER.error(f"The gui4us server did not start ({url}).")
            return 1
        if not headless and not stop_requested.is_set():
            if window in ("auto", "webview") and _open_webview(url, title):
                return 0  # the window was closed
            if window == "webview":
                LOGGER.error("Could not open the embedded web view window (see the errors above).")
                return 1
            _open_browser(url, app_mode=(window == "auto"))
        LOGGER.info(f"gui4us is running: {url} (press Ctrl+C to stop)")
        while server_thread.is_alive() and not stop_requested.is_set():
            server_thread.join(timeout=0.5)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        stop_handler.close()
        server_thread.server.should_exit = True
        server_thread.join(timeout=5)


def _request_stop(stop_requested: threading.Event):
    """Stops run_app: closes the embedded window (if any), ends the serving loop."""
    stop_requested.set()
    try:
        import webview
        for w in list(webview.windows):
            w.destroy()
    except Exception:  # noqa: BLE001 - no pywebview / no window
        pass


class _StopSignalHandler:
    """
    Turns SIGTERM, SIGINT and SIGHUP into a graceful stop of run_app -- so that the caller closes the environment
    (the us4R: stops the acquisition) also when the process is killed (e.g. `kill`, `timeout`, a closed terminal).

    NOTE: the Python signal handlers run only in the main thread, and only when it executes Python code -- which the
    embedded window's event loop (C++) does not; so the signals are delivered via signal.set_wakeup_fd to a helper
    thread instead. Does nothing when not called from the main thread.
    """
    SIGNALS = tuple(getattr(signal, name) for name in ("SIGTERM", "SIGINT", "SIGHUP") if hasattr(signal, name))

    def __init__(self, on_stop):
        self._on_stop = on_stop
        self._previous = {}
        self._previous_fd = None
        self._reader = None
        self._active = threading.current_thread() is threading.main_thread()
        if not self._active:
            return
        for s in self.SIGNALS:
            self._previous[s] = signal.signal(s, self._on_signal)
        if sys.platform != "win32":
            self._reader, writer = os.pipe()
            os.set_blocking(writer, False)
            self._writer = writer
            self._previous_fd = signal.set_wakeup_fd(writer)
            threading.Thread(target=self._wait, name="gui4us-signals", daemon=True).start()

    def _on_signal(self, signum, frame):
        # Runs when the main thread executes Python code (e.g. the headless serving loop).
        LOGGER.info(f"Received signal {signum}, stopping gui4us.")
        self._on_stop()

    def _wait(self):
        try:
            while True:
                data = os.read(self._reader, 64)
                if not data:
                    return
                if any(b in self.SIGNALS for b in data):
                    LOGGER.info(f"Received signal {data[0]}, stopping gui4us.")
                    self._on_stop()
        except OSError:
            return

    def close(self):
        if not self._active:
            return
        self._active = False
        if self._reader is not None:
            signal.set_wakeup_fd(self._previous_fd if self._previous_fd is not None else -1)
            os.close(self._writer)
            os.close(self._reader)
        for s, handler in self._previous.items():
            signal.signal(s, handler)


def _open_webview(url: str, title: str) -> bool:
    """Shows the URL in an embedded web engine window; blocks until it is closed. False: not available."""
    try:
        import webview
    except ImportError:
        LOGGER.info("pywebview is not installed (pip install pywebview); using a browser window instead.")
        return False
    gui = None
    if sys.platform.startswith("linux"):
        # Prefer Qt WebEngine (PyQtWebEngine), fall back to pywebview's default choice (WebKitGTK).
        try:
            os.environ.setdefault("QT_API", "pyqt5")
            # The Qt WebEngine (Chromium) renderer sandbox does not start in many setups (e.g. pip/conda installed
            # PyQtWebEngine: "Zygote could not fork") and the window stays blank. The window shows only the local
            # gui4us page, so the sandbox is disabled by default; set QTWEBENGINE_DISABLE_SANDBOX=0 to keep it.
            os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
            import qtpy.QtWebEngineWidgets  # noqa: F401
            gui = "qt"
        except Exception:  # noqa: BLE001 - any import problem: let pywebview choose
            gui = None
    try:
        webview.create_window(title, url, width=WINDOW_SIZE[0], height=WINDOW_SIZE[1])
        webview.start(gui=gui)
        return True
    except Exception as e:  # noqa: BLE001 - e.g. no web engine backend available
        LOGGER.warning(f"Could not start the embedded web view ({type(e).__name__}: {e}).")
        return False


def _open_browser(url: str, app_mode: bool = True):
    """Opens the URL in a Chromium-based browser window in the app mode, if available, else in the default one."""
    if app_mode:
        for name in _APP_MODE_BROWSERS:
            path = shutil.which(name)
            if path is not None:
                try:
                    subprocess.Popen([path, f"--app={url}",
                                      f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    LOGGER.info(f"Opened {url} in {name} (app mode).")
                    return
                except OSError:
                    continue
    if webbrowser.open(url):
        LOGGER.info(f"Opened {url} in the default web browser.")
    else:
        LOGGER.warning(f"Could not open a web browser; open {url} manually.")
