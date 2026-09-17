// @ts-check
/**
 * Transports: how components exchange messages with the Python side.
 *
 * Components never import a transport -- they take frames/state as properties and emit
 * CustomEvents. The host (the web app or an anywidget widget) wires one of these in, which is
 * what lets the same components run in the browser and in a notebook.
 */

import { decodeFrame } from "./protocol.js";

/**
 * @typedef {Object} Transport
 * @property {(message: any) => void} send
 * @property {(callback: (message: any) => void) => void} onMessage
 * @property {(callback: (frame: import("./protocol.js").DecodedFrame) => void) => void} onFrame
 * @property {() => void} [close]
 */

/**
 * WebSocket transport used by the standalone web application.
 * @implements {Transport}
 */
export class WebSocketTransport {
  /** @param {string} [url] defaults to /ws/stream on the serving origin */
  constructor(url) {
    const defaultUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/stream`;
    this.url = url || defaultUrl;
    /** @type {Array<(m: any) => void>} */ this.messageCallbacks = [];
    /** @type {Array<(f: any) => void>} */ this.frameCallbacks = [];
    /** @type {any[]} */ this.pending = [];
    this.socket = new WebSocket(this.url);
    this.socket.binaryType = "arraybuffer";
    this.socket.addEventListener("open", () => {
      this.pending.splice(0).forEach((m) => this.send(m));
    });
    this.socket.addEventListener("message", (event) => {
      if (typeof event.data === "string") {
        const message = JSON.parse(event.data);
        this.messageCallbacks.forEach((cb) => cb(message));
      } else {
        const frame = decodeFrame(event.data);
        this.frameCallbacks.forEach((cb) => cb(frame));
      }
    });
  }

  /** @param {any} message */
  send(message) {
    if (this.socket.readyState !== WebSocket.OPEN) {
      this.pending.push(message);
      return;
    }
    this.socket.send(JSON.stringify(message));
  }

  /** @param {(m: any) => void} callback */
  onMessage(callback) { this.messageCallbacks.push(callback); }

  /** @param {(f: any) => void} callback */
  onFrame(callback) { this.frameCallbacks.push(callback); }

  close() { this.socket.close(); }
}

/**
 * anywidget transport: control messages travel over the widget's custom messages, frames over
 * a binary traitlet.
 * @implements {Transport}
 */
export class ModelTransport {
  /** @param {any} model the anywidget model */
  constructor(model) {
    this.model = model;
    /** @type {Array<(m: any) => void>} */ this.messageCallbacks = [];
    /** @type {Array<(f: any) => void>} */ this.frameCallbacks = [];

    model.on("msg:custom", (/** @type {any} */ message) => {
      this.messageCallbacks.forEach((cb) => cb(message));
    });
    model.on("change:frame", () => this._emitFrame());
    // The widget may already hold a frame and the descriptor when the view is (re)created.
    queueMicrotask(() => {
      const descriptor = model.get("descriptor");
      if (descriptor && Object.keys(descriptor).length > 0) {
        this.messageCallbacks.forEach((cb) => cb(descriptor));
      }
      const state = model.get("state");
      if (state && Object.keys(state).length > 0) {
        this.messageCallbacks.forEach((cb) => cb({ type: "state", ...state }));
      }
      this._emitFrame();
    });
  }

  _emitFrame() {
    const raw = this.model.get("frame");
    if (!raw || raw.byteLength === 0) return;
    const bytes = raw instanceof DataView ? new Uint8Array(raw.buffer) : new Uint8Array(raw);
    const frame = decodeFrame(bytes);
    this.frameCallbacks.forEach((cb) => cb(frame));
  }

  /** @param {any} message */
  send(message) { this.model.send(message); }

  /** @param {(m: any) => void} callback */
  onMessage(callback) { this.messageCallbacks.push(callback); }

  /** @param {(f: any) => void} callback */
  onFrame(callback) { this.frameCallbacks.push(callback); }
}
