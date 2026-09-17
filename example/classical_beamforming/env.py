"""Classical (scan line by scan line) B-mode imaging.

The GUI4us counterpart of ``arrus/api/python/examples/classical_beamforming.py``: the same
LinSequence and the same ``get_bmode_imaging`` reconstruction, with the display, TGC/voltage
controls and capture provided by GUI4us. No sub-sequences are selected -- every frame is the
full scan -- so this is the baseline for checking the live pipeline and the view.

    ARRUS_SESSION_CFG=~/us4r.prototxt gui4us --cfg example/classical_beamforming --view web
"""
import os

import numpy as np

import arrus.logging
import arrus.medium
from arrus.ops.imaging import LinSequence
from arrus.ops.us4r import Pulse, Scheme
from arrus.utils.imaging import get_bmode_imaging

from gui4us.model.envs.arrus import ArrusEnvConfiguration, Curve, UltrasoundEnv

SESSION_CFG = os.path.expanduser(os.environ.get("ARRUS_SESSION_CFG", "~/us4r.prototxt"))
VOLTAGE = int(os.environ.get("ARRUS_VOLTAGE", "20"))   # [V], as in the ARRUS example
SPEED_OF_SOUND = 1450                                    # [m/s]

# Imaging output grid [m].
X_GRID = np.arange(-15, 15, 0.1)*1e-3
Z_GRID = np.arange(5, 45, 0.1)*1e-3

# The example's tgc_start=14 dB, tgc_slope=200 dB/m, sampled at 10 depths; adjustable from the
# control panel. (UltrasoundEnv applies this curve after the upload, so it overrides the
# LinSequence's own TGC.)
TGC_SAMPLING_POINTS = np.linspace(np.min(Z_GRID), np.max(Z_GRID), 10)
TGC_VALUES = 14 + 2e2*TGC_SAMPLING_POINTS


def configure(session: arrus.Session) -> ArrusEnvConfiguration:
    us4r = session.get_device("/Us4R:0")
    n_elements = us4r.get_probe_model().n_elements

    sequence = LinSequence(
        tx_aperture_center_element=np.arange(0, n_elements),
        tx_aperture_size=64,
        tx_focus=20e-3,
        pulse=Pulse(center_frequency=6e6, n_periods=2, inverse=False),
        rx_aperture_center_element=np.arange(0, n_elements),
        rx_aperture_size=64,
        rx_sample_range=(0, 4096),
        pri=200e-6,
        tgc_start=14,
        tgc_slope=2e2,
        speed_of_sound=SPEED_OF_SOUND)

    scheme = Scheme(
        tx_rx_sequence=sequence,
        processing=get_bmode_imaging(sequence=sequence, grid=(X_GRID, Z_GRID)),
    )
    return ArrusEnvConfiguration(
        scheme=scheme,
        tgc=Curve(points=TGC_SAMPLING_POINTS, values=TGC_VALUES),
        medium=arrus.medium.Medium(name="tissue", speed_of_sound=SPEED_OF_SOUND),
        voltage=VOLTAGE,
    )


ENV = UltrasoundEnv(
    session_cfg=SESSION_CFG,
    configure=configure,
    log_file="arrus.log",
    log_file_level=arrus.logging.INFO,
)
