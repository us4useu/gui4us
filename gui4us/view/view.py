

from gui4us.controller.controller import *
from gui4us.common import EventQueue
from gui4us.view.widgets import show_error_message
from gui4us.view.control import *
from gui4us.view.display import *
from gui4us.state_graph import *

# states
_INIT = "INIT"
_STARTED = "STARTED"
_STOPPED = "STOPPED"
_STATES = {_INIT, _STOPPED, _STARTED}

# actions
_START = "start"
_STOP = "stop"
_ACTIONS = {_START, _STOP}

# buffer state
_EMPTY = "EMPTY"
_CAPTURING = "CAPTURING"
_CAPTURED = "CAPTURED"

# buffer actions
_CAPTURE = "capture"
_SAVE = "save"
_CAPTURE_DONE = "capture_done"

_DYNAMIC_RANGE_STEP = 10
_VOLTAGE_STEP = 10






def close_model_and_controller(model, controller):
    if model is not None:
        try:
            model.close()
        except Exception as e:
            logging.exception(e)
        try:
            controller.close()
        except Exception as e:
            logging.exception(e)


class View(QtWidgets.QMainWindow):

    def __init__(self, title, event_queue: EventQueue):
        super().__init__()
        self.event_queue = event_queue
        self.text_format = Qt.MarkdownText
        self.statusBar().showMessage('Configuring...')
        try:
            self.setWindowTitle(title)
            # Main layout
            self.main_widget = QWidget()
            self.setCentralWidget(self.main_widget)
            self.main_layout = QHBoxLayout(self.main_widget)
            self.control_panel = ControlPanel()
            self.display_panel = DisplayPanel()

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
        self.on_started()

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

    def _on_voltage_change(self, value):
        # TODO make the setting voltage operation cheap (implement session controller)
        self._voltage_spin_box.setDisabled(True)
        controller.send(SetVoltageEvent(value))
        self._voltage_spin_box.setDisabled(False)
        self._voltage_spin_box.setFocus()

    def _on_tgc_slider_change(self):
        self._current_gain_value = self._slider.value() / 10 ** _TGC_SLIDER_PRECISION
        controller.send(SetGainEvent(self._current_gain_value))


