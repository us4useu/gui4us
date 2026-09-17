import { w as _ } from "./_widget-_BnPWc-d.js";
const E = `
  :host { display: block; font-family: system-ui, sans-serif; color: #e6e6e6;
          background: #17171c; padding: .75rem; box-sizing: border-box; overflow-y: auto; }
  h3 { margin: 0 0 .6rem; font-size: .9rem; font-weight: 600; opacity: .8;
       text-transform: uppercase; letter-spacing: .04em; }
  .setting { margin-bottom: .9rem; }
  .setting > label { display: block; font-size: .8rem; margin-bottom: .25rem; opacity: .9; }
  .row { display: flex; align-items: center; gap: .5rem; }
  input[type=range] { flex: 1; accent-color: #4fc3f7; }
  input[type=number] { width: 5.5rem; background: #23232b; color: inherit; border: 1px solid #34343e;
                       border-radius: 4px; padding: .2rem .35rem; font-size: .8rem; }
  .component { display: flex; align-items: center; gap: .4rem; margin-bottom: .2rem; }
  .component > span { font-size: .72rem; width: 5rem; opacity: .7; }
  :host([disabled]) { opacity: .45; pointer-events: none; }
  .empty { font-size: .8rem; opacity: .5; }
`;
class x extends HTMLElement {
  constructor() {
    super();
    const e = this.attachShadow({ mode: "open" });
    e.innerHTML = `<style>${E}</style><h3>Control panel</h3><div class="settings"></div>`, this._container = /** @type {HTMLElement} */
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
    if (this._container.replaceChildren(), this._settings.length === 0) {
      const e = document.createElement("div");
      e.className = "empty", e.textContent = "This environment exposes no settings.", this._container.append(e);
      return;
    }
    for (const e of this._settings)
      this._container.append(e.kind === "vector" ? this._vectorSetting(e) : this._scalarSetting(e));
  }
  /** @param {any} setting */
  _scalarSetting(e) {
    const s = document.createElement("div");
    s.className = "setting";
    const m = document.createElement("label");
    m.textContent = y(e);
    const o = document.createElement("div");
    o.className = "row";
    const c = d(e.low, 0), p = d(e.high, 100), u = d(e.step, 1) || 1, h = d(e.initial_value, c), n = document.createElement("input");
    n.type = "range", n.min = String(c), n.max = String(p), n.step = String(u), n.value = String(h);
    const r = document.createElement("input");
    r.type = "number", r.min = n.min, r.max = n.max, r.step = n.step, r.value = n.value;
    const i = (l) => {
      n.value = l, r.value = l, this._emit(e.name, Number(l));
    };
    return n.addEventListener("input", () => i(n.value)), r.addEventListener("change", () => i(r.value)), o.append(n, r), s.append(m, o), s;
  }
  /** @param {any} setting */
  _vectorSetting(e) {
    const s = document.createElement("div");
    s.className = "setting";
    const m = document.createElement("label");
    m.textContent = y(e), s.append(m);
    const o = e.shape && e.shape[0] || 0, c = b(e.low, o, 0), p = b(e.high, o, 100), u = b(e.initial_value, o, c[0]), h = d(e.step, 1) || 1, n = e.component_names || [], r = u.slice();
    for (let i = 0; i < o; i++) {
      const l = document.createElement("div");
      l.className = "component";
      const f = document.createElement("span");
      f.textContent = n[i] !== void 0 ? String(n[i]) : `#${i}`;
      const a = document.createElement("input");
      a.type = "range", a.min = String(c[i]), a.max = String(p[i]), a.step = String(h), a.value = String(r[i]);
      const g = document.createElement("span");
      g.textContent = String(r[i]), a.addEventListener("input", () => {
        r[i] = Number(a.value), g.textContent = a.value, this._emit(e.name, r.slice());
      }), l.append(f, a, g), s.append(l);
    }
    return s;
  }
  /** @param {string} name @param {number|number[]} value */
  _emit(e, s) {
    this.dispatchEvent(new CustomEvent("set-setting", {
      detail: { name: e, value: s },
      bubbles: !0,
      composed: !0
    }));
  }
}
function y(t) {
  const e = Array.isArray(t.unit) ? t.unit[0] : t.unit;
  return e ? `${t.name} [${e}]` : t.name;
}
function d(t, e) {
  return Array.isArray(t) ? t.length ? Number(t[0]) : e : t == null ? e : Number(t);
}
function b(t, e, s) {
  if (Array.isArray(t))
    return t.length === e ? t.map(Number) : Array.from({ length: e }, (o, c) => Number(t[c] !== void 0 ? t[c] : t[0]));
  const m = t == null ? s : Number(t);
  return Array.from({ length: e }, () => m);
}
customElements.get("g4u-control-panel") || customElements.define("g4u-control-panel", x);
const v = _("g4u-control-panel");
export {
  v as default
};
