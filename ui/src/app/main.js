// @ts-check
/**
 * The standalone GUI4us web application.
 *
 * It only lays the components out and connects them to the WebSocket transport -- all the
 * behaviour lives in the components themselves, which the Jupyter widgets reuse unchanged.
 */

import "../components/stream-view.js";
import "../components/control-panel.js";
import "../components/actions-panel.js";
import "../components/capture-panel.js";
import { bindAll } from "../core/bind.js";
import { WebSocketTransport } from "../core/transport.js";
import { TYPE } from "../core/protocol.js";

const transport = new WebSocketTransport();

// The custom elements are declared in index.html; the casts give the JSDoc checker the element
// type (querySelector only promises an Element, which has none of their properties).
const controlPanel = /** @type {HTMLElement & Record<string, any>} */(
  document.querySelector("g4u-control-panel"));
const actionsPanel = /** @type {HTMLElement & Record<string, any>} */(
  document.querySelector("g4u-actions-panel"));
const capturePanel = /** @type {HTMLElement & Record<string, any>} */(
  document.querySelector("g4u-capture-panel"));
const displays = document.querySelector("#displays");

/** @type {Array<any>} */
const streamViews = [];

// One <g4u-stream-view> per display in the descriptor.
transport.onMessage((message) => {
  if (message.type !== TYPE.DESCRIPTOR) return;
  displays.replaceChildren();
  streamViews.splice(0);
  for (const display of message.displays || []) {
    const view = /** @type {HTMLElement & Record<string, any>} */(
      document.createElement("g4u-stream-view"));
    view.setAttribute("display", display.id);
    view.descriptor = message;
    displays.append(view);
    streamViews.push(view);
    bindAll([view], transport);
  }
});

bindAll([controlPanel, actionsPanel, capturePanel], transport);

// "Save" in the browser downloads the buffer instead of writing a server-side path.
capturePanel.askForPath = false;
capturePanel.addEventListener("download", async () => {
  const response = await fetch("/api/capture.pkl");
  if (!response.ok) {
    console.error("gui4us: capture download failed", await response.text());
    return;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "capture.pkl";
  link.click();
  URL.revokeObjectURL(url);
});
