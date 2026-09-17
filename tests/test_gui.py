"""Tests of the programmatic API (``gui4us.Gui4us``).

This is GUI4us used the way a script uses it: construct it from the three configuration objects
(display/env/app), acquire, capture into variables. The environment here is a fake one; the
same code paths are what ``example/arrus`` drives with real hardware.
"""

import pathlib
import sys
import threading
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gui4us import AppCfg, Gui4us  # noqa: E402
from tests.test_web_view import FakeEnv, make_view_cfg  # noqa: E402


class ScriptingApiTest(unittest.TestCase):
    """The API a script like api/python/examples/custom_tx_rx_sequence.py would use."""

    def make_gui(self, **kwargs):
        env = FakeEnv()
        app = AppCfg(capture_buffer_size=kwargs.pop("capture_buffer_size", 4),
                     max_fps=kwargs.pop("max_fps", 0), view=None)
        gui = Gui4us(env=env, display=make_view_cfg(), app=app, **kwargs)
        self.addCleanup(gui.close)
        return env, gui

    def test_constructor_takes_the_three_configuration_objects(self):
        env, gui = self.make_gui()
        self.assertIs(gui.env.env, env)
        self.assertEqual(gui.app_cfg.capture_buffer_size, 4)
        self.assertEqual([d["id"] for d in gui.session.view_descriptor()["displays"]],
                         ["B-mode", "Line"])
        self.assertEqual({s.name for s in gui.settings}, {"voltage", "TGC"})
        self.assertIsNotNone(gui.metadata)

    def test_environment_can_be_a_factory_called_on_the_env_thread(self):
        created_in = {}

        def factory():
            created_in["thread"] = threading.current_thread().name
            return FakeEnv()

        gui = Gui4us(env=factory, display=make_view_cfg(), app=AppCfg(view=None))
        self.addCleanup(gui.close)
        self.assertIn("thread", created_in)
        self.assertNotEqual(created_in["thread"], threading.current_thread().name)

    def test_start_stop_and_settings(self):
        """start/stop/set must be synchronous: a script relies on the hardware being up."""
        env, gui = self.make_gui()
        gui.start()
        self.assertTrue(env.started)
        gui.set("voltage", 20)
        np.testing.assert_allclose(env.actions[-1].value, [20])
        self.assertEqual(gui.get("voltage"), 10)      # the declared initial value
        gui.stop()
        self.assertFalse(env.started)

    def test_unknown_setting_is_rejected(self):
        env, gui = self.make_gui()
        with self.assertRaises(ValueError):
            gui.set("nope", 1)
        with self.assertRaises(ValueError):
            gui.get("nope")

    def test_capture_returns_arrays_to_the_script(self):
        env, gui = self.make_gui()
        gui.start()
        threading.Timer(0.05, lambda: [env.stream.produce(value=v) for v in (1.0, 2.0)]).start()
        frames = gui.capture(2, timeout=5)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0][0].dtype, np.float32)
        np.testing.assert_allclose([float(f[0][0, 0]) for f in frames], [1.0, 2.0])
        self.assertEqual(gui.captured_array(output=0).shape, (2, ) + frames[0][0].shape)

    def test_on_new_data_callback(self):
        env, gui = self.make_gui()
        received = []
        gui.on_new_data(received.append)
        env.stream.produce(value=9.0)
        self.assertEqual(len(received), 1)
        self.assertTrue(np.all(received[0][0] == 9.0))

    def test_save(self):
        import pickle
        import tempfile
        env, gui = self.make_gui(capture_buffer_size=1)
        gui.capture(1, wait=False)
        env.stream.produce(value=4.0)
        gui.session.capture_wait(timeout=1)
        with tempfile.TemporaryDirectory() as directory:
            path = gui.save(str(pathlib.Path(directory)/"capture.pkl"))
            with open(path, "rb") as f:
                stored = pickle.load(f)
        self.assertTrue(np.all(stored["data"][0][0] == 4.0))

    def test_call_forwards_to_the_environment_thread(self):
        class EnvWithExtras(FakeEnv):
            def __init__(self):
                super().__init__()
                self.calls = []

            def set_subsequence(self, ops, sri=None):
                self.calls.append((tuple(ops), sri,
                                   threading.current_thread().name))
                return "done"

        env = EnvWithExtras()
        gui = Gui4us(env=env, display=make_view_cfg(), app=AppCfg(view=None))
        self.addCleanup(gui.close)
        result = gui.call("set_subsequence", [2, 3, 5], sri=1e-3)
        self.assertEqual(result, "done")
        self.assertEqual(env.calls[0][0], (2, 3, 5))
        self.assertEqual(env.calls[0][1], 1e-3)
        # ... and it ran on the environment thread, not this one.
        self.assertNotEqual(env.calls[0][2], threading.current_thread().name)

    def test_call_propagates_errors(self):
        env, gui = self.make_gui()
        with self.assertRaises(AttributeError):
            gui.call("there_is_no_such_method")

    def test_run_with_no_view_returns_immediately(self):
        env, gui = self.make_gui()
        self.assertEqual(gui.run(), 0)
        self.assertEqual(gui.run(view="none"), 0)
        with self.assertRaises(ValueError):
            gui.run(view="banana")

    def test_context_manager_closes_the_environment(self):
        env = FakeEnv()
        env.started = True
        with Gui4us(env=env, display=make_view_cfg(), app=AppCfg(view=None)) as gui:
            self.assertIsNotNone(gui.session)
        self.assertFalse(env.started)


class InterpreterExitTest(unittest.TestCase):
    """A script that forgets close() must still exit -- and close the environment on the way.

    Regression: the environment thread is a non-daemon thread and Python joins those before
    running atexit handlers, so the process used to hang forever at exit with the hardware
    still running.
    """

    def test_script_without_close_exits_and_closes_the_environment(self):
        import subprocess
        import textwrap
        script = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})
            from gui4us import AppCfg, Gui4us
            from tests.test_web_view import FakeEnv, make_view_cfg

            class ReportingEnv(FakeEnv):
                def close(self):
                    super().close()
                    print("ENV CLOSED", flush=True)

            gui = Gui4us(env=ReportingEnv(), display=make_view_cfg(), app=AppCfg(view=None))
            gui.start()
            print("SCRIPT DONE", flush=True)
            # no gui.close() on purpose
        """)
        result = subprocess.run([sys.executable, "-c", script], capture_output=True,
                                text=True, timeout=60, cwd=str(ROOT))
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("SCRIPT DONE", result.stdout)
        self.assertIn("ENV CLOSED", result.stdout)


class AppCfgTest(unittest.TestCase):
    def test_from_module_reads_the_legacy_app_py(self):
        import types
        module = types.SimpleNamespace(CAPTURE_BUFFER_SIZE=42)
        cfg = AppCfg.from_module(module)
        self.assertEqual(cfg.capture_buffer_size, 42)
        # Everything else keeps its default, so old configurations still load.
        self.assertEqual(cfg.max_fps, AppCfg().max_fps)
        self.assertEqual(cfg.view, AppCfg().view)


class FromCfgTest(unittest.TestCase):
    """Gui4us.from_cfg must accept the configuration directories the CLI uses."""

    def setUp(self):
        try:
            import arrus  # noqa: F401
        except ImportError:
            self.skipTest("the dummy example environment imports arrus")

    def test_from_cfg_dummy_example(self):
        gui = Gui4us.from_cfg(str(ROOT/"example"/"dummy"))
        self.addCleanup(gui.close)
        # ... as declared by example/dummy/app.py (CAPTURE_BUFFER_SIZE).
        self.assertEqual(gui.app_cfg.capture_buffer_size, 200)
        self.assertGreaterEqual(len(gui.session.view_descriptor()["displays"]), 1)
        gui.start()
        frames = gui.capture(3, timeout=10)
        self.assertEqual(len(frames), 3)
        gui.stop()


if __name__ == "__main__":
    unittest.main()
