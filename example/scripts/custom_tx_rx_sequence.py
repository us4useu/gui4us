"""GUI4us as a library: a custom TX/RX sequence, displayed and captured from a script.

This is the GUI4us counterpart of ``arrus/api/python/examples/custom_tx_rx_sequence.py``: the
same acquisition, but instead of ``arrus.utils.gui.Display2D`` the display, the control panel
and the capture buttons come from GUI4us -- in a Qt window, in the browser or in a notebook,
and the captured frames are ordinary numpy arrays in this script.

    python custom_tx_rx_sequence.py --cfg /opt/us4us/us4r.prototxt --view web
"""

import argparse

import numpy as np

import arrus
import arrus.logging
import arrus.medium
from arrus.ops.us4r import Pulse, Rx, Scheme, Tx, TxRx, TxRxSequence
from arrus.utils.imaging import Pipeline, RemapToLogicalOrder, Squeeze

from gui4us import AppCfg, Gui4us
from gui4us.cfg import Display2D, Layer2D, ViewCfg
from gui4us.model import StreamDataId
from gui4us.model.envs.arrus import ArrusEnvConfiguration, Curve, UltrasoundEnv

TGC_SAMPLING_POINTS = np.linspace(5e-3, 40e-3, 8)


def make_environment(session_cfg: str, voltage: int):
    """The environment (what ``env.py`` provides as ``ENV``).

    The factory is called on the GUI4us environment thread, which then owns the session.
    """
    def configure(session: arrus.Session) -> ArrusEnvConfiguration:
        us4r = session.get_device("/Us4R:0")
        n_elements = us4r.get_probe_model().n_elements
        sequence = TxRxSequence(
            ops=[
                TxRx(
                    Tx(aperture=[True]*n_elements,
                       excitation=Pulse(center_frequency=6e6, n_periods=2, inverse=False),
                       delays=delays),
                    Rx(aperture=[True]*n_elements, sample_range=(0, 4096),
                       downsampling_factor=1),
                    pri=200e-6,
                )
                for delays in ([0]*n_elements, np.linspace(0, 1e-6, n_elements))
            ],
            tgc_curve=[],          # TGC is set by GUI4us from the control panel
            sri=50e-3,
        )
        scheme = Scheme(
            tx_rx_sequence=sequence,
            processing=Pipeline(
                steps=(RemapToLogicalOrder(), Squeeze()),
                placement="/GPU:0",
            ),
        )
        return ArrusEnvConfiguration(
            scheme=scheme,
            tgc=Curve(points=TGC_SAMPLING_POINTS, values=[34]*len(TGC_SAMPLING_POINTS)),
            medium=arrus.medium.Medium(name="water", speed_of_sound=1490),
            voltage=voltage,
        )

    return lambda: UltrasoundEnv(session_cfg=session_cfg, configure=configure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfg", required=True, help="ARRUS session configuration file")
    parser.add_argument("--voltage", type=int, default=5, help="TX voltage [V]")
    parser.add_argument("--view", default="web", choices=("qt", "web", "none"),
                        help="which view to run")
    parser.add_argument("--capture", type=int, default=0,
                        help="capture this many frames before showing the view")
    args = parser.parse_args()

    arrus.set_clog_level(arrus.logging.INFO)

    # display.py, env.py and app.py -- as objects.
    display = ViewCfg(displays={
        "RF": Display2D(
            title="RF frame 0",
            layers=(Layer2D(input=StreamDataId("default", 0), cmap="viridis",
                            value_range=(-100, 100)), ),
        ),
    })
    app = AppCfg(capture_buffer_size=100, title="Custom TX/RX sequence", view=args.view)

    with Gui4us(env=make_environment(args.cfg, args.voltage),
                display=display, app=app) as gui:
        print("settings exposed by the environment:",
              [setting.name for setting in gui.settings])
        gui.start()

        if args.capture:
            # Data straight into this script, before any view is shown.
            frames = gui.capture(args.capture)
            data = gui.captured_array(output=0)
            print(f"captured {len(frames)} frames, stacked: {data.shape} {data.dtype}")
            np.save("capture.npy", data)

        # Blocks until the window/page is closed; --view none skips it.
        gui.run()


if __name__ == "__main__":
    main()
