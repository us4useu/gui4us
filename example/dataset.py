from gui4us.cfg.environment import *
from gui4us.cfg.display import *
from arrus.ops.us4r import *
from arrus.utils.imaging import *
from arrus.ops.imaging import *
import numpy as np
import scipy.signal
import importlib
import sys


environment = DatasetEnvironment(
    input=p
)


displays = {
    "displays": Display2D(
        title=f"",
        layers=(
            Layer2D(
                value_range=dynamic_range,
                cmap=colormap,
                input=LiveDataId("default", 0),
            ),
        )
    )
}


view_cfg = ViewCfg(displays)
