import panel as pn
import numpy as np
import param
from panel.reactive import ReactiveHTML
from gui4us.view.env.displays.vtk import (
    VTKDisplayServer, VTKDisplayServerOptions
)
from .utils import to_vtk_image_data
import vtk
from pathlib import Path
import threading
import time


class Display2D(ReactiveHTML):
    session_url = param.String(default="ws://localhost:1234/")
    display_name = param.String(default="Display2D")

    __javascript__ = [
        "http://localhost:5006/env_static/connectToDisplay.js"
    ]
    _template = '<div id="display_2d"></div>'
    _scripts = {
        "render": "state.client = connectToDisplay(display_2d, {application: data.display_name, sessionURL: data.session_url})"
    }

    def __init__(self, host: str, port: str, **params):
        super().__init__(**params)
        self.render_view = self._create_pipeline()
        self.server = VTKDisplayServer(
            render_view=self.render_view,
            options=VTKDisplayServerOptions(
                host=host,
                port=port,
                debug=True
                # content=str(Path(__file__).parent / "content/")
            )
        )
        # Only for debug purposes
        self._update_thread = threading.Thread(target=self._update)

    def start(self):
        self._update_thread.start()
        return self.server.start()

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
        self.render_window.SetSize(300, 300)
        self.render_window.SetOffScreenRendering(1)

        self.renderer.SetBackground(colors.GetColor3d('DarkSlateGray'))
        return self.render_window

    def _update(self):
        self.i = 0
        while True:
            print("ALIVE!")
            data = vtk.util.numpy_support.numpy_to_vtk(
                self.bmodes[self.i].ravel(), deep=False)
            self.i = (self.i + 1) % 100
            self.vtk_img.GetPointData().SetScalars(data)
            self.render_window.Render()
            time.sleep(0.05)

