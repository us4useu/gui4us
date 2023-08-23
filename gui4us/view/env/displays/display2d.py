from typing import List
import time

import numpy as np
import param
import vtk
from panel.reactive import ReactiveHTML

import gui4us.cfg.display as display_cfg
from gui4us.common import ImageMetadata
from gui4us.logging import get_logger
from gui4us.utils import get_free_port_for_address
from gui4us.view.env.displays.vtk import (
    VTKDisplayServer, VTKDisplayServerOptions
)
from .utils import to_vtk_image_data, convert_from_named_to_vtk_cmap


# TODO possible optimization:
# avoid calling vtk.util.numpy_support.numpy_to_vtk
# envs should return "BufferStream" which has "data" property, which is a tuple
# of numpy arrays
# then in the create_pipeline, simply use the vtk.util.numpy_support.numpy_to_vtk
# and update should only run render method in order to update the current
# display
# Run _update for each layer and display in a separate thread
class Display2D(ReactiveHTML):
    host = param.String(default="localhost")
    port = param.Integer(default=0)
    display_name = param.String(default="Display2D")

    __javascript__ = [
        "content/connectToDisplay.js"
    ]
    # NOTE: width and height of the below node determines the final
    # dimensions of the image generated by the VTK display server
    _template = '<div id="display_2d" style="width: 50%; height: 50%; margin: 0 auto;"></div>'
    _scripts = {
        "render":
            "sessionURL = 'ws://' + data.host + ':' + data.port; "
            "state.client = connectToDisplay(display_2d, {application: data.display_name, sessionURL: sessionURL})"
    }

    def __init__(
            self,
            cfg: display_cfg.Display2D,
            metadatas: List[ImageMetadata],
            **params):
        """
        :param metadatas: list of output metadata; metadata[i] corresponds to
            value[i] from the update method
        """
        super().__init__(**params)
        self.logger = get_logger(f"{type(self)}:{self.display_name}")
        self.cfg = cfg
        self.metadatas = metadatas
        self.vtk_inputs = []
        self.initial_arrays = []
        self.preprocessing_outputs = []
        self.vtk_main_img_actor = None
        self.render_view = self._create_pipeline(self.metadatas, self.cfg)
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

    def start(self):
        self.start_result = self.server.start()
        self.logger.info(f"Server started at: ws://{self.host}:{self.port}")

    def join(self):
        self.server.join()

    def _create_pipeline(
            self,
            metadatas: List[ImageMetadata],
            cfg: display_cfg.Display2D
    ):
        # General
        colors = vtk.vtkNamedColors()
        layer_cfgs = cfg.layers
        assert len(layer_cfgs) == len(metadatas)

        # Create a renderer, render window
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        for i, layer_cfg in enumerate(layer_cfgs):
            m = metadatas[i]
            initial_array = np.zeros(m.shape, dtype=m.dtype)
            self.initial_arrays.append(initial_array)
            vtk_img = to_vtk_image_data(initial_array)
            self.vtk_inputs.append(vtk_img)

            # pre-processing
            # Flip the input image.
            # Without that VTK will display image flipped vertically.
            flip = vtk.vtkImageFlip()
            flip.SetInputData(vtk_img)
            flip.SetFilteredAxes(1)

            # Map to colors and apply dynamic range.
            dr_min, dr_max = layer_cfg.value_range
            vtk_cmap_lut = convert_from_named_to_vtk_cmap(layer_cfg.cmap)
            vtk_cmap_lut.SetTableRange(dr_min, dr_max)
            vtk_cmap_lut.SetNanColor(0.0, 0.0, 0.0, 0.0)
            color_map = vtk.vtkImageMapToColors()
            color_map.SetInputConnection(flip.GetOutputPort())
            color_map.SetLookupTable(vtk_cmap_lut)
            color_map.Update()

            self.preprocessing_outputs.append(color_map)

           # Merge layers
        if len(self.preprocessing_outputs) > 1:
            # Blend and create the final actor
            blend = vtk.vtkImageBlend()
            for i, output in enumerate(self.preprocessing_outputs):
                blend.AddInputConnection(output.GetOutputPort())
                blend.SetOpacity(i, 1.0)
            self.vtk_main_img_actor = vtk.vtkImageActor()
            self.vtk_main_img_actor.GetMapper().SetInputConnection(blend.GetOutputPort())
        else:
            # Just set the only output.
            output = self.preprocessing_outputs[0]
            self.vtk_main_img_actor = vtk.vtkImageActor()
            self.vtk_main_img_actor.GetMapper().SetInputConnection(output.GetOutputPort())
        # Axes
        self.axes = vtk.vtkCubeAxesActor2D()
        # TODO
        # self.axes.GetXAxisActor2D().SetLabelFormat("%3.1f")
        label_property = vtk.vtkTextProperty()
        label_property.ItalicOff()
        label_property.SetFontSize(10)
        self.axes.SetAxisLabelTextProperty(label_property)
        self.axes.SetAxisTitleTextProperty(label_property)
        # self.axes.GetXAxisActor2D().SetLabelTextProperty(label_property)

        self.axes.SetCamera(self.renderer.GetActiveCamera())
        self.axes.SetZAxisVisibility(0)
        reference_metadata = metadatas[0]
        ny, nx = reference_metadata.shape
        self.axes.SetBounds(0, nx, 0, ny, 0, 1)

        # Extent
        extents = None
        if cfg.extents is not None:
            extents = cfg.extents
        elif reference_metadata.extents is not None:
            extents = reference_metadata.extents
        if extents is not None:
            min_z, max_z = extents[0]
            min_x, max_x = extents[1]
            self.axes.SetRanges(min_x, max_x, max_z, min_z, 0, 1)
            self.axes.UseRangesOn()
        else:
            raise ValueError


        # AXIS LABELS
        if cfg.ax_labels is not None:
            axis_labels = cfg.ax_labels
        elif reference_metadata.ids is not None:
            axis_labels = reference_metadata.ids
        else:
            axis_labels = "", ""

        units = "" , ""
        if reference_metadata.units is not None:
            units = reference_metadata.units
            unit_x, unit_y = f" ({units[0]})", f" ({units[1]})"
            units = unit_x, unit_y

        self.axes.SetXLabel(f"{axis_labels[0]}{units[0]}")
        self.axes.SetYLabel(f"{axis_labels[1]}{units[1]}")

        # Add the actor to the scene
        self.renderer.AddViewProp(self.axes)
        self.renderer.ResetCamera()
        self.renderer.AddActor(self.vtk_main_img_actor)
        self.renderer.AddActor(self.axes)
        self.renderer.GetActiveCamera().Zoom(1.3)
        self.render_window.SetOffScreenRendering(1)

        self.renderer.SetBackground(colors.GetColor3d("silver"))
        return self.render_window

    def update(self, data):
        for i, d in enumerate(data):
            new_d = vtk.util.numpy_support.numpy_to_vtk(d.ravel(), deep=False)
            self.vtk_inputs[i].GetPointData().SetScalars(new_d)
            self.render_window.Render()

