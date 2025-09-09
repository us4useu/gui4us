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

                        print(extents)
                        print(input_shape)
                        print(ox_dx)
                        print(ox_dz)
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
                    cmap = layer.cmap  # TODO

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

                for img, l in zip(self.images, self.layers):
                    d = data[l.input.ordinal]
                    img.setImage(d, autoLevels=False)
        except Exception as e:
            self.logger.exception(e)

    def get_ax_label(self, label, unit):
        label = f"{label}"
        if unit:
            label = f"{label} [{unit}]"
        return label
