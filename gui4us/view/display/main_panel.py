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
    FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib

from gui4us.controller.env import EnvController
from gui4us.common import ImageMetadata
from gui4us.controller.task import Promise

from gui4us.view.widgets import Panel
from gui4us.view.common import *
from gui4us.model import *
from gui4us.logging import get_logger
import gui4us.cfg
from typing import Dict, Sequence, Any
from queue import Queue


@dataclass(frozen=True)
class Layer1D:
    """
    NOTE: this class is not a part of gui4us API.
    This is class is intended only to keep the compatiblitiy
    between 1D and 2D displays implementation (see the source code below).
    """
    input: StreamDataId


class DisplayPanel(Panel):

    def _create_ax_grid(self, cfg: gui4us.cfg.ViewCfg, displays: Sequence[Tuple[str, Any]]) -> Tuple[Any, Dict]:
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
        axes = {}
        for i, l in enumerate(grid_spec.locations):
            display_id = l.display_id
            if display_id is None:
                display_id = displays[i][0]
            rows, columns = l.rows, l.columns
            if isinstance(rows, int):
                rows = (rows, rows+1)
            if isinstance(columns, int):
                columns = (columns, columns+1)
            ax = fig.add_subplot(gs[rows[0]:rows[1], columns[0]:columns[1]])
            axes[display_id] = ax
        return fig, axes

    def __init__(self, cfg: gui4us.cfg.ViewCfg, env: EnvController,
                 parent_window, title="Display"):
        super().__init__(title)

        self.logger = get_logger(type(self))

        displays = cfg.displays
        if not isinstance(displays, Dict):
            if isinstance(displays, Iterable):
                displays = ((f"Display:{i}", d) for d in displays)
                displays = dict(*displays)
            else:
                raise ValueError("ViewCfg.displays should be a Dict or Iterable")

        displays = displays.items()
        # sort by input id
        displays_with_input_id = [(d, self._get_input_id(d)) for d in displays]
        displays = sorted(displays_with_input_id, key=lambda x: x[1])
        displays, _ = zip(*displays)

        n_displays = len(displays)
        self.cfg = cfg
        self.env = env
        # One ax -> one display
        self.fig, self.axes = self._create_ax_grid(self.cfg, displays)
        img_canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(img_canvas)
        self.layout.addWidget(NavigationToolbar(img_canvas, parent_window))
        self.unique_axes_list = []
        # TODO wrap the below into some data structure
        self.axes_list = []  # Should have the same size as self.canvases
        self.canvases = []
        self.axes_bg = []
        self.layers = []  # Flatten list of layers.
        self.layer_type = []   # 1 - Layer1D, 2 - Layer2D
        self.sampling_points = []
        metadata_promise: Promise = self.env.get_stream_metadata()
        self.metadata_collection: MetadataCollection = metadata_promise.get_result()

        for display_id, display_cfg in displays:
            ax = self.axes[display_id]
            self.unique_axes_list.append(ax)
            if display_cfg.title is not None:
                ax.set_title(display_cfg.title)

            # axis labels (provided by user)
            axis_labels = None
            if display_cfg.ax_labels is not None:
                axis_labels = display_cfg.ax_labels

            if isinstance(display_cfg, gui4us.cfg.Display1D):
                stream_id = display_cfg.input
                metadata: ImageMetadata = self.metadata_collection.output(stream_id)
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
                sp = np.arange(init_data.shape[-1])
                self.axes_bg.append(self.fig.canvas.copy_from_bbox(ax.bbox))

                scanline_labels = display_cfg.labels
                if scanline_labels is None:
                    scanline_labels = [f"Input:{i}" for i in range(len(init_data))]
                for i, scanline in enumerate(init_data):
                    canvas, = ax.plot(sp, scanline)
                    canvas.set_label(scanline_labels[i])
                    self.canvases.append(canvas)
                    self.sampling_points.append(sp)
                    self.axes_list.append(ax)
                    self.layer_type.append(1)
                    self.layers.append(Layer1D(input=stream_id))
                ax.legend()

            elif isinstance(display_cfg, gui4us.cfg.Display2D):
                extents = None
                if display_cfg.extents is not None:
                    extents = display_cfg.extents

                for layer in display_cfg.layers:
                    self.layers.append(layer)
                    self.layer_type.append(2)
                    metadata: ImageMetadata = self.metadata_collection.output(layer.input)
                    imshow_params = {}
                    input_shape = metadata.shape
                    dtype = metadata.dtype

                    # Extents.
                    # TODO: verify if all image metadata have exactly the
                    # same extents and ids
                    if extents is None and metadata.extents is not None:
                        extents = metadata.extents
                    if extents is not None:
                        extent_x, extent_y = extents
                        matplotlib_extents = [extent_y[0], extent_y[1],
                                            extent_x[1], extent_x[0]]

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
                    ax.set_xlabel(self.get_ax_label(axis_labels[0], units[0]))
                    ax.set_ylabel(self.get_ax_label(axis_labels[1], units[1]))
                    cmap = layer.cmap
                    init_data = np.zeros(input_shape, dtype=dtype)
                    if len(input_shape) == 2:
                        # 2D grayscale or some other array -- apply matplotlib
                        # cmap to get the final image.
                        imshow_params["cmap"] = cmap
                    elif len(input_shape) == 3:
                        # 3D -- RGB or RGBA
                        # Check the last axis size
                        if not input_shape[-1] in {3, 4}:
                            raise ValueError("2D layer image should be "
                                             "a 2D array or 3D array with "
                                             "the last axis of size 3 or 4.")
                    else:
                        raise ValueError("2D layer image should be "
                                         "a 2D array or 3D array with "
                                         "the last axis of size 3 or 4.")
                    canvas = ax.imshow(
                        init_data, vmin=ax_vmin, vmax=ax_vmax,
                        extent=matplotlib_extents,
                        interpolation="none",
                        **imshow_params
                    )
                    self.canvases.append(canvas)
                    self.axes_list.append(ax)
                    self.sampling_points.append(None)
                    self.axes_bg.append(self.fig.canvas.copy_from_bbox(ax.bbox))
        self.canvases[0].figure.tight_layout()
        self.n_canvases = len(self.canvases)
        # self.fig.colorbar(self.canvases[-1])
        # View worker
        self.is_started = False  # TODO state_graph
        self.data_queue = deque(maxlen=1)
        self.env.get_stream().append_on_new_data_callback(
            self._put_input_data
        )
        self.i = 0

    def _get_input_id(self, display):
        _, display = display
        if isinstance(display, gui4us.cfg.Display1D):
            return display.input.ordinal
        elif isinstance(display, gui4us.cfg.Display2D):
            ordinals = [l.input.ordinal for l in display.layers]
            return min(ordinals)
        else:
            raise ValueError(f"Unsupported display type: {type(display)}")

    def _put_input_data(self, data):
        self.data_queue.append(data)

    def start(self):
        self.is_started = True
        self.anim = FuncAnimation(self.fig, self.update_display, interval=10, blit=True)

    def stop(self):
        self.is_started = False
        self.anim.pause()

    def close(self):
        self.stop()

    def update_display(self, ev):
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

                # Draw
                for j in range(self.n_canvases):
                    l_t = self.layer_type[j]
                    l = self.layers[j]
                    d = data[l.input.ordinal]
                    ax = self.axes_list[j]
                    if l_t == 1:
                        # 1D
                        # c is a collection of canvases
                        d = np.atleast_2d(d)
                        for scanline in d:
                            canvas = self.canvases[j]
                            canvas.set_ydata(scanline)
                    else:
                        # 2D
                        c = self.canvases[j]
                        c.set_data(d)
                        j += 1
                self.canvases[0].figure.canvas.draw()
            return self.canvases
        except Exception as e:
            self.logger.exception(e)

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label


