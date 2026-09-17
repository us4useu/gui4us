"""End-to-end test with the real controller stack and the shipped ``example/dummy`` config.

Unlike the other tests this one goes through ``create_session`` -> ``load_cfg`` ->
``EnvController`` (worker thread) -> ``DummyEnv``, i.e. exactly what ``gui4us --view web`` and
``NotebookView(cfg_path)`` do, with the environment replaced by the dummy data source rather
than hardware.
"""

import pathlib
import sys
import time
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DUMMY_CFG = ROOT/"example"/"dummy"

try:
    import arrus  # noqa: F401
    HAS_ARRUS = True
except ImportError:  # pragma: no cover - depends on the environment
    HAS_ARRUS = False


@unittest.skipUnless(HAS_ARRUS, "the dummy example environment imports arrus")
class DummyConfigurationTest(unittest.TestCase):
    def setUp(self):
        from gui4us.view.session import create_session
        self.session = create_session(str(DUMMY_CFG), max_fps=0)
        self.addCleanup(self.session.close)

    def test_descriptor_matches_the_example_display_cfg(self):
        descriptor = self.session.view_descriptor()
        self.assertGreaterEqual(len(descriptor["displays"]), 1)
        self.assertGreaterEqual(len(descriptor["settings"]), 1)
        names = {s["name"] for s in descriptor["settings"]}
        self.assertIn("TGC", names)
        import json
        json.dumps(descriptor)

    def test_streaming_and_capture(self):
        from gui4us.view.protocol import decode_frame_arrays
        frames = []
        self.session.on_frame(frames.append)
        self.session.start()
        try:
            self.session.capture_start(5)
            self.assertTrue(self.session.capture_wait(timeout=10),
                            "the dummy environment produced no data")
            captured = self.session.captured_arrays()
            self.assertEqual(len(captured), 5)
            # The capture holds the raw arrays produced by the environment.
            self.assertEqual(captured[0][0].dtype, np.float32)
            # ... while the stream carries encoded frames the front end can decode.
            self.assertTrue(frames)
            header, arrays = decode_frame_arrays(frames[-1].to_bytes())
            self.assertEqual(header["type"], "frame")
            self.assertEqual(arrays[0].dtype, np.uint8)
        finally:
            self.session.stop()


if __name__ == "__main__":
    unittest.main()
