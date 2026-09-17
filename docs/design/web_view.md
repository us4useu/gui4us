# GUI4us web / notebook view — technical design

Status: proposal + reference implementation (`gui4us/view/web`, `gui4us/view/jupyter`, `ui/`).

## 1. Goal

Add a second view implementation to GUI4us that

1. renders in the browser, driven by a Node.js component project — ultrasound stream display,
   action buttons (capture buffer, capture-and-save) and a control panel, each a separate
   component;
2. exposes **the same components** to Jupyter, so a notebook can show live ultrasound streams
   next to the control and action panels, and capture acquired data straight into notebook
   variables.

The existing architecture stays as it is. Nothing in `gui4us/model` or `gui4us/controller`
changes, and the PyQt view remains the default.

## 2. What already exists

```
gui4us/model/        Env (start/stop/close/set/get_settings/get_stream/get_stream_metadata),
                     Stream (callback based), SettingDef/SetAction/Box/Space,
                     MetadataCollection, StreamDataId.   model/envs/arrus.py = ARRUS env.
gui4us/controller/   EnvController  -- Env behind a task queue + worker thread, returns Promises
                     AppController  -- multiple envs, capture buffer
                     CaptureBuffer  -- fixed-capacity frame buffer
gui4us/cfg/          ViewCfg: Display2D/Display1D + Layer2D (cmap, value_range), GridSpec
gui4us/view/         PyQt5 + matplotlib: View -> EnvironmentView -> {DisplayPanel, ControlPanel
                     {ActionsPanel, CaptureBufferComponent, SettingsPanel}}
gui4us/state_graph.py  the small state machine the views drive their UI state with
```

A configuration directory holds `env.py`, `app.py`, `display.py`, loaded by `gui4us.utils.load_cfg`.

Two observations drive the design:

* The Qt view is the *only* consumer of the controller API, and it is a thin one: it reads
  `ViewCfg`, subscribes to the stream, renders arrays, and pushes `SetAction`s back. Everything
  it does can be done by any other front end.
* The pieces the Qt view mixes into its widgets — value-range clipping, colour mapping, the
  capture-buffer state machine — are *view-model* concerns, not toolkit concerns. Factoring
  them out is what makes one component set serve both hosts.

## 3. Architecture

```
                    ┌──────────── unchanged ────────────┐
   Env (arrus/...) ─┤ EnvController ── AppController    │
                    └───────────────────┬───────────────┘
                                        │  frames (np.ndarray tuples), settings, actions
                             ┌──────────▼───────────┐
                             │     ViewSession      │   gui4us/view/web/session.py
                             │  - view descriptor   │   (host independent view-model)
                             │  - frame encoder     │
                             │  - capture buffer    │
                             └─────┬──────────┬─────┘
                    WebSocket/REST │          │ traitlets (anywidget comm)
                      ┌────────────▼───┐  ┌───▼───────────────┐
                      │  web server    │  │ Jupyter widgets   │
                      │ (FastAPI)      │  │ (anywidget)       │
                      └────────┬───────┘  └───┬───────────────┘
                               │  same wire protocol
                          ┌────▼──────────────▼────┐
                          │  ui/  (Node.js)        │
                          │  <g4u-stream-view>     │
                          │  <g4u-control-panel>   │
                          │  <g4u-actions-panel>   │
                          │  <g4u-capture-panel>   │
                          └────────────────────────┘
```

### 3.1 `ViewSession` — the shared view-model

`ViewSession` is the only new Python object that knows about both the controller and the view.
It is host independent: it has no idea whether a browser or a notebook is attached.

```python
session = ViewSession(env_controller, view_cfg, capture_capacity=100)
session.view_descriptor()          # displays, layers, settings, extents, capacity -> JSON
session.on_frame(callback)         # callback(EncodedFrame) for every stream update (throttled)
session.start() / session.stop()   # hardware start / freeze
session.set_setting(name, value)   # -> SetAction -> EnvController
session.capture_start(n) / capture_state() / captured_arrays() / capture_save(path)
session.close()
```

Responsibilities that used to live inside Qt widgets and now live here:

* **view descriptor** — flattens `ViewCfg` + `MetadataCollection` into a JSON structure the
  front end can render without any knowledge of Python objects;
* **frame encoding** — see §4;
* **capture buffer** — reuses `gui4us.controller.buffer.CaptureBuffer`, with the state machine
  (`empty → capturing → captured`) from `gui4us.state_graph`, so the Qt and web views behave
  identically.

### 3.2 Component library (`ui/`, Node.js)

A Node project (npm + Vite) holding the four components as **custom elements**, plus a
transport abstraction and colour-map LUTs. It builds the standalone single-page app.

The components are authored as **plain ES modules with JSDoc types** rather than TypeScript
sources. That is a deliberate constraint: anywidget loads an ES module *as-is* in the notebook,
so a build step would mean shipping two different artefacts and debugging two pipelines. With
this choice the very same file is:

* bundled by Vite into the app (`npm run build`), and
* handed to anywidget as `_esm` (`npm` not required at notebook run time).

Types are still checked in CI/dev by `npm run typecheck` (`tsc --noEmit --checkJs`).

| element | responsibility |
|---|---|
| `<g4u-stream-view>` | one display: canvas, colour map, value range, extents, axis labels; consumes binary frames |
| `<g4u-control-panel>` | renders `SettingDef`s (scalar → labelled number + slider; vector → one slider per component), emits `set-setting` |
| `<g4u-actions-panel>` | start / freeze, reflects hardware state |
| `<g4u-capture-panel>` | capture N frames, progress, save (browser download / server-side path), emits `capture`/`save` |

None of them import a transport: they receive frames/state through properties and emit
`CustomEvent`s. That is what makes them host agnostic.

### 3.3 Transports

```js
interface Transport {
  send(message)            // {type: "action"|"set_setting"|..., ...}
  onMessage(cb)            // JSON control messages
  onFrame(cb)              // decoded binary frames
}
```

* `WebSocketTransport` — `/ws/stream` for frames and control messages (standalone app).
* `ModelTransport` — anywidget `model`: control messages over `model.set("msg_out", …)` /
  `model.on("msg:custom")`, frames over a binary traitlet (`frame`).

## 4. Wire protocol

Control messages are JSON; frames are binary, because a B-mode frame at 30 fps through JSON
would dominate the CPU budget.

### 4.1 Frame message

A single binary blob, so that both WebSocket (`bytes` message) and anywidget (`bytes` traitlet)
carry it unchanged:

```
 0      4                4+H                    4+H+N
 ┌──────┬────────────────┬──────────────────────┐
 │ H:u32│ JSON header (H)│ payload (N bytes)    │
 └──────┴────────────────┴──────────────────────┘
```

Header:

```jsonc
{
  "type": "frame",
  "seq": 1234,                  // monotonic, lets the client drop stale frames
  "timestamp": 1699999999.123,
  "arrays": [                    // one entry per display layer, in descriptor order
    {"display": "OX", "layer": 0, "shape": [512, 256], "dtype": "uint8",
     "offset": 0, "size": 131072}
  ]
}
```

Pixel conversion is done in Python (`numpy`), because it is vectorised there and because the
value range is a *display* setting that already lives in `ViewCfg`:

* 2-D float/int arrays → clipped to `value_range`, scaled to `uint8`; the colour map is applied
  on the client through a 256-entry LUT (`cmap` name travels in the descriptor, not per frame);
* 3-D `(h, w, 3|4)` arrays → passed through as `uint8` RGB(A).

Sending `uint8` rather than `float32` is a 4× bandwidth cut and matches what a canvas can
display; a notebook that needs the raw values uses the capture API, which never goes through
this path.

### 4.2 Control messages

| direction | message |
|---|---|
| server → client | `{"type":"descriptor", …}` — displays, layers, settings, capacity |
| server → client | `{"type":"state", "hardware":"started|stopped", "capture":{…}}` |
| server → client | `{"type":"error", "message":…}` |
| client → server | `{"type":"action", "name":"start|stop|capture|save|clear"}` |
| client → server | `{"type":"set_setting", "name":"TGC", "value":[…]}` |

## 5. The two hosts

### 5.1 Standalone web app

`gui4us --cfg <dir> --view web [--host 0.0.0.0 --port 7777]` starts FastAPI + uvicorn:

```
GET  /                      the built app (ui/dist), or a hint if it has not been built
GET  /api/descriptor        view descriptor (also pushed on WS connect)
POST /api/actions/{name}    start|stop|capture|save|clear
POST /api/settings/{name}   {"value": …}
GET  /api/capture.pkl       download the captured buffer
WS   /ws/stream             frames + control messages
```

### 5.2 Jupyter

```python
from gui4us.view.jupyter import NotebookView

view = NotebookView("/path/to/cfg")     # builds EnvController + ViewSession
view                                     # _repr_mimebundle_ -> display + controls + actions
```

or component by component, which is the point of the exercise:

```python
view.display          # anywidget wrapping <g4u-stream-view>
view.control_panel    # <g4u-control-panel>
view.actions          # <g4u-actions-panel>
view.capture          # <g4u-capture-panel>
ipywidgets.HBox([view.control_panel, view.display])
```

Every widget is an `anywidget.AnyWidget` whose `_esm` is read from `ui/src/widgets/*.js`, i.e.
the same component sources the web app bundles.

### 5.3 Capture into notebook variables

The capture buffer holds the *raw* arrays the environment produced — not the 8-bit display
frames — so a notebook gets exactly what the pipeline computed:

```python
view.capture(50)              # blocks until 50 frames are captured (or returns a Future)
data = view.captured          # list[tuple[np.ndarray, ...]], one tuple per frame
meta = view.captured_metadata # MetadataCollection of the stream
np.save("frames.npy", np.stack([d[0] for d in data]))
```

`view.capture(...)` and the `<g4u-capture-panel>` button drive the same
`ViewSession.capture_start`, so pressing *Capture* in the notebook UI fills `view.captured`
too — that is the "capture directly into notebook variables" requirement.

## 6. Threading

`EnvController` already serialises environment access on its own thread; stream callbacks run
on the acquisition thread. Therefore:

* `ViewSession` does the array→`uint8` conversion **on the acquisition thread** but keeps only
  the newest frame (`deque(maxlen=1)`) and hands it to a sender thread, so a slow client cannot
  block acquisition;
* the web server pushes from an asyncio task that polls that slot at `--max-fps` (default 30);
* the notebook widget pushes from a timer thread at the same rate — ipykernel comms are
  thread-safe enough for this (the same pattern anywidget's own examples use).

## 7. Build and run

```bash
cd ui && npm ci && npm run build      # -> ui/dist, served by the web view
cd ui && npm run dev                  # Vite dev server against a running gui4us --view web
cd ui && npm run typecheck            # tsc --noEmit --checkJs over the JSDoc types
pip install "gui4us[web]"             # fastapi, uvicorn, websockets
pip install "gui4us[jupyter]"         # anywidget, ipywidgets
```

The notebook path needs neither Node nor `ui/dist`: the widgets read the component sources
directly from the installed package.

## 8. Testing

* `tests/test_protocol.py` — frame encode/decode round-trip, header correctness.
* `tests/test_session.py` — descriptor generation from a `ViewCfg` + dummy env, settings
  round-trip, capture state machine, captured arrays are the raw ones.
* `tests/test_server.py` — FastAPI `TestClient`: descriptor endpoint, actions, and a WebSocket
  client receiving decodable frames from `example/dummy`.
* `npm run typecheck` + `npm run build` for the component library.

## 9. Out of scope / future work

* Multi-environment layouts (`AppController` supports several envs; the web view exposes one).
* Authentication — the server binds to `127.0.0.1` by default and is meant for a local console.
* Streaming compression (JPEG/WebP per frame) — worth measuring before adding.
* 1-D displays currently render as a line plot in the same canvas component; a dedicated
  `<g4u-plot-view>` may be cleaner.
