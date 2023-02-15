from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (
    QPushButton,
    QSlider,
    QSpinBox,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QDoubleSpinBox
)
from PyQt5.QtCore import pyqtSlot

from gui4us.controller.env import EnvController
from gui4us.model import Env

from gui4us.view.widgets import *
from gui4us.view.settings import SettingsPanel
from gui4us.view.capture_buffer import CaptureBufferComponent
from gui4us.state_graph import *
from typing import Callable


class ControlPanel(Panel):

    def __init__(self, env: EnvController, capture_buffer_capacity: int,
                 title: str = "Control panel"):
        super().__init__(title)
        self.env = env
        self.actions_panel = ActionsPanel()
        self.buffer_panel = CaptureBufferComponent(
            env,
            capture_buffer_capacity=capture_buffer_capacity)

        self.settings_panel = SettingsPanel(env)
        # Settings panel should take all the available space.
        self.settings_panel.layout.insertStretch(-1, 1)
        self.panels = (
            self.actions_panel,
            self.buffer_panel,
            self.settings_panel
        )
        for panel in self.panels:
            self.add_component(panel)


class ActionsPanel(Panel):
    """
    Start, stop, previous, next panel.
    """
    def __init__(self, title="Actions"):
        super().__init__(title)
        # Action buttons
        self.start_stop_button = PushButton("Start")
        self.add_component(self.start_stop_button)
        self.start_stop_button.on_pressed(callback=self.on_start_stop)
        self.on_start_stop_callbacks = []
        self.is_started = False

    def on_start_stop(self, *args):
        for callback in self.on_start_stop_callbacks:
            is_continue = callback()
            if not is_continue:
                # Stop executing callbacks and keep the current state.
                return
        if not self.is_started:
            self.is_started = True
            self.start_stop_button.set_text("Freeze")
        else:
            self.is_started = False
            self.start_stop_button.set_text("Start")

    def add_on_start_stop_callback(self, callback: Callable[[], bool]):
        """
        Adds callback to be run when the start/stop button is pressed.
        The callback function should return True if it was executed
        """
        def callback_wrapper():
            try:
                return callback()
            except:
                return False

        self.on_start_stop_callbacks.append(callback_wrapper)
