"""Browser based GUI4us view.

The Python side is a thin shell around :class:`gui4us.view.session.ViewSession`: a FastAPI
server that exposes it over REST + WebSocket. The user interface itself lives in ``ui/`` and is
shared with the Jupyter widgets (see docs/design/web_view.md).
"""

from gui4us.view.frames import FrameEncoder, LayerSpec, create_layers
from gui4us.view.protocol import (
    Frame,
    decode_frame,
    decode_frame_arrays,
    encode_frame,
)
from gui4us.view.session import ViewSession, create_session

__all__ = [
    "Frame", "FrameEncoder", "LayerSpec", "ViewSession",
    "create_layers", "create_session", "decode_frame", "decode_frame_arrays", "encode_frame",
]
