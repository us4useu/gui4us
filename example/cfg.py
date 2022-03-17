from gui4us.cfg.environment import *
from gui4us.cfg.display import *
from arrus.ops.us4r import *
from arrus.utils.imaging import *
from arrus.ops.imaging import *
import numpy as np
import scipy.signal

# Medium parameters
speed_of_sound = 5900

# TX/RX parameters
tx_frequency = 2.25e6
rx_sample_range_us = (10e-6, 31.5e-6)  # [s]
rx_sample_range = np.array(rx_sample_range_us)
pri = 200e-6
sri = 7e-3
initial_gain = 48
initial_voltage = 5
downsampling_factor = 1
sampling_frequency = 65e6 / downsampling_factor

# Processing parameters
fir_filter_taps = scipy.signal.firwin(
    64, np.array([0.5, 1.5]) * tx_frequency, pass_zero=False,
    fs=sampling_frequency)
frame = 15

environment = HardwareEnvironment(
    session_cfg="/home/pjarosik/us4r.prototxt",
    tx_rx_sequence=StaSequence(
        tx_aperture_center_element=np.arange(0, 32),
        rx_aperture_center_element=15,
        rx_aperture_size=32,
        tx_focus=0.0,
        pulse=Pulse(center_frequency=tx_frequency,
                    n_periods=2, inverse=False),
        rx_sample_range=rx_sample_range,
        downsampling_factor=downsampling_factor,
        speed_of_sound=speed_of_sound,
        pri=pri, sri=sri,
        tgc_start=initial_tgc,
        tgc_slope=0),
    pipeline=Pipeline(
        steps=(
            RemapToLogicalOrder(),
            Transpose(axes=(0, 1, 3, 2)),
            FirFilter(fir_filter_taps),
            SelectSequence([0]),
            SelectFrames([frame]),
            Squeeze()
        ),
        placement="/GPU:0"),
    work_mode="HOST",
    capture_buffer_capacity=500,
    initial_tx_voltage=initial_voltage,
    initial_gain=initial_gain
)

displays = {
    "rf": Display2D(
        title=f"RF frame: {frame}",
        layers=(
            Layer2D(
                value_range=(-1000, 1000),
                cmap="grey",
                input=LiveDataId("default", 0)
            ),
        )
    )
}

view_cfg = ViewCfg(displays)
