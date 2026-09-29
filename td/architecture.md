# GUI4us — architecture (summary)

GUI4us shows live ultrasound data and lets you control the acquisition: from a Python script, a
Jupyter notebook, a browser or a Qt window. It is a plain Python package: the browser front end
is built into it, so `pip install gui4us` is all a user needs (no Node).

More detail: [../docs/design/architecture.md](../docs/design/architecture.md) (layers, threading,
API) and [../docs/design/web_view.md](../docs/design/web_view.md) (browser/notebook protocol).

## 1. Layers

```
 script / notebook ──► gui4us.Gui4us  (facade: env + display config + app config)
                          │
 model        Env (start/stop/set/get_settings/get_stream) ── envs/arrus.py: UltrasoundEnv
                          │  Stream callbacks (acquisition thread)
 controller   EnvController: the Env behind one thread + a task queue (hardware is touched
              from that thread only; every call returns a Promise)
                          │
 view         ViewSession (host-independent view model: descriptor, frame encoding, capture)
                ├─ web/      FastAPI: REST + WebSocket          ─┐ same components,
                ├─ jupyter/  anywidget widgets                   ─┘ same wire protocol
                └─ view.py   PyQt window (matplotlib)
```

A frame: `Env` produces a tuple of numpy arrays → `ViewSession` stores the raw arrays in the
capture buffer (what `gui.capture()` returns) and encodes the newest frame for display (one byte
per pixel, rate-limited, never blocking the acquisition) → the front end colours and draws it.

## 2. Configuration (three objects)

| | object | old configuration directory |
|---|---|---|
| environment | an `Env` instance, or a factory called on the environment thread | `env.py` → `ENV` |
| displays | `gui4us.cfg.ViewCfg` | `display.py` → `VIEW_CFG` |
| application | `gui4us.AppCfg` (capture buffer, title, fps cap, view, host, port) | `app.py` |

```python
gui = Gui4us(env=lambda: UltrasoundEnv(session_cfg, configure), display=view_cfg, app=AppCfg(...))
with gui:
    gui.start(); gui.set("Voltage", 10)
    frames = gui.capture(20, timeout=60)      # raw arrays, into variables
    gui.run()                                 # "web" | "qt" | None
```
`Gui4us.from_cfg(dir)` still loads the directory form (the `gui4us --cfg` CLI).

## 3. Displays and layers

* **`Display2D`** — an image made of **layers**, drawn in order. Layers after the first are
  overlays: a **NaN pixel is transparent**, so e.g. colour Doppler (`bwr`) shows only where there
  is flow and the B-mode shows through elsewhere — the matplotlib convention, now in every view.
  Encoding: data → 0..254 within the layer's `value_range`, NaN → 255 (`NO_DATA`), transparent in
  every colour map (`gray`, `bone`, `hot`, `jet`, `viridis`, `inferno`, `magma`, `bwr`,
  `seismic`, `coolwarm`, `rdbu_r`). Layers are alpha-composited on the client.
* **Axes** — images are drawn inside OZ/OX axes with ticks and labels (mm when the extents are in
  metres). The extents come from the environment's metadata (ARRUS reports the reconstruction
  grid) or from `Display2D(extents=...)`.
* **`Display1D`** — line plots. **`DisplaySequence`** — one node per TX/RX, highlighted while it
  is being acquired (e.g. the sub-sequence an agent selected).
* **`GridSpec`** — the layout: rows/columns and the cells each display spans.

## 4. Views

| view | how | notes |
|---|---|---|
| browser | `gui.run("web")`, `gui.serve(background=True)`, `gui4us --cfg dir --view web` | default front end; `--host 0.0.0.0` exposes it (no authentication) |
| notebook | `gui.widget()` / `gui.notebook_view()` | `pip install "gui4us[jupyter]"` |
| Qt | `gui.run("qt")`, `gui4us --cfg dir` | `pip install "gui4us[qt]"` |

The browser app and the notebook widgets are the same Web Components (`ui/src`), so a display
looks the same in both.

## 5. The ARRUS environment and ARRUS versions

`gui4us.model.envs.arrus.UltrasoundEnv(session_cfg, configure)` opens the session, uploads the
scheme, exposes the pipeline parameters plus `Voltage` and `TGC` as settings, and feeds the
pipeline output to the stream. It works with the **released ARRUS 0.14.1** and with the
development build; what it can do depends on what the installed ARRUS supports:

| | ARRUS 0.14.1 (release) | development build |
|---|---|---|
| upload, start/stop, settings, capture | yes | yes |
| `set_subsequence(ops)` | contiguous ranges only (`slices=`) | any increasing list of TX/RXs |
| `prepare_subsequence(ops)` (sequencer double-buffering) | no (clear error) | yes |

The feature detection is in `supports_arbitrary_subsequences` / `supports_subsequence_double_buffering`.

## 6. Packaging and the front end

* `gui4us/view/web/static/` (the browser app) and `gui4us/view/jupyter/static/` (the widgets)
  are built files **shipped in the package** (`package_data`, `MANIFEST.in`). The server serves
  the package's copy.
* Developers change `ui/src` and rebuild both with `cd ui && npm run build:package` (Node ≥ 18:
  `npm ci`, typecheck, build); the output lands in the package directories above and is meant to
  be committed with the sources.
* The version comes from git when building from a checkout, otherwise from `gui4us/version.py`
  (e.g. a Docker build context), so `pip install` works on a plain copy of the sources.
* ARRUS is not a pip dependency (it is distributed as GitHub wheels matched to the system's
  drivers): install the ARRUS wheel first.

## 7. Examples

* `arrus-toolkit/examples/linear_array/bmode/` — `run.py` (classical, PWI, STA, DWI:
  `--sequence`) and `run.ipynb`.
* `arrus-toolkit/examples/linear_array/color_doppler/` — `run.py` and `run.ipynb`: colour and
  power Doppler overlaid on the B-mode, the Doppler thresholds in the control panel.
* `example/scripts/custom_tx_rx_sequence.py` in this repository, and the IUS 2026 cognitive
  ultrasound demo (us4us-demo-ius26), which drives sub-sequences through `gui.call(...)`, pushes
  its own images with `gui.show(...)` and uses `DisplaySequence`.

Each `run.py` defines `create_environment`, `create_display` and `create_gui` (the old `env.py`,
`display.py`, `app.py`); its notebook imports them.

## 8. Rules worth knowing

* The environment (hence the us4R session) belongs to the `EnvController` thread: call
  environment-specific methods through `gui.call(...)`, not directly.
* Close with `gui.close()` / the `with` block (or Ctrl+C): it stops the scheme, turns the HV off
  and closes the session. **Do not kill a process that holds a us4R session** — the boards can
  be left needing a power cycle.
* `gui.capture()` waits in short slices, so Ctrl+C works even when no frames arrive; pass a
  `timeout` in scripts. If the log says the us4R watchdog stopped the device (default 1 s), the
  host did not process a frame in time — e.g. GPU kernels compiled on the first frame (warm them
  up in the operation's `prepare`, as the Doppler example's `ops.py` does).

## 9. Tests

`python -m unittest discover -s tests` (53 tests; fake environments, no hardware). The server
tests need `httpx`, the widget tests `anywidget`/`ipywidgets`, the JavaScript checks `esprima`.
