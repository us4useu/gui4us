"""Tests for the notebook view.

The widgets are exercised in-process: anywidget/ipywidgets do not need a browser to build the
widget, sync traits or dispatch the messages a front end would send. Skipped when the
``jupyter`` extra is missing.
"""

import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.test_web_view import make_session  # noqa: E402

try:
    import anywidget  # noqa: F401
    import ipywidgets  # noqa: F401
    HAS_ANYWIDGET = True
except ImportError:  # pragma: no cover - depends on the environment
    HAS_ANYWIDGET = False


@unittest.skipUnless(HAS_ANYWIDGET, "anywidget is not installed (pip install 'gui4us[jupyter]')")
class JupyterWidgetsTest(unittest.TestCase):
    def setUp(self):
        from gui4us.view.jupyter import widgets
        self.widgets = widgets
        self.env, self.session = make_session(capture_capacity=2)

    def test_display_widget_carries_the_component_and_the_descriptor(self):
        display = self.widgets.StreamDisplay(self.session)
        self.assertIn("g4u-stream-view", display._esm)
        self.assertEqual(display.display_id, "B-mode")
        self.assertEqual([d["id"] for d in display.descriptor["displays"]],
                         ["B-mode", "Line"])
        self.assertEqual(display.state["hardware"], "stopped")

    def test_display_widget_receives_frames(self):
        from gui4us.view.protocol import decode_frame_arrays
        display = self.widgets.StreamDisplay(self.session, max_fps=0)
        self.env.stream.produce(value=100.0)
        self.assertTrue(display.frame, "no frame was pushed to the widget")
        header, arrays = decode_frame_arrays(display.frame)
        self.assertEqual(header["type"], "frame")
        self.assertTrue(np.all(arrays[0] == 255))

    def test_panels_expose_their_own_component(self):
        cases = {
            "controls": (self.widgets.ControlPanel, "g4u-control-panel"),
            "actions": (self.widgets.ActionsPanel, "g4u-actions-panel"),
            "capture": (self.widgets.CapturePanel, "g4u-capture-panel"),
        }
        for name, (factory, tag) in cases.items():
            with self.subTest(widget=name):
                widget = factory(self.session)
                self.assertIn(tag, widget._esm)
                self.assertIn("customElements.define", widget._esm)

    def test_actions_from_the_front_end_reach_the_environment(self):
        actions = self.widgets.ActionsPanel(self.session)
        actions._on_client_message(actions, {"type": "action", "name": "start"}, None)
        self.assertTrue(self.env.started)
        self.assertEqual(actions.state["hardware"], "started")
        actions._on_client_message(actions, {"type": "action", "name": "stop"}, None)
        self.assertFalse(self.env.started)

    def test_settings_from_the_front_end_reach_the_environment(self):
        controls = self.widgets.ControlPanel(self.session)
        controls._on_client_message(
            controls, {"type": "set_setting", "name": "TGC", "value": [30, 31, 32]}, None)
        self.assertEqual(self.env.actions[-1].name, "TGC")
        np.testing.assert_allclose(self.env.actions[-1].value, [30, 31, 32])

    def test_a_failing_action_is_reported_not_raised(self):
        controls = self.widgets.ControlPanel(self.session)
        sent = []
        controls.send = lambda message, *a, **kw: sent.append(message)
        controls._on_client_message(
            controls, {"type": "set_setting", "name": "nope", "value": 1}, None)
        self.assertEqual(sent[-1]["type"], "error")


@unittest.skipUnless(HAS_ANYWIDGET, "anywidget is not installed")
class NotebookViewTest(unittest.TestCase):
    def setUp(self):
        from gui4us.view.jupyter import NotebookView
        self.env, session = make_session(capture_capacity=3)
        self.view = NotebookView(session=session)

    def test_the_view_exposes_every_component(self):
        self.assertIn("g4u-stream-view", self.view.display._esm)
        self.assertIn("g4u-control-panel", self.view.control_panel._esm)
        self.assertIn("g4u-actions-panel", self.view.actions._esm)
        self.assertIn("g4u-capture-panel", self.view.capture_panel._esm)

    def test_layout_is_an_ipywidget(self):
        import ipywidgets
        self.assertIsInstance(self.view.widget(), ipywidgets.HBox)
        self.assertIsNotNone(self.view._repr_mimebundle_())

    def test_capture_lands_in_notebook_variables(self):
        import threading

        # The acquisition runs on its own thread, as it does with real hardware.
        def produce():
            for value in (1.0, 2.0, 3.0):
                self.env.stream.produce(value=value)

        self.view.start()
        self.assertTrue(self.env.started)
        threading.Timer(0.05, produce).start()
        frames = self.view.capture(3, timeout=5)

        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0][0].dtype, np.float32)      # raw, not the 8-bit display frame
        np.testing.assert_allclose([float(f[0][0, 0]) for f in frames], [1.0, 2.0, 3.0])
        # ... and the same data is reachable as attributes of the view.
        self.assertEqual(len(self.view.captured), 3)
        stacked = self.view.captured_array(output=0)
        self.assertEqual(stacked.shape, (3, ) + frames[0][0].shape)
        self.assertEqual(self.view.captured_metadata, "stream-metadata")

    def test_capture_from_the_ui_fills_the_same_variables(self):
        # Pressing "Capture" in the notebook UI must be equivalent to view.capture(...).
        panel = self.view.capture_panel
        panel._on_client_message(panel, {"type": "action", "name": "capture", "n_frames": 1},
                                 None)
        self.env.stream.produce(value=7.0)
        self.view.session.capture_wait(timeout=1)
        self.assertEqual(len(self.view.captured), 1)
        self.assertTrue(np.all(self.view.captured[0][0] == 7.0))


if __name__ == "__main__":
    unittest.main()
