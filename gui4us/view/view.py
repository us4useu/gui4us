import sys

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from gui4us.controller.controller import *
from gui4us.view.widgets import show_error_message
from gui4us.view.control import *
from gui4us.view.display import *
from gui4us.state_graph import *

APP = None
MAIN_WINDOW = None


def start_view(view):
    APP = QApplication(sys.argv)
    APP.setStyle("Fusion")
    view.show()
    return APP._exec()


class View(QtWidgets.QMainWindow):

    def __init__(self, title, cfg, controller: Controller):
        super().__init__()
        self.controller = controller
        self.text_format = Qt.MarkdownText
        self.statusBar().showMessage('Configuring...')
        try:
            self.setWindowTitle(title)
            # Main layout
            self.main_widget = QWidget()
            self.setCentralWidget(self.main_widget)
            self.main_layout = QHBoxLayout(self.main_widget)
            self.control_panel = ControlPanel(controller)
            self.display_panel = DisplayPanel(controller, cfg.displays)

            self.main_layout.addWidget(self.control_panel.backend_widget)
            self.main_layout.addWidget(self.display_panel.backend_widget)

            # Main application state, enter the init state.
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
            self.control_panel.actions_panel.on_start_stop(
                self.on_start_stop_pressed)

            # Buffer state graph
            self._create_buffer_state_graph()
            self._reset_capture_buffer()

            self.adjustSize()
            self.setFixedSize(self.size())

        except Exception as e:
            logging.exception(e)
            self._controller.close()

    def on_start_stop_pressed(self):
        if self.state.is_current_state({"init", "stopped"}):
            self.state.go("start")
        else:
            self.state.go("stop")

    def on_init(self, event):
        self.control_panel.disable()
        self._reset_capture_buffer()
        self._start_stop_button.setText("Start")
        self.statusBar().showMessage(
            "Ready, press 'Start' button to start the hardware.")

    def on_init_start(self, event):
        self.statusBar().showMessage("Starting system.")
        self._controller.start()
        self.on_started(event)

    def on_started(self, event):
        self._settings_panel.setEnabled(True)
        self._buffer_panel.setEnabled(True)
        self._reset_capture_buffer()
        self.thread.start(priority=QThread.TimeCriticalPriority)
        self._start_stop_button.setText("Freeze")
        self.statusBar().showMessage("Running.")

    def on_stopped(self, event):
        self._buffer_panel.setEnabled(False)
        self._settings_panel.setEnabled(False)
        self._start_stop_button.setText("Resume")
        self.statusBar().showMessage("Stopped.")




