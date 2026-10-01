import { w as N } from "./_widget-_BnPWc-d.js";
const A = `
  :host { display: block; font-family: system-ui, sans-serif; color: #e6e6e6;
          background: #17171c; padding: .75rem; box-sizing: border-box; overflow-x: hidden; overflow-y: auto; }
  /* Thin, dark scrollbar: -webkit- (Chromium, incl. the Qt WebEngine window), standard elsewhere (Firefox). */
  @supports not selector(::-webkit-scrollbar) {
    :host { scrollbar-width: thin; scrollbar-color: #3a3d47 transparent; }
  }
  :host::-webkit-scrollbar { width: 6px; height: 6px; }
  :host::-webkit-scrollbar-button { display: none; }
  :host::-webkit-scrollbar-track { background: transparent; }
  :host::-webkit-scrollbar-thumb { background: #3a3d47; border-radius: 3px; }
  h3 { margin: 0 0 .6rem; font-size: .9rem; font-weight: 600; opacity: .8;
       text-transform: uppercase; letter-spacing: .04em; }
  .setting { margin-bottom: .9rem; }
  .setting > label { display: block; font-size: .8rem; margin-bottom: .25rem; opacity: .9;
                     white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .row { display: flex; align-items: center; gap: .5rem; }
  /* min-width 0: a range input has an intrinsic width; without it a row does not shrink to the panel. */
  input[type=range] { flex: 1; min-width: 0; accent-color: #4fc3f7; }
  input[type=number] { width: 5.5rem; flex: none; box-sizing: border-box; background: #23232b; color: inherit; border: 1px solid #34343e;
                       border-radius: 4px; padding: .2rem .35rem; font-size: .8rem; }
  .component { display: flex; align-items: center; gap: .4rem; margin-bottom: .2rem; }
  .component > span { font-size: .72rem; width: 5rem; opacity: .7; flex: none;
                      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  /* The value read-out (the last span of a row): only as wide as a number needs. */
  .component > span:last-child { width: 3.2rem; text-align: right; }
  .setting, .row, .component { min-width: 0; max-width: 100%; }
  :host([disabled]) { opacity: .45; pointer-events: none; }
  .empty { font-size: .8rem; opacity: .5; }
`;
class S extends HTMLElement {
  constructor() {
    super();
    const e = this.attachShadow({ mode: "open" });
    e.innerHTML = `<style>${A}</style><h3>Control panel</h3><div class="settings"></div>`, this._container = /** @type {HTMLElement} */
    e.querySelector(".settings"), this._settings = [];
  }
  /** The `settings` array of the view descriptor. */
  get settings() {
    return this._settings;
  }
  set settings(e) {
    this._settings = e || [], this._render();
  }
  /** @param {boolean} value */
  set disabled(e) {
    e ? this.setAttribute("disabled", "") : this.removeAttribute("disabled");
  }
  get disabled() {
    return this.hasAttribute("disabled");
  }
  _render() {
    if (this._container.textContent = "", this._settings.length === 0) {
      const e = document.createElement("div");
      e.className = "empty", e.textContent = "This environment exposes no settings.", this._container.append(e);
      return;
    }
    for (const e of this._settings)
      this._container.append(e.kind === "vector" ? this._vectorSetting(e) : this._scalarSetting(e));
  }
  /** @param {any} setting */
  _scalarSetting(e) {
    const o = document.createElement("div");
    o.className = "setting";
    const l = document.createElement("label");
    w(l, v(e));
    const s = document.createElement("div");
    s.className = "row";
    const a = p(e.low, 0), d = p(e.high, 100), h = p(e.step, 1) || 1, b = p(e.initial_value, a), r = document.createElement("input");
    r.type = "range", r.min = String(a), r.max = String(d), r.step = String(h), r.value = String(b);
    const n = document.createElement("input");
    n.type = "number", n.min = r.min, n.max = r.max, n.step = r.step, n.value = r.value;
    const i = (c) => {
      r.value = c, n.value = c, this._emit(e.name, Number(c));
    };
    return r.addEventListener("input", () => i(r.value)), n.addEventListener("change", () => i(n.value)), _(e.low, e.high, 0) ? s.append(r, n) : (n.removeAttribute("min"), n.removeAttribute("max"), n.step = "any", n.value = String(p(e.initial_value, 0)), s.append(n)), o.append(l, s), o;
  }
  /** @param {any} setting */
  _vectorSetting(e) {
    const o = document.createElement("div");
    o.className = "setting";
    const l = document.createElement("label");
    w(l, v(e)), o.append(l);
    const s = e.shape && e.shape[0] || 0, a = y(e.low, s, 0), d = y(e.high, s, 100), h = y(e.initial_value, s, a[0]), b = p(e.step, 1) || 1, r = e.component_names || [], n = h.slice();
    for (let i = 0; i < s; i++) {
      const c = document.createElement("div");
      c.className = "component";
      const g = document.createElement("span");
      if (w(g, r[i] !== void 0 ? String(r[i]) : `#${i}`), !_(e.low, e.high, i)) {
        const u = document.createElement("input");
        u.type = "number", u.step = "any", u.value = String(n[i]), u.addEventListener("change", () => {
          n[i] = Number(u.value), this._emit(e.name, n.slice());
        }), c.append(g, u), o.append(c);
        continue;
      }
      const m = document.createElement("input");
      m.type = "range", m.min = String(a[i]), m.max = String(d[i]), m.step = String(b), m.value = String(n[i]);
      const f = document.createElement("span");
      f.textContent = E(n[i]), m.addEventListener("input", () => {
        n[i] = Number(m.value), f.textContent = E(Number(m.value)), this._emit(e.name, n.slice());
      }), c.append(g, m, f), o.append(c);
    }
    return o;
  }
  /** @param {string} name @param {number|number[]} value */
  _emit(e, o) {
    this.dispatchEvent(new CustomEvent("set-setting", {
      detail: { name: e, value: o },
      bubbles: !0,
      composed: !0
    }));
  }
}
const x = 28;
function w(t, e) {
  t.textContent = e.length > x ? `${e.slice(0, x - 1)}…` : e, t.title = e;
}
function v(t) {
  const e = Array.isArray(t.unit) ? t.unit[0] : t.unit;
  return e ? `${t.name} [${e}]` : t.name;
}
function _(t, e, o) {
  const l = (d) => Array.isArray(d) ? d[o] : d, s = l(t), a = l(e);
  return s != null && a !== null && a !== void 0 && Number.isFinite(Number(s)) && Number.isFinite(Number(a));
}
function E(t) {
  return String(Math.round(t * 100) / 100);
}
function p(t, e) {
  return Array.isArray(t) ? t.length ? Number(t[0]) : e : t == null ? e : Number(t);
}
function y(t, e, o) {
  if (Array.isArray(t))
    return t.length === e ? t.map(Number) : Array.from({ length: e }, (s, a) => Number(t[a] !== void 0 ? t[a] : t[0]));
  const l = t == null ? o : Number(t);
  return Array.from({ length: e }, () => l);
}
customElements.get("g4u-control-panel") || customElements.define("g4u-control-panel", S);
const L = N("g4u-control-panel");
export {
  L as default
};
