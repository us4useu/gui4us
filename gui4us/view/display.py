import time

import numpy as np
import datetime
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
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.backends.qt_compat import QtCore, QtWidgets

from matplotlib.figure import Figure

from gui4us.view.widgets import Panel
import gui4us.cfg


class ViewWorker(QObject):

    def __init__(self, func, interval=0.05):
        super().__init__()
        self.func = func
        self.is_working = False
        self.interval = interval

    @pyqtSlot()
    def run(self):
        # TODO sync point
        self.is_working = True
        while self.is_working:
            self.func()
            time.sleep(self.interval)

    def stop(self):
        self.is_working = False


class DisplayPanel(Panel):

    def __init__(self, cfg: gui4us.cfg.Display2D, controller, title="Display"):
        # TODO live data, model <-> view communication
        super().__init__(title, layout="h")
        # Validate configuration.
        if len(cfg.layers) > 1:
            raise ValueError("Currently only a single layer of data is "
                             "supported.")
        self.layer_cfg = cfg.layers[0]
        self.controller = controller
        image_metadata = self.controller.get_image_metadata()
        img_canvas = FigureCanvas(Figure(figsize=(6, 6)))
        self.layout.addWidget(NavigationToolbar(img_canvas, self))
        self.layout.addWidget(img_canvas)
        # Create a single Ax.
        ax = img_canvas.figure.subplots()
        # Ax parameters
        input_shape = image_metadata.shape
        dtype = image_metadata.dtype
        extent_oz, extent_ox = image_metadata.extents
        label_oz, label_ox = image_metadata.ids
        unit_oz, unit_ox = image_metadata.units
        ax_vmin, ax_vmax = self.layer_cfg.value_range
        cmap = self.layer_cfg.cmap

        ax.set_xlabel(f"{label_ox} [{unit_ox}]")
        ax.set_ylabel(f"{label_oz} [{unit_oz}]")
        init_data = np.zeros(input_shape, dtype=dtype)
        self.img_canvas = ax.imshow(
            init_data, cmap=cmap, vmin=ax_vmin, vmax=ax_vmax,
            extent=[extent_ox[0], extent_ox[1], extent_oz[1], extent_oz[0]])
        self.img_canvas.figure.tight_layout()
        # View worker
        self.thread = QThread()
        self.worker = ViewWorker(self.update)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.is_started = False  # TODO state_graph

    def start(self):
        self.is_started = True

    def stop(self):
        self.is_started = False

    def update(self):
        try:
            if self.is_started:
                data = self.img_data.get()
                if not self.is_started:
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return
                self.img_canvas.set_data(data)
                self.img_canvas.figure.canvas.draw()
        except Exception as e:
            print(e)

