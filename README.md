## GUI4us

GUI4us is intended as a general front-end framework for fast prototyping
of ultrasound application demonstrator.

Please check https://us4useu.github.io/gui4us/ for more information.

### Views

The model and controller layers are shared by all views; pick the front end that fits:

| view | start it with | notes |
|---|---|---|
| Application window (default) | `gui4us --cfg <cfg dir>` | the browser UI in its own window; closing the window stops gui4us |
| Server only | `gui4us --cfg <cfg dir> --headless` | open http://127.0.0.1:7777 in a browser (`--host 0.0.0.0` for other machines) |
| PyQt | `gui4us --cfg <cfg dir> --view qt` | the original matplotlib desktop window |
| Jupyter | `NotebookView("<cfg dir>")` | needs `pip install "gui4us[jupyter]"` |

The application window uses an embedded web engine (pywebview: WebView2 on Windows, Qt WebEngine on
Linux x86_64 -- both installed with gui4us). Without one (e.g. on aarch64/Jetson), a Chromium/Chrome/Edge
window in the app mode or the default browser is opened instead (`--window auto|webview|browser`). With no
display (e.g. over SSH) gui4us runs headless. On Linux the Qt WebEngine sandbox is disabled by default (it
does not start with the pip-installed Qt WebEngine and the window stays blank); the window shows only the
local gui4us page. Set `QTWEBENGINE_DISABLE_SANDBOX=0` to keep the sandbox.

The browser and the notebook share one component library (`ui/`): the ultrasound stream display,
the control panel, and the action/capture buttons are the same custom elements in both. In a
notebook the acquisition runs in the kernel, so captured frames are ordinary numpy arrays:

```python
from gui4us.view.jupyter import NotebookView

view = NotebookView("example/dummy")   # the same cfg directory the Qt view uses
view                                    # display + control + action panels
view.start()

frames = view.capture(50)               # or press "Capture" in the panel
data = view.captured_array(output=0)    # (50, ...) numpy array
```

A script example is `example/scripts/custom_tx_rx_sequence.py` (the GUI4us version of the ARRUS
example of the same name), a notebook one is
`example/notebooks/gui4us_notebook_view.ipynb`.

Documentation: [docs/design/architecture.md](docs/design/architecture.md) (layers, the library
API, configuration, threading) and [docs/design/web_view.md](docs/design/web_view.md) (the
browser/notebook view and its wire protocol).

### Building the web front end

`pip install .` / `pip install -e .` / `pip wheel .` build the front end automatically (`npm ci` when
`ui/node_modules` is missing or outdated, then `npm run build:all`, into `gui4us/view/web/static` and
`gui4us/view/jupyter/static`); Node.js >= 18 with npm must be on the PATH. Without npm the already built
front end is installed (a warning is printed); `GUI4US_SKIP_UI_BUILD=1` skips the step.

To work on the front end directly:

```bash
cd ui
npm ci
npm run build          # -> gui4us/view/web/static, served by gui4us
npm run build:widgets  # optional: pre-built Jupyter widget bundles
npm run dev            # Vite dev server, proxying to a running gui4us --view web
npm run typecheck      # tsc --noEmit over the JSDoc types
```

### Tests

```bash
python -m unittest discover -s tests -v
```
