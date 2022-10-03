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
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("tkagg")

from gui4us.view.widgets import Panel
from gui4us.view.common import *
import gui4us.cfg
from typing import Dict


class DisplayPanel(Panel):

    def __init__(self, cfg: Dict[str, gui4us.cfg.Display2D], controller,
                 parent_window, title="Display"):
        super().__init__(title)
        # Validate configuration.
        # TODO handle multiple displays
        if len(cfg) > 1:
            raise ValueError("Currently only a single display is supported")
        _, self.cfg = list(cfg.items())[0]
        if len(self.cfg.layers) > 1:
            raise ValueError("Currently only a single layer of data is "
                             "supported.")
        self.layer_cfg = self.cfg.layers[0]
        self.controller = controller
        image_metadata = self.controller.get_image_metadata(0).get_result()
        self.figure = Figure(figsize=(6, 6))
        img_canvas = FigureCanvas(self.figure)
        self.layout.addWidget(img_canvas)
        self.layout.addWidget(NavigationToolbar(img_canvas, parent_window))
        # Create a single Ax.
        ax = img_canvas.figure.subplots()
        # Ax parameters
        input_shape = image_metadata.shape
        dtype = image_metadata.dtype
        if self.layer_cfg.extent is not None:
            extent_oz, extent_ox = self.layer_cfg.extent
        else:
            extent_oz, extent_ox = image_metadata.extents
        if self.layer_cfg.ax_labels is not None:
            label_oz, label_ox = self.layer_cfg.ax_labels
        else:
            label_oz, label_ox = image_metadata.ids
        if self.layer_cfg.units is not None:
            unit_oz, unit_ox = self.layer_cfg.units
        else:
            unit_oz, unit_ox = image_metadata.units
        ax_vmin, ax_vmax = None, None
        if self.layer_cfg.value_range is not None:
            ax_vmin, ax_vmax = self.layer_cfg.value_range


        cmap = self.layer_cfg.cmap

        ax.set_xlabel(self.get_ax_label(label_ox, unit_ox))
        ax.set_ylabel(self.get_ax_label(label_oz, unit_oz))
        init_data = np.zeros(input_shape, dtype=dtype)
        self.img_canvas = ax.imshow(
            init_data, cmap=cmap, vmin=ax_vmin, vmax=ax_vmax,
            extent=[extent_ox[0], extent_ox[1], extent_oz[1], extent_oz[0]])
        self.img_canvas.figure.tight_layout()
        self.figure.colorbar(self.img_canvas)
        # View worker
        self.is_started = False  # TODO state_graph
        self.input = self.controller.get_output("out_0")
        self.i = 0
        self.ax = ax

    def start(self):
        self.is_started = True
        self.anim = FuncAnimation(self.figure, self.update, interval=0.01,
                                  blit=True)
        plt.show()

    def stop(self):
        self.is_started = False
        self.anim.pause()

    def close(self):
        self.stop()

    def update(self, ev):
        try:
            if self.is_started:
                data = self.input.get()  # Data index
                if data is None or not self.is_started:
                    # None means that the buffer has stopped
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return
                self.img_canvas.set_data(data)
                self.img_canvas.figure.canvas.draw()
                self.ax.set_title(f"{self.cfg.title}")
        except Exception as e:
            # TODO notify that there was an error while drawing
            print(e)
        return self.img_canvas,

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label


