import sys

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMenu

from gui4us.logging import get_logger
from gui4us.controller.app import *
from gui4us.view.control import *
from gui4us.view.display import *
from gui4us.state_graph import *
from gui4us.cfg.environment import *
from gui4us.cfg import *
from gui4us.cfg.display import *


class EnvironmentView:
    """
    A component responsible for controlling and displaying
    a single environment.
    """

    def __init__(self, parent, view_cfg: ViewCfg, env: EnvController,
                 capture_buffer_capacity: int):
        self.logger = get_logger(f"{type(self)}_id")
        self.parent = parent
        self.env = env
        self.display_panel = DisplayPanel(
            view_cfg,
            self.env,
            self.parent
        )
        self.control_panel = ControlPanel(
            self.env,
            capture_buffer_capacity=capture_buffer_capacity
        )
        self.state_graph = StateGraph(
            states={
                State("init", on_enter=self.on_init),
                State("started"),
                State("stopped")
            },
            actions={
                Action("start"),
                Action("stop")
            },
            transitions={
                Transition("init", "start", "started", self.on_init_start),
                Transition("started", "stop", "stopped", self.on_stopped),
                Transition("stopped", "start", "started", self.on_started)
            }
        )
        self.state = StateGraphIterator(
            self.state_graph, start_state="init")
        # Register callbacks to be called when some events occur.
        self.control_panel.actions_panel.add_on_start_stop_callback(
            self.on_start_stop_pressed
        )

    def on_start_stop_pressed(self):
        if self.state.is_current_state({"init", "stopped"}):
            # is_continue: whether the transition from the step to step
            # was actually performed.
            return self.state.do("start").is_continue
        else:
            return self.state.do("stop").is_continue

    def statusBar(self):
        return self.parent.statusBar()

    def on_init(self, event):
        self.control_panel.actions_panel.enable()
        self.control_panel.settings_panel.disable()
        # self.control_panel.buffer_panel.disable()
        self.statusBar().showMessage(
            "Ready, press 'Start' button to start the hardware.")

    def on_init_start(self, event):
        self.statusBar().showMessage("Starting system.")
        try:
            self.env.start()
        except Exception as e:
            self.logger.exception(e)
            self.statusBar().showMessage(
                f"Exception '{e}' while starting environment, "
                f"please check logs for more details.")
            event.stop()
            return
        self.on_started(event)

    def on_started(self, event: Event):
        self.control_panel.settings_panel.enable()
        # self.control_panel.buffer_panel.enable()  # TODO
        self.display_panel.start()
        # self.control_panel.buffer_panel.start()  # TODO
        self.statusBar().showMessage("Running.")

    def on_stopped(self, event):
        """
        Actually, this method is to freeze the current display.
        TODO this should be a proper stop after migrating
        from matplotlib to some vtk-like library
        """
        self.display_panel.stop()
        self.control_panel.settings_panel.disable()
        # self.control_panel.actions_panel.disable()
        self.statusBar().showMessage("Stopped.")

    def closeEvent(self, event):
        self.env.close()
        event.accept()
