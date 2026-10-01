// @ts-check
/**
 * <g4u-control-panel> -- the environment settings.
 *
 * Built from the `settings` part of the view descriptor, which is a direct rendering of the
 * environment's `SettingDef`s: scalars become a slider + number field, vectors (e.g. a TGC
 * curve) become one labelled slider per component. Emits `set-setting`
 * ({name, value}) -- it never talks to a transport itself.
 */

const CONTROL_PANEL_STYLE = `
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

export class ControlPanel extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${CONTROL_PANEL_STYLE}</style><h3>Control panel</h3><div class="settings"></div>`;
    this._container = /** @type {HTMLElement} */ (root.querySelector(".settings"));
    /** @type {any[]} */ this._settings = [];
  }

  /** The `settings` array of the view descriptor. */
  get settings() { return this._settings; }
  set settings(settings) {
    this._settings = settings || [];
    this._render();
  }

  /** @param {boolean} value */
  set disabled(value) {
    if (value) this.setAttribute("disabled", ""); else this.removeAttribute("disabled");
  }

  get disabled() { return this.hasAttribute("disabled"); }

  _render() {
    // Not replaceChildren(): the Qt WebEngine window (Chromium 83) does not have it.
    this._container.textContent = "";
    if (this._settings.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "This environment exposes no settings.";
      this._container.append(empty);
      return;
    }
    for (const setting of this._settings) {
      this._container.append(setting.kind === "vector"
        ? this._vectorSetting(setting) : this._scalarSetting(setting));
    }
  }

  /** @param {any} setting */
  _scalarSetting(setting) {
    const wrapper = document.createElement("div");
    wrapper.className = "setting";
    const label = document.createElement("label");
    setLabel(label, settingLabel(setting));
    const row = document.createElement("div");
    row.className = "row";

    const low = scalar(setting.low, 0);
    const high = scalar(setting.high, 100);
    const step = scalar(setting.step, 1) || 1;
    const initial = scalar(setting.initial_value, low);

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = String(low);
    slider.max = String(high);
    slider.step = String(step);
    slider.value = String(initial);

    const number = document.createElement("input");
    number.type = "number";
    number.min = slider.min;
    number.max = slider.max;
    number.step = slider.step;
    number.value = slider.value;

    const emit = (/** @type {string} */ value) => {
      slider.value = value;
      number.value = value;
      this._emit(setting.name, Number(value));
    };
    slider.addEventListener("input", () => emit(slider.value));
    number.addEventListener("change", () => emit(number.value));

    if (isBounded(setting.low, setting.high, 0)) {
      row.append(slider, number);
    } else {
      // No (finite) range, e.g. an ARRUS pipeline parameter declared with low=-inf, high=inf: a slider
      // would be meaningless -- only the number field, with any step.
      number.removeAttribute("min");
      number.removeAttribute("max");
      number.step = "any";
      number.value = String(scalar(setting.initial_value, 0));
      row.append(number);
    }
    wrapper.append(label, row);
    return wrapper;
  }

  /** @param {any} setting */
  _vectorSetting(setting) {
    const wrapper = document.createElement("div");
    wrapper.className = "setting";
    const label = document.createElement("label");
    setLabel(label, settingLabel(setting));
    wrapper.append(label);

    const size = (setting.shape && setting.shape[0]) || 0;
    const low = asArray(setting.low, size, 0);
    const high = asArray(setting.high, size, 100);
    const initial = asArray(setting.initial_value, size, low[0]);
    const step = scalar(setting.step, 1) || 1;
    const names = setting.component_names || [];
    const values = initial.slice();

    for (let i = 0; i < size; i++) {
      const row = document.createElement("div");
      row.className = "component";
      const name = document.createElement("span");
      setLabel(name, names[i] !== undefined ? String(names[i]) : `#${i}`);
      if (!isBounded(setting.low, setting.high, i)) {
        // An unbounded component: a number field only (see _scalarSetting).
        const number = document.createElement("input");
        number.type = "number";
        number.step = "any";
        number.value = String(values[i]);
        number.addEventListener("change", () => {
          values[i] = Number(number.value);
          this._emit(setting.name, values.slice());
        });
        row.append(name, number);
        wrapper.append(row);
        continue;
      }
      const slider = document.createElement("input");
      slider.type = "range";
      slider.min = String(low[i]);
      slider.max = String(high[i]);
      slider.step = String(step);
      slider.value = String(values[i]);
      const readout = document.createElement("span");
      readout.textContent = formatReadout(values[i]);
      slider.addEventListener("input", () => {
        values[i] = Number(slider.value);
        readout.textContent = formatReadout(Number(slider.value));
        // A TGC curve is set as a whole: send the full vector.
        this._emit(setting.name, values.slice());
      });
      row.append(name, slider, readout);
      wrapper.append(row);
    }
    return wrapper;
  }

  /** @param {string} name @param {number|number[]} value */
  _emit(name, value) {
    this.dispatchEvent(new CustomEvent("set-setting", {
      detail: { name, value }, bubbles: true, composed: true,
    }));
  }
}

/** The longest setting name printed in full; longer ones are cut ("name...") with the full one in a tooltip. */
const MAX_LABEL_LENGTH = 28;

/** @param {HTMLElement} element @param {string} text */
function setLabel(element, text) {
  element.textContent = text.length > MAX_LABEL_LENGTH ? `${text.slice(0, MAX_LABEL_LENGTH - 1)}\u2026` : text;
  element.title = text;
}

/** @param {any} setting */
function settingLabel(setting) {
  const unit = Array.isArray(setting.unit) ? setting.unit[0] : setting.unit;
  return unit ? `${setting.name} [${unit}]` : setting.name;
}

/**
 * Whether the i-th component of a setting has a finite range. The server sends null for an unbounded (+-inf)
 * limit (JSON has no Infinity).
 * @param {any} low @param {any} high @param {number} i
 */
function isBounded(low, high, i) {
  const component = (/** @type {any} */ value) => (Array.isArray(value) ? value[i] : value);
  const l = component(low);
  const h = component(high);
  return l !== null && l !== undefined && h !== null && h !== undefined
    && Number.isFinite(Number(l)) && Number.isFinite(Number(h));
}

/** The displayed value: at most 2 decimals (e.g. 18.44, not 18.4444444444). @param {number} value */
function formatReadout(value) {
  return String(Math.round(value * 100) / 100);
}

/** @param {any} value @param {number} fallback @returns {number} */
function scalar(value, fallback) {
  if (Array.isArray(value)) return value.length ? Number(value[0]) : fallback;
  return value === null || value === undefined ? fallback : Number(value);
}

/** @param {any} value @param {number} size @param {number} fallback @returns {number[]} */
function asArray(value, size, fallback) {
  if (Array.isArray(value)) {
    return value.length === size ? value.map(Number)
      : Array.from({ length: size }, (_, i) => Number(value[i] !== undefined ? value[i] : value[0]));
  }
  const filled = value === null || value === undefined ? fallback : Number(value);
  return Array.from({ length: size }, () => filled);
}

if (!customElements.get("g4u-control-panel")) {
  customElements.define("g4u-control-panel", ControlPanel);
}
