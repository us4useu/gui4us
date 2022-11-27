from gui4us.cfg.environment import *
from gui4us.cfg.display import *
from arrus.ops.us4r import *
from arrus.utils.imaging import *
from arrus.ops.imaging import *
import numpy as np
import scipy.signal
import importlib
import sys


# Utility functions
def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


reconstruction = load_module("gui4us_recon", "C:/Users/NDT/src/gui4us/example/cfg/reconstruction.py")
from gui4us_recon import *
parameters = load_module("gui4us_params", "C:/Users/NDT/src/gui4us/example/cfg/parameters.py")
from gui4us_params import *


# HERE STARTS THE ACTUAL CONFIGURATION
rx_sample_range = np.array(rx_sample_range_us)*65e6
rx_sample_range = np.round(rx_sample_range).astype(np.int32)
rx_sample_range = ((rx_sample_range+64-1)//64)*64


# Processing parameters
fir_filter_taps = scipy.signal.firwin(
    64, np.array([0.5, 1.5]) * tx_frequency, pass_zero=False, fs=sampling_frequency)


environment = UltrasoundEnvironment(
    session_cfg="C:/Users/NDT/us4r.prototxt",
    tx_rx_sequence=StaSequence(
        tx_aperture_center_element=np.arange(0, 32),
        rx_aperture_center_element=15,
        tx_aperture_size=1,
        rx_aperture_size=32,
        tx_focus=0.0,
        pulse=Pulse(center_frequency=tx_frequency, n_periods=2, inverse=False),
        rx_sample_range=rx_sample_range,
        downsampling_factor=downsampling_factor,
        speed_of_sound=speed_of_sound,
        pri=pri, tgc_start=initial_gain,
        tgc_slope=0),
    pipeline=Pipeline(
        steps=(
            RemapToLogicalOrder(),
            # Output # 1
            Pipeline(
                steps=(
                    Lambda(lambda data: data),
                ),
                placement="/GPU:0"
            ),
            Transpose(axes=(0, 1, 3, 2)),
            BandpassFilter(),
            #FirFilter(fir_filter_taps),
            QuadratureDemodulation(),
            Decimation(decimation_factor=4, cic_order=2),
            # Data beamforming.
            ReconstructLriWedge(x_grid=x_grid, z_grid=z_grid,
                                wedge_speed_of_sound=wedge_speed_of_sound,
                                wedge_size=wedge_size, wedge_angle=wedge_angle),
            # TODO Phase coherence weighting
            # IQ compounding
            # Post-processing to B-mode image.
            Mean(axis=1),
            EnvelopeDetection(),
            Mean(axis=0),
            Transpose(),
            LogCompression()
            # Output #0
        ),
        placement="/GPU:0"),
    work_mode="HOST",
    capture_buffer_capacity=capture_buffer_capacity,
    initial_tx_voltage=initial_voltage,
    initial_gain=initial_gain,
    rx_buffer_size=4,
    host_buffer_size=4,
    log_file_level="TRACE",
    log_file="ndt.log"
)


displays = {
    "rf": Display2D(
        title=f"S-scan",
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
