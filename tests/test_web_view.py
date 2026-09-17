"""Tests for the web/notebook view: protocol, frame encoding, session and bundler.

They run against a fake environment (the same shape as ``example/dummy``), so no hardware and
no PyQt are needed.
"""

import pathlib
import sys
import threading
import time
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import gui4us.cfg  # noqa: E402
from gui4us.common import ImageMetadata  # noqa: E402
from gui4us.model import (  # noqa: E402
    Box,
    Env,
    MetadataCollection,
    SetAction,
    SettingDef,
    Stream,
    StreamDataId,
)
from gui4us.view.frames import create_layers  # noqa: E402
from gui4us.view.protocol import (  # noqa: E402
    decode_frame,
    decode_frame_arrays,
    encode_frame,
)
from gui4us.view.session import ViewSession  # noqa: E402

IMAGE_SHAPE = (8, 6)
CURVE_SHAPE = (10, )


class FakeStream(Stream):
    def __init__(self):
        self.callbacks = []

    def append_on_new_data_callback(self, callback):
        self.callbacks.append(callback)

    def get_metadata(self):
        return "stream-metadata"

    def produce(self, value=1.0):
        image = np.full(IMAGE_SHAPE, value, dtype=np.float32)
        curve = np.arange(CURVE_SHAPE[0], dtype=np.float32)
        for callback in self.callbacks:
            callback((image, curve))


class FakeEnv(Env):
    def __init__(self):
        self.stream = FakeStream()
        self.actions = []
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def close(self):
        self.started = False

    def set(self, set_action: SetAction):
        self.actions.append(set_action)

    def get_settings(self):
        return [
            SettingDef(name="voltage",
                       space=Box(shape=(1, ), dtype=np.float32, low=5, high=90, unit="V"),
                       initial_value=10, step=1),
            SettingDef(name="TGC",
                       space=Box(shape=(3, ), dtype=np.float32, low=14, high=54,
                                 name=["0 mm", "10 mm", "20 mm"], unit=["dB"]*3),
                       initial_value=[20, 20, 20], step=1),
        ]

    def get_stream(self):
        return self.stream

    def get_stream_metadata(self):
        return MetadataCollection({
            StreamDataId("default", 0): ImageMetadata(
                shape=IMAGE_SHAPE, dtype="float32", ids=("OZ", "OX"), units=("mm", "mm"),
                extents=((0, 40), (-20, 20))),
            StreamDataId("default", 1): ImageMetadata(
                shape=CURVE_SHAPE, dtype="float32", ids=("sample", "amplitude")),
        })


class FakeEnvController:
    """The part of EnvController the session uses, without the worker thread."""

    def __init__(self, env: FakeEnv):
        self.env = env

    class _Promise:
        def __init__(self, value):
            self.value = value

        def get_result(self):
            return self.value

    def get_stream(self):
        return self.env.get_stream()

    def get_stream_metadata(self):
        return self._Promise(self.env.get_stream_metadata())

    def get_settings(self):
        return self._Promise(self.env.get_settings())

    def start(self):
        self.env.start()

    def stop(self):
        self.env.stop()

    def set(self, action):
        self.env.set(action)

    def close(self):
        self.env.close()


def make_view_cfg():
    return gui4us.cfg.ViewCfg(displays={
        "B-mode": gui4us.cfg.Display2D(
            title="B-mode",
            layers=(gui4us.cfg.Layer2D(input=StreamDataId("default", 0), cmap="gray",
                                       value_range=(0, 100)), ),
        ),
        "Line": gui4us.cfg.Display1D(title="Line", input=StreamDataId("default", 1)),
    })


def make_session(**kwargs):
    env = FakeEnv()
    session = ViewSession(FakeEnvController(env), make_view_cfg(),
                          capture_capacity=kwargs.pop("capture_capacity", 3),
                          max_fps=kwargs.pop("max_fps", 0))
    return env, session


class ProtocolTest(unittest.TestCase):
    def test_frame_round_trip(self):
        header = {"type": "frame", "seq": 7, "timestamp": 1.5, "arrays": []}
        message = encode_frame(header, b"payload")
        decoded_header, payload = decode_frame(message)
        self.assertEqual(decoded_header, header)
        self.assertEqual(payload, b"payload")

    def test_truncated_message_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_frame(b"\x02")


class FrameEncodingTest(unittest.TestCase):
    def test_layers_follow_the_view_cfg(self):
        env = FakeEnv()
        layers = create_layers(make_view_cfg(), env.get_stream_metadata())
        self.assertEqual([(l.display_id, l.kind) for l in layers],
                         [("B-mode", "2d"), ("Line", "1d")])
        self.assertEqual(layers[0].cmap, "gray")
        self.assertEqual(layers[0].extents, ((0, 40), (-20, 20)))

    def test_2d_layer_is_scaled_to_uint8(self):
        env, session = make_session()
        frames = []
        session.on_frame(frames.append)
        env.stream.produce(value=50.0)     # mid of the (0, 100) value range
        self.assertEqual(len(frames), 1)
        header, arrays = decode_frame_arrays(frames[0].to_bytes())
        self.assertEqual(header["arrays"][0]["dtype"], "uint8")
        self.assertEqual(arrays[0].shape, IMAGE_SHAPE)
        self.assertTrue(np.all(arrays[0] == 127) or np.all(arrays[0] == 128))
        # The 1D display keeps the raw values.
        self.assertEqual(arrays[1].dtype, np.float32)
        np.testing.assert_allclose(arrays[1].ravel(), np.arange(CURVE_SHAPE[0]))

    def test_values_outside_the_range_are_clipped(self):
        env, session = make_session()
        frames = []
        session.on_frame(frames.append)
        env.stream.produce(value=1e6)
        _, arrays = decode_frame_arrays(frames[0].to_bytes())
        self.assertTrue(np.all(arrays[0] == 255))


class SessionTest(unittest.TestCase):
    def test_descriptor(self):
        env, session = make_session()
        descriptor = session.view_descriptor()
        self.assertEqual([d["id"] for d in descriptor["displays"]], ["B-mode", "Line"])
        settings = {s["name"]: s for s in descriptor["settings"]}
        self.assertEqual(settings["voltage"]["kind"], "scalar")
        self.assertEqual(settings["TGC"]["kind"], "vector")
        self.assertEqual(settings["TGC"]["component_names"], ["0 mm", "10 mm", "20 mm"])
        self.assertEqual(settings["TGC"]["low"], 14)
        self.assertEqual(descriptor["capture"]["capacity"], 3)
        # The descriptor must be JSON serialisable (no numpy types).
        import json
        json.dumps(descriptor)

    def test_start_stop_and_state(self):
        env, session = make_session()
        states = []
        session.on_state(states.append)
        session.start()
        self.assertTrue(env.started)
        self.assertEqual(session.state()["hardware"], "started")
        session.stop()
        self.assertFalse(env.started)
        self.assertEqual(session.state()["hardware"], "stopped")
        self.assertEqual([s["hardware"] for s in states], ["started", "stopped"])

    def test_set_setting_reaches_the_environment(self):
        env, session = make_session()
        session.set_setting("voltage", 30)
        session.set_setting("TGC", [21, 22, 23])
        self.assertEqual([a.name for a in env.actions], ["voltage", "TGC"])
        np.testing.assert_allclose(env.actions[0].value, [30])
        np.testing.assert_allclose(env.actions[1].value, [21, 22, 23])

    def test_capture_collects_raw_arrays(self):
        env, session = make_session(capture_capacity=2)
        session.capture_start()
        self.assertEqual(session.state()["capture"]["state"], "capturing")
        env.stream.produce(value=1.0)
        env.stream.produce(value=2.0)
        self.assertTrue(session.capture_wait(timeout=1))
        self.assertEqual(session.state()["capture"]["state"], "captured")
        captured = session.captured_arrays()
        self.assertEqual(len(captured), 2)
        # RAW values, not the 8-bit display frames.
        self.assertEqual(captured[0][0].dtype, np.float32)
        self.assertTrue(np.all(captured[0][0] == 1.0))
        self.assertTrue(np.all(captured[1][0] == 2.0))
        self.assertEqual(session.captured_metadata, "stream-metadata")

    def test_capture_can_be_sized_per_call(self):
        env, session = make_session(capture_capacity=100)
        session.capture_start(1)
        env.stream.produce()
        self.assertTrue(session.capture_wait(timeout=1))
        self.assertEqual(len(session.captured_arrays()), 1)

    def test_capture_save(self):
        import pickle
        import tempfile
        env, session = make_session(capture_capacity=1)
        session.capture_start()
        env.stream.produce(value=3.0)
        session.capture_wait(timeout=1)
        with tempfile.TemporaryDirectory() as directory:
            path = session.capture_save(str(pathlib.Path(directory)/"capture"))
            self.assertTrue(path.endswith(".pkl"))
            with open(path, "rb") as f:
                stored = pickle.load(f)
        self.assertTrue(np.all(stored["data"][0][0] == 3.0))

    def test_frame_rate_is_throttled(self):
        env, session = make_session(max_fps=5)
        frames = []
        session.on_frame(frames.append)
        for _ in range(10):
            env.stream.produce()
        # 10 acquisitions in well under 200 ms must not produce 10 frames.
        self.assertLess(len(frames), 10)
        self.assertGreaterEqual(len(frames), 1)

    def test_acquisition_is_not_broken_by_a_failing_client(self):
        env, session = make_session()

        def broken(_frame):
            raise RuntimeError("client is gone")

        session.on_frame(broken)
        ok = []
        session.on_frame(ok.append)
        env.stream.produce()
        self.assertEqual(len(ok), 1)


class BundlerTest(unittest.TestCase):
    """The fallback bundler is what makes the notebook work without Node."""

    UI_SRC = pathlib.Path(__file__).resolve().parents[1]/"ui"/"src"

    def setUp(self):
        if not self.UI_SRC.is_dir():
            self.skipTest("ui sources are not available")

    def test_widgets_bundle(self):
        from gui4us.view.jupyter.bundler import bundle, top_level_names
        for widget in ("display", "controls", "actions", "capture"):
            with self.subTest(widget=widget):
                source = bundle(self.UI_SRC/"widgets"/f"{widget}.js")
                self.assertIn("customElements.define", source)
                self.assertIn("export default", source)
                # No import statement survives: anywidget cannot resolve them. (JSDoc type
                # references like {import("./x.js").T} live in comments and are harmless.)
                import re
                self.assertIsNone(re.search(r"^[ \t]*import\s", source, re.MULTILINE),
                                  "an import statement survived bundling")
                duplicates = {n: c for n, c in top_level_names(source).items() if c > 1}
                self.assertEqual(duplicates, {},
                                 f"Top-level names must be unique across modules: {duplicates}")

    def test_component_sources_only_use_relative_imports(self):
        from gui4us.view.jupyter.bundler import BundleError, bundle
        try:
            bundle(self.UI_SRC/"widgets"/"display.js")
        except BundleError as e:
            self.fail(str(e))


if __name__ == "__main__":
    unittest.main()
