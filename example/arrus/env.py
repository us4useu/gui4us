import numpy as np
import arrus.medium
import os
from arrus.utils.imaging import *
from arrus.ops.imaging import *
from arrus.ops.us4r import *
from gui4us.model.envs.arrus import UltrasoundEnv

X_GRID = np.arange(-15e-3, 15e-3, 0.1e-3)
Z_GRID = np.arange(0e-3, 40e-3, 0.1e-3)
TGC_SAMPLING_POINTS = np.linspace(np.min(Z_GRID), np.max(Z_GRID), 10)
TGC_VALUES = np.linspace(54, 54, 10)

MEDIUM = arrus.medium.Medium(name="test_block", speed_of_sound=5800)


def create_scheme(session: arrus.Session):
    us4r = session.get_device("/Us4R:0")
    n_elements = us4r.get_probe_model().n_elements
    sequence = StaSequence(
        tx_aperture_center_element=np.arange(0, n_elements),
        tx_aperture_size=1,
        tx_focus=0,
        pulse=Pulse(center_frequency=9e6, n_periods=2, inverse=False),
        rx_sample_range=(0, 5*1024),
        downsampling_factor=1,
        speed_of_sound=MEDIUM.speed_of_sound,
        pri=200e-6,
        tgc_start=34,
        tgc_slope=0)

    pipeline = Pipeline(
        steps=(
            # Channel data pre-processing.
            RemapToLogicalOrder(),
            Transpose(axes=(0, 1, 3, 2)),
            BandpassFilter(),
            QuadratureDemodulation(),
            Decimation(decimation_factor=4, cic_order=2),
            ReconstructLri(x_grid=X_GRID, z_grid=Z_GRID),
            Mean(axis=1),  # Along tx axis.
            EnvelopeDetection(),
            Mean(axis=0),
            Transpose(),
            LogCompression()
        ),
        placement="/GPU:0")
    processing = Processing(
        pipeline=pipeline,
        callback=None,
        extract_metadata=False
    )
    return arrus.ops.us4r.Scheme(
        # Run the provided sequence.
        tx_rx_sequence=sequence,
        # Processing pipeline to perform on the GPU device.
        processing=processing
    )


ENV = UltrasoundEnv(
    session_cfg="/home/us4us/us4r.prototxt",
    medium=arrus.medium.Medium(name="test_block", speed_of_sound=5780),
    log_file="arrus.log", log_file_level=arrus.logging.INFO,
    configure=create_scheme,
    initial_voltage=5,
    tgc_sampling_points=TGC_SAMPLING_POINTS,
    initial_tgc_values=TGC_VALUES
)
