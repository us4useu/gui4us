"""End-to-end tests of the web view's HTTP + WebSocket API.

Skipped when the ``web`` extra (fastapi) is not installed.
"""

import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.test_web_view import make_session  # noqa: E402

try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:  # pragma: no cover - depends on the environment
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "fastapi is not installed (pip install 'gui4us[web]')")
class WebServerTest(unittest.TestCase):
    def setUp(self):
        from gui4us.view.web.server import create_app
        self.env, self.session = make_session(capture_capacity=2)
        self.client = TestClient(create_app(self.session))

    def test_descriptor_endpoint(self):
        response = self.client.get("/api/descriptor")
        self.assertEqual(response.status_code, 200)
        descriptor = response.json()
        self.assertEqual([d["id"] for d in descriptor["displays"]], ["B-mode", "Line"])
        self.assertEqual({s["name"] for s in descriptor["settings"]}, {"voltage", "TGC"})

    def test_actions(self):
        self.assertEqual(self.client.post("/api/actions/start").status_code, 200)
        self.assertTrue(self.env.started)
        state = self.client.get("/api/state").json()
        self.assertEqual(state["hardware"], "started")
        self.assertEqual(self.client.post("/api/actions/stop").status_code, 200)
        self.assertFalse(self.env.started)

    def test_unknown_action_is_a_client_error(self):
        self.assertEqual(self.client.post("/api/actions/nope").status_code, 400)

    def test_set_setting(self):
        response = self.client.post("/api/settings/voltage", json={"value": 42})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.env.actions[-1].name, "voltage")
        np.testing.assert_allclose(self.env.actions[-1].value, [42])

    def test_capture_download(self):
        import pickle
        # Nothing captured yet.
        self.assertEqual(self.client.get("/api/capture.pkl").status_code, 400)
        self.client.post("/api/actions/capture", json={"n_frames": 1})
        self.env.stream.produce(value=5.0)
        self.session.capture_wait(timeout=1)
        response = self.client.get("/api/capture.pkl")
        self.assertEqual(response.status_code, 200)
        stored = pickle.loads(response.content)
        self.assertTrue(np.all(stored["data"][0][0] == 5.0))

    def test_websocket_streams_decodable_frames(self):
        from gui4us.view.protocol import decode_frame_arrays
        with self.client.websocket_connect("/ws/stream") as websocket:
            descriptor = websocket.receive_json()
            self.assertEqual(descriptor["type"], "descriptor")
            # An action over the socket must reach the environment...
            websocket.send_json({"type": "action", "name": "start"})
            # ...and the produced data must come back as a decodable binary frame.
            for _ in range(20):
                self.env.stream.produce(value=100.0)
                message = websocket.receive()
                if "bytes" in message and message["bytes"]:
                    header, arrays = decode_frame_arrays(message["bytes"])
                    self.assertEqual(header["type"], "frame")
                    self.assertEqual(arrays[0].shape, (8, 6))
                    self.assertTrue(np.all(arrays[0] == 255))
                    break
            else:  # pragma: no cover - only on a broken implementation
                self.fail("No binary frame was received.")
        self.assertTrue(self.env.started)

    def test_websocket_reports_errors_without_closing(self):
        with self.client.websocket_connect("/ws/stream") as websocket:
            websocket.receive_json()  # descriptor
            websocket.send_json({"type": "set_setting", "name": "nope", "value": 1})
            for _ in range(20):
                message = websocket.receive()
                if "text" in message and message["text"]:
                    import json
                    payload = json.loads(message["text"])
                    if payload.get("type") == "error":
                        self.assertIn("nope", payload["message"])
                        break
            else:  # pragma: no cover
                self.fail("No error message was received.")


if __name__ == "__main__":
    unittest.main()
