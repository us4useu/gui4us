import os
import threading
from multiprocessing.pool import ThreadPool
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
from collections import defaultdict


class EnvironmentView(AbstractPanelView):

    def __init__(
            self,
            title: str,
            address: Optional[str],
            app_url: Optional[str],
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
        self.metadata_by_display = self._split_metadata_by_display(
            m=self.metadatas,
            view_cfg=self.view_cfg
        )
        self.ordinals_by_display = self._get_ordinals_by_display(
            self.view_cfg
        )
        # Intentionally calling superclass constructor here.
        # note: some of the above properties are required on components
        # initialization.
        super().__init__(title=title, app_url=app_url, address=address)
        self.stream = env.get_stream()
        self.stream.append_on_new_data_callback(self._update)
        self.workers_pool = None

    def run(self):
        super().run()
        # +1 is heuristic
        # self.workers_pool = ThreadPool(processes=10)
        # self.update_callbacks = [lambda data: d.update(data) for _, d in self.displays.items()]
        # print(self.update_callbacks)
        for _, display in self.displays.items():
            display.start()

    def join(self):
        super().join()
        for _, d in self.displays.items():
            d.join()

    def _create_control_panel(self) -> Viewable:
        control_panel = ControlPanel(self.env)
        control_panel.set_start_stop_button_callback(
            start_callback=self._start_controller,
            stop_callback=self._stop_controller
        )
        return control_panel

    def _start_controller(self):
        self.env.start()

    def _stop_controller(self):
        self.env.stop()

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
                metadatas=self.metadata_by_display[key],
                align="center",
                sizing_mode="stretch_both"
            )
        return self.displays

    def _create_envs_panel(self) -> Viewable:
        return EnvironmentSelector()

    def _create_console_log_panel(self) -> Viewable:
        return ConsoleLog()

    def _split_metadata_by_display(
            self,
            m: MetadataCollection,
            view_cfg: ViewCfg
    ):
        """
        The returned lists are sorted by display layer order.
        """
        displays = view_cfg.displays
        result = defaultdict(list)
        for id, display in displays.items():
            # TODO make the 3D display multi-layered
            if isinstance(display, display_cfg.Display3D):
                result[id].append(m.output(display.input))
            else:
                for layer in display.layers:
                    result[id].append(m.output(layer.input))
        return result

    def _update(self, data):
        for display_id, display in self.displays.items():
            # For that display, get outputs in the proper order.
            ordinals = self.ordinals_by_display[display_id]
            display_data = [data[o] for o in ordinals]
            threading.Thread(target=lambda: display.update(display_data)).start()
            # self.workers_pool.apply_async(lambda: display.update(display_data))
            # display.update(display_data)

    def _get_ordinals_by_display(self, view_cfg: ViewCfg):
        result = {}
        for k, display in view_cfg.displays.items():
            # TODO make 3D display multi-layered
            if isinstance(display, display_cfg.Display3D):
                ordinals = [display.input.ordinal]
            elif isinstance(display, display_cfg.Display2D):
                ordinals = [l.input.ordinal for l in display.layers]
            else:
                raise ValueError(f"Unsupported display configuration: {display}")
            result[k] = ordinals
        return result

    def _get_total_number_of_workers(self, displays):
        result = 0
        for k, display in displays.items():
            if isinstance(display, display_cfg.Display3D):
                result += 1
            else:
                for l in display.layers:
                    result += 1
        print(f"Number of workers: {result}")
        return result

