import panel as pn
import numpy as np
import param
from panel.reactive import ReactiveHTML

from gui4us.model import MetadataCollection
from gui4us.view.env.displays.vtk import (
    VTKDisplayServer, VTKDisplayServerOptions
)
from .utils import to_vtk_image_data
from gui4us.utils import get_free_port_for_address
import vtk
import threading
import time
from gui4us.logging import get_logger
import gui4us.cfg.display as display_cfg


class Display2D(ReactiveHTML):
    host = param.String(default="localhost")
    port = param.Integer(default=0)
    display_name = param.String(default="Display2D")

    __javascript__ = [
        "content/connectToDisplay.js"
    ]
    _template = '<div id="display_2d" style="width: 100%; height: 100%; margin: 0 auto;"></div>'
    _scripts = {
        "render":
            "sessionURL = 'ws://' + data.host + ':' + data.port; "
            "state.client = connectToDisplay(display_2d, {application: data.display_name, sessionURL: sessionURL})"
    }

    def __init__(
            self,
            cfg: display_cfg.Display2D,
            metadatas: MetadataCollection,
            **params):
        super().__init__(**params)
        self.logger = get_logger(f"{type(self)}:{self.display_name}")
        self.cfg = cfg
        self.metadatas = metadatas
        self.render_view = self._create_pipeline()
        if self.port == 0:
            self.port = get_free_port_for_address(self.host)
        self.server = VTKDisplayServer(
            render_view=self.render_view,
            options=VTKDisplayServerOptions(
                host=self.host,
                port=self.port,
                debug=False
            )
        )
        # Only for debug purposes
        self._update_thread = threading.Thread(target=self._update)

    def start(self):
        self._update_thread.start()
        self.start_result = self.server.start()
        self.logger.info(f"Server started at: ws://{self.host}:{self.port}")

    def join(self):
        self.server.join()

    def _create_pipeline(self):
        self.bmodes = np.load(
            "/home/pjarosik/data/us4useu/gui4us/data_2023-05-24_15-28-33_bmodes.npy")
        colors = vtk.vtkNamedColors()

        def to_img(bmode):
            bmode = np.clip(bmode, 20, 80)
            bmode_max, bmode_min = np.max(bmode), np.min(bmode)
            bmode = (bmode-bmode_min) / (bmode_max-bmode_min)
            return bmode * 255

        self.bmodes = [to_img(b) for b in self.bmodes]

        self.vtk_img = to_vtk_image_data(self.bmodes[0])

        # Create a renderer, render window, and interactor
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        img = vtk.vtkImageActor()
        img.GetMapper().SetInputData(self.vtk_img)

        self.axes = vtk.vtkCubeAxesActor2D()
        self.axes.SetCamera(self.renderer.GetActiveCamera())
        self.axes.SetZAxisVisibility(0)
        ny, nx = self.bmodes[0].shape
        self.axes.SetBounds(0, nx, 0, ny, 0, 1)
        self.axes.SetRanges(-25, 25, 0, 50, 0, 1)
        self.axes.UseRangesOn()
        self.axes.SetXLabel("OX (mm)")
        self.renderer.AddViewProp(self.axes)

        # Add the actor to the scene
        self.renderer.ResetCamera()
        self.renderer.AddActor(img)
        # TODO remove below?
        self.renderer.AddActor(self.axes)
        self.render_window.SetSize(300,300)
        self.render_window.SetOffScreenRendering(1)

        self.renderer.SetBackground(colors.GetColor3d("silver"))
        return self.render_window

    def _update(self):
        self.i = 0
        while True:
            data = vtk.util.numpy_support.numpy_to_vtk(
                self.bmodes[self.i].ravel(), deep=False)
            self.i = (self.i + 1) % 100
            self.vtk_img.GetPointData().SetScalars(data)
            self.render_window.Render()
            time.sleep(0.05)

