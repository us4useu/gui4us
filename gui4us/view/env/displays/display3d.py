from typing import List

import numpy as np
import param
import scipy.ndimage
import vtk

from gui4us.logging import get_logger
from gui4us.view.env.displays.vtk_display import AbstractVTKDisplay


class Display3D(AbstractVTKDisplay):
    host = param.String(default="localhost")
    port = param.Integer(default=0)
    display_name = param.String(default="Display3D")

    def __init__(self, cfg, metadatas, **params):
        self.logger = get_logger(f"{type(self)}:{self.display_name}")
        self.cfg = cfg
        self.metadatas = metadatas
        self._create_pipeline(self.metadatas)
        # Must be called after creating the pipeline
        super().__init__(**params)

    def _create_pipeline(self, metadatas):
        colors = vtk.vtkNamedColors()
        assert len(metadatas) == 1, "Exactly one input should be be connected to " \
                                    "the 3D display. "
        dimensions = metadatas[0].shape

        ren1 = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(ren1)

        self.data = vtk.vtkImageData()
        dimensions = tuple(reversed(dimensions))
        self.data.SetDimensions(*dimensions)
        self.data.SetSpacing([1, 1, 1])
        self.data.SetOrigin([0, 0, 0])

        opacityTransferFunction = vtk.vtkPiecewiseFunction()
        opacityTransferFunction.AddPoint(0, 0.0)
        opacityTransferFunction.AddPoint(40, 0.0)
        opacityTransferFunction.AddPoint(120, 1.0)

        # Create transfer mapping scalar value to color.
        colorTransferFunction = vtk.vtkColorTransferFunction()
        colorTransferFunction.AddRGBPoint(0.0, 1.0, 1.0, 1.0)
        # colorTransferFunction.AddRGBPoint(20.0, 0.2, 0.2, 0.2)
        # colorTransferFunction.AddRGBPoint(40.0, 0.4, 0.4, 0.4)
        # colorTransferFunction.AddRGBPoint(60.0, 0.8, 0.8, 0.8)
        # colorTransferFunction.AddRGBPoint(80.0, 1.0, 1.0, 1.0)

        # The property describes how the data will look.
        volumeProperty = vtk.vtkVolumeProperty()
        volumeProperty.SetColor(colorTransferFunction)
        volumeProperty.SetScalarOpacity(opacityTransferFunction)
        volumeProperty.ShadeOn()
        volumeProperty.SetInterpolationTypeToLinear()

        # The mapper / ray cast function know how to render the data.
        volumeMapper = vtk.vtkGPUVolumeRayCastMapper()
        volumeMapper.SetInputData(self.data)

        # The volume holds the mapper and the property and
        # can be used to position/orient the volume.
        volume = vtk.vtkVolume()
        volume.SetMapper(volumeMapper)
        volume.SetProperty(volumeProperty)

        ren1.AddVolume(volume)
        ren1.SetBackground(colors.GetColor3d('Wheat'))
        ren1.GetActiveCamera().Azimuth(-10)
        ren1.GetActiveCamera().Elevation(-10)
        ren1.GetActiveCamera().Roll(-90)
        ren1.ResetCameraClippingRange()
        ren1.ResetCamera()

    def update(self, data):
        frames = data[0]
        # gain = np.linspace(1, 3, frames.shape[-1])
        # gain = gain.reshape(1, 1, -1)
        # frames = frames*gain
        # frames[frames == -np.inf] = np.max(frames)
        frames = -frames
        frames -= np.min(frames)
        frames = -frames
        frames = frames - np.min(frames)
        frames = frames[:, :, :]
        frames = scipy.ndimage.median_filter(frames, size=5)
        volume_data = vtk.util.numpy_support.numpy_to_vtk(
            frames.ravel(), deep=True)
        self.data.GetPointData().SetScalars(volume_data)
        self.render_window.Render()
