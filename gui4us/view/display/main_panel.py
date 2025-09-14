import queue
from collections import deque, defaultdict

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
from gui4us.controller.env import EnvController
from gui4us.common import ImageMetadata
from gui4us.controller.task import Promise
from PyQt5.QtCore import QTimer

from gui4us.view.widgets import Panel
from gui4us.view.common import *
from gui4us.model import *
from gui4us.logging import get_logger
import gui4us.cfg
from typing import Dict, Sequence
from queue import Queue
from PyQt5.QtGui import QTransform

import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import numpy as np

import pyqtgraph as pg


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
        # TODO

    def __init__(self, cfg: gui4us.cfg.ViewCfg, env: EnvController,
                 parent_window, title="Display"):
        super().__init__(title)

        self.logger = get_logger(type(self))

        n_displays = len(cfg.displays)
        self.cfg = cfg
        self.env = env

        # sort displays by StreamDataId: (name, ordinal)
        # One ax -> one display
        # self.fig, self.axes = self._create_ax_grid(self.cfg) TODO
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        self.images = []
        self.layers = []
        metadata_promise: Promise = self.env.get_stream_metadata()
        self.metadata_collection: MetadataCollection = metadata_promise.get_result()
        # NOTE: the below is the state managed during configuration
        self._value_ranges = dict()
        self._cmaps = dict()
        self._preprocess_outputs = dict()
        self._is_preprocess = dict()

        plot = self.plot_widget
        for i, (title, display_cfg) in enumerate(cfg.displays.items()):
            # TODO create new plot widget for multiple axes?
            vb = plot.getViewBox()
            vb.setAspectLocked(True)
            vb.invertY(True)

            # if display_cfg.title is not None:  TODO
            #     ax.set_title(display_cfg.title)

            # axis labels (provided by user)
            axis_labels = None
            if display_cfg.ax_labels is not None:
                axis_labels = display_cfg.ax_labels

            if isinstance(display_cfg, gui4us.cfg.Display1D):
                raise ValueError("Display1D is currently not supported")
            elif isinstance(display_cfg, gui4us.cfg.Display2D):
                extents = None
                if display_cfg.extents is not None:
                    extents = display_cfg.extents

                for layer in display_cfg.layers:
                    layer_nr = len(self.layers)
                    image = pg.ImageItem(axisOrder="row-major")
                    self.images.append(image)
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
                        (oz_min, oz_max), (ox_min, ox_max) = extents
                        nz, nx = input_shape[:2]
                        ox_dx = (ox_max-ox_min) / nx
                        ox_dz = (oz_max-oz_min) / nz

                        transform = QTransform()
                        transform.scale(ox_dz, ox_dx)
                        transform.translate(oz_min, -(ox_max-ox_min)/2)  # TODO fix
                        image.setTransform(transform)

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

                    if len(input_shape) == 2:
                        self._prepare_preprocess(
                            layer_nr=layer_nr,
                            vmin=ax_vmin, vmax=ax_vmax,
                            cmap=cmap,
                            input_shape=input_shape
                        )
                        self._is_preprocess[layer_nr] = True
                    elif len(input_shape) == 3 and dtype == np.float32:
                        # No pre-processing is needed.
                        self._is_preprocess[layer_nr] = False
                    else:
                        raise ValueError(f"Unsupported combination of data shape "
                                         f"and type: {input_shape}, {dtype}")


                    # TODO avoid setting this multiple times (multiple layers per plot)
                    plot.setLabel("bottom", self.get_ax_label(axis_labels[0], units[0]))
                    plot.setLabel("left", self.get_ax_label(axis_labels[1], units[1]))

                    vb.addItem(image)

        self._update_func = self.update_display_2d
        # View worker
        self.is_started = False  # TODO state_graph
        self.data_queue = deque(maxlen=1)
        self.env.get_stream().append_on_new_data_callback(
            self._put_input_data
        )
        self.i = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_func)
        self._interval = 50e-3

    def _put_input_data(self, data):
        self.data_queue.append(data)

    def start(self):
        self.is_started = True
        self.timer.start(int(round(self._interval*1e3)))

    def stop(self):
        self.is_started = False
        self.timer.stop()

    def close(self):
        self.stop()

    def update_display_2d(self):
        try:
            if self.is_started:
                if len(self.data_queue) == 0:
                    # No data, no update.
                    return self.images
                data = self.data_queue[-1]

                if data is None or not self.is_started:
                    # None means that the buffer has stopped
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return

                for layer_nr, (img, l) in enumerate(zip(self.images, self.layers)):
                    d = data[l.input.ordinal]
                    if self._is_preprocess[layer_nr]:
                        d = self._preprocess(d, layer_nr)
                    img.setImage(d, autoLevels=True)
        except Exception as e:
            self.logger.exception(e)

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label

    def _prepare_preprocess(self, layer_nr, vmin, vmax, cmap, input_shape):
        # prepare dynamic range adjustment
        self._value_ranges[layer_nr] = (vmin, vmax)
        # prepare color map
        cmap = self._extract_segmented_data_cmap(cmap)
        _internal_cmap = dict()

        for k, v in cmap.items():
            _internal_cmap[k] = self._prepare_cmap_channel(v)
        self._cmaps[layer_nr] = _internal_cmap
        output_shape = input_shape + (3, )  # RGB array
        self._preprocess_outputs[layer_nr] = np.zeros(output_shape, dtype=np.float32)

    def _prepare_cmap_channel(self, cmap):
        xs = np.array([x for x, _, _ in cmap])
        ys0 = np.array([y0 for _, y0, _ in cmap])
        ys1 = np.array([y1 for _, _, y1 in cmap])
        return xs, ys0, ys1

    def _preprocess(self, data, layer_nr):
        data = data.astype(np.float32)
        vmin, vmax = self._value_ranges[layer_nr]
        cmap = self._cmaps[layer_nr]
        output = self._preprocess_outputs[layer_nr]

        # dynamic range adjustment
        data = np.clip(data, a_min=vmin, a_max=vmax)
        data = data - vmin
        data = data / (vmax - vmin)  # [0, 1]

        # color map
        data = self._interpolate_to_cmap(output, data, cmap)
        return data

    def _extract_segmented_data_cmap(self, cmap):
        if isinstance(cmap, str):
            cmap = cm.get_cmap(cmap)

        if isinstance(cmap, LinearSegmentedColormap):
            return cmap._segmentdata

        elif isinstance(cmap, ListedColormap):
            x = np.linspace(0, 1, len(cmap.colors))
            colors = np.array(cmap.colors)
            red = [(float(xi), float(ri), float(ri)) for xi, ri in
                   zip(x, colors[:, 0])]
            green = [(float(xi), float(gi), float(gi)) for xi, gi in
                     zip(x, colors[:, 1])]
            blue = [(float(xi), float(bi), float(bi)) for xi, bi in
                    zip(x, colors[:, 2])]
            return {"red": red, "green": green, "blue": blue}
        else:
            raise ValueError(f"Unsupported cmap: {cmap}")

    def _interpolate_to_cmap(self, output, data, cmap):
        output[..., 0] = self._interpolate_channel(data, cmap["red"])
        output[..., 1] = self._interpolate_channel(data, cmap["green"])
        output[..., 2] = self._interpolate_channel(data, cmap["blue"])
        return output

    def _interpolate_channel(self, data, cmap):
        xs, ys0, ys1 = cmap
        indices = np.searchsorted(xs, data, side="right") - 1
        indices = np.clip(indices, 0, len(xs) - 2)
        x0 = xs[indices]
        x1 = xs[indices + 1]
        y0 = ys1[indices]
        y1 = ys0[indices + 1]
        t = (data - x0) / (x1 - x0 + 1e-8)
        return y0 + (y1 - y0) * t

