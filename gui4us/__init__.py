"""GUI4us -- a front end framework for ultrasound application prototyping.

Used as a library::

    from gui4us import AppCfg, Gui4us

    gui = Gui4us(env=..., display=..., app=AppCfg(capture_buffer_size=100))

or from the command line::

    gui4us --cfg <configuration directory> [--view qt|web]
"""

from gui4us.version import __version__
from gui4us.cfg.app import AppCfg
from gui4us.gui import Gui4us
from gui4us.__main__ import main

__all__ = ["AppCfg", "Gui4us", "main", "__version__"]
