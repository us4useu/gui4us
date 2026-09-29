import { w as T } from "./_widget-_BnPWc-d.js";
const g = { left: 58, right: 14, top: 26, bottom: 44 }, A = "#9aa0aa", C = "#d4d7dd", I = "11px system-ui, sans-serif";
function v(e, t, s = 6) {
  const i = Math.abs(t - e);
  if (!(i > 0) || !Number.isFinite(i)) return [e];
  const n = i / Math.max(2, s), h = Math.pow(10, Math.floor(Math.log10(n))), a = [1, 2, 2.5, 5, 10].map((l) => l * h).find((l) => l >= n) || 10 * h, r = Math.min(e, t), o = Math.max(e, t), d = [];
  for (let l = Math.ceil(r / a) * a; l <= o + a * 1e-6; l += a)
    d.push(Math.abs(l) < a * 1e-6 ? 0 : l);
  return d;
}
function x(e, t) {
  const s = t >= 10 || t >= 1 ? 0 : t >= 0.1 ? 1 : 2;
  return e.toFixed(s);
}
function k(e, t) {
  return {
    x: g.left,
    y: g.top,
    width: Math.max(1, e - g.left - g.right),
    height: Math.max(1, t - g.top - g.bottom)
  };
}
function S(e, t, s) {
  const { x: i, y: n } = s;
  e.save(), e.font = I, e.strokeStyle = A, e.fillStyle = C, e.lineWidth = 1, e.strokeRect(t.x + 0.5, t.y + 0.5, t.width, t.height);
  const h = v(i[0], i[1]), a = h.length > 1 ? Math.abs(h[1] - h[0]) : 1;
  e.textAlign = "center", e.textBaseline = "top";
  for (const d of h) {
    const l = t.x + (d - i[0]) / (i[1] - i[0]) * t.width;
    l < t.x - 1 || l > t.x + t.width + 1 || (e.beginPath(), e.moveTo(l, t.y + t.height), e.lineTo(l, t.y + t.height + 5), e.stroke(), e.fillText(x(d, a), l, t.y + t.height + 8));
  }
  const r = v(n[0], n[1]), o = r.length > 1 ? Math.abs(r[1] - r[0]) : 1;
  e.textAlign = "right", e.textBaseline = "middle";
  for (const d of r) {
    const l = t.y + (d - n[0]) / (n[1] - n[0]) * t.height;
    l < t.y - 1 || l > t.y + t.height + 1 || (e.beginPath(), e.moveTo(t.x - 5, l), e.lineTo(t.x, l), e.stroke(), e.fillText(x(d, o), t.x - 8, l));
  }
  s.xLabel && (e.textAlign = "center", e.textBaseline = "bottom", e.fillText(s.xLabel, t.x + t.width / 2, t.y + t.height + g.bottom - 4)), s.yLabel && (e.save(), e.translate(12, t.y + t.height / 2), e.rotate(-Math.PI / 2), e.textAlign = "center", e.textBaseline = "top", e.fillText(s.yLabel, 0, 0), e.restore()), s.title && (e.textAlign = "left", e.textBaseline = "alphabetic", e.fillStyle = "#f0f2f5", e.fillText(s.title, t.x, t.y - 8)), e.restore();
}
const _ = 255;
function c(e) {
  const t = new Uint8ClampedArray(1024), s = e.length - 1;
  for (let i = 0; i < _; i++) {
    const n = i / (_ - 1) * s, h = Math.min(Math.floor(n), s - 1), a = n - h, r = e[h], o = e[h + 1];
    t[i * 4 + 0] = r[0] + (o[0] - r[0]) * a, t[i * 4 + 1] = r[1] + (o[1] - r[1]) * a, t[i * 4 + 2] = r[2] + (o[2] - r[2]) * a, t[i * 4 + 3] = 255;
  }
  return t[_ * 4 + 3] = 0, t;
}
const p = c([[0, 0, 0], [255, 255, 255]]), L = {
  gray: p,
  grey: p,
  bone: c([[0, 0, 0], [84, 84, 116], [169, 201, 201], [255, 255, 255]]),
  hot: c([[0, 0, 0], [255, 0, 0], [255, 255, 0], [255, 255, 255]]),
  inferno: c([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]]),
  magma: c([[0, 0, 4], [81, 18, 124], [183, 55, 121], [252, 137, 97], [252, 253, 191]]),
  viridis: c([[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]),
  jet: c([[0, 0, 128], [0, 0, 255], [0, 255, 255], [255, 255, 0], [255, 0, 0], [128, 0, 0]]),
  // Diverging maps, e.g. for the colour Doppler velocity.
  bwr: c([[0, 0, 255], [255, 255, 255], [255, 0, 0]]),
  seismic: c([[0, 0, 76], [0, 0, 255], [255, 255, 255], [255, 0, 0], [128, 0, 0]]),
  coolwarm: c([[59, 76, 192], [221, 221, 221], [180, 4, 38]]),
  rdbu_r: c([[5, 48, 97], [67, 147, 195], [247, 247, 247], [214, 96, 77], [103, 0, 31]])
};
function O(e) {
  return e && L[e.toLowerCase()] || p;
}
function R(e, t, s) {
  const i = s && s.length === e.length * 4 ? s : new Uint8ClampedArray(e.length * 4);
  for (let n = 0; n < e.length; n++) {
    const h = e[n] * 4, a = n * 4;
    i[a] = t[h], i[a + 1] = t[h + 1], i[a + 2] = t[h + 2], i[a + 3] = t[h + 3];
  }
  return i;
}
const E = `
  :host { display: block; position: relative; background: #101014; color: #e6e6e6;
          font-family: system-ui, sans-serif; min-width: 0; min-height: 0; overflow: hidden; }
  /* The canvas covers the element; the image is drawn inside the axes (see core/axes.js), so
     the ticks and labels are part of the same drawing. */
  canvas { width: 100%; height: 100%; display: block; }
  .empty { position: absolute; inset: 0; display: grid; place-items: center; font-size: .85rem;
           opacity: .5; }
`;
class D extends HTMLElement {
  constructor() {
    super();
    const t = this.attachShadow({ mode: "open" });
    t.innerHTML = `<style>${E}</style>
      <canvas></canvas>
      <div class="empty">waiting for data…</div>`, this._canvas = /** @type {HTMLCanvasElement} */
    t.querySelector("canvas"), this._context = this._canvas.getContext("2d"), this._emptyElement = /** @type {HTMLElement} */
    t.querySelector(".empty"), this._descriptor = null, this._rgbaCache = /* @__PURE__ */ new Map(), this._displayId = "", this._hasData = !1, this._layerCanvases = /* @__PURE__ */ new Map(), this._lastArrays = [], this._resizeObserver = new ResizeObserver(() => this._render()), this._resizeObserver.observe(this);
  }
  disconnectedCallback() {
    this._resizeObserver.disconnect();
  }
  static get observedAttributes() {
    return ["display"];
  }
  /** @param {string} name @param {string} _old @param {string} value */
  attributeChangedCallback(t, s, i) {
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
    this._descriptor = t, !this._displayId && t && t.displays && t.displays.length && (this._displayId = t.displays[0].id), this._render();
  }
  _display() {
    return !this._descriptor || !this._descriptor.displays ? null : this._descriptor.displays.find((t) => t.id === this._displayId) || this._descriptor.displays[0];
  }
  /** @param {string} display @param {number} layer */
  _layerDescriptor(t, s) {
    return !this._descriptor || !this._descriptor.layers ? null : this._descriptor.layers.find(
      (i) => i.display === t && i.layer === s
    ) || null;
  }
  /**
   * Draws one decoded frame.
   * @param {import("../core/protocol.js").DecodedFrame} frame
   */
  update(t) {
    const s = t.arrays.filter((i) => i.header.display === this._displayId);
    s.length !== 0 && (this._hasData || (this._hasData = !0, this._emptyElement.remove()), s.sort((i, n) => i.header.layer - n.header.layer), this._lastArrays = s, this._render());
  }
  /** Draws the axes and the newest frame; also called when the element is resized. */
  _render() {
    const t = this._lastArrays, s = window.devicePixelRatio || 1, i = Math.max(1, Math.round(this.clientWidth * s)), n = Math.max(1, Math.round(this.clientHeight * s));
    (this._canvas.width !== i || this._canvas.height !== n) && (this._canvas.width = i, this._canvas.height = n);
    const h = this._context;
    h.setTransform(s, 0, 0, s, 0, 0), h.clearRect(0, 0, this.clientWidth, this.clientHeight);
    const a = k(this.clientWidth, this.clientHeight), r = this._display();
    if (t.length > 0) {
      const o = this._layerDescriptor(this._displayId, t[0].header.layer);
      if (o && o.kind === "1d")
        this._drawPlot(t[0], o, a);
      else {
        h.imageSmoothingEnabled = !0;
        for (const d of t) {
          const l = this._drawImage(
            d,
            this._layerDescriptor(this._displayId, d.header.layer)
          );
          h.drawImage(l, a.x, a.y, a.width, a.height);
        }
      }
    }
    S(h, a, z(r, t));
  }
  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   * @returns {HTMLCanvasElement} the layer's canvas
   */
  _drawImage(t, s) {
    const [i, n] = t.header.shape, h = t.header.layer;
    let a = this._layerCanvases.get(h);
    if (!a) {
      const l = document.createElement("canvas");
      a = { canvas: l, context: (
        /** @type {CanvasRenderingContext2D} */
        l.getContext("2d")
      ) }, this._layerCanvases.set(h, a);
    }
    (a.canvas.width !== n || a.canvas.height !== i) && (a.canvas.width = n, a.canvas.height = i, this._rgbaCache.delete(h));
    const r = t.header.shape.length === 3;
    let o;
    if (r)
      o = U(
        /** @type {Uint8Array} */
        t.data,
        t.header.shape[2]
      );
    else {
      const l = O(s && s.cmap);
      o = R(
        /** @type {Uint8Array} */
        t.data,
        l,
        this._rgbaCache.get(t.header.layer)
      ), this._rgbaCache.set(t.header.layer, o);
    }
    const d = new ImageData(
      /** @type {Uint8ClampedArray<ArrayBuffer>} */
      o,
      n,
      i
    );
    return a.context.putImageData(d, 0, 0), a.canvas;
  }
  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   */
  _drawPlot(t, s, i) {
    const [n, h] = t.header.shape, a = i.width, r = i.height, o = this._context;
    o.save(), o.translate(i.x, i.y), o.fillStyle = "#101014", o.fillRect(0, 0, a, r);
    const d = (
      /** @type {Float32Array} */
      t.data
    );
    let [l, m] = s && s.value_range || P(d);
    m > l || (l -= 1, m += 1);
    const u = ["#4fc3f7", "#ffb74d", "#81c784", "#e57373", "#ba68c8"];
    for (let y = 0; y < n; y++) {
      o.beginPath(), o.strokeStyle = u[y % u.length], o.lineWidth = 1.5;
      for (let f = 0; f < h; f++) {
        const M = d[y * h + f], b = f / (h - 1 || 1) * a, w = r - (M - l) / (m - l) * r;
        f === 0 ? o.moveTo(b, w) : o.lineTo(b, w);
      }
      o.stroke();
    }
    o.restore();
  }
}
function P(e) {
  let t = 1 / 0, s = -1 / 0;
  for (let i = 0; i < e.length; i++)
    e[i] < t && (t = e[i]), e[i] > s && (s = e[i]);
  return [t, s];
}
function U(e, t) {
  if (t === 4) return new Uint8ClampedArray(e);
  const s = new Uint8ClampedArray(e.length / 3 * 4);
  for (let i = 0, n = 0; i < e.length; i += 3, n += 4)
    s[n] = e[i], s[n + 1] = e[i + 1], s[n + 2] = e[i + 2], s[n + 3] = 255;
  return s;
}
function z(e, t) {
  const s = e ? e.title || e.id : "", i = e && e.ax_labels || ["OZ", "OX"], n = t.length > 0 ? t[0].header.shape : null;
  if (e && e.extents && e.extents.length >= 2) {
    const [h, a] = e.extents, r = Math.max(Math.abs(h[1]), Math.abs(a[1])) < 1 ? 1e3 : 1, o = r === 1e3 ? " [mm]" : "";
    return {
      x: (
        /** @type {[number, number]} */
        [a[0] * r, a[1] * r]
      ),
      y: (
        /** @type {[number, number]} */
        [h[0] * r, h[1] * r]
      ),
      xLabel: (i[1] || "OX") + o,
      yLabel: (i[0] || "OZ") + o,
      title: s
    };
  }
  return {
    x: (
      /** @type {[number, number]} */
      [0, n ? n[1] : 1]
    ),
    y: (
      /** @type {[number, number]} */
      [0, n ? n[0] : 1]
    ),
    xLabel: i[1] || "OX",
    yLabel: i[0] || "OZ",
    title: s
  };
}
customElements.get("g4u-stream-view") || customElements.define("g4u-stream-view", D);
const W = T("g4u-stream-view", (e, t) => {
  const s = t.get("display_id");
  s && e.setAttribute("display", s), e.style.height = `${t.get("height") || 320}px`;
});
export {
  W as default
};
