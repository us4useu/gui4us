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


from gui4us.view.widgets import *
from gui4us.view.settings import SettingsPanel
from gui4us.view.capture_buffer import CaptureBufferComponent
from gui4us.state_graph import *


class ControlPanel(Panel):

    def __init__(self, controller, title="Control panel"):
        super().__init__(title)
        self.controller = controller
        self.actions_panel = ActionsPanel(controller)
        self.buffer_panel = CaptureBufferComponent(controller)
        settings = self.controller.get_settings().get_result()

        self.settings_panel = SettingsPanel(
            controller,
            settings=settings,
        )
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
    def __init__(self, controller, title="Actions"):
        super().__init__(title)
        self.controller = controller
        # Action buttons
        self.start_stop_button = PushButton("Start")
        self.add_component(self.start_stop_button)
        self.start_stop_button.on_pressed(callback=self.on_start_stop)
        self.on_start_stop_callbacks = []
        self.is_started = False

    def on_start_stop(self, *args):
        if self.is_started:
            self.controller.stop()
            self.start_stop_button.set_text("Start")
        else:
            self.controller.start()
            self.start_stop_button.set_text("Freeze")
        for callback in self.on_start_stop_callbacks:
            callback()

    def add_on_start_stop_callback(self, callback):
        self.on_start_stop_callbacks.append(callback)
