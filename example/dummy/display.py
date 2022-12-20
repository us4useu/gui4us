from gui4us.model import *
from gui4us.cfg.display import *

# Display configuration file.

displays = {
    "main": Display2D(
        title=f"B-mode OX",
        layers=(
            Layer2D(
                value_range=(-1.0, 1.0),
                cmap="viridis",
                input=StreamDataId("default", 0),
            ),
        ),
    )
}

VIEW_CFG = ViewCfg(displays)
