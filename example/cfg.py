from gui4us.cfg.environment import *
from gui4us.cfg.display import *
from arrus.ops.us4r import *
from arrus.utils.imaging import *
from arrus.ops.imaging import *
import numpy as np

X_GRID = np.arange(-15, 15, 0.1) * 1e-3
Z_GRID = np.arange(5, 35, 0.1) * 1e-3

ENVIRONMENTS = {
   "us4r": HardwareEnvironment(
        session_cfg="/home/pjarosik/us4r.prototxt",
        scheme=Scheme(
            tx_rx_sequence=PwiSequence(
                angles=np.linspace(-10, 10, 7)*np.pi/180,
                pulse=Pulse(center_frequency=6e6, n_periods=2, inverse=False),
                rx_sample_range=(256, 1024*4),
                downsampling_factor=1,
                speed_of_sound=1450,
                pri=200e-6,
                tgc_start=14, tgc_slope=2e2),
            processing=Pipeline(
                steps=(
                    RemapToLogicalOrder(),
                    Transpose(axes=(0, 1, 3, 2)),
                    BandpassFilter(),
                    QuadratureDemodulation(),
                    Decimation(decimation_factor=4, cic_order=2),
                    ReconstructLri(x_grid=X_GRID, z_grid=Z_GRID),
                    Mean(axis=1),
                    EnvelopeDetection(),
                    Mean(axis=0),
                    Transpose(),
                    LogCompression()
                    ),
                    placement="/GPU:0")
            )
        )
}

DISPLAYS = {
    "sscan": Display2D(
        title="S-scan",
        layers=(
            Layer2D(
                value_range=(20, 80),
                cmap="grey",
                input=LiveDataId("us4r", 0)
            ),
        )
    )
}
