import os
from typing import Optional, Dict

from gui4us.controller.task import Promise
from gui4us.logging import get_logger
from gui4us.model import MetadataCollection
from gui4us.utils import load_cfg
from gui4us.view.env.base import AbstractPanelView, Viewable
from gui4us.controller.env import EnvironmentController

from gui4us.view.env.panes import ControlPanel, EnvironmentSelector, ConsoleLog
from gui4us.cfg.display import ViewCfg
import gui4us.cfg.display as display_cfg
import gui4us.view.env.displays as displays


class EnvironmentView(AbstractPanelView):

    def __init__(
            self,
            title: str,
            address: Optional[str],
            app_url: str,
            cfg_path: str,
            env: EnvironmentController,
    ):
        self.logger = get_logger(f"{type(self)}_{id(self)}")
        self.host_address = address
        self.displays = {}
        self.cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
        self.view_cfg: ViewCfg = self.cfg.VIEW_CFG
        self.env = env
        metadata_promise: Promise = self.env.get_stream_metadata()
        self.metadatas: MetadataCollection = metadata_promise.get_result()
        # Intentionally calling superclass constructor here.
        # note: some of the above properties are required on components
        # initialization.
        super().__init__(title=title, app_url=app_url, address=address)

    def run(self):
        super().run()
        for _, display in self.displays.items():
            display.start()

    def join(self):
        super().join()
        for _, d in self.displays.items():
            d.join()

    def _create_control_panel(self) -> Viewable:
        return ControlPanel()

    def _create_displays(self) -> Dict[str, Viewable]:
        cfg_to_clz = {
            display_cfg.Display2D: displays.Display2D,
            display_cfg.Display3D: displays.Display3D
        }
        for key, cfg in self.view_cfg.displays.items():
            display_clz = cfg_to_clz[type(cfg)]
            self.displays[key] = display_clz(
                cfg=cfg,
                host=self.host_address,
                metadatas=self.metadatas,
            )
        return self.displays

    def _create_envs_panel(self) -> Viewable:
        return EnvironmentSelector()

    def _create_console_log_panel(self) -> Viewable:
        return ConsoleLog()


