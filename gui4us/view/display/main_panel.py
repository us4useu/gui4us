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
import arrus.metadata

matplotlib.use("tkagg")

from gui4us.view.widgets import Panel
import gui4us.cfg
from typing import Dict


class DisplayPanel(Panel):

    def __init__(self, cfg: Dict[str, gui4us.cfg.Display2D], env,
                 parent_window, title="Display"):
        super().__init__(title)
        # Validate configuration.
        # TODO handle multiple displays
        if len(cfg) > 1:
            raise ValueError("Currently only a single display is supported")
        _, self.cfg = list(cfg.items())[0]
        if len(self.cfg.layers) > 1:
            raise ValueError("Currently only a single layer of data is supported.")
        self.layer_cfg = self.cfg.layers[0]
        self.env = env
        image_metadata = self.env.get_output_metadata(0).get_result()
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
            label_oz, label_ox = "", ""
        if self.layer_cfg.units is not None:
            unit_oz, unit_ox = self.layer_cfg.units
        else:
            unit_oz, unit_ox = image_metadata.units
        unit_oz = self._convert_arrus_unit_to_string(unit_oz)
        unit_ox = self._convert_arrus_unit_to_string(unit_ox)
        self.ax_vmin, self.ax_vmax = None, None
        if self.layer_cfg.value_range is not None:
            self.ax_vmin, self.ax_vmax = self.layer_cfg.value_range
        cmap = self.layer_cfg.cmap
        ax.set_xlabel(self.get_ax_label(label_ox, unit_ox))
        ax.set_ylabel(self.get_ax_label(label_oz, unit_oz))
        init_data = np.zeros(input_shape, dtype=dtype)
        self.img_canvas = ax.imshow(
            init_data, cmap=cmap, vmin=self.ax_vmin, vmax=self.ax_vmax,
            extent=[extent_ox[0], extent_ox[1], extent_oz[1], extent_oz[0]],
            interpolation="none", interpolation_stage="rgba"
        )
        self.img_canvas.figure.tight_layout()
        self.figure.colorbar(self.img_canvas)
        # View worker
        self.is_started = False  # TODO state_graph
        self.input = self.env.get_output()
        self.i = 0
        self.ax = ax

    def _convert_arrus_unit_to_string(self, unit):
        if isinstance(unit, arrus.metadata.Units):
            return {
                arrus.metadata.Units.PIXELS: "px",
                arrus.metadata.Units.METERS: "m",
                arrus.metadata.Units.SECONDS: "s"
            }[unit]

    def start(self):
        self.is_started = True
        self.anim = FuncAnimation(self.figure, self.update, interval=50,
                                  blit=True, repeat=True)

    def stop(self):
        self.is_started = False
        self.anim.pause()
        plt.show()

    def close(self):
        self.stop()

    def update(self, ev):
        try:
            if self.is_started:
                data = self.input.get()[0]  # Data index
                if data is None or not self.is_started:
                    # None means that the buffer has stopped
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return
                if self.ax_vmin is None:
                    self.ax_vmin, self.ax_vmax = np.min(data), np.max(data)
                    self.img_canvas.set(clim=(self.ax_vmin, self.ax_vmax))
                self.img_canvas.set_data(data)
                self.img_canvas.figure.canvas.draw()
        except Exception as e:
            # TODO notify that there was an error while drawing
            print(e)
        return self.img_canvas,

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label


