import sys

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMenu

from gui4us.controller.controller import *
from gui4us.view.control import *
from gui4us.view.display import *
from gui4us.state_graph import *
from gui4us.cfg.environment import *
from gui4us.cfg import *

APP = None


def start_view(*args):
    global APP
    APP = QApplication(sys.argv)
    APP.setStyle("Fusion")
    view = View(*args)
    view.show()
    return APP.exec_()


class EnvironmentView:

    def __init__(self, parent, cfg, controller: EnvController):
        self.parent = parent
        self.controller = controller
        self.display_panel = DisplayPanel(cfg.displays, controller, self.parent)
        self.control_panel = ControlPanel(controller, self.display_panel)
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

    def on_start_stop_pressed(self):
        if self.state.is_current_state({"init", "stopped"}):
            self.state.do("start")
        else:
            self.state.do("stop")

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
        self.on_started(event)

    def on_started(self, event):
        self.control_panel.settings_panel.enable()
        self.control_panel.buffer_panel.enable()
        self.display_panel.start()
        self.control_panel.buffer_panel.start()
        self.statusBar().showMessage("Running.")

    def on_stopped(self, event):
        self.control_panel.settings_panel.disable()
        # self.control_panel.actions_panel.disable()
        self.statusBar().showMessage("Stopped.")

    def closeEvent(self, event):
        self.controller.close()
        event.accept()


class View(QtWidgets.QMainWindow):
    """
    Main window view.
    """

    _PICKLE_EXTENSION = "Python pickle dataset (*.pkl)"
    _PYTHON_EXTENSION = "Python configuration file (*.py)"

    _FILE_EXTENSIONS = ";;".join([
        _PYTHON_EXTENSION, _PICKLE_EXTENSION,
    ])

    def __init__(self, title, controller: MainController):
        super().__init__()
        self.controller = controller
        self.env_views = {}
        self.text_format = Qt.MarkdownText
        self.statusBar().showMessage('Configuring...')
        try:
            self.setWindowTitle(title)
            self.create_menu_bar()
            # Main layout
            self.main_widget = QWidget()
            self.setCentralWidget(self.main_widget)
            self.main_layout = QHBoxLayout(self.main_widget)

            self.control_panel_placeholder = QGroupBox("Control panel")
            self.display_placeholder = QGroupBox("Display")
            self.size_policy_control = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                                        QtWidgets.QSizePolicy.Policy.Preferred)
            self.size_policy_display = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
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
            screen_size = APP.primaryScreen().size()
            height, width = screen_size.height(), screen_size.width()
            height, width = 3*height//4, 3*width//4
            self.setMinimumSize(width, height)

        except Exception as e:
            print(traceback.format_exc())
            print(e)
            self.controller.close()

    def create_menu_bar(self):
        self.actions = {}
        menuBar = self.menuBar()

        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        self.actions["open_env"] = QAction("&Open...", self)
        self.actions["open_env"].triggered.connect(self.open_environment_menu_action)
        fileMenu.addAction(self.actions["open_env"])

        helpMenu = QMenu("&Help", self)
        menuBar.addMenu(helpMenu)
        self.actions["about"] = QAction("About", self)
        self.actions["about"].triggered.connect(self.show_about)
        helpMenu.addAction(self.actions["about"])

    def open_environment_menu_action(self):
        filename, extension = QFileDialog.getOpenFileName(
            parent=None, caption="Save File", directory=".",
            filter=View._FILE_EXTENSIONS)
        self.open_environment(filename, extension)

    def show_about(self):
        QMessageBox.about(self, "About", "gui4us v0.2.0-dev")

    def open_environment(self, path, extension):
        name = path
        if extension == View._PICKLE_EXTENSION:
            import pickle
            data = pickle.load(open(path, "rb"))
            if "data" not in data.keys() or "metadata" not in data.keys():
                QtWidgets.QErrorMessage().showMessage(
                    "Invalid .pkl file (should contain 'data' and 'metadata' fields)")
            else:
                env_cfg = DatasetEnvironment(input=data)
                env = self.controller.open_environment(name, env_cfg)
                display_cfgs = {}
                display_cfgs[f"output_0"] = Display2D(
                    title=f"output_0",
                    layers=(Layer2D(input=LiveDataId("default", 0), cmap="gray"), ))
                env_view = EnvironmentView(self, cfg=ViewCfg(display_cfgs),
                                           controller=env)
                self.env_views[name] = env_view
        elif extension == View._PYTHON_EXTENSION:
            cfg = load_cfg(path)
            env = self.controller.open_environment(path, path)
            env_view = EnvironmentView(self, cfg=cfg.view_cfg, controller=env)
            self.env_views[name] = env_view
        else:
            QtWidgets.QErrorMessage().showMessage(f"Unsupported file type {extension}")
        self.set_environment(name)

    def set_environment(self, name):
        env_view = self.env_views[name]
        self.main_layout.replaceWidget(self.current_control_panel,
                                       env_view.control_panel.backend_widget)
        self.main_layout.replaceWidget(self.current_display,
                                       env_view.display_panel.backend_widget)
        self.current_control_panel.hide()
        self.current_display.hide()
        self.current_control_panel = env_view.control_panel
        self.current_display = env_view.display_panel
        self.current_control_panel.backend_widget.setSizePolicy(self.size_policy_control)
        self.current_display.backend_widget.setSizePolicy(self.size_policy_display)
