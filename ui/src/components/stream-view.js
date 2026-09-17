// @ts-check
/**
 * <g4u-stream-view> -- one ultrasound display.
 *
 * Renders the frames of a single display id onto a canvas: 2-D layers through a colour-map LUT,
 * 1-D layers as a line plot. It knows nothing about transports; the host sets `descriptor` and
 * calls `update(frame)`.
 */

import { applyColormap, getColormap } from "../core/colormap.js";

const STREAM_VIEW_STYLE = `
  :host { display: block; position: relative; background: #101014; color: #e6e6e6;
          font-family: system-ui, sans-serif; min-width: 0; min-height: 0; overflow: hidden; }
  .title { position: absolute; top: .35rem; left: .6rem; font-size: .85rem; opacity: .85;
           pointer-events: none; text-shadow: 0 1px 2px #000; }
  .axes { position: absolute; bottom: .35rem; right: .6rem; font-size: .75rem; opacity: .6;
          pointer-events: none; text-shadow: 0 1px 2px #000; }
  /* The element sets the size; the image is scaled to fit inside it, keeping its aspect ratio
     (the canvas' pixel size is the frame size, its CSS size is the element's). */
  canvas { width: 100%; height: 100%; display: block; object-fit: contain;
           image-rendering: auto; }
  .empty { position: absolute; inset: 0; display: grid; place-items: center; font-size: .85rem;
           opacity: .5; }
`;

export class StreamView extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STREAM_VIEW_STYLE}</style>
      <canvas></canvas>
      <div class="title"></div>
      <div class="axes"></div>
      <div class="empty">waiting for data…</div>`;
    /** @type {HTMLCanvasElement} */
    this._canvas = /** @type {HTMLCanvasElement} */ (root.querySelector("canvas"));
    this._context = this._canvas.getContext("2d");
    this._titleElement = /** @type {HTMLElement} */ (root.querySelector(".title"));
    this._axesElement = /** @type {HTMLElement} */ (root.querySelector(".axes"));
    this._emptyElement = /** @type {HTMLElement} */ (root.querySelector(".empty"));
    /** @type {any} */ this._descriptor = null;
    /** @type {Map<number, Uint8ClampedArray>} */ this._rgbaCache = new Map();
    /** @type {string} */ this._displayId = "";
    this._hasData = false;
  }

  static get observedAttributes() { return ["display"]; }

  /** @param {string} name @param {string} _old @param {string} value */
  attributeChangedCallback(name, _old, value) {
    if (name === "display") this._displayId = value;
  }

  /** The display this view renders (defaults to the first one in the descriptor). */
  get display() { return this._displayId; }
  set display(value) { this._displayId = value; }

  /** The view descriptor: {displays: [...], layers: [...]}. */
  get descriptor() { return this._descriptor; }
  set descriptor(descriptor) {
    this._descriptor = descriptor;
    if (!this._displayId && descriptor && descriptor.displays && descriptor.displays.length) {
      this._displayId = descriptor.displays[0].id;
    }
    const display = this._display();
    this._titleElement.textContent = display ? (display.title || display.id) : "";
    this._axesElement.textContent = display ? formatAxes(display) : "";
  }

  _display() {
    if (!this._descriptor || !this._descriptor.displays) return null;
    return this._descriptor.displays.find((/** @type {any} */ d) => d.id === this._displayId)
      || this._descriptor.displays[0];
  }

  /** @param {string} display @param {number} layer */
  _layerDescriptor(display, layer) {
    if (!this._descriptor || !this._descriptor.layers) return null;
    return this._descriptor.layers.find(
      (/** @type {any} */ l) => l.display === display && l.layer === layer) || null;
  }

  /**
   * Draws one decoded frame.
   * @param {import("../core/protocol.js").DecodedFrame} frame
   */
  update(frame) {
    const arrays = frame.arrays.filter((a) => a.header.display === this._displayId);
    if (arrays.length === 0) return;
    if (!this._hasData) {
      this._hasData = true;
      this._emptyElement.remove();
    }
    // Layers are drawn in order; the first one sizes the canvas.
    arrays.sort((a, b) => a.header.layer - b.header.layer);
    const descriptor = this._layerDescriptor(this._displayId, arrays[0].header.layer);
    if (descriptor && descriptor.kind === "1d") {
      this._drawPlot(arrays[0], descriptor);
      return;
    }
    arrays.forEach((array, index) => {
      this._drawImage(array, this._layerDescriptor(this._displayId, array.header.layer),
        /* clear */ index === 0);
    });
  }

  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   * @param {boolean} clear
   */
  _drawImage(array, descriptor, clear) {
    const [height, width] = array.header.shape;
    if (this._canvas.width !== width || this._canvas.height !== height) {
      this._canvas.width = width;
      this._canvas.height = height;
      this._rgbaCache.clear();
    }
    const isColour = array.header.shape.length === 3;
    let rgba;
    if (isColour) {
      rgba = toRgba(/** @type {Uint8Array} */(array.data), array.header.shape[2]);
    } else {
      const lut = getColormap(descriptor && descriptor.cmap);
      rgba = applyColormap(/** @type {Uint8Array} */(array.data), lut,
        this._rgbaCache.get(array.header.layer));
      this._rgbaCache.set(array.header.layer, rgba);
    }
    // rgba is a Uint8ClampedArray over a plain ArrayBuffer; the cast is only for the checker,
    // which also allows a SharedArrayBuffer backing here.
    const image = new ImageData(/** @type {Uint8ClampedArray<ArrayBuffer>} */(rgba),
                                width, height);
    if (clear) this._context.clearRect(0, 0, width, height);
    this._context.putImageData(image, 0, 0);
  }

  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   */
  _drawPlot(array, descriptor) {
    const [nCurves, nSamples] = array.header.shape;
    const width = Math.max(nSamples, 256);
    const height = 240;
    if (this._canvas.width !== width || this._canvas.height !== height) {
      this._canvas.width = width;
      this._canvas.height = height;
    }
    const context = this._context;
    context.fillStyle = "#101014";
    context.fillRect(0, 0, width, height);
    const values = /** @type {Float32Array} */ (array.data);
    let [low, high] = (descriptor && descriptor.value_range) || minMax(values);
    if (!(high > low)) { low -= 1; high += 1; }
    const colours = ["#4fc3f7", "#ffb74d", "#81c784", "#e57373", "#ba68c8"];
    for (let curve = 0; curve < nCurves; curve++) {
      context.beginPath();
      context.strokeStyle = colours[curve % colours.length];
      context.lineWidth = 1.5;
      for (let i = 0; i < nSamples; i++) {
        const value = values[curve * nSamples + i];
        const x = (i / (nSamples - 1 || 1)) * width;
        const y = height - ((value - low) / (high - low)) * height;
        if (i === 0) context.moveTo(x, y); else context.lineTo(x, y);
      }
      context.stroke();
    }
  }
}

/** @param {Float32Array} values @returns {[number, number]} */
function minMax(values) {
  let low = Infinity;
  let high = -Infinity;
  for (let i = 0; i < values.length; i++) {
    if (values[i] < low) low = values[i];
    if (values[i] > high) high = values[i];
  }
  return [low, high];
}

/** @param {Uint8Array} data @param {number} channels @returns {Uint8ClampedArray} */
function toRgba(data, channels) {
  if (channels === 4) return new Uint8ClampedArray(data);
  const rgba = new Uint8ClampedArray((data.length / 3) * 4);
  for (let i = 0, j = 0; i < data.length; i += 3, j += 4) {
    rgba[j] = data[i];
    rgba[j + 1] = data[i + 1];
    rgba[j + 2] = data[i + 2];
    rgba[j + 3] = 255;
  }
  return rgba;
}

/** @param {any} display */
function formatAxes(display) {
  if (!display.extents) return "";
  const [z, x] = display.extents;
  const labels = display.ax_labels || ["OZ", "OX"];
  return `${labels[0]}: ${z[0]}…${z[1]}   ${labels[1]}: ${x[0]}…${x[1]}`;
}

if (!customElements.get("g4u-stream-view")) {
  customElements.define("g4u-stream-view", StreamView);
}
