import traceback

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
        n_displays = len(cfg.items())
        self.cfg = cfg
        self.env = env

        # One ax -> one display
        self.fig, self.axes = plt.subplots(1, n_displays)
        self.fig.set_size_inches(6, 6)
        if n_displays == 1:
            self.axes = [self.axes]
        img_canvas = FigureCanvas(self.fig)
        self.layout.addWidget(img_canvas)
        self.layout.addWidget(NavigationToolbar(img_canvas, parent_window))
        self.canvases = []
        self.layers = []  # Flatten list of layers.
        for i, (name, display_cfg) in enumerate(cfg.items()):
            ax = self.axes[i]
            for layer in display_cfg.layers:
                self.layers.append(layer)
                metadata = self.env.get_output_metadata(i).get_result()
                input_shape = metadata.shape
                dtype = metadata.dtype
                if layer.extent is not None:
                    extent_oz, extent_ox = layer.extent
                else:
                    extent_oz, extent_ox = metadata.extents
                if layer.ax_labels is not None:
                    label_oz, label_ox = layer.ax_labels
                else:
                    label_oz, label_ox = "", ""
                if layer.units is not None:
                    unit_oz, unit_ox = layer.units
                else:
                    unit_oz, unit_ox = metadata.units
                unit_oz = self._convert_arrus_unit_to_string(unit_oz)
                unit_ox = self._convert_arrus_unit_to_string(unit_ox)
                ax_vmin, ax_vmax = None, None
                if layer.value_range is not None:
                    ax_vmin, ax_vmax = layer.value_range
                cmap = layer.cmap
                ax.set_xlabel(self.get_ax_label(label_ox, unit_ox))
                ax.set_ylabel(self.get_ax_label(label_oz, unit_oz))
                init_data = np.zeros(input_shape, dtype=dtype)
                canvas = ax.imshow(
                    init_data, cmap=cmap, vmin=ax_vmin, vmax=ax_vmax,
                    extent=[extent_ox[0], extent_ox[1], extent_oz[1], extent_oz[0]],
                    interpolation="none", interpolation_stage="rgba")
                self.canvases.append(canvas)
        self.canvases[0].figure.tight_layout()
        self.fig.colorbar(self.canvases[-1])
        # View worker
        self.is_started = False  # TODO state_graph
        self.input = self.env.get_output()
        self.i = 0

    def _convert_arrus_unit_to_string(self, unit):
        if isinstance(unit, arrus.metadata.Units):
            return {
                arrus.metadata.Units.PIXELS: "px",
                arrus.metadata.Units.METERS: "m",
                arrus.metadata.Units.SECONDS: "s"
            }[unit]

    def start(self):
        self.is_started = True
        self.anim = FuncAnimation(self.fig, self.update, interval=50, blit=True)

    def stop(self):
        self.is_started = False
        self.anim.pause()

    def close(self):
        self.stop()

    def update(self, ev):
        try:
            if self.is_started:
                data = self.input.get(timeout=5)
                if data is None or not self.is_started:
                    # None means that the buffer has stopped
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return
                for c, l in zip(self.canvases, self.layers):
                    d = data[l.input.ordinal]
                    if l.value_func is not None:
                        d = l.value_func(d)
                    c.set_data(d)
                    if l.value_range is None:
                        # FIXME the below shouldn't be called for each frame
                        ax_vmin, ax_vmax = np.min(data), np.max(data)
                        c.set(clim=(ax_vmin, ax_vmax))
                    c.figure.canvas.draw()
            return self.canvases
        except Exception as e:
            # TODO notify that there was an error while drawing
            print(e)
            print(traceback.print_exc())

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label


