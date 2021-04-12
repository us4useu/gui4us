"""gui4us main script"""

__version__ = "0.0.1"
NAME = "GUI4us"

import sys
import time
import numpy as np
from PyQt5 import QtWidgets, QtCore
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
)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure


class DataSource:

    def get(self):
        raise ValueError("NYI")


class CineloopDataSource(DataSource):

    def __init__(self, collection):
        self.collection = collection
        self._counter = 0

    def get(self):
        result = self.collection[self._counter]
        self._counter = (self._counter+1) % len(self.collection)
        return result


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, title, data_source: DataSource):
        super().__init__()
        self.data_source = data_source
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

        # status bar
        self.statusBar().showMessage('Ready')

    def _create_control_panel(self):
        control_panel = QGroupBox("Control panel")
        control_panel_layout = QVBoxLayout()
        control_panel.setLayout(control_panel_layout)

        actions = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        actions.setLayout(actions_layout)
        control_panel_layout.addWidget(actions)
        actions_layout.addWidget(QPushButton("Save data"))

        settings = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings.setLayout(settings_layout)
        control_panel_layout.addWidget(settings)

        # Form editor.
        settings_form_layout = QFormLayout()
        settings_layout.addLayout(settings_form_layout)
        settings_form_layout.addRow("Voltage [V]:", QSpinBox())
        settings_form_layout.addRow("Dynamic range min [dB]:", QSpinBox())
        settings_form_layout.addRow("Dynamic range max [dB]:", QSpinBox())

        # TGC editor
        control_panel_tgc_layout = QFormLayout()
        settings_layout.addLayout(control_panel_tgc_layout)
        control_panel_tgc_layout.addRow("TGC:", None)
        for i in range(10):
            control_panel_tgc_layout.addRow(f"{i*0.5} [cm]", QSlider(Qt.Horizontal))
        settings_layout.addStretch()
        return control_panel

    def _create_display_panel(self):
        display_panel_widget = QGroupBox("B-mode display")
        display_panel_layout = QHBoxLayout()
        display_panel_widget.setLayout(display_panel_layout)
        img_canvas = FigureCanvas(Figure(figsize=(4, 4)))
        display_panel_layout.addWidget(img_canvas)
        ax = img_canvas.figure.subplots()
        ax.set_xlabel("Azimuth [mm]")
        ax.set_ylabel("Depth [mm]")
        ax.imshow(self.data_source.get(), cmap="gray", vmin=20, vmax=80, extent=[-17, 17, 45, 10])
        return display_panel_widget

    def _update_canvas(self):
        t = np.linspace(0, 10, 101)
        # Shift the sinusoid as a function of time.
        self._line.set_data(t, np.sin(t + time.time()))
        self._line.figure.canvas.draw()


def create_random_data_source():
    return np.random.rand(10, 256, 256)


def create_mock_data_source():
    frames = np.load("pwi_64_lri.npy")
    frames = np.sum(frames, axis=1)
    frames = 20*np.log10(np.abs(frames))
    frames = np.transpose(frames, (0, 2, 1))
    print(frames.shape)
    return CineloopDataSource(frames)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    data_source = create_mock_data_source()
    window = MainWindow(f"{NAME} {__version__}", data_source)
    window.show()
    sys.exit(app.exec_())
