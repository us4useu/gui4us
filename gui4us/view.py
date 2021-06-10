"""gui4us main script"""

__version__ = "0.0.1"
NAME = "GUI4us-FMC"

import sys
import time
import datetime
import numpy as np
import yaml
import glob, os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (
    QApplication,
    QPushButton,
    QLabel,
    QSlider,
    QSpinBox,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QWidget,
    QMenuBar,
    QFileDialog,
    QMessageBox,
    QDoubleSpinBox
)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.backends.qt_compat import QtCore, QtWidgets

from matplotlib.figure import Figure

from gui4us.model import ArrusModel
from gui4us.controller import (
    Controller,
    Event,
    SetVoltageEvent,
    SetGainEvent
)
import logging
import scipy.io
import traceback

logging_file_handler = logging.FileHandler(filename="gui4us.log")
# logging_stderr_handler = logging.StreamHandler(sys.stderr)
logging_handlers = [logging_file_handler]# , logging_stderr_handler]
logging.basicConfig(level=logging.INFO, handlers=logging_handlers)

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

_DYNAMIC_RANGE = (0, 120)
_DYNAMIC_RANGE_MIN_DIFF = 10
_DYNAMIC_RANGE_STEP = 10
_VOLTAGE_STEP = 10
_TGC_SLIDER_PRECISION = 2

# Supported file extensions
_NUMPY_FILE_EXTENSION = "Numpy file (*.npz)"
_MAT_FILE_EXTENSION = "MATLAB file (*.mat)"

_FILE_EXTENSION_STR = ";;".join([_NUMPY_FILE_EXTENSION])

_INTERVAL = 50  # [ms]


class ViewWorker(QObject):

    def __init__(self, func):
        super().__init__()
        self.func = func
        self.is_working = False

    @pyqtSlot()
    def run(self):
        # TODO sync point
        self.is_working = True
        while self.is_working:
            self.func()


class CaptureBuffer:

    def __init__(self, size):
        self.size = size
        self._counter = 0
        self._data = []

    def append(self, data):
        self._data.append(data)
        self._counter += 1

    def is_ready(self):
        return self.size == self._counter

    @property
    def data(self):
        return self._data


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


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, title, controller: Controller):
        super().__init__()

        self.statusBar().showMessage('Configuring...')
        self._controller = controller
        try:
            self.rf_buffer_size = self._controller.settings["capture_buffer_size"]
            self._text_format = Qt.MarkdownText
            self.setWindowTitle(title)
            # Main layout
            self._central_widget = QWidget()
            self.setCentralWidget(self._central_widget)
            self._main_layout = QHBoxLayout(self._central_widget)
            # Control panel
            self._control_panel = self._create_control_panel()
            # Display panel
            self._display_panel = self._create_display_panel()
            # Main layout
            # Left
            self._main_layout.addWidget(self._control_panel)
            # Right
            self._main_layout.addWidget(self._display_panel)

            # Application state graph
            self._create_state_graph()
            self._current_state = _INIT
            self._on_init()

            # Buffer state graph
            self._create_buffer_state_graph()
            self._reset_capture_buffer()
            self.adjustSize()
            self.setFixedSize(self.size())

            # Create worker thread
            self.thread = QThread()
            self.worker = ViewWorker(self._update_canvas)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self._last_rf_trigger = None

        except Exception as e:
            logging.exception(e)
            self._controller.close()

    def _create_control_panel(self):
        control_panel = QGroupBox("Control panel")
        control_panel_layout = QVBoxLayout()
        control_panel.setLayout(control_panel_layout)

        # Actions
        self._actions = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        self._actions.setLayout(actions_layout)
        control_panel_layout.addWidget(self._actions)
        # Action buttons
        self._start_stop_button = self._create_push_button(
            "Freeze", self._on_start_stop_button_pressed, actions_layout)

        # Buffer
        self._buffer_panel = QGroupBox("Capture buffer")
        buffer_panel_layout = QVBoxLayout()
        self._buffer_panel.setLayout(buffer_panel_layout)
        control_panel_layout.addWidget(self._buffer_panel)
        # Action buttons
        self._capture_button = self._create_push_button(
            "Capture", self._on_capture_button_pressed, buffer_panel_layout)
        self._save_data_button = self._create_push_button(
            "Save", self._on_save_button_pressed, buffer_panel_layout)

        # Settings
        self._settings_panel = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        self._settings_panel.setLayout(settings_layout)
        control_panel_layout.addWidget(self._settings_panel)

        settings_form_layout = QFormLayout()
        settings_layout.addLayout(settings_form_layout)

        self._voltage_spin_box = self._create_spin_box(
            range=(self._controller.settings["min_voltage"],
                   self._controller.settings["max_voltage"]),
            value=self._controller.settings["tx_voltage"],
            step=_VOLTAGE_STEP,
            on_change=self._on_voltage_change,
            line_edit_read_only=True
        )

        self._add_setting_form_field(
            layout=settings_form_layout,
            name="Transmit voltage", unit="V",
            widget=self._voltage_spin_box)

        # TGC editor
        control_panel_tgc_layout = QFormLayout()
        settings_layout.addLayout(control_panel_tgc_layout)
        control_panel_tgc_layout.addRow("", None)

        tgc_value_range = (
            self._controller.settings["min_tgc"],
            self._controller.settings["max_tgc"]
        )
        self._slider = self._create_tgc_slider(
            tgc_value_range,
            self._controller.settings["tgc_start"],
            self._on_tgc_slider_change)
        control_panel_tgc_layout.addRow("Gain: ", self._slider)
        settings_layout.addStretch()
        return control_panel

    def _create_display_panel(self):
        settings = self._controller.settings
        display_panel_widget = QGroupBox("RF data")
        display_panel_layout = QHBoxLayout()
        display_panel_widget.setLayout(display_panel_layout)
        img_canvas = FigureCanvas(Figure(figsize=(6, 6)))
        self.addToolBar(QtCore.Qt.BottomToolBarArea,
                        NavigationToolbar(img_canvas, self))

        display_panel_layout.addWidget(img_canvas)
        ax = img_canvas.figure.subplots()
        ax.set_xlabel("Azimuth [mm]")
        ax.set_ylabel("Acquisition time [us]")
        ax.set_title("Press start button...")
        self.extent_ox = np.array(settings["image_extent_ox"]) * 1e3
        self.extent_oz = np.array(settings["image_extent_oz"])
        self._current_gain_value = settings["tgc_start"]

        empty_input = np.zeros((settings["n_pix_oz"], settings["n_pix_ox"]), dtype=np.float32)
        self.img_canvas = ax.imshow(empty_input, cmap="gray",
                                    vmin=-16000, vmax=16000,
                                    extent=[self.extent_ox[0], self.extent_ox[1],
                                            self.extent_oz[1], self.extent_oz[0]])
        alphas = np.zeros((settings["n_pix_oz"], settings["n_pix_ox"]), dtype=np.float32)
        self.img_canvas2 = ax.imshow(empty_input, cmap="YlOrRd", vmin=0, vmax=2,
                                     extent=[self.extent_ox[0], self.extent_ox[1],
                                             self.extent_oz[1], self.extent_oz[0]])
        # self.img_canvas.figure.colorbar(self.img_canvas)
        self.img_canvas.figure.tight_layout()
        return display_panel_widget

    def _create_push_button(self, label, onpressed=None, layout=None):
        button = QPushButton(label)
        if onpressed is not None:
            button.pressed.connect(onpressed)
        if layout is not None:
            layout.addWidget(button)
        return button

    def _add_setting_form_field(self, layout, widget, name: str,
                                unit: str=""):
        label = name
        if unit:
            label = f"{name} [{unit}]:"
        layout.addRow(label, widget)

    def _create_spin_box(self, range, step, value, on_change=None,
                         line_edit_read_only=False, data_type="int"):
        if data_type == "int":
            spin_box = QSpinBox()
        elif data_type == "double":
            spin_box = QDoubleSpinBox()
        minimum, maximum = range
        spin_box.setRange(minimum, maximum)
        spin_box.setSingleStep(step)
        spin_box.setValue(value)
        if line_edit_read_only:
            spin_box.lineEdit().setReadOnly(True)
        if on_change is not None:
            spin_box.valueChanged.connect(on_change)
        return spin_box

    def _create_tgc_slider(self, range, value, on_change=None):
        slider = QSlider(Qt.Horizontal)
        def rescale(value):
            return int(round(value * 10 ** _TGC_SLIDER_PRECISION))
        # range
        slider.setMinimum(rescale(range[0]))
        slider.setMaximum(rescale(range[1]))
        # value
        slider.setValue(rescale(value))
        # Do not signal each slider move
        slider.setTracking(False)
        if on_change is not None:
            slider.valueChanged.connect(on_change)
        return slider

    def _update_canvas(self):
        try:
            if self._current_state == _STARTED:
                data_mask = self._controller.get_defect_mask().T
                rf_sum = self._controller.get_rf_sum().T
                rf = self._controller.get_rf()

                if self._current_state == _STOPPED or rf is None or rf_sum is None:
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return

                if self._rf_buffer_state == _CAPTURING:
                    current_trigger = rf[0, 0]

                    data_correctness_msg = "correct"
                    if self._last_rf_trigger is not None:
                        trigger_diff = current_trigger - self._last_rf_trigger
                        if trigger_diff != 32:
                            data_correctness_msg = f"INCORRECT (trigger difference: {trigger_diff})"

                    self._last_rf_trigger = current_trigger

                    self.statusBar().showMessage(f"Captured frame {len(self._rf_buffer.data)}, "
                                                 f"current trigger: {current_trigger}, "
                                                 f"data: {data_correctness_msg}")

                    # bmode, mask, RF, gain, voltage
                    self._rf_buffer.append((rf_sum, data_mask, rf, self._current_gain_value,
                                            self._voltage_spin_box.value()))
                    if self._rf_buffer.is_ready():
                        self._last_rf_trigger = None
                        self._update_buffer_state_graph(_CAPTURE_DONE)
                self.img_canvas.axes.set_title(f"FMC, gain: {self._current_gain_value} [dB]")
                self.img_canvas.set_data(rf_sum)
                self.img_canvas2.set_data(data_mask)
                alpha = (data_mask != 0.0).astype(np.float32)
                self.img_canvas2.set_alpha(alpha)
                self.img_canvas.figure.canvas.draw()
        except Exception as e:
            print(e)

    # Application state.
    def _create_state_graph(self):
        self._state_transitions = {
            _INIT: {
                _START: {
                    "callback": self._on_init_start,
                    "dst_state": _STARTED
                }
            },
            _STOPPED: {
                _START: {
                    "callback": self._on_started,
                    "dst_state": _STARTED
                }
            },
            _STARTED: {
                _STOP: {
                    "callback": self._on_stopped,
                    "dst_state": _STOPPED
                }
            }
        }

    def _on_start_stop_button_pressed(self):
        if self._current_state in {_INIT, _STOPPED}:
            self._update_graph_state(_START)
        else:
            self._update_graph_state(_STOP)

    def _on_init(self):
        self._settings_panel.setEnabled(False)
        self._buffer_panel.setEnabled(False)
        self._reset_capture_buffer()
        self._start_stop_button.setText("Start")
        self.statusBar().showMessage(
            "Ready, press 'Start' button to start the hardware.")
        return True

    def _on_init_start(self):
        self.statusBar().showMessage("Starting system.")
        self._controller.start()
        self._on_started()
        return True

    def _on_started(self):
        self._settings_panel.setEnabled(True)
        self._buffer_panel.setEnabled(True)
        self._reset_capture_buffer()
        self.thread.start(priority=QThread.TimeCriticalPriority)
        self._start_stop_button.setText("Freeze")
        self.statusBar().showMessage("Running.")
        return True

    def _on_stopped(self):
        self._buffer_panel.setEnabled(False)
        self._settings_panel.setEnabled(False)
        self._start_stop_button.setText("Resume")
        self.statusBar().showMessage("Stopped.")
        return True

    def _update_graph_state(self, action):
        self._current_state = self._update_state(
            self._state_transitions, self._current_state, action)

    # Capture buffer
    def _create_buffer_state_graph(self):
        self._rf_buffer_state_transitions = {
            _EMPTY: {
                _CAPTURE: {
                    "callback": self._on_capture_start,
                    "dst_state": _CAPTURING
                }
            },
            _CAPTURING: {
                # Reset the capture buffer
                _CAPTURE: {
                    "callback": self._on_capture_start,
                    "dst_state": _CAPTURING
                },
                _CAPTURE_DONE: {
                    "callback": self._on_capture_end,
                    "dst_state": _CAPTURED
                },
                _SAVE: {
                    "callback": self._on_save,
                    "dst_state": _EMPTY
                }
            },
            _CAPTURED: {
                _CAPTURE: {
                    "callback": self._on_capture_start,
                    "dst_state": _CAPTURING
                },
                _SAVE: {
                    "callback": self._on_save,
                    "dst_state": _EMPTY
                }
            }
        }

    def _on_capture_button_pressed(self):
        self._rf_buffer_state = self._update_state(
            self._rf_buffer_state_transitions, self._rf_buffer_state, _CAPTURE)

    def _on_save_button_pressed(self):
        self._rf_buffer_state = self._update_state(
            self._rf_buffer_state_transitions, self._rf_buffer_state, _SAVE)

    def _on_capture_start(self):
        self._capture_button.setEnabled(True)
        self._save_data_button.setEnabled(True)
        # Discard the previous buffer
        self._rf_buffer = None
        # Create new buffer
        self._rf_buffer = CaptureBuffer(self.rf_buffer_size)
        self.statusBar().showMessage("Capturing RF frames...")
        return True

    def _on_capture_end(self):
        self._capture_button.setEnabled(True)
        self._save_data_button.setEnabled(True)
        self.statusBar().showMessage(
            "Capture done, press 'Save' button to save the data to disk.")
        return True

    def _on_save(self):
        # Stop the processing thread, so we now the system is not running
        # TODO sync
        if self._current_state == _STARTED:
            self._update_graph_state(_STOP)
        filename, extension = QFileDialog.getSaveFileName(
            self, "Save File", ".", _FILE_EXTENSION_STR)
        if extension == "":
            return False
        date_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = filename.strip()
        datas, mask, rfs, gain, voltage = zip(*self._rf_buffer.data)
        rfs = np.stack(rfs)
        datas = np.stack(datas)
        mask = np.stack(mask)
        gain = np.stack(gain)
        voltage = np.stack(voltage)
        data = {"time": date_time, "rf": rfs, "bmode": datas, "mask": mask,
                "gain": gain, "voltage": voltage,
                "extent_ox": self.extent_ox, "extent_oz": self.extent_oz,
                "tx_frequency": self._controller.settings["sequence"]["tx_frequency"]}

        self.statusBar().showMessage(f"Saving file to {filename}, please wait...")
        time.sleep(1)
        np.savez(filename, **data)
        self._reset_capture_buffer()
        self.statusBar().showMessage(f"Saved file to {filename}. Ready.")
        time.sleep(1)
        # Start the processing thread back
        if self._current_state == _STOPPED:
            self._update_graph_state(_START)
        return True

    def _reset_capture_buffer(self):
        self._capture_button.setEnabled(True)
        self._save_data_button.setEnabled(False)
        self._rf_buffer = CaptureBuffer(self.rf_buffer_size)
        self._rf_buffer_state = _EMPTY

    def _update_buffer_state_graph(self, action):
        self._rf_buffer_state = self._update_state(
            self._rf_buffer_state_transitions, self._rf_buffer_state, action)

    def _update_state(self, graph, state_from, action):
        transition = None
        try:
            transition = graph[state_from][action]
        except KeyError:
            raise ValueError(
                f"There is no transition from {state_from} using {action}.")
        should_change_state = transition["callback"]()
        if not should_change_state:
            return state_from
        return transition["dst_state"]

    def _on_voltage_change(self, value):
        # TODO make the setting voltage operation cheap (implement session controller)
        self._voltage_spin_box.setDisabled(True)
        controller.send(SetVoltageEvent(value))
        self._voltage_spin_box.setDisabled(False)
        self._voltage_spin_box.setFocus()

    def _on_tgc_slider_change(self):
        self._current_gain_value = self._slider.value() / 10 ** _TGC_SLIDER_PRECISION
        controller.send(SetGainEvent(self._current_gain_value))

    def _show_error(self, msg):
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setText(msg)
        box.setWindowTitle("Error")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()


if __name__ == "__main__":
    us4r_settings_file = sys.argv[1]
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    model = None
    controller = None
    with open("settings.yml", "r") as f:
        settings = yaml.safe_load(f)
    try:
        model = ArrusModel(settings, us4r_settings_file)
        controller = Controller(model)
        window = MainWindow(f"{NAME} {__version__}", controller=controller)
        window.show()
        sys.exit(app.exec_())
    except BaseException as e:
        if not (isinstance(e, SystemExit) and e.code == 0):
            print(f"Exception occurred: {e}")
            traceback.print_exception(*sys.exc_info())
            input("Press enter to exit...")
    finally:
        close_model_and_controller(model, controller)

