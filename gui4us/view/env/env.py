import os
from typing import Optional

from gui4us.utils import load_cfg
from gui4us.view.env.base import AbstractPanelView, Viewable
from gui4us.controller.env import EnvironmentController


class EnvironmentView(AbstractPanelView):

    def __init__(
            self,
            title: str,
            cfg_path: str,
            env: EnvironmentController,
            address: Optional[str] = None
    ):
        super().__init__(title=title, address=address)
        self.cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
        self.view_cfg = self.cfg.VIEW_CFG
        self.env = env

    def _create_viewable(self) -> Viewable:
        raise NotImplementedError()
