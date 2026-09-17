// @ts-check
/**
 * <g4u-actions-panel> -- hardware actions.
 *
 * Start/Freeze, reflecting the hardware state reported by the session. Emits `action`
 * ({name: "start"|"stop"}).
 */

const ACTIONS_PANEL_STYLE = `
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

export class ActionsPanel extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${ACTIONS_PANEL_STYLE}</style>
      <h3>Actions</h3>
      <button type="button">Start</button>
      <div class="state">stopped</div>`;
    this._button = /** @type {HTMLButtonElement} */ (root.querySelector("button"));
    this._stateElement = /** @type {HTMLElement} */ (root.querySelector(".state"));
    this._hardware = "stopped";
    this._button.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("action", {
        detail: { name: this._hardware === "started" ? "stop" : "start" },
        bubbles: true, composed: true,
      }));
    });
  }

  /** "started" | "stopped", as reported by the session. */
  get hardware() { return this._hardware; }
  set hardware(state) {
    this._hardware = state;
    const running = state === "started";
    this._button.textContent = running ? "Freeze" : "Start";
    this._button.classList.toggle("running", running);
    this._stateElement.textContent = running ? "running" : "stopped";
  }

  /** @param {{hardware?: string}} state */
  set state(state) {
    if (state && state.hardware) this.hardware = state.hardware;
  }
}

if (!customElements.get("g4u-actions-panel")) {
  customElements.define("g4u-actions-panel", ActionsPanel);
}
