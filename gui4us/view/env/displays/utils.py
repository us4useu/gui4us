import vtk
import vtk.util.numpy_support
import numpy as np
import matplotlib.pyplot as plt


def to_vtk_image_data(img):

    # assuming single channel

    channel_count = 1

    output = vtk.vtkImageData()
    ny, nx = img.shape

    output.SetDimensions(nx, ny, channel_count)

    vtk_type_by_numpy_type = {
        np.uint8: vtk.VTK_UNSIGNED_CHAR,
        np.uint16: vtk.VTK_UNSIGNED_SHORT,
        np.uint32: vtk.VTK_UNSIGNED_INT,
        np.uint64: vtk.VTK_UNSIGNED_LONG if vtk.VTK_SIZEOF_LONG == 64 else vtk.VTK_UNSIGNED_LONG_LONG,
        np.int8: vtk.VTK_CHAR,
        np.int16: vtk.VTK_SHORT,
        np.int32: vtk.VTK_INT,
        np.int64: vtk.VTK_LONG if vtk.VTK_SIZEOF_LONG == 64 else vtk.VTK_LONG_LONG,
        np.float32: vtk.VTK_FLOAT,
        np.float64: vtk.VTK_DOUBLE
    }
    vtk_datatype = vtk.VTK_DOUBLE

    # source_numpy_array = np.flipud(source_numpy_array)

    array = vtk.util.numpy_support.numpy_to_vtk(
        img.ravel(), deep=False, array_type=vtk_datatype)
    array.SetNumberOfComponents(channel_count)
    output.SetSpacing([1, 1, 1])
    output.SetOrigin([-1, -1, -1])
    output.GetPointData().SetScalars(array)
    output.Modified()
    return output


def convert_from_named_to_vtk_cmap(name: str):
    matplotlib_cmap = plt.get_cmap(name)
    vtk_cmap = vtk.vtkLookupTable()
    vtk_cmap.SetNumberOfColors(matplotlib_cmap.N)
    for i in range(matplotlib_cmap.N):
        rgba_color = matplotlib_cmap(i)
        # Set colormap values (color component: [0, 1])
        vtk_cmap.SetTableValue(i, *rgba_color[:3], 1.0)
    return vtk_cmap

