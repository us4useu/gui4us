import { w as S } from "./_widget-_BnPWc-d.js";
const y = { left: 58, right: 14, top: 26, bottom: 44 }, O = "#9aa0aa", L = "#d4d7dd", R = "11px system-ui, sans-serif";
function k(e, t, s = 6) {
  const i = Math.abs(t - e);
  if (!(i > 0) || !Number.isFinite(i)) return [e];
  const a = i / Math.max(2, s), h = Math.pow(10, Math.floor(Math.log10(a))), n = [1, 2, 2.5, 5, 10].map((o) => o * h).find((o) => o >= a) || 10 * h, r = Math.min(e, t), l = Math.max(e, t), d = [];
  for (let o = Math.ceil(r / n) * n; o <= l + n * 1e-6; o += n)
    d.push(Math.abs(o) < n * 1e-6 ? 0 : o);
  return d;
}
function C(e, t) {
  const s = t >= 10 || t >= 1 ? 0 : t >= 0.1 ? 1 : 2;
  return e.toFixed(s);
}
function D(e, t) {
  return {
    x: y.left,
    y: y.top,
    width: Math.max(1, e - y.left - y.right),
    height: Math.max(1, t - y.top - y.bottom)
  };
}
function E(e, t) {
  if (!(t > 0) || !Number.isFinite(t)) return e;
  let s = e.width, i = s / t;
  return i > e.height && (i = e.height, s = i * t), {
    x: e.x + (e.width - s) / 2,
    y: e.y + (e.height - i) / 2,
    width: Math.max(1, s),
    height: Math.max(1, i)
  };
}
function F(e, t, s) {
  const { x: i, y: a } = s;
  e.save(), e.font = R, e.strokeStyle = O, e.fillStyle = L, e.lineWidth = 1, e.strokeRect(t.x + 0.5, t.y + 0.5, t.width, t.height);
  const h = k(i[0], i[1]), n = h.length > 1 ? Math.abs(h[1] - h[0]) : 1;
  e.textAlign = "center", e.textBaseline = "top";
  for (const d of h) {
    const o = t.x + (d - i[0]) / (i[1] - i[0]) * t.width;
    o < t.x - 1 || o > t.x + t.width + 1 || (e.beginPath(), e.moveTo(o, t.y + t.height), e.lineTo(o, t.y + t.height + 5), e.stroke(), e.fillText(C(d, n), o, t.y + t.height + 8));
  }
  const r = k(a[0], a[1]), l = r.length > 1 ? Math.abs(r[1] - r[0]) : 1;
  e.textAlign = "right", e.textBaseline = "middle";
  for (const d of r) {
    const o = t.y + (d - a[0]) / (a[1] - a[0]) * t.height;
    o < t.y - 1 || o > t.y + t.height + 1 || (e.beginPath(), e.moveTo(t.x - 5, o), e.lineTo(t.x, o), e.stroke(), e.fillText(C(d, l), t.x - 8, o));
  }
  s.xLabel && (e.textAlign = "center", e.textBaseline = "bottom", e.fillText(s.xLabel, t.x + t.width / 2, t.y + t.height + y.bottom - 4)), s.yLabel && (e.save(), e.translate(12, t.y + t.height / 2), e.rotate(-Math.PI / 2), e.textAlign = "center", e.textBaseline = "top", e.fillText(s.yLabel, 0, 0), e.restore()), s.title && (e.textAlign = "left", e.textBaseline = "alphabetic", e.fillStyle = "#f0f2f5", e.fillText(s.title, t.x, t.y - 8)), e.restore();
}
const A = 255;
function g(e) {
  const t = new Uint8ClampedArray(1024), s = e.length - 1;
  for (let i = 0; i < A; i++) {
    const a = i / (A - 1) * s, h = Math.min(Math.floor(a), s - 1), n = a - h, r = e[h], l = e[h + 1];
    t[i * 4 + 0] = r[0] + (l[0] - r[0]) * n, t[i * 4 + 1] = r[1] + (l[1] - r[1]) * n, t[i * 4 + 2] = r[2] + (l[2] - r[2]) * n, t[i * 4 + 3] = 255;
  }
  return t[A * 4 + 3] = 0, t;
}
const w = g([[0, 0, 0], [255, 255, 255]]), N = {
  gray: w,
  grey: w,
  bone: g([[0, 0, 0], [84, 84, 116], [169, 201, 201], [255, 255, 255]]),
  hot: g([[0, 0, 0], [255, 0, 0], [255, 255, 0], [255, 255, 255]]),
  inferno: g([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]]),
  magma: g([[0, 0, 4], [81, 18, 124], [183, 55, 121], [252, 137, 97], [252, 253, 191]]),
  viridis: g([[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]),
  jet: g([[0, 0, 128], [0, 0, 255], [0, 255, 255], [255, 255, 0], [255, 0, 0], [128, 0, 0]]),
  // Diverging maps, e.g. for the colour Doppler velocity.
  bwr: g([[0, 0, 255], [255, 255, 255], [255, 0, 0]]),
  seismic: g([[0, 0, 76], [0, 0, 255], [255, 255, 255], [255, 0, 0], [128, 0, 0]]),
  coolwarm: g([[59, 76, 192], [221, 221, 221], [180, 4, 38]]),
  rdbu_r: g([[5, 48, 97], [67, 147, 195], [247, 247, 247], [214, 96, 77], [103, 0, 31]])
};
function B(e) {
  return e && N[e.toLowerCase()] || w;
}
function P(e, t, s) {
  const i = s && s.length === e.length * 4 ? s : new Uint8ClampedArray(e.length * 4);
  for (let a = 0; a < e.length; a++) {
    const h = e[a] * 4, n = a * 4;
    i[n] = t[h], i[n + 1] = t[h + 1], i[n + 2] = t[h + 2], i[n + 3] = t[h + 3];
  }
  return i;
}
const U = `
  :host { display: block; position: relative; background: #101014; color: #e6e6e6;
          font-family: system-ui, sans-serif; min-width: 0; min-height: 0; overflow: hidden; }
  /* The canvas covers the element; the image is drawn inside the axes (see core/axes.js), so
     the ticks and labels are part of the same drawing. */
  canvas { width: 100%; height: 100%; display: block; }
  .empty { position: absolute; inset: 0; display: grid; place-items: center; font-size: .85rem;
           opacity: .5; }
`;
class z extends HTMLElement {
  constructor() {
    super();
    const t = this.attachShadow({ mode: "open" });
    t.innerHTML = `<style>${U}</style>
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
    s.length !== 0 && (this._hasData || (this._hasData = !0, this._emptyElement.remove()), s.sort((i, a) => i.header.layer - a.header.layer), this._lastArrays = s, this._render());
  }
  /** Draws the axes and the newest frame; also called when the element is resized. */
  _render() {
    const t = this._lastArrays, s = window.devicePixelRatio || 1, i = Math.max(1, Math.round(this.clientWidth * s)), a = Math.max(1, Math.round(this.clientHeight * s));
    (this._canvas.width !== i || this._canvas.height !== a) && (this._canvas.width = i, this._canvas.height = a);
    const h = this._context;
    h.setTransform(s, 0, 0, s, 0, 0), h.clearRect(0, 0, this.clientWidth, this.clientHeight);
    let n = D(this.clientWidth, this.clientHeight);
    const r = this._display(), l = t.length > 0 ? this._layerDescriptor(this._displayId, t[0].header.layer) : null, d = l && l.kind === "1d" ? X(r, t[0], l) : H(r, t);
    if (t.length > 0) {
      const o = l;
      if (o && o.kind === "1d" || (n = E(n, Math.abs(d.x[1] - d.x[0]) / Math.abs(d.y[1] - d.y[0]))), o && o.kind === "1d")
        this._drawPlot(t[0], o, n);
      else {
        h.imageSmoothingEnabled = !0;
        for (const u of t) {
          const m = this._drawImage(
            u,
            this._layerDescriptor(this._displayId, u.header.layer)
          );
          h.drawImage(m, n.x, n.y, n.width, n.height);
        }
      }
    }
    F(h, n, d);
  }
  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   * @returns {HTMLCanvasElement} the layer's canvas
   */
  _drawImage(t, s) {
    const [i, a] = t.header.shape, h = t.header.layer;
    let n = this._layerCanvases.get(h);
    if (!n) {
      const o = document.createElement("canvas");
      n = { canvas: o, context: (
        /** @type {CanvasRenderingContext2D} */
        o.getContext("2d")
      ) }, this._layerCanvases.set(h, n);
    }
    (n.canvas.width !== a || n.canvas.height !== i) && (n.canvas.width = a, n.canvas.height = i, this._rgbaCache.delete(h));
    const r = t.header.shape.length === 3;
    let l;
    if (r)
      l = W(
        /** @type {Uint8Array} */
        t.data,
        t.header.shape[2]
      );
    else {
      const o = B(s && s.cmap);
      l = P(
        /** @type {Uint8Array} */
        t.data,
        o,
        this._rgbaCache.get(t.header.layer)
      ), this._rgbaCache.set(t.header.layer, l);
    }
    const d = new ImageData(
      /** @type {Uint8ClampedArray<ArrayBuffer>} */
      l,
      a,
      i
    );
    return n.context.putImageData(d, 0, 0), n.canvas;
  }
  /**
   * @param {import("../core/protocol.js").DecodedArray} array
   * @param {any} descriptor
   */
  _drawPlot(t, s, i) {
    const [a, h] = t.header.shape, n = i.width, r = i.height, l = this._context;
    l.save(), l.translate(i.x, i.y), l.fillStyle = "#101014", l.fillRect(0, 0, n, r);
    const d = (
      /** @type {Float32Array} */
      t.data
    );
    let [o, u] = s && s.value_range || I(d);
    u > o || (o -= 1, u += 1);
    const m = ["#4fc3f7", "#ffb74d", "#81c784", "#e57373", "#ba68c8"], v = (f) => f / (h - 1 || 1) * n, x = (f) => r - (f - o) / (u - o) * r;
    for (let f = 0; f < a; f++) {
      const _ = m[f % m.length], b = (c) => d[f * h + c];
      l.beginPath(), l.strokeStyle = _, l.lineWidth = 1.5;
      let M = !1;
      for (let c = 0; c < h; c++) {
        const p = b(c);
        if (!Number.isFinite(p)) {
          M = !1;
          continue;
        }
        M ? l.lineTo(v(c), x(p)) : l.moveTo(v(c), x(p)), M = !0;
      }
      l.stroke(), l.fillStyle = _;
      for (let c = 0; c < h; c++) {
        const p = b(c);
        if (!Number.isFinite(p)) continue;
        !(c > 0 && Number.isFinite(b(c - 1))) && !(c < h - 1 && Number.isFinite(b(c + 1))) && l.fillRect(v(c) - 1.5, x(p) - 1.5, 3, 3);
      }
    }
    const T = s && s.labels || [];
    l.font = "11px system-ui, sans-serif", l.textBaseline = "middle";
    for (let f = 0; f < Math.min(a, T.length); f++) {
      const _ = 10 + 14 * f;
      l.fillStyle = m[f % m.length], l.fillRect(8, _ - 1, 14, 3), l.fillStyle = "#d4d7dd", l.fillText(String(T[f]), 28, _);
    }
    l.restore();
  }
}
function I(e) {
  let t = 1 / 0, s = -1 / 0;
  for (let i = 0; i < e.length; i++)
    Number.isFinite(e[i]) && (e[i] < t && (t = e[i]), e[i] > s && (s = e[i]));
  return [t, s];
}
function W(e, t) {
  if (t === 4) return new Uint8ClampedArray(e);
  const s = new Uint8ClampedArray(e.length / 3 * 4);
  for (let i = 0, a = 0; i < e.length; i += 3, a += 4)
    s[a] = e[i], s[a + 1] = e[i + 1], s[a + 2] = e[i + 2], s[a + 3] = 255;
  return s;
}
function H(e, t) {
  const s = e ? e.title || e.id : "", i = e && e.ax_labels || ["OZ", "OX"], a = t.length > 0 ? t[0].header.shape : null;
  if (e && e.extents && e.extents.length >= 2) {
    const [h, n] = e.extents, r = Math.max(Math.abs(h[1]), Math.abs(n[1])) < 1 ? 1e3 : 1, l = r === 1e3 ? " [mm]" : "";
    return {
      x: (
        /** @type {[number, number]} */
        [n[0] * r, n[1] * r]
      ),
      y: (
        /** @type {[number, number]} */
        [h[0] * r, h[1] * r]
      ),
      xLabel: (i[1] || "OX") + l,
      yLabel: (i[0] || "OZ") + l,
      title: s
    };
  }
  return {
    x: (
      /** @type {[number, number]} */
      [0, a ? a[1] : 1]
    ),
    y: (
      /** @type {[number, number]} */
      [0, a ? a[0] : 1]
    ),
    xLabel: i[1] || "OX",
    yLabel: i[0] || "OZ",
    title: s
  };
}
function X(e, t, s) {
  const i = e ? e.title || e.id : "", a = e && e.ax_labels || ["", ""], h = t.header.shape[t.header.shape.length - 1];
  let [n, r] = s && s.value_range || I(
    /** @type {Float32Array} */
    t.data
  );
  return r > n || (n -= 1, r += 1), {
    x: [0, Math.max(1, h - 1)],
    y: [r, n],
    xLabel: a[0] || "",
    yLabel: a[1] || "",
    title: i
  };
}
customElements.get("g4u-stream-view") || customElements.define("g4u-stream-view", z);
const q = S("g4u-stream-view", (e, t) => {
  const s = t.get("display_id");
  s && e.setAttribute("display", s), e.style.height = `${t.get("height") || 320}px`;
});
export {
  q as default
};
