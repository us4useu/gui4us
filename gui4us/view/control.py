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
from gui4us.view.widgets import *
from gui4us.view.settings import SettingsPanel
from gui4us.view.capture_buffer import CaptureBufferComponent
from gui4us.state_graph import *


class ControlPanel(Panel):

    def __init__(self, title="Control panel"):
        super().__init__(title)
        self.actions_panel = ActionsPanel()
        self.buffer_panel = CaptureBufferComponent()
        self.settings_panel = SettingsPanel()
        self.panels = (
            self.actions_panel,
            self.buffer_panel,
            self.settings_panel
        )
        for panel in self.panels:
            self.add_component(panel)

    def on_start_stop(self, callback):
        self.actions_panel.on_start_stop(callback)

    def on_buffer_capture(self, callback):
        self.buffer_panel.__on_capture(callback)

    def on_buffer_save(self, callback):
        self.buffer_panel.on_save(callback)


class ActionsPanel(Panel):
    """
    Start, stop, previous, next panel.
    """
    def __init__(self, title="Actions"):
        super().__init__(title)
        # Action buttons
        self.start_stop_button = PushButton("Freeze")
        self.add_component(self.start_stop_button)

    def on_start_stop(self, callback):
        self.start_stop_button.on_pressed(callback)






