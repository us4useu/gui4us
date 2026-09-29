// @ts-check
/**
 * <g4u-sequence-view> -- the TX/RXs of a sequence as a graph of nodes.
 *
 * One node per TX/RX, in the order they are executed, connected by the edges of the sequence.
 * A node is highlighted while its TX/RX belongs to the sub-sequence that is being acquired, so
 * the display shows what `set_subsequence` selected. The data is a 1-D array with one value per
 * node: 0 is inactive, anything above 0 is active.
 */

const SEQUENCE_VIEW_STYLE = `
  :host { display: block; position: relative; background: #101014; color: #e6e6e6;
          font-family: system-ui, sans-serif; min-width: 0; min-height: 0; overflow: hidden; }
  canvas { width: 100%; height: 100%; display: block; }
  .empty { position: absolute; inset: 0; display: grid; place-items: center; font-size: .85rem;
           opacity: .5; }
`;

const INACTIVE = "#4a4f57";
const ACTIVE = "#3d8bfd";
const EDGE = "#2a2e35";
const MARGIN = { left: 42, right: 20, top: 34, bottom: 38 };
/** Below this spacing (CSS px) between nodes, the sequence is wrapped into more rows. */
const MIN_SPACING = 16;

export class SequenceView extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${SEQUENCE_VIEW_STYLE}</style>
      <canvas></canvas>
      <div class="empty">waiting for data…</div>`;
    this._canvas = /** @type {HTMLCanvasElement} */ (root.querySelector("canvas"));
    this._context = this._canvas.getContext("2d");
    this._emptyElement = /** @type {HTMLElement} */ (root.querySelector(".empty"));
    /** @type {any} */ this._descriptor = null;
    /** @type {string} */ this._displayId = "";
    /** @type {Float32Array|null} */ this._values = null;
    this._resizeObserver = new ResizeObserver(() => this._render());
    this._resizeObserver.observe(this);
  }

  static get observedAttributes() { return ["display"]; }

  /** @param {string} name @param {string} _old @param {string} value */
  attributeChangedCallback(name, _old, value) {
    if (name === "display") this._displayId = value;
  }

  disconnectedCallback() { this._resizeObserver.disconnect(); }

  get display() { return this._displayId; }
  set display(value) { this._displayId = value; }

  get descriptor() { return this._descriptor; }
  set descriptor(descriptor) {
    this._descriptor = descriptor;
    if (!this._displayId && descriptor && descriptor.displays && descriptor.displays.length) {
      this._displayId = descriptor.displays[0].id;
    }
    this._render();
  }

  _display() {
    if (!this._descriptor || !this._descriptor.displays) return null;
    return this._descriptor.displays.find((/** @type {any} */ d) => d.id === this._displayId) || null;
  }

  /**
   * @param {import("../core/protocol.js").DecodedFrame} frame
   */
  update(frame) {
    const array = frame.arrays.find((a) => a.header.display === this._displayId);
    if (!array) return;
    if (this._emptyElement.isConnected) this._emptyElement.remove();
    const data = /** @type {Float32Array} */ (array.data);
    // (1, n) from the encoder's atleast_2d, or (n, ).
    this._values = data;
    this._render();
  }

  _render() {
    const values = this._values;
    const display = this._display();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(this.clientWidth*ratio));
    const height = Math.max(1, Math.round(this.clientHeight*ratio));
    if (this._canvas.width !== width || this._canvas.height !== height) {
      this._canvas.width = width;
      this._canvas.height = height;
    }
    const context = this._context;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, this.clientWidth, this.clientHeight);
    context.font = "11px system-ui, sans-serif";

    if (display) {
      context.fillStyle = "#f0f2f5";
      context.textAlign = "left";
      context.textBaseline = "top";
      context.fillText(display.title || display.id, MARGIN.left, 8);
    }
    if (!values || values.length === 0) return;

    const n = values.length;
    const requested = display && display.n_columns ? Number(display.n_columns) : 0;
    const area = {
      x: MARGIN.left,
      y: MARGIN.top,
      width: Math.max(1, this.clientWidth - MARGIN.left - MARGIN.right),
      height: Math.max(1, this.clientHeight - MARGIN.top - MARGIN.bottom),
    };
    // One row while the nodes stay legible; otherwise the sequence is wrapped into as many rows
    // as it takes (and the rows are connected, so it still reads as one sequence).
    const columns = requested > 0 ? requested
      : Math.max(1, Math.min(n, Math.floor(area.width/MIN_SPACING)));
    const rows = Math.ceil(n/columns);
    const stepX = area.width/Math.max(1, columns);
    const stepY = area.height/rows;
    const radius = Math.max(2, Math.min(stepX*0.34, stepY*0.34, 14));
    const centreY = (/** @type {number} */ row) => area.y + stepY*(row + 0.5);
    const centreX = (/** @type {number} */ column) => area.x + stepX*(column + 0.5);

    // The edges of the sequence: node i is executed before node i+1, row after row.
    context.strokeStyle = EDGE;
    context.lineWidth = Math.max(1, radius*0.25);
    context.beginPath();
    for (let row = 0; row < rows; row++) {
      const first = row*columns;
      const last = Math.min(n, first + columns) - 1;
      if (last > first) {
        context.moveTo(centreX(0), centreY(row));
        context.lineTo(centreX(last - first), centreY(row));
      }
      if (last + 1 < n) {
        // Down to the beginning of the next row.
        context.moveTo(centreX(last - first), centreY(row));
        context.lineTo(centreX(last - first) + stepX*0.35, centreY(row));
        context.lineTo(centreX(last - first) + stepX*0.35, centreY(row + 1));
        context.lineTo(centreX(0) - stepX*0.35, centreY(row + 1));
        context.lineTo(centreX(0), centreY(row + 1));
      }
    }
    context.stroke();

    for (let i = 0; i < n; i++) {
      const row = Math.floor(i/columns);
      const column = i - row*columns;
      const x = area.x + stepX*(column + 0.5);
      const y = centreY(row);
      const active = values[i] > 0;
      context.beginPath();
      context.arc(x, y, active ? radius*1.25 : radius, 0, 2*Math.PI);
      context.fillStyle = active ? ACTIVE : INACTIVE;
      context.fill();
    }

    // The node axis: first, last and a few in between.
    context.fillStyle = "#9aa0aa";
    context.textAlign = "center";
    context.textBaseline = "top";
    if (rows === 1) {
      const labelStep = Math.max(1, Math.round(n/12));
      for (let i = 0; i < n; i += labelStep) {
        context.fillText(String(i), centreX(i), area.y + area.height + 6);
      }
    } else {
      // The first node of every row, at its left.
      context.textAlign = "right";
      for (let row = 0; row < rows; row++) {
        context.fillText(String(row*columns), area.x - 6, centreY(row) - 5);
      }
      context.textAlign = "center";
    }
    const labels = (display && display.node_labels) || ["not acquired", "acquired"];
    const axisLabel = display && display.ax_labels ? display.ax_labels[0] : "";
    context.textAlign = "left";
    const legendY = this.clientHeight - 14;
    context.fillStyle = INACTIVE;
    context.beginPath(); context.arc(MARGIN.left + 4, legendY + 4, 4, 0, 2*Math.PI); context.fill();
    context.fillStyle = "#9aa0aa";
    context.fillText(labels[0], MARGIN.left + 14, legendY);
    const secondX = MARGIN.left + 24 + context.measureText(labels[0]).width;
    context.fillStyle = ACTIVE;
    context.beginPath(); context.arc(secondX, legendY + 4, 5, 0, 2*Math.PI); context.fill();
    context.fillStyle = "#9aa0aa";
    context.fillText(labels[1], secondX + 10, legendY);
    if (axisLabel) {
      context.textAlign = "right";
      context.fillText(axisLabel, this.clientWidth - MARGIN.right, legendY);
    }
  }
}

if (!customElements.get("g4u-sequence-view")) {
  customElements.define("g4u-sequence-view", SequenceView);
}
