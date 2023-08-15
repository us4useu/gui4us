from typing import Optional, Dict
import panel as pn
import numpy as np

from gui4us.view.env.base import AbstractPanelView, Viewable
from gui4us.view.env.displays import (
    Display1D,
    Display2D,
)
from gui4us.view.env.panes import ControlPanel, EnvironmentSelector, ConsoleLog


class DummyView(AbstractPanelView):

    def __init__(self,
                 title: str,
                 app_url: str,
                 address: Optional[str] = None):
        super().__init__(
            title=title,
            app_url=app_url,
            address=address,
            # Force environment selection
            dialog_closable=False,
            dialog_autostart=False
        )

    def _create_control_panel(self) -> Viewable:
        return ControlPanel()

    def _create_displays(self) -> Dict[str, Viewable]:
        return {
            "display1": Display2D(),
            "display2": Display2D()
        }

    def _create_envs_panel(self) -> Viewable:
        return EnvironmentSelector()

    def _create_console_log_panel(self) -> Viewable:
        return ConsoleLog()







