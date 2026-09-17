function u(e) {
  const t = (
    /** @type {ArrayBuffer} */
    e instanceof Uint8Array ? e.buffer : e
  ), s = e instanceof Uint8Array ? e.byteOffset : 0, r = new DataView(t, s).getUint32(
    0,
    /* littleEndian */
    !0
  ), a = new Uint8Array(t, s + 4, r), n = JSON.parse(new TextDecoder().decode(a)), f = s + 4 + r, d = n.arrays.map((o) => ({
    header: o,
    data: p(t, f + o.offset, o)
  }));
  return { header: n, arrays: d };
}
function p(e, t, s) {
  const i = s.shape.reduce((r, a) => r * a, 1);
  if (s.dtype === "uint8")
    return new Uint8Array(e, t, i);
  if (s.dtype === "float32")
    return new Float32Array(e.slice(t, t + i * 4));
  throw new Error(`Unsupported dtype in frame: ${s.dtype}`);
}
const c = Object.freeze({
  FRAME: "frame",
  DESCRIPTOR: "descriptor",
  STATE: "state",
  ERROR: "error",
  ACTION: "action",
  SET_SETTING: "set_setting"
});
function y(e, t) {
  const s = (n) => {
    !n || !n.type || (n.type === c.DESCRIPTOR ? ("descriptor" in e && (e.descriptor = n), "settings" in e && (e.settings = n.settings || []), "capacity" in e && n.capture && (e.capacity = n.capture.capacity), n.state && "state" in e && (e.state = n.state)) : n.type === c.STATE ? "state" in e && (e.state = n) : n.type === c.ERROR && (console.error("gui4us:", n.message), e.dispatchEvent(new CustomEvent("g4u-error", {
      detail: n,
      bubbles: !0,
      composed: !0
    }))));
  }, i = (n) => {
    typeof e.update == "function" && e.update(n);
  }, r = (n) => {
    t.send({ type: c.ACTION, ...n.detail });
  }, a = (n) => {
    t.send({ type: c.SET_SETTING, ...n.detail });
  };
  return t.onMessage(s), t.onFrame(i), e.addEventListener("action", r), e.addEventListener("set-setting", a), () => {
    e.removeEventListener("action", r), e.removeEventListener("set-setting", a);
  };
}
class h {
  /** @param {any} model the anywidget model */
  constructor(t) {
    this.model = t, this.messageCallbacks = [], this.frameCallbacks = [], t.on("msg:custom", (s) => {
      this.messageCallbacks.forEach((i) => i(s));
    }), t.on("change:frame", () => this._emitFrame()), queueMicrotask(() => {
      const s = t.get("descriptor");
      s && Object.keys(s).length > 0 && this.messageCallbacks.forEach((r) => r(s));
      const i = t.get("state");
      i && Object.keys(i).length > 0 && this.messageCallbacks.forEach((r) => r({ type: "state", ...i })), this._emitFrame();
    });
  }
  _emitFrame() {
    const t = this.model.get("frame");
    if (!t || t.byteLength === 0) return;
    const s = t instanceof DataView ? new Uint8Array(t.buffer) : new Uint8Array(t), i = u(s);
    this.frameCallbacks.forEach((r) => r(i));
  }
  /** @param {any} message */
  send(t) {
    this.model.send(t);
  }
  /** @param {(m: any) => void} callback */
  onMessage(t) {
    this.messageCallbacks.push(t);
  }
  /** @param {(f: any) => void} callback */
  onFrame(t) {
    this.frameCallbacks.push(t);
  }
}
function E(e, t) {
  return {
    render({ model: s, el: i }) {
      const r = (
        /** @type {any} */
        document.createElement(e)
      ), a = new h(s), n = y(r, a);
      return t && t(r, s), i.classList.add("gui4us-widget"), i.appendChild(r), () => {
        n(), r.remove();
      };
    }
  };
}
export {
  E as w
};
