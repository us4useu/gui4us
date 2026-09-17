"""GUI4us in Jupyter.

The notebook view reuses the components of the web view (``ui/src/components``) through
anywidget, and runs the session in the kernel, so captured data lands directly in notebook
variables::

    from gui4us.view.jupyter import NotebookView

    view = NotebookView("/path/to/cfg")
    view                       # displays + control + action panels
    view.start()
    frames = view.capture(50)  # list[tuple[np.ndarray, ...]]

See docs/design/web_view.md.
"""

from gui4us.view.jupyter.widgets import (
    ActionsPanel,
    CapturePanel,
    ControlPanel,
    NotebookView,
    StreamDisplay,
)

__all__ = ["ActionsPanel", "CapturePanel", "ControlPanel", "NotebookView", "StreamDisplay"]
