import numpy as np


# ARRUS EchoDataDescription.grid
def get_image_extent(grids):
    return [(np.min(grid.points), np.max(grid.points)) for grid in grids]
