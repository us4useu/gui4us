import { w as o } from "./_widget-_BnPWc-d.js";
const n = `
  :host { display: block; font-family: system-ui, sans-serif; color: #e6e6e6;
          background: #17171c; padding: .75rem; box-sizing: border-box; }
  h3 { margin: 0 0 .6rem; font-size: .9rem; font-weight: 600; opacity: .8;
       text-transform: uppercase; letter-spacing: .04em; }
  .row { display: flex; gap: .5rem; align-items: center; margin-bottom: .5rem; }
  label { font-size: .78rem; opacity: .8; }
  input[type=number] { width: 5rem; background: #23232b; color: inherit; border: 1px solid #34343e;
                       border-radius: 4px; padding: .2rem .35rem; font-size: .8rem; }
  button { flex: 1; padding: .45rem .6rem; font-size: .85rem; border-radius: 6px;
           border: 1px solid #34343e; background: #2f3140; color: #fff; cursor: pointer; }
  button.primary { background: #3a5fb0; }
  button:disabled { opacity: .4; cursor: default; }
  button:not(:disabled):hover { filter: brightness(1.15); }
  progress { width: 100%; height: .4rem; }
  .state { margin-top: .4rem; font-size: .78rem; opacity: .7; }
`;
class i extends HTMLElement {
  constructor() {
    super();
    const e = this.attachShadow({ mode: "open" });
    e.innerHTML = `<style>${n}</style>
      <h3>Buffer</h3>
      <div class="row"><label for="n">Frames</label><input id="n" type="number" min="1" value="100"></div>
      <div class="row">
        <button type="button" class="primary capture">Capture</button>
        <button type="button" class="save" disabled>Save</button>
      </div>
      <progress value="0" max="100"></progress>
      <div class="state">Press capture…</div>`, this._nFrames = /** @type {HTMLInputElement} */
    e.querySelector("#n"), this._captureButton = /** @type {HTMLButtonElement} */
    e.querySelector(".capture"), this._saveButton = /** @type {HTMLButtonElement} */
    e.querySelector(".save"), this._progress = /** @type {HTMLProgressElement} */
    e.querySelector("progress"), this._stateElement = /** @type {HTMLElement} */
    e.querySelector(".state"), this.askForPath = !0, this._captureButton.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("action", {
        detail: { name: "capture", n_frames: Number(this._nFrames.value) || void 0 },
        bubbles: !0,
        composed: !0
      }));
    }), this._saveButton.addEventListener("click", () => {
      if (!this.askForPath) {
        this.dispatchEvent(new CustomEvent("download", { bubbles: !0, composed: !0 }));
        return;
      }
      const t = prompt("Save the captured buffer as:", "capture.pkl");
      t && this.dispatchEvent(new CustomEvent("action", {
        detail: { name: "save", path: t },
        bubbles: !0,
        composed: !0
      }));
    });
  }
  /** The capacity advertised by the descriptor. */
  set capacity(e) {
    e && (this._nFrames.value = String(e));
  }
  /** @param {{state?: string, size?: number, capacity?: number}} capture */
  set capture(e) {
    if (!e) return;
    const { state: t, size: r = 0, capacity: a = 0 } = e;
    this._progress.max = a || 100, this._progress.value = r, this._saveButton.disabled = t !== "captured", t === "capturing" ? this._stateElement.textContent = `Capturing… ${r}/${a} frames` : t === "captured" ? this._stateElement.textContent = `Captured ${r} frames` : this._stateElement.textContent = "Press capture…";
  }
  /** @param {{capture?: any}} state */
  set state(e) {
    e && e.capture && (this.capture = e.capture);
  }
}
customElements.get("g4u-capture-panel") || customElements.define("g4u-capture-panel", i);
const p = o("g4u-capture-panel", (s) => {
  s.askForPath = !0;
});
export {
  p as default
};
