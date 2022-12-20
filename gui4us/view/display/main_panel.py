import queue

import time
import traceback

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

from gui4us.controller.env import EnvController
from gui4us.common import ImageMetadata
from gui4us.controller.task import Promise

matplotlib.use("tkagg")

from gui4us.view.widgets import Panel
from gui4us.view.common import *
from gui4us.model import *
from gui4us.logging import get_logger
import gui4us.cfg
from typing import Dict
from queue import Queue


class DisplayPanel(Panel):

    def __init__(self, cfg: Dict[str, gui4us.cfg.Display2D],
                 env: EnvController,
                 parent_window, title="Display"):
        super().__init__(title)

        self.logger = get_logger(type(self))

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
        metadata_promise: Promise = self.env.get_stream_metadata()
        self.metadata_collection: MetadataCollection = metadata_promise.get_result()
        for i, (name, display_cfg) in enumerate(cfg.items()):
            ax = self.axes[i]

            # extends for this axis (provided by user).
            extents = None
            if display_cfg.extents is not None:
                extents = display_cfg.extents

            # axis labels (provided by user)
            axis_labels = None
            if display_cfg.ax_labels is not None:
                axis_labels = display_cfg.ax_labels

            for layer in display_cfg.layers:
                self.layers.append(layer)
                metadata: ImageMetadata = self.metadata_collection.output(layer.input)
                input_shape = metadata.shape
                dtype = metadata.dtype

                # Extents.
                # TODO: verify if all image metadata have exactly the
                # same extents and ids
                if extents is None and metadata.extents is not None:
                    extents = metadata.extents
                if extents is not None:
                    extent_ox, extent_oz = extents
                    extents = [extent_oz[0], extent_oz[1],
                               extent_ox[1], extent_ox[0]]

                # Axis labels defined per output image metadata.
                # TODO: verify if all image metadata have exactly the
                # same extents and ids
                if axis_labels is None and metadata.ids is not None:
                    axis_labels = metadata.ids
                if axis_labels is None:
                    axis_labels = "", ""
                if metadata.units is not None:
                    units = metadata.units
                else:
                    units = "", ""

                ax_vmin, ax_vmax = None, None
                if layer.value_range is not None:
                    ax_vmin, ax_vmax = layer.value_range
                cmap = layer.cmap
                ax.set_xlabel(self.get_ax_label(axis_labels[0], units[0]))
                ax.set_ylabel(self.get_ax_label(axis_labels[1], units[1]))

                init_data = np.zeros(input_shape, dtype=dtype)
                canvas = ax.imshow(
                    init_data, cmap=cmap, vmin=ax_vmin, vmax=ax_vmax,
                    extent=extents,
                    interpolation="none", interpolation_stage="rgba")
                self.canvases.append(canvas)
        self.canvases[0].figure.tight_layout()
        self.fig.colorbar(self.canvases[-1])
        # View worker
        self.is_started = False  # TODO state_graph
        self.data_queue = Queue(maxsize=2)
        self.env.get_stream().append_on_new_data_callback(
            self._put_input_data
        )
        self.i = 0

    def _put_input_data(self, data):
        try:
            self.data_queue.put_nowait(data)
        except queue.Full:
            pass

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
                data = self.data_queue.get()
                if data is None or not self.is_started:
                    # None means that the buffer has stopped
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return
                for c, l in zip(self.canvases, self.layers):
                    d = data[l.input.ordinal]
                    c.set_data(d)
                    if l.value_range is None:
                        # FIXME the below shouldn't be called for each frame
                        ax_vmin, ax_vmax = np.min(data), np.max(data)
                        c.set(clim=(ax_vmin, ax_vmax))
                    c.figure.canvas.draw()
            return self.canvases
        except Exception as e:
            self.logger.exception(e)

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label


