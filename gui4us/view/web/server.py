"""FastAPI server for the GUI4us web view.

REST for control, a WebSocket for frames. The static files it serves are the Vite build of the
component library (``ui/dist``) -- the very same components the Jupyter widgets load.
"""

import asyncio
import os
import pathlib
from typing import Any, Dict, List, Optional

from gui4us.logging import get_logger
from gui4us.view.protocol import TYPE_ACTION, TYPE_SET_SETTING
from gui4us.view.session import ViewSession

LOGGER = get_logger(__name__)

#: Where the built single page app is looked up (ui/dist in a source checkout, then the
#: package's own copy for an installed gui4us).
_UI_DIST_CANDIDATES = (
    pathlib.Path(__file__).resolve().parents[3]/"ui"/"dist",
    pathlib.Path(__file__).resolve().parent/"static",
)

_NO_UI_MESSAGE = """<!doctype html>
<html><body style="font-family: sans-serif; margin: 3rem">
<h2>GUI4us web view</h2>
<p>The front end has not been built yet. From the repository root run:</p>
<pre>cd ui &amp;&amp; npm ci &amp;&amp; npm run build</pre>
<p>The REST API and the <code>/ws/stream</code> WebSocket are already serving
(see <a href="/api/descriptor">/api/descriptor</a>).</p>
</body></html>"""


def find_ui_dist() -> Optional[pathlib.Path]:
    for candidate in _UI_DIST_CANDIDATES:
        if (candidate/"index.html").is_file():
            return candidate
    return None


def create_app(session: ViewSession):
    """Creates the FastAPI application serving the given session."""
    # Imported here so that gui4us without the [web] extra still imports.
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="GUI4us")
    app.state.session = session

    @app.get("/api/descriptor")
    def get_descriptor() -> Dict[str, Any]:
        return session.view_descriptor()

    @app.get("/api/state")
    def get_state() -> Dict[str, Any]:
        return session.state()

    @app.post("/api/settings/{name}")
    async def set_setting(name: str, body: Dict[str, Any]):
        try:
            session.set_setting(name, body["value"])
        except Exception as e:  # noqa: BLE001 - reported to the client
            raise HTTPException(status_code=400, detail=str(e))
        return {"status": "ok"}

    @app.post("/api/actions/{name}")
    async def do_action(name: str, body: Optional[Dict[str, Any]] = None):
        body = body or {}
        try:
            _run_action(session, name, body)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(e))
        return {"status": "ok", "state": session.state()}

    @app.get("/api/capture.pkl")
    def download_capture():
        try:
            payload = session.capture_bytes()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(e))
        return Response(
            content=payload, media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="capture.pkl"'})

    @app.websocket("/ws/stream")
    async def stream(websocket: WebSocket):
        await websocket.accept()
        loop = asyncio.get_running_loop()
        # Control messages are produced on acquisition/controller threads; hand them to the
        # event loop instead of touching the socket from there.
        outgoing: asyncio.Queue = asyncio.Queue(maxsize=16)

        def on_state(message: Dict[str, Any]):
            loop.call_soon_threadsafe(_put_nowait, outgoing, message)

        session.on_state(on_state)
        await websocket.send_json(session.view_descriptor())
        sender = asyncio.create_task(_send_frames(websocket, session, outgoing))
        try:
            while True:
                message = await websocket.receive_json()
                try:
                    _handle_client_message(session, message)
                except Exception as e:  # noqa: BLE001
                    await websocket.send_json({"type": "error", "message": str(e)})
        except WebSocketDisconnect:
            LOGGER.debug("Web socket client disconnected.")
        finally:
            sender.cancel()
            _remove_callback(session._state_callbacks, on_state)

    ui_dist = find_ui_dist()
    if ui_dist is not None:
        app.mount("/", StaticFiles(directory=str(ui_dist), html=True), name="ui")
    else:
        @app.get("/")
        def no_ui():
            return HTMLResponse(_NO_UI_MESSAGE)

    return app


def _put_nowait(queue: "asyncio.Queue", item) -> None:
    try:
        queue.put_nowait(item)
    except asyncio.QueueFull:
        pass


def _remove_callback(callbacks: List, callback) -> None:
    try:
        callbacks.remove(callback)
    except ValueError:
        pass


async def _send_frames(websocket, session: ViewSession, outgoing: "asyncio.Queue") -> None:
    """Pushes the newest frame (and any pending control message) to one client."""
    interval = session.min_frame_interval or 1/30
    last_seq = -1
    try:
        while True:
            while not outgoing.empty():
                await websocket.send_json(outgoing.get_nowait())
            frame = session.latest_frame()
            if frame is not None and frame.seq != last_seq:
                last_seq = frame.seq
                await websocket.send_bytes(frame.to_bytes())
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001 - the socket died; the receive loop reports it
        LOGGER.debug(f"Frame sender finished: {e}")


def _handle_client_message(session: ViewSession, message: Dict[str, Any]) -> None:
    message_type = message.get("type")
    if message_type == TYPE_ACTION:
        _run_action(session, message["name"], message)
    elif message_type == TYPE_SET_SETTING:
        session.set_setting(message["name"], message["value"])
    else:
        raise ValueError(f"Unknown message type: {message_type}")


def _run_action(session: ViewSession, name: str, body: Dict[str, Any]) -> None:
    if name == "start":
        session.start()
    elif name == "stop":
        session.stop()
    elif name == "capture":
        session.capture_start(body.get("n_frames"))
    elif name == "clear":
        session.capture_clear()
    elif name == "save":
        path = body.get("path")
        if not path:
            raise ValueError("The 'save' action requires a 'path'.")
        session.capture_save(path)
    else:
        raise ValueError(f"Unknown action: {name}")


def serve_app(app, host: str = "127.0.0.1", port: int = 7777, background: bool = False,
              log_level: str = "info"):
    """Serves a FastAPI application with uvicorn.

    :param background: when True, the server runs in a daemon thread and the function returns
      immediately (with the thread); otherwise it blocks until the server stops.
    """
    import threading

    import uvicorn

    if find_ui_dist() is None:
        LOGGER.warning(
            "The web UI has not been built (ui/dist is missing); serving the API only. "
            "Run: cd ui && npm ci && npm run build")
    config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
    server = uvicorn.Server(config)
    LOGGER.info(f"GUI4us web view: http://{host}:{port}")
    if not background:
        server.run()
        return 0
    thread = threading.Thread(target=server.run, name="gui4us-web", daemon=True)
    thread.start()
    thread.server = server  # so that the caller can ask it to exit
    return thread


def start_view_app(cfg_path: str, host: str = "127.0.0.1", port: int = 7777,
                   max_fps: float = 30.0, session: Optional[ViewSession] = None,
                   **kwargs) -> int:
    """Starts the web view; the signature mirrors ``gui4us.view.start_view_app``."""
    from gui4us.view.session import create_session

    own_session = session is None
    if session is None:
        session = create_session(cfg_path, max_fps=max_fps)
    try:
        return serve_app(create_app(session), host=host, port=port, background=False)
    finally:
        if own_session:
            session.close()
