import { w as n } from "./_widget-_BnPWc-d.js";
const r = `
  :host { display: block; font-family: system-ui, sans-serif; color: #e6e6e6;
          background: #17171c; padding: .75rem; box-sizing: border-box; }
  h3 { margin: 0 0 .6rem; font-size: .9rem; font-weight: 600; opacity: .8;
       text-transform: uppercase; letter-spacing: .04em; }
  button { width: 100%; padding: .55rem .8rem; font-size: .9rem; font-weight: 600;
           border-radius: 6px; border: 1px solid #34343e; background: #2a7d46; color: #fff;
           cursor: pointer; }
  button.running { background: #8a5a13; }
  button:hover { filter: brightness(1.12); }
  .state { margin-top: .45rem; font-size: .78rem; opacity: .65; }
`;
class s extends HTMLElement {
  constructor() {
    super();
    const t = this.attachShadow({ mode: "open" });
    t.innerHTML = `<style>${r}</style>
      <h3>Actions</h3>
      <button type="button">Start</button>
      <div class="state">stopped</div>`, this._button = /** @type {HTMLButtonElement} */
    t.querySelector("button"), this._stateElement = /** @type {HTMLElement} */
    t.querySelector(".state"), this._hardware = "stopped", this._button.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("action", {
        detail: { name: this._hardware === "started" ? "stop" : "start" },
        bubbles: !0,
        composed: !0
      }));
    });
  }
  /** "started" | "stopped", as reported by the session. */
  get hardware() {
    return this._hardware;
  }
  set hardware(t) {
    this._hardware = t;
    const e = t === "started";
    this._button.textContent = e ? "Freeze" : "Start", this._button.classList.toggle("running", e), this._stateElement.textContent = e ? "running" : "stopped";
  }
  /** @param {{hardware?: string}} state */
  set state(t) {
    t && t.hardware && (this.hardware = t.hardware);
  }
}
customElements.get("g4u-actions-panel") || customElements.define("g4u-actions-panel", s);
const i = n("g4u-actions-panel");
export {
  i as default
};
