"""Conversion of environment output arrays into displayable frames.

The value range and the colour map are display settings that already live in
``gui4us.cfg.ViewCfg``; applying the range here (vectorised, in numpy) and leaving the colour
map to a 256-entry LUT on the client keeps the wire payload at one byte per pixel.
"""

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

import gui4us.cfg
from gui4us.common import ImageMetadata
from gui4us.model import MetadataCollection, StreamDataId

from gui4us.view.protocol import ArrayHeader, Frame

#: Arrays with this many dimensions and a trailing axis of this size are already colour images.
_RGB_CHANNELS = (3, 4)


class LayerSpec:
    """A single displayable layer: where its data comes from and how it is rendered.

    :param display_id: the display (canvas) this layer belongs to
    :param layer: the layer number within the display
    :param input: the stream output the data is taken from
    :param kind: "2d" (image), "1d" (line plot) or "sequence" (nodes, see cfg.DisplaySequence)
    :param cmap: colour map name, applied by the client
    :param value_range: (min, max) mapped onto 0..255; None means per-metadata/auto
    """

    def __init__(self, display_id: str, layer: int, input: StreamDataId, kind: str,
                 cmap: Optional[str] = None, value_range: Optional[Tuple[float, float]] = None,
                 n_columns: Optional[int] = None, node_labels: Optional[Tuple[str, str]] = None,
                 metadata: Optional[ImageMetadata] = None,
                 title: Optional[str] = None, ax_labels: Optional[Sequence[str]] = None,
                 extents: Optional[Sequence[Sequence[float]]] = None,
                 labels: Optional[Sequence[str]] = None):
        self.display_id = display_id
        self.layer = layer
        self.input = input
        self.kind = kind
        self.n_columns = n_columns
        self.node_labels = node_labels
        self.cmap = cmap
        self.value_range = value_range
        self.metadata = metadata
        self.title = title
        self.ax_labels = ax_labels
        self.extents = extents
        self.labels = labels

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display": self.display_id,
            "layer": self.layer,
            "input": {"name": self.input.name, "ordinal": self.input.ordinal},
            "kind": self.kind,
            "n_columns": self.n_columns,
            "node_labels": list(self.node_labels) if self.node_labels is not None else None,
            "cmap": self.cmap,
            "value_range": list(self.value_range) if self.value_range is not None else None,
            "title": self.title,
            "ax_labels": list(self.ax_labels) if self.ax_labels is not None else None,
            "units": list(self.metadata.units) if self.metadata is not None
                     and self.metadata.units is not None else None,
            "extents": [list(e) for e in self.extents] if self.extents is not None else None,
            "shape": list(self.metadata.shape) if self.metadata is not None else None,
            "labels": list(self.labels) if self.labels is not None else None,
        }


def create_layers(view_cfg: gui4us.cfg.ViewCfg,
                  metadata: MetadataCollection) -> List[LayerSpec]:
    """Flattens a ViewCfg into the ordered list of layers the front end renders.

    Mirrors what ``gui4us.view.display.main_panel.DisplayPanel`` does for matplotlib, so that
    both views present the same displays for the same configuration.
    """
    displays = view_cfg.displays
    if not isinstance(displays, dict):
        displays = {f"Display:{i}": d for i, d in enumerate(displays)}

    layers: List[LayerSpec] = []
    for display_id, display_cfg in displays.items():
        if isinstance(display_cfg, gui4us.cfg.Display1D):
            layers.append(LayerSpec(
                display_id=display_id, layer=0, input=display_cfg.input, kind="1d",
                value_range=display_cfg.value_range,
                metadata=_get_metadata(metadata, display_cfg.input),
                title=display_cfg.title, ax_labels=display_cfg.ax_labels,
                labels=display_cfg.labels,
            ))
        elif isinstance(display_cfg, gui4us.cfg.DisplaySequence):
            layers.append(LayerSpec(
                display_id=display_id, layer=0, input=display_cfg.input, kind="sequence",
                metadata=_get_metadata(metadata, display_cfg.input),
                title=display_cfg.title, ax_labels=(display_cfg.ax_label, ""),
                n_columns=display_cfg.n_columns, node_labels=display_cfg.labels,
            ))
        elif isinstance(display_cfg, gui4us.cfg.Display2D):
            for i, layer_cfg in enumerate(display_cfg.layers):
                layer_metadata = _get_metadata(metadata, layer_cfg.input)
                extents = display_cfg.extents
                if extents is None and layer_metadata is not None:
                    extents = layer_metadata.extents
                layers.append(LayerSpec(
                    display_id=display_id, layer=i, input=layer_cfg.input, kind="2d",
                    cmap=layer_cfg.cmap, value_range=layer_cfg.value_range,
                    metadata=layer_metadata, title=display_cfg.title,
                    ax_labels=display_cfg.ax_labels, extents=extents,
                ))
        else:
            raise ValueError(f"Unsupported display type: {type(display_cfg)}")
    return layers


def _get_metadata(metadata: MetadataCollection,
                  input: StreamDataId) -> Optional[ImageMetadata]:
    if metadata is None:
        return None
    try:
        return metadata.output(input)
    except KeyError:
        return None


class FrameEncoder:
    """Turns the arrays produced by a Stream into an encoded :class:`Frame`."""

    def __init__(self, layers: Sequence[LayerSpec]):
        self.layers = list(layers)
        self._seq = 0

    def encode(self, data: Sequence[np.ndarray]) -> Frame:
        headers: List[ArrayHeader] = []
        chunks: List[bytes] = []
        offset = 0
        for layer in self.layers:
            if layer.input.ordinal >= len(data):
                # This layer's input is not in this frame -- e.g. a display fed by
                # Gui4us.show() with arrays the stream does not produce. Skip it.
                continue
            array = data[layer.input.ordinal]
            converted = self._convert(array, layer)
            payload = converted.tobytes()
            headers.append(ArrayHeader(
                display=layer.display_id, layer=layer.layer,
                shape=tuple(int(v) for v in converted.shape),
                dtype=str(converted.dtype), offset=offset, size=len(payload),
            ))
            chunks.append(payload)
            offset += len(payload)
        self._seq += 1
        return Frame(seq=self._seq, timestamp=time.time(), arrays=headers,
                     payload=b"".join(chunks))

    def _convert(self, array: np.ndarray, layer: LayerSpec) -> np.ndarray:
        array = np.asarray(array)
        if layer.kind in ("1d", "sequence"):
            # Line plots need the actual values; they are small (one scan line), so float32
            # costs nothing and saves the client from undoing a quantisation.
            return np.ascontiguousarray(np.atleast_2d(array), dtype=np.float32)
        if array.ndim == 3 and array.shape[-1] in _RGB_CHANNELS:
            # Already a colour image.
            if array.dtype != np.uint8:
                array = np.clip(array, 0, 255)
            return np.ascontiguousarray(array, dtype=np.uint8)
        if array.ndim != 2:
            raise ValueError(
                f"A 2D layer expects a 2D array or a 3D array with a trailing axis of size "
                f"3 or 4, got shape {array.shape}.")
        return _to_uint8(array, layer.value_range)


#: The encoded value of a pixel without data (NaN): the front end draws it transparent, which is
#: how an overlay layer (e.g. colour Doppler over a B-mode) shows the layers below it -- the same
#: convention matplotlib follows for NaN. Data is encoded as 0..NO_DATA-1.
NO_DATA = 255
_MAX_VALUE = NO_DATA - 1


def _to_uint8(array: np.ndarray, value_range: Optional[Tuple[float, float]]) -> np.ndarray:
    """Clips to the display's value range and rescales to 0..254; NaN becomes NO_DATA."""
    if array.dtype == np.uint8 and value_range is None:
        return np.ascontiguousarray(np.minimum(array, _MAX_VALUE))
    array = np.asarray(array, dtype=np.float32)
    missing = np.isnan(array)
    has_missing = bool(missing.any())
    if value_range is None:
        if has_missing and missing.all():
            return np.full(array.shape, NO_DATA, dtype=np.uint8)
        low, high = float(np.nanmin(array)), float(np.nanmax(array))
    else:
        low, high = float(value_range[0]), float(value_range[1])
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        # Degenerate range (e.g. a constant frame): show it as black rather than dividing by 0.
        result = np.zeros(array.shape, dtype=np.uint8)
    else:
        scaled = (array - low)*(_MAX_VALUE/(high - low))
        result = np.clip(np.nan_to_num(scaled, nan=0.0), 0, _MAX_VALUE).astype(np.uint8)
    if has_missing:
        result[missing] = NO_DATA
    return np.ascontiguousarray(result)
