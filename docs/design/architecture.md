# GUI4us technical documentation

This document describes how GUI4us is put together and how to use it — as a library, from the
command line, in the browser and in a notebook. Companion documents:

* [web_view.md](web_view.md) — the browser/notebook view and its wire protocol in detail.

## 1. Layers

GUI4us is a model / controller / view stack. Every front end drives the same two lower layers.

```
      ┌──────────────────────────── gui4us.model ─────────────────────────────┐
      │  Env          start/stop/close, set(SetAction), get_settings(),       │
      │               get_stream(), get_stream_metadata()                     │
      │  Stream       push based: append_on_new_data_callback(cb)             │
      │  SettingDef   name + Space (Box) + initial value + step               │
      │  Metadata     ImageMetadata: shape, dtype, extents, units, ids        │
      │  envs/arrus.py  UltrasoundEnv -- ARRUS session + scheme + settings    │
      └───────────────────────────────┬───────────────────────────────────────┘
                                      │
      ┌──────────────────── gui4us.controller ────────────────────────────────┐
      │  EnvController   the Env behind a task queue on its own thread;       │
      │                  every call returns a Promise                        │
      │  AppController   several environments + a capture buffer              │
      │  CaptureBuffer   fixed capacity frame buffer                          │
      └───────────────────────────────┬───────────────────────────────────────┘
                                      │
      ┌───────────────────── gui4us.view ─────────────────────────────────────┐
      │  ViewSession   view-model: descriptor, frame encoding, capture        │
      │  view.py       PyQt window (matplotlib displays)                     │
      │  web/          FastAPI server (REST + WebSocket)                      │
      │  jupyter/      anywidget widgets                                      │
      │  ui/ (Node)    the components both of the latter render               │
      └───────────────────────────────────────────────────────────────────────┘
                                      │
      ┌───────────────────── gui4us.Gui4us ───────────────────────────────────┐
      │  the facade a script or a notebook uses                               │
      └───────────────────────────────────────────────────────────────────────┘
```

### Why `EnvController` has a thread

Hardware must be touched from one thread. `EnvController` runs an event loop over a task queue:
every public method posts a `MethodCallEvent` and returns a `Promise`. `EnvController.call(name,
*args)` extends that to *any* method of the environment, which is how environment specific
operations (for example `set_subsequence` of the ARRUS environment) stay on the owning thread.

`start()`, `stop()` and `set()` return their promise; `ViewSession` waits on it, so a failure to
start the hardware surfaces as an exception in the caller instead of only in the log.

### Data flow of one frame

```
 Env (acquisition thread)                 ViewSession                     view
 ─────────────────────────                ───────────                     ────
 pipeline output (np.ndarray tuple)
        │ Stream callback
        ├─────────────────────────────────► capture buffer (raw arrays)  ── Python variables
        └─────────────────────────────────► FrameEncoder                 ── uint8 + JSON header
                                             (value_range → uint8,        → WebSocket / traitlet
                                              newest frame only)          → <g4u-stream-view>
```

Two properties matter:

* the capture buffer stores what the environment produced — not the 8-bit display frames, so a
  notebook/script gets the real values;
* only the newest encoded frame is kept (`deque(maxlen=1)`) and the frame rate is capped
  (`AppCfg.max_fps`), so a slow or absent client never blocks acquisition.

## 2. Configuration

The same three pieces of configuration exist in two forms.

| | configuration directory | objects (library use) |
|---|---|---|
| environment | `env.py` → `ENV` | `Env` instance or a factory |
| displays | `display.py` → `VIEW_CFG` | `gui4us.cfg.ViewCfg` |
| application | `app.py` → `CAPTURE_BUFFER_SIZE`, … | `gui4us.cfg.AppCfg` |

`AppCfg.from_module` maps the module form onto the dataclass, so existing configuration
directories keep working; unknown attributes are ignored and missing ones keep their defaults.

```python
AppCfg(capture_buffer_size=100,   # frames per capture
       title=None,                # window/page title
       max_fps=30.0,              # display rate cap; acquisition is unaffected
       view="qt",                 # what Gui4us.run() starts: "qt" | "web" | None
       host="127.0.0.1", port=7777)
```

`ViewCfg` holds `Display2D` (with `Layer2D`: `input`, `cmap`, `value_range`) and `Display1D`
entries, optionally arranged by a `GridSpec`. A display's `input` is a `StreamDataId(name,
ordinal)`, where the ordinal selects one output of the environment's stream.

## 3. Using GUI4us as a library

```python
from gui4us import AppCfg, Gui4us
from gui4us.cfg import Display2D, Layer2D, ViewCfg
from gui4us.model import StreamDataId

gui = Gui4us(
    env=make_env,                       # Env instance or a callable returning one
    display=ViewCfg(displays={"B-mode": Display2D(
        title="B-mode",
        layers=(Layer2D(input=StreamDataId("default", 0), cmap="gray",
                        value_range=(20, 80)), ))}),
    app=AppCfg(capture_buffer_size=100, view="web"),
)
with gui:
    gui.start()                         # blocks until the hardware is running
    gui.set("Voltage", 20)              # a setting the environment exposes
    frames = gui.capture(50)            # list[tuple[np.ndarray, ...]] -- raw arrays
    data = gui.captured_array(output=0) # (50, ...) stacked
    gui.run()                           # the configured view; blocks until it closes
```

| member | purpose |
|---|---|
| `Gui4us(env, display, app=None, env_id="main")` | build from configuration objects |
| `Gui4us.from_cfg(path)` | build from a configuration directory (what the CLI does) |
| `start()` / `stop()` / `close()` | acquisition lifecycle; also a context manager |
| `set(name, value)` / `get(name)` | environment settings |
| `call(method, *args)` | any environment method, executed on the environment thread |
| `capture(n, timeout=None, wait=True)`, `captured`, `captured_array(i)`, `save(path)` | data into Python |
| `on_new_data(cb)`, `get_stream()` | per-frame callback (acquisition thread) |
| `run(view=None)` | run the view configured in `AppCfg` ("qt", "web", None) |
| `serve(host, port, background=False)` | the browser view; `background=True` returns a thread |
| `widget()` / `notebook_view()` | the notebook view of this instance |
| `settings`, `metadata`, `session`, `env` | introspection and the lower layers |

A worked example is `example/scripts/custom_tx_rx_sequence.py` — the GUI4us version of the ARRUS
example of the same name, replacing `arrus.utils.gui.Display2D`.

### Environment factory vs instance

Passing a **callable** (`env=lambda: UltrasoundEnv(...)`) is preferred for hardware: it is
invoked on the environment thread, so the session and everything it opens belong to that
thread. Passing an instance is fine for environments that do not care (e.g. replaying a file).

## 4. Views

| view | entry point | notes |
|---|---|---|
| PyQt | `gui4us --cfg <dir>` / `Gui4us.run("qt")` | matplotlib displays; needs PyQt5 |
| Browser | `gui4us --cfg <dir> --view web` / `Gui4us.serve()` | `pip install "gui4us[web]"`; build `ui/` |
| Jupyter | `NotebookView(...)` / `Gui4us.widget()` | `pip install "gui4us[jupyter]"`; no Node needed |

The browser and the notebook share the component library in `ui/` (`<g4u-stream-view>`,
`<g4u-control-panel>`, `<g4u-actions-panel>`, `<g4u-capture-panel>`) and the same binary frame
protocol; see [web_view.md](web_view.md). `gui4us.view` resolves the PyQt names lazily, so the
web/notebook views and library use do not require PyQt to be installed.

## 5. The ARRUS environment

`gui4us.model.envs.arrus.UltrasoundEnv(session_cfg, configure)` is the standard environment:

* `configure(session)` returns an `ArrusEnvConfiguration(scheme, tgc, medium, voltage)`;
* the constructor opens the ARRUS session, applies the voltage/medium, uploads the scheme and
  wraps the scheme's `Pipeline` into a `Processing` whose callback feeds the GUI4us `Stream`;
* `get_settings()` exposes the pipeline's own parameters (`Processing.get_parameters()`) plus
  `Voltage` and `TGC`, so the control panel is generated from the environment;
* `set(SetAction)` routes `Voltage`/`TGC` to the device and anything else to
  `Processing.set_parameter`;
* `set_subsequence(ops, sri=None, array_id=0)` limits the acquisition to the given TX/RXs
  (`arrus.Session.set_subsequences`): the scheme is stopped, the sequencer re-programmed, the
  pipeline reused (so the stream's callback and the views survive), the metadata refreshed, and
  the acquisition resumed if it was running. Call it through the controller:
  `gui.call("set_subsequence", [2, 3, 5, 8, 13])`.

## 6. Threading summary

| thread | what runs on it |
|---|---|
| caller (script / notebook kernel / Qt main) | `Gui4us` methods, view code |
| environment thread (`EnvController`) | everything that touches the environment/hardware |
| acquisition thread (ARRUS callback) | `Stream` callbacks: capture buffer append, frame encoding |
| view threads | Qt event loop, uvicorn (own thread when `background=True`), widget push timers |

Rules of thumb: never call the environment directly — go through `Gui4us`/`EnvController`;
keep `on_new_data` callbacks short, they run on the acquisition thread.

## 7. Tests

```bash
python -m unittest discover -s tests        # 49 tests
```

They use fake and dummy environments, so no hardware is required. `gui4us[web]`,
`gui4us[jupyter]` and `esprima` unlock the server, widget and JavaScript checks respectively;
the relevant tests skip when those are missing.

| file | covers |
|---|---|
| `tests/test_gui.py` | the `Gui4us` facade: configuration objects, factory, settings, capture, `call`, `from_cfg` |
| `tests/test_web_view.py` | protocol, frame encoding, `ViewSession`, the notebook bundler |
| `tests/test_web_server.py` | REST + WebSocket against `fastapi.TestClient` |
| `tests/test_jupyter_view.py` | the anywidget widgets and `NotebookView` |
| `tests/test_example_dummy.py` | the whole stack against `example/dummy` |
| `tests/test_ui_sources.py` | every JS module and widget bundle parses as an ES module |
