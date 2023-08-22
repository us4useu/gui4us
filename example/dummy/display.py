from gui4us.model import *
from gui4us.cfg.display import *

# Display configuration file.

displays = {
    "OX": Display2D(
        title=f"OX",
        layers=(
            Layer2D(
                value_range=(0.0, 1.0),
                cmap="inferno",
                input=StreamDataId("default", 0),
            ),
        ),
    ),
    # "OY": Display2D(
    #     title=f"OY",
    #     layers=(
    #         Layer2D(
    #             value_range=(0, 255),
    #             cmap="gray",
    #             input=StreamDataId("default", 1),
    #         ),
    #     ),
    # ),
}

VIEW_CFG = ViewCfg(displays)
