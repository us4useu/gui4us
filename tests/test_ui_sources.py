"""Static checks of the component library.

`npm run typecheck` / `npm run build` are the real gate, but they need Node. These tests catch
the failure that would be hardest to debug from a notebook -- a widget bundle that is not valid
JavaScript -- using a pure-python ES parser.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
UI_SRC = ROOT/"ui"/"src"

try:
    import esprima
    HAS_ESPRIMA = True
except ImportError:  # pragma: no cover - depends on the environment
    HAS_ESPRIMA = False


@unittest.skipUnless(HAS_ESPRIMA, "esprima is not installed (pip install esprima)")
class UiSourcesTest(unittest.TestCase):
    def setUp(self):
        if not UI_SRC.is_dir():
            self.skipTest("ui sources are not available")

    def test_every_module_is_valid_javascript(self):
        for path in sorted(UI_SRC.rglob("*.js")):
            with self.subTest(module=str(path.relative_to(UI_SRC))):
                esprima.parseModule(path.read_text(encoding="utf-8"))

    def test_every_widget_bundle_is_valid_javascript(self):
        from gui4us.view.jupyter.bundler import bundle
        for widget in ("display", "controls", "actions", "capture"):
            with self.subTest(widget=widget):
                # This is exactly what anywidget evaluates as _esm.
                esprima.parseModule(bundle(UI_SRC/"widgets"/f"{widget}.js"))


if __name__ == "__main__":
    unittest.main()
