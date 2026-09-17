"""Wire protocol shared by the web view and the Jupyter widgets.

Control messages are JSON, frames are binary. A frame is a single self-describing blob so that
the WebSocket transport and the anywidget (traitlet) transport can carry exactly the same bytes:

     0      4                4+H                  4+H+N
     +------+----------------+--------------------+
     | H:u32| JSON header (H)| payload (N bytes)  |
     +------+----------------+--------------------+

See docs/design/web_view.md for the rationale.
"""

import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

#: Header length prefix: unsigned 32-bit, little endian.
HEADER_LENGTH_FORMAT = "<I"
HEADER_LENGTH_SIZE = struct.calcsize(HEADER_LENGTH_FORMAT)

#: Message type names (also used by ui/src/core/protocol.js).
TYPE_FRAME = "frame"
TYPE_DESCRIPTOR = "descriptor"
TYPE_STATE = "state"
TYPE_ERROR = "error"
TYPE_ACTION = "action"
TYPE_SET_SETTING = "set_setting"


@dataclass(frozen=True)
class ArrayHeader:
    """Description of a single array (one display layer) inside a frame payload."""
    display: str
    layer: int
    shape: Tuple[int, ...]
    dtype: str
    offset: int
    size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display": self.display,
            "layer": self.layer,
            "shape": list(self.shape),
            "dtype": self.dtype,
            "offset": self.offset,
            "size": self.size,
        }


@dataclass(frozen=True)
class Frame:
    """An encoded frame: a JSON header plus the concatenated array payloads."""
    seq: int
    timestamp: float
    arrays: Sequence[ArrayHeader]
    payload: bytes = field(repr=False)

    def header_dict(self) -> Dict[str, Any]:
        return {
            "type": TYPE_FRAME,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "arrays": [a.to_dict() for a in self.arrays],
        }

    def to_bytes(self) -> bytes:
        return encode_frame(self.header_dict(), self.payload)


def encode_frame(header: Dict[str, Any], payload: bytes) -> bytes:
    """Packs a JSON header and a binary payload into a single frame message."""
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    return (struct.pack(HEADER_LENGTH_FORMAT, len(header_bytes))
            + header_bytes + payload)


def decode_frame(message: bytes) -> Tuple[Dict[str, Any], bytes]:
    """Splits a frame message back into its header and payload.

    This is the Python counterpart of ``decodeFrame`` in ui/src/core/protocol.js; it exists so
    that the tests can check both sides against the same definition.
    """
    if len(message) < HEADER_LENGTH_SIZE:
        raise ValueError("Truncated frame: no header length.")
    (header_length, ) = struct.unpack_from(HEADER_LENGTH_FORMAT, message, 0)
    header_end = HEADER_LENGTH_SIZE + header_length
    if len(message) < header_end:
        raise ValueError("Truncated frame: no header.")
    header = json.loads(message[HEADER_LENGTH_SIZE:header_end].decode("utf-8"))
    return header, message[header_end:]


def decode_frame_arrays(message: bytes) -> Tuple[Dict[str, Any], List[np.ndarray]]:
    """Decodes a frame into the header and the list of numpy arrays it carries."""
    header, payload = decode_frame(message)
    arrays = []
    for array_header in header["arrays"]:
        start = array_header["offset"]
        end = start + array_header["size"]
        array = np.frombuffer(payload[start:end], dtype=array_header["dtype"])
        arrays.append(array.reshape(array_header["shape"]))
    return header, arrays
