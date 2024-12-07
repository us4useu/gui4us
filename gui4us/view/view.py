import sys
import enum
import threading

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMenu
from PyQt5 import QtWidgets

from gui4us.controller.app import *
from gui4us.view.control import *
from gui4us.view.display import *
from gui4us.state_graph import *
from gui4us.cfg.display import *
import gui4us.version
from gui4us.view.env import EnvironmentView

APP = None


def start_view_app(env, **view_kwargs):
    global APP
    APP = QApplication(sys.argv)
    APP.setStyle("Fusion")
    view = View(**view_kwargs)
    view.set_environment("main", env)
    view.show()
    return APP.exec_()


class View(QtWidgets.QMainWindow):
    """
    Main window view.
    """
    def __init__(self, title, cfg_path: str):
        super().__init__()
        self.cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
        self.app_cfg = load_cfg(os.path.join(cfg_path, "app.py"), "app")
        self.view_cfg = self.cfg.VIEW_CFG
        self.env_views: Dict[EnvId, EnvironmentView] = {}
        self.text_format = Qt.MarkdownText
        self.statusBar().showMessage('Configuring...')
        self.setWindowTitle(title)
        # Create and adjust main layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        self.control_panel_placeholder = QGroupBox("Control panel")
        self.display_placeholder = QGroupBox("Display")
        self.size_policy_control = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred)
        self.size_policy_display = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred)
        self.size_policy_control.setHorizontalStretch(1)
        self.size_policy_display.setHorizontalStretch(4)

        self.control_panel_placeholder.setSizePolicy(self.size_policy_control)
        self.display_placeholder.setSizePolicy(self.size_policy_display)

        self.main_layout.addWidget(self.control_panel_placeholder)
        self.main_layout.addWidget(self.display_placeholder)
        self.current_control_panel = self.control_panel_placeholder
        self.current_display = self.display_placeholder
        # Main application state, enter the init state.
        self.statusBar().showMessage("Open environment to start.")
        # screen_size = APP.primaryScreen().size()
        # height, width = screen_size.height(), screen_size.width()
        # height, width = 3 * height // 4, 3 * width // 4
        # self.setMinimumSize(width, height)
        # self.showMaximized()
        # self.showFullScreen()

    def set_environment(
            self,
            id: EnvId,
            env: EnvController
    ):
        env_view = EnvironmentView(
            self, view_cfg=self.view_cfg, env=env,
            capture_buffer_capacity=self.app_cfg.CAPTURE_BUFFER_SIZE)
        self.env_views[id] = env_view
        self.main_layout.replaceWidget(self.current_control_panel,
                                   env_view.control_panel.backend_widget)
        self.main_layout.replaceWidget(self.current_display,
                                   env_view.display_panel.backend_widget)
        self.current_control_panel.hide()
        self.current_display.hide()
        self.current_control_panel = env_view.control_panel
        self.current_display = env_view.display_panel
        self.current_control_panel.backend_widget.setSizePolicy(
            self.size_policy_control)
        self.current_display.backend_widget.setSizePolicy(
            self.size_policy_display)
