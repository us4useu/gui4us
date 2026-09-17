## GUI4us

GUI4us is intended as a general front-end framework for fast prototyping
of ultrasound application demonstrator.

Please check https://us4useu.github.io/gui4us/ for more information.

### Views

The model and controller layers are shared by all views; pick the front end that fits:

| view | start it with | notes |
|---|---|---|
| PyQt (default) | `gui4us --cfg <cfg dir>` | the original desktop window |
| Browser | `gui4us --cfg <cfg dir> --view web` | needs `pip install "gui4us[web]"`, serves http://127.0.0.1:7777 |
| Jupyter | `NotebookView("<cfg dir>")` | needs `pip install "gui4us[jupyter]"` |

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

The notebook view works out of the box. The browser view serves a bundle built with Node:

```bash
cd ui
npm ci
npm run build          # -> ui/dist, picked up by `gui4us --view web`
npm run build:widgets  # optional: pre-built Jupyter widget bundles
npm run dev            # Vite dev server, proxying to a running gui4us --view web
npm run typecheck      # tsc --noEmit over the JSDoc types
```

### Tests

```bash
python -m unittest discover -s tests -v
```
