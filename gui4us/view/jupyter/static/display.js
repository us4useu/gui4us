import { w as v } from "./_widget-_BnPWc-d.js";
function h(s) {
  const t = new Uint8ClampedArray(1024), e = s.length - 1;
  for (let i = 0; i < 256; i++) {
    const n = i / 255 * e, a = Math.min(Math.floor(n), e - 1), o = n - a, r = s[a], l = s[a + 1];
    t[i * 4 + 0] = r[0] + (l[0] - r[0]) * o, t[i * 4 + 1] = r[1] + (l[1] - r[1]) * o, t[i * 4 + 2] = r[2] + (l[2] - r[2]) * o, t[i * 4 + 3] = 255;
  }
  return t;
}
const f = h([[0, 0, 0], [255, 255, 255]]), w = {
  gray: f,
  grey: f,
  bone: h([[0, 0, 0], [84, 84, 116], [169, 201, 201], [255, 255, 255]]),
  hot: h([[0, 0, 0], [255, 0, 0], [255, 255, 0], [255, 255, 255]]),
  inferno: h([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]]),
  magma: h([[0, 0, 4], [81, 18, 124], [183, 55, 121], [252, 137, 97], [252, 253, 191]]),
  viridis: h([[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]),
  jet: h([[0, 0, 128], [0, 0, 255], [0, 255, 255], [255, 255, 0], [255, 0, 0], [128, 0, 0]])
};
function x(s) {
  return s && w[s.toLowerCase()] || f;
}
function b(s, t, e) {
  const i = e && e.length === s.length * 4 ? e : new Uint8ClampedArray(s.length * 4);
  for (let n = 0; n < s.length; n++) {
    const a = s[n] * 4, o = n * 4;
    i[o] = t[a], i[o + 1] = t[a + 1], i[o + 2] = t[a + 2], i[o + 3] = t[a + 3];
  }
  return i;
}
const C = `
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
class I extends HTMLElement {
  constructor() {
    super();
    const t = this.attachShadow({ mode: "open" });
    t.innerHTML = `<style>${C}</style>
      <canvas></canvas>
      <div class="title"></div>
      <div class="axes"></div>
      <div class="empty">waiting for data…</div>`, this._canvas = /** @type {HTMLCanvasElement} */
    t.querySelector("canvas"), this._context = this._canvas.getContext("2d"), this._titleElement = /** @type {HTMLElement} */
    t.querySelector(".title"), this._axesElement = /** @type {HTMLElement} */
    t.querySelector(".axes"), this._emptyElement = /** @type {HTMLElement} */
    t.querySelector(".empty"), this._descriptor = null, this._rgbaCache = /* @__PURE__ */ new Map(), this._displayId = "", this._hasData = !1;
  }
  static get observedAttributes() {
    return ["display"];
  }
  /** @param {string} name @param {string} _old @param {string} value */
  attributeChangedCallback(t, e, i) {
    t === "display" && (this._displayId = i);
  }
  /** The display this view renders (defaults to the first one in the descriptor). */
  get display() {
    return this._displayId;
  }
  set display(t) {
    this._displayId = t;
  }
  /** The view descriptor: {displays: [...], layers: [...]}. */
  get descriptor() {
    return this._descriptor;
  }
  set descriptor(t) {
    this._descriptor = t, !this._displayId && t && t.displays && t.displays.length && (this._displayId = t.displays[0].id);
    const e = this._display();
    this._titleElement.textContent = e ? e.title || e.id : "", this._axesElement.textContent = e ? A(e) : "";
  }
  _display() {
    return !this._descriptor || !this._descriptor.displays ? null : this._descriptor.displays.find((t) => t.id === this._displayId) || this._descriptor.displays[0];
  }
  /** @param {string} display @param {number} layer */
  _layerDescriptor(t, e) {
    return !this._descriptor || !this._descriptor.layers ? null : this._descriptor.layers.find(
      (i) => i.display === t && i.layer === e
    ) || null;
  }
  /**
   * Draws one decoded frame.
   * @param {import("../core/protocol.js").DecodedFrame} frame
   */
  update(t) {
    const e = t.arrays.filter((n) => n.header.display === this._displayId);
    if (e.length === 0) return;
    this._hasData || (this._hasData = !0, this._emptyElement.remove()), e.sort((n, a) => n.header.layer - a.header.layer);
    const i = this._layerDescriptor(this._displayId, e[0].header.layer);
    if (i && i.kind === "1d") {
      this._drawPlot(e[0], i);
      return;
    }
    e.forEach((n, a) => {
      this._drawImage(
        n,
        this._layerDescriptor(this._displayId, n.header.layer),
        /* clear */
        a === 0
      );
    });
  }
  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   * @param {boolean} clear
   */
  _drawImage(t, e, i) {
    const [n, a] = t.header.shape;
    (this._canvas.width !== a || this._canvas.height !== n) && (this._canvas.width = a, this._canvas.height = n, this._rgbaCache.clear());
    const o = t.header.shape.length === 3;
    let r;
    if (o)
      r = E(
        /** @type {Uint8Array} */
        t.data,
        t.header.shape[2]
      );
    else {
      const c = x(e && e.cmap);
      r = b(
        /** @type {Uint8Array} */
        t.data,
        c,
        this._rgbaCache.get(t.header.layer)
      ), this._rgbaCache.set(t.header.layer, r);
    }
    const l = new ImageData(
      /** @type {Uint8ClampedArray<ArrayBuffer>} */
      r,
      a,
      n
    );
    i && this._context.clearRect(0, 0, a, n), this._context.putImageData(l, 0, 0);
  }
  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   */
  _drawPlot(t, e) {
    const [i, n] = t.header.shape, a = Math.max(n, 256), o = 240;
    (this._canvas.width !== a || this._canvas.height !== o) && (this._canvas.width = a, this._canvas.height = o);
    const r = this._context;
    r.fillStyle = "#101014", r.fillRect(0, 0, a, o);
    const l = (
      /** @type {Float32Array} */
      t.data
    );
    let [c, g] = e && e.value_range || S(l);
    g > c || (c -= 1, g += 1);
    const y = ["#4fc3f7", "#ffb74d", "#81c784", "#e57373", "#ba68c8"];
    for (let p = 0; p < i; p++) {
      r.beginPath(), r.strokeStyle = y[p % y.length], r.lineWidth = 1.5;
      for (let d = 0; d < n; d++) {
        const u = l[p * n + d], _ = d / (n - 1 || 1) * a, m = o - (u - c) / (g - c) * o;
        d === 0 ? r.moveTo(_, m) : r.lineTo(_, m);
      }
      r.stroke();
    }
  }
}
function S(s) {
  let t = 1 / 0, e = -1 / 0;
  for (let i = 0; i < s.length; i++)
    s[i] < t && (t = s[i]), s[i] > e && (e = s[i]);
  return [t, e];
}
function E(s, t) {
  if (t === 4) return new Uint8ClampedArray(s);
  const e = new Uint8ClampedArray(s.length / 3 * 4);
  for (let i = 0, n = 0; i < s.length; i += 3, n += 4)
    e[n] = s[i], e[n + 1] = s[i + 1], e[n + 2] = s[i + 2], e[n + 3] = 255;
  return e;
}
function A(s) {
  if (!s.extents) return "";
  const [t, e] = s.extents, i = s.ax_labels || ["OZ", "OX"];
  return `${i[0]}: ${t[0]}…${t[1]}   ${i[1]}: ${e[0]}…${e[1]}`;
}
customElements.get("g4u-stream-view") || customElements.define("g4u-stream-view", I);
const z = v("g4u-stream-view", (s, t) => {
  const e = t.get("display_id");
  e && s.setAttribute("display", e), s.style.height = `${t.get("height") || 320}px`;
});
export {
  z as default
};
