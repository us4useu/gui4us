import queue
from collections import deque

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
from typing import Dict, Sequence
from queue import Queue


class DisplayPanel(Panel):

    def _create_ax_grid(self, cfg: gui4us.cfg.ViewCfg):
        displays = cfg.displays
        grid_spec = cfg.grid_spec
        if grid_spec is None:
            n_displays = len(displays)
            grid_spec = gui4us.cfg.GridSpec(
                n_rows=1,
                n_columns=n_displays,
                locations=[gui4us.cfg.DisplayLocation(rows=0, columns=i)
                           for i in range(n_displays)]
            )
        fig = plt.figure()
        gs = fig.add_gridspec(grid_spec.n_rows, grid_spec.n_columns)
        axes = []
        for l in grid_spec.locations:
            rows, columns = l.rows, l.columns
            if isinstance(rows, int):
                rows = (rows, rows+1)
            if isinstance(columns, int):
                columns = (columns, columns+1)
            ax = fig.add_subplot(gs[rows[0]:rows[1], columns[0]:columns[1]])
            axes.append(ax)
        return fig, axes

    def __init__(self, cfg: gui4us.cfg.ViewCfg, env: EnvController,
                 parent_window, title="Display"):
        super().__init__(title)

        self.logger = get_logger(type(self))

        n_displays = len(cfg.displays)
        self.cfg = cfg
        self.env = env

        # sort displays by StreamDataId: (name, ordinal)
        # One ax -> one display

        self.fig, self.axes = self._create_ax_grid(self.cfg)
        img_canvas = FigureCanvas(self.fig)
        self.layout.addWidget(img_canvas)
        self.layout.addWidget(NavigationToolbar(img_canvas, parent_window))
        self.canvases = []
        self.layers = []  # Flatten list of layers.
        metadata_promise: Promise = self.env.get_stream_metadata()
        self.metadata_collection: MetadataCollection = metadata_promise.get_result()
        for i, display_cfg in enumerate(cfg.displays):
            ax = self.axes[i]
            if display_cfg.title is not None:
                ax.set_title(display_cfg.title)

            # axis labels (provided by user)
            axis_labels = None
            if display_cfg.ax_labels is not None:
                axis_labels = display_cfg.ax_labels

            if isinstance(display_cfg, gui4us.cfg.Display1D):
                if len(cfg) > 1:
                    raise ValueError("Currently only a single Display can be used with Display1D")
                metadata: ImageMetadata = self.metadata_collection.output(StreamDataId("default", 0))
                input_shape = metadata.shape
                dtype = metadata.dtype

                if axis_labels is None and metadata.ids is not None:
                    axis_labels = metadata.ids
                if axis_labels is None:
                    axis_labels = "", ""
                if metadata.units is not None:
                    units = metadata.units
                else:
                    units = "", ""

                ax_vmin, ax_vmax = None, None
                if display_cfg.value_range is not None:
                    ax_vmin, ax_vmax = display_cfg.value_range
                ax.set_xlabel(self.get_ax_label(axis_labels[0], units[0]))
                ax.set_ylabel(self.get_ax_label(axis_labels[1], units[1]))
                ax.set_ylim([ax_vmin, ax_vmax])

                init_data = np.zeros(input_shape, dtype=dtype)
                init_data = np.atleast_2d(init_data)
                self.sampling_points = np.arange(init_data.shape[-1])
                for i, scanline in enumerate(init_data):
                    canvas, = ax.plot(self.sampling_points, scanline)
                    canvas.set_label(f"Input {i}")
                    self.canvases.append(canvas)
                ax.legend()
                self._update_func = self.update_display_1d

            elif isinstance(display_cfg, gui4us.cfg.Display2D):
                extents = None
                if display_cfg.extents is not None:
                    extents = display_cfg.extents

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
                        matplotlib_extents = [extent_oz[0], extent_oz[1],
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
                        extent=matplotlib_extents,
                        interpolation="none")
                    self.canvases.append(canvas)
                self._update_func = self.update_display_2d
        self.canvases[0].figure.tight_layout()
        # self.fig.colorbar(self.canvases[-1])
        # View worker
        self.is_started = False  # TODO state_graph
        self.data_queue = deque(maxlen=1)
        self.env.get_stream().append_on_new_data_callback(
            self._put_input_data
        )
        self.i = 0

    def _put_input_data(self, data):
        self.data_queue.append(data)

    def start(self):
        self.is_started = True
        self.anim = FuncAnimation(self.fig, self._update_func, interval=20e-3, blit=True)

    def stop(self):
        self.is_started = False
        self.anim.pause()

    def close(self):
        self.stop()

    def update_display_2d(self, ev):
        try:
            if self.is_started:
                if len(self.data_queue) == 0:
                    # No data, no update.
                    return self.canvases
                data = self.data_queue[-1]
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

    def update_display_1d(self, ev):
        try:
            if self.is_started:
                if len(self.data_queue) == 0:
                    # No data, no update.
                    return self.canvases
                data = self.data_queue[-1]
                if data is None or not self.is_started:
                    # None means that the buffer has stopped
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return self.canvases
                d = data[0]  # Only input 0 is supported
                d = np.atleast_2d(d)
                for i, (scanline, canvas) in enumerate(zip(d, self.canvases)):
                    canvas.set_data(self.sampling_points, scanline)
                self.canvases[0].figure.canvas.draw()
            return self.canvases
        except Exception as e:
            self.logger.exception(e)

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label


