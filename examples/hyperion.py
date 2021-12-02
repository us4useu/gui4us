from arrus.ops.imaging import *
from arrus.utils.imaging import *
from arrus.ops.us4r import *
import numpy as np


sequence = PwiSequence(
    angles=np.linspace(-20, 20, 65) * np.pi / 180,
    pulse=Pulse(center_frequency=18e6, n_periods=3, inverse=False),
    rx_sample_range=(0, 1024 * 2 + 256),
    downsampling_factor=1,
    speed_of_sound=1540,
    pri=900e-6,
    tgc_start=14,
    tgc_slope=2e2)

# Imaging output grid.
x_grid = np.arange(-7, 7, 0.05) * 1e-3
z_grid = np.arange(2, 10, 0.05) * 1e-3

SESSION_CFG_PATH = "./us4r.prototxt"
SCHEME = Scheme(
    tx_rx_sequence=sequence,
    processing=Pipeline(
        steps=(
            # Channel data pre-processing.
            RemapToLogicalOrder(),
            Transpose(axes=(0, 2, 1)),
            Pipeline(
                steps=(
                    Lambda(lambda data: data),
                ),
                placement="/GPU:0"
            ),
            BandpassFilter(),
            QuadratureDemodulation(),
            Decimation(decimation_factor=1, cic_order=1),
            # Data beamforming.
            ReconstructLri(x_grid=x_grid, z_grid=z_grid),
            Mean(axis=0),
            # Post-processing to B-mode image.
            EnvelopeDetection(),
            Transpose(),
            LogCompression()),
        placement="/GPU:0"))

INITIAL_PARAMS = {
    "dynamic_range": (20, 80),
    "tgc": {
        "tgc_sampling_step": 5e-3  # [m]
    },

    "voltage_range": (5, 15) #  [V]  TODO replace with the values read from ProbeModel specification
}