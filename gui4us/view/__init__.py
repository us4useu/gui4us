"""GUI4us views.

Two view implementations share the model/controller layers:

* the PyQt one (``gui4us.view.view``), started by :func:`start_view_app` -- the default;
* the browser/Jupyter one (``gui4us.view.web``, ``gui4us.view.jupyter``).

``View`` and ``start_view_app`` are resolved lazily so that importing the web or the notebook
view does not require PyQt to be installed.
"""

__all__ = ["View", "start_view_app"]

_QT_NAMES = {"View", "start_view_app", "APP"}


def __getattr__(name):
    # PEP 562: keep `from gui4us.view import View, start_view_app` working, without importing
    # PyQt for users of the web view.
    if name in _QT_NAMES:
        from gui4us.view import view as _view
        return getattr(_view, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
