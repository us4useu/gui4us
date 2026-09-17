"""Application level settings.

The configuration-directory form of these settings is ``app.py`` (a module with
``CAPTURE_BUFFER_SIZE``); scripts pass an :class:`AppCfg` instance to
:class:`gui4us.Gui4us` instead.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AppCfg:
    """GUI4us application settings.

    :param capture_buffer_size: how many frames a capture holds by default
    :param title: window/page title
    :param max_fps: upper bound on the frame rate pushed to a view; the acquisition itself is
      not slowed down by it
    :param view: which view :meth:`gui4us.Gui4us.run` starts: "qt", "web" or None (no view --
      useful for scripts that only capture data)
    :param host: web view: address to bind to
    :param port: web view: port to listen on
    """
    capture_buffer_size: int = 100
    title: Optional[str] = None
    max_fps: float = 30.0
    view: Optional[str] = "qt"
    host: str = "127.0.0.1"
    port: int = 7777

    @staticmethod
    def from_module(module) -> "AppCfg":
        """Reads the settings from a loaded ``app.py``.

        Unknown attributes are ignored, missing ones keep their defaults, so old configuration
        directories keep working.
        """
        def get(name, default):
            return getattr(module, name, default)

        defaults = AppCfg()
        return AppCfg(
            capture_buffer_size=get("CAPTURE_BUFFER_SIZE", defaults.capture_buffer_size),
            title=get("TITLE", defaults.title),
            max_fps=get("MAX_FPS", defaults.max_fps),
            view=get("VIEW", defaults.view),
            host=get("HOST", defaults.host),
            port=get("PORT", defaults.port),
        )
