from gui4us.cfg.display import *
from gui4us.model import *

# One B-mode display. get_bmode_imaging ends with LogCompression, i.e. ABSOLUTE dB values, so
# the value range is in absolute dB too -- the same (20, 80) as the ARRUS example.
displays = {
    "B-mode": Display2D(
        title="B-mode",
        layers=(
            Layer2D(
                input=StreamDataId("default", 0),
                cmap="gray",
                value_range=(20, 80),
            ),
        ),
    ),
}

VIEW_CFG = ViewCfg(displays)
