// @ts-check
/**
 * <g4u-stream-view> -- one ultrasound display.
 *
 * Renders the frames of a single display id onto a canvas: 2-D layers through a colour-map LUT,
 * 1-D layers as a line plot. It knows nothing about transports; the host sets `descriptor` and
 * calls `update(frame)`.
 */

import { drawAxes, fitAspect, plotRect } from "../core/axes.js";
import { applyColormap, getColormap } from "../core/colormap.js";

const STREAM_VIEW_STYLE = `
  :host { display: block; position: relative; background: #101014; color: #e6e6e6;
          font-family: system-ui, sans-serif; min-width: 0; min-height: 0; overflow: hidden; }
  /* The canvas covers the element; the image is drawn inside the axes (see core/axes.js), so
     the ticks and labels are part of the same drawing. */
  canvas { width: 100%; height: 100%; display: block; }
  .empty { position: absolute; inset: 0; display: grid; place-items: center; font-size: .85rem;
           opacity: .5; }
`;

export class StreamView extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STREAM_VIEW_STYLE}</style>
      <canvas></canvas>
      <div class="empty">waiting for data…</div>`;
    /** @type {HTMLCanvasElement} */
    this._canvas = /** @type {HTMLCanvasElement} */ (root.querySelector("canvas"));
    this._context = this._canvas.getContext("2d");
    this._emptyElement = /** @type {HTMLElement} */ (root.querySelector(".empty"));
    /** @type {any} */ this._descriptor = null;
    /** @type {Map<number, Uint8ClampedArray>} */ this._rgbaCache = new Map();
    /** @type {string} */ this._displayId = "";
    this._hasData = false;
    //: layer -> the canvas its latest frame is drawn into, before it is scaled into the plot.
    //: Each layer has its own, so that an overlay (e.g. colour Doppler) can be alpha-blended
    //: over the layers below it: its NO_DATA pixels are transparent.
    /** @type {Map<number, {canvas: HTMLCanvasElement, context: CanvasRenderingContext2D}>} */
    this._layerCanvases = new Map();
    /** @type {any[]} */ this._lastArrays = [];
    this._resizeObserver = new ResizeObserver(() => this._render());
    this._resizeObserver.observe(this);
  }

  disconnectedCallback() { this._resizeObserver.disconnect(); }

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
    this._render();
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
    // Layers are drawn in order; the first one sizes the frame.
    arrays.sort((a, b) => a.header.layer - b.header.layer);
    this._lastArrays = arrays;
    this._render();
  }

  /** Draws the axes and the newest frame; also called when the element is resized. */
  _render() {
    const arrays = this._lastArrays;
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(this.clientWidth*ratio));
    const height = Math.max(1, Math.round(this.clientHeight*ratio));
    if (this._canvas.width !== width || this._canvas.height !== height) {
      this._canvas.width = width;
      this._canvas.height = height;
    }
    const context = this._context;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, this.clientWidth, this.clientHeight);
    let rect = plotRect(this.clientWidth, this.clientHeight);
    const display = this._display();
    const firstDescriptor = arrays.length > 0
      ? this._layerDescriptor(this._displayId, arrays[0].header.layer) : null;
    const axes = firstDescriptor && firstDescriptor.kind === "1d"
      ? plotAxesOf(display, arrays[0], firstDescriptor) : axesOf(display, arrays);
    if (arrays.length > 0) {
      const descriptor = firstDescriptor;
      if (!(descriptor && descriptor.kind === "1d")) {
        // An image keeps its aspect ratio: the physical one (x/z extents: 1 mm across = 1 mm down),
        // or the pixel one when there are no extents.
        rect = fitAspect(rect, Math.abs(axes.x[1] - axes.x[0])/Math.abs(axes.y[1] - axes.y[0]));
      }
      if (descriptor && descriptor.kind === "1d") {
        this._drawPlot(arrays[0], descriptor, rect);
      } else {
        // Layers in order, each alpha-blended over the ones before it.
        context.imageSmoothingEnabled = true;
        for (const array of arrays) {
          const layer = this._drawImage(
            array, this._layerDescriptor(this._displayId, array.header.layer));
          context.drawImage(layer, rect.x, rect.y, rect.width, rect.height);
        }
      }
    }
    drawAxes(context, rect, axes);
  }

  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   * @returns {HTMLCanvasElement} the layer's canvas
   */
  _drawImage(array, descriptor) {
    const [height, width] = array.header.shape;
    const key = array.header.layer;
    let target = this._layerCanvases.get(key);
    if (!target) {
      const canvas = document.createElement("canvas");
      target = { canvas, context: /** @type {CanvasRenderingContext2D} */ (canvas.getContext("2d")) };
      this._layerCanvases.set(key, target);
    }
    if (target.canvas.width !== width || target.canvas.height !== height) {
      target.canvas.width = width;
      target.canvas.height = height;
      this._rgbaCache.delete(key);
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
    // putImageData copies the pixels as they are (alpha included); the blending happens when
    // the layer canvas is drawn into the plot.
    target.context.putImageData(image, 0, 0);
    return target.canvas;
  }

  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   */
  _drawPlot(array, descriptor, rect) {
    const [nCurves, nSamples] = array.header.shape;
    const width = rect.width;
    const height = rect.height;
    const context = this._context;
    context.save();
    context.translate(rect.x, rect.y);
    context.fillStyle = "#101014";
    context.fillRect(0, 0, width, height);
    const values = /** @type {Float32Array} */ (array.data);
    let [low, high] = (descriptor && descriptor.value_range) || minMax(values);
    if (!(high > low)) { low -= 1; high += 1; }
    const colours = ["#4fc3f7", "#ffb74d", "#81c784", "#e57373", "#ba68c8"];
    const xOf = (/** @type {number} */ i) => (i / (nSamples - 1 || 1)) * width;
    const yOf = (/** @type {number} */ value) => height - ((value - low) / (high - low)) * height;
    for (let curve = 0; curve < nCurves; curve++) {
      const colour = colours[curve % colours.length];
      const valueAt = (/** @type {number} */ i) => values[curve * nSamples + i];
      context.beginPath();
      context.strokeStyle = colour;
      context.lineWidth = 1.5;
      // Non-finite values (NaN: no data) break the line, instead of being bridged.
      let penDown = false;
      for (let i = 0; i < nSamples; i++) {
        const value = valueAt(i);
        if (!Number.isFinite(value)) { penDown = false; continue; }
        if (penDown) context.lineTo(xOf(i), yOf(value)); else context.moveTo(xOf(i), yOf(value));
        penDown = true;
      }
      context.stroke();
      // Isolated points (no finite neighbour) would draw nothing: mark them.
      context.fillStyle = colour;
      for (let i = 0; i < nSamples; i++) {
        const value = valueAt(i);
        if (!Number.isFinite(value)) continue;
        const isolated = !(i > 0 && Number.isFinite(valueAt(i - 1)))
          && !(i < nSamples - 1 && Number.isFinite(valueAt(i + 1)));
        if (isolated) context.fillRect(xOf(i) - 1.5, yOf(value) - 1.5, 3, 3);
      }
    }
    // Legend (Display1D labels).
    const labels = (descriptor && descriptor.labels) || [];
    context.font = "11px system-ui, sans-serif";
    context.textBaseline = "middle";
    for (let curve = 0; curve < Math.min(nCurves, labels.length); curve++) {
      const y = 10 + 14 * curve;
      context.fillStyle = colours[curve % colours.length];
      context.fillRect(8, y - 1, 14, 3);
      context.fillStyle = "#d4d7dd";
      context.fillText(String(labels[curve]), 28, y);
    }
    context.restore();
  }
}

/** @param {Float32Array} values @returns {[number, number]} */
function minMax(values) {
  let low = Infinity;
  let high = -Infinity;
  for (let i = 0; i < values.length; i++) {
    if (!Number.isFinite(values[i])) continue;
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

/**
 * The axis ranges and labels of a display: the extents come from the environment's metadata
 * (metres are shown as millimetres); without them the axes count samples.
 * @param {any} display @param {any[]} arrays
 * @returns {{x: [number, number], y: [number, number], xLabel: string, yLabel: string, title: string}}
 */
function axesOf(display, arrays) {
  const title = display ? (display.title || display.id) : "";
  const labels = (display && display.ax_labels) || ["OZ", "OX"];
  const shape = arrays.length > 0 ? arrays[0].header.shape : null;
  if (display && display.extents && display.extents.length >= 2) {
    const [z, x] = display.extents;
    // Extents in metres (an ultrasound image is a few centimetres): show millimetres.
    const scale = Math.max(Math.abs(z[1]), Math.abs(x[1])) < 1 ? 1e3 : 1;
    const unit = scale === 1e3 ? " [mm]" : "";
    return {
      x: /** @type {[number, number]} */([x[0]*scale, x[1]*scale]),
      y: /** @type {[number, number]} */([z[0]*scale, z[1]*scale]),
      xLabel: (labels[1] || "OX") + unit, yLabel: (labels[0] || "OZ") + unit, title,
    };
  }
  return {
    x: /** @type {[number, number]} */([0, shape ? shape[1] : 1]),
    y: /** @type {[number, number]} */([0, shape ? shape[0] : 1]),
    xLabel: labels[1] || "OX", yLabel: labels[0] || "OZ", title,
  };
}

/**
 * The axes of a line plot (Display1D): the sample number across, the value range upwards (the top of the
 * plotting area is the maximum). ax_labels are (x, y), as in the Qt view.
 * @param {any} display @param {any} array @param {any} descriptor
 * @returns {{x: [number, number], y: [number, number], xLabel: string, yLabel: string, title: string}}
 */
function plotAxesOf(display, array, descriptor) {
  const title = display ? (display.title || display.id) : "";
  const labels = (display && display.ax_labels) || ["", ""];
  const nSamples = array.header.shape[array.header.shape.length - 1];
  let [low, high] = (descriptor && descriptor.value_range)
    || minMax(/** @type {Float32Array} */ (array.data));
  if (!(high > low)) { low -= 1; high += 1; }
  return {
    x: [0, Math.max(1, nSamples - 1)],
    y: [high, low],
    xLabel: labels[0] || "", yLabel: labels[1] || "", title,
  };
}

if (!customElements.get("g4u-stream-view")) {
  customElements.define("g4u-stream-view", StreamView);
}
