// @ts-check
/**
 * <g4u-capture-panel> -- the capture buffer.
 *
 * "Capture" fills the buffer with N raw frames; "Save" writes it out (in the notebook the data
 * is already in `view.captured`, so saving is optional there). Emits `action` with
 * {name: "capture", n_frames} / {name: "save", path} / {name: "clear"}, and `download` when the
 * host should fetch the buffer over HTTP.
 */

const CAPTURE_PANEL_STYLE = `
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

export class CapturePanel extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${CAPTURE_PANEL_STYLE}</style>
      <h3>Buffer</h3>
      <div class="row"><label for="n">Frames</label><input id="n" type="number" min="1" value="100"></div>
      <div class="row">
        <button type="button" class="primary capture">Capture</button>
        <button type="button" class="save" disabled>Save</button>
      </div>
      <progress value="0" max="100"></progress>
      <div class="state">Press capture…</div>`;
    this._nFrames = /** @type {HTMLInputElement} */ (root.querySelector("#n"));
    this._captureButton = /** @type {HTMLButtonElement} */ (root.querySelector(".capture"));
    this._saveButton = /** @type {HTMLButtonElement} */ (root.querySelector(".save"));
    this._progress = /** @type {HTMLProgressElement} */ (root.querySelector("progress"));
    this._stateElement = /** @type {HTMLElement} */ (root.querySelector(".state"));
    /** Whether Save should ask for a path (web app) or just notify the host (notebook). */
    this.askForPath = true;

    this._captureButton.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("action", {
        detail: { name: "capture", n_frames: Number(this._nFrames.value) || undefined },
        bubbles: true, composed: true,
      }));
    });
    this._saveButton.addEventListener("click", () => {
      if (!this.askForPath) {
        this.dispatchEvent(new CustomEvent("download", { bubbles: true, composed: true }));
        return;
      }
      const path = prompt("Save the captured buffer as:", "capture.pkl");
      if (!path) return;
      this.dispatchEvent(new CustomEvent("action", {
        detail: { name: "save", path }, bubbles: true, composed: true,
      }));
    });
  }

  /** The capacity advertised by the descriptor. */
  set capacity(value) {
    if (value) this._nFrames.value = String(value);
  }

  /** @param {{state?: string, size?: number, capacity?: number}} capture */
  set capture(capture) {
    if (!capture) return;
    const { state, size = 0, capacity = 0 } = capture;
    this._progress.max = capacity || 100;
    this._progress.value = size;
    this._saveButton.disabled = state !== "captured";
    if (state === "capturing") {
      this._stateElement.textContent = `Capturing… ${size}/${capacity} frames`;
    } else if (state === "captured") {
      this._stateElement.textContent = `Captured ${size} frames`;
    } else {
      this._stateElement.textContent = "Press capture…";
    }
  }

  /** @param {{capture?: any}} state */
  set state(state) {
    if (state && state.capture) this.capture = state.capture;
  }
}

if (!customElements.get("g4u-capture-panel")) {
  customElements.define("g4u-capture-panel", CapturePanel);
}
