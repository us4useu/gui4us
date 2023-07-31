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
        data = np.load("/home/pjarosik/data/ats_549_cysta_p_15db.npy")
        frame1 = np.clip(20*np.log10(np.abs(data[:])), a_min=30, a_max=80)
        return {
            "display1": Display2D(frame1[80].T),
            "display2": Display2D(frame1[:, 80].T)
        }

    def _create_envs_panel(self) -> Viewable:
        return EnvironmentSelector()

    def _create_console_log_panel(self) -> Viewable:
        return ConsoleLog()







