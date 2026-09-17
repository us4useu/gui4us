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


def start_view_app_for(env, view_cfg, capture_buffer_capacity: int, title: str):
    """Starts the Qt view for already loaded configuration objects.

    This is the entry point used by :class:`gui4us.Gui4us`; ``start_view_app`` (which loads the
    configuration from a directory) is kept for the command line.
    """
    return start_view_app(env=env, title=title, view_cfg=view_cfg,
                          capture_buffer_capacity=capture_buffer_capacity)


class View(QtWidgets.QMainWindow):
    """
    Main window view.
    """
    def __init__(self, title, cfg_path: str = None, view_cfg=None,
                 capture_buffer_capacity: int = None):
        """
        :param title: window title
        :param cfg_path: configuration directory (``display.py``, ``app.py``); the alternative
          to passing the configuration objects directly
        :param view_cfg: display configuration (``gui4us.cfg.ViewCfg``)
        :param capture_buffer_capacity: capture buffer size
        """
        super().__init__()
        if cfg_path is not None:
            self.cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
            self.app_cfg = load_cfg(os.path.join(cfg_path, "app.py"), "app")
            view_cfg = self.cfg.VIEW_CFG
            capture_buffer_capacity = self.app_cfg.CAPTURE_BUFFER_SIZE
        elif view_cfg is None:
            raise ValueError("Provide either cfg_path or view_cfg.")
        self.capture_buffer_capacity = capture_buffer_capacity
        self.view_cfg = view_cfg
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
            capture_buffer_capacity=self.capture_buffer_capacity)
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
