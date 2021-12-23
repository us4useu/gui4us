import sys
import traceback

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


def start_view(*args):
    global APP
    APP = QApplication(sys.argv)
    APP.setStyle("Fusion")
    view = View(*args)
    view.show()
    return APP.exec_()


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
            self.display_panel = DisplayPanel(cfg.displays, controller, self)

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
            self.control_panel.actions_panel.add_on_start_stop_callback(
                self.on_start_stop_pressed)
            self.showMaximized()
            # self.adjustSize()
            # self.setFixedSize(self.size())

        except Exception as e:
            print(traceback.format_exc())
            print(e)
            self.controller.close()

    def on_start_stop_pressed(self):
        if self.state.is_current_state({"init", "stopped"}):
            self.state.do("start")
        else:
            self.state.do("stop")

    def on_init(self, event):
        self.control_panel.actions_panel.enable()
        self.control_panel.settings_panel.disable()
        self.control_panel.buffer_panel.disable()
        self.statusBar().showMessage(
            "Ready, press 'Start' button to start the hardware.")

    def on_init_start(self, event):
        self.statusBar().showMessage("Starting system.")
        self.on_started(event)

    def on_started(self, event):
        self.control_panel.settings_panel.enable()
        self.control_panel.buffer_panel.enable()
        self.display_panel.start()
        self.control_panel.buffer_panel.start()
        self.statusBar().showMessage("Running.")

    def on_stopped(self, event):
        self.control_panel.settings_panel.disable()
        self.control_panel.actions_panel.disable()
        self.statusBar().showMessage("Stopped.")

    def closeEvent(self, event):
        self.controller.close()
        event.accept()




