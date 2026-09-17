// @ts-check
/**
 * Wiring between the components and a transport.
 *
 * The components are deliberately transport-agnostic (properties in, CustomEvents out); this is
 * the one place that connects them, and it is shared by the web app and the Jupyter widgets so
 * both behave identically.
 */

import { TYPE } from "./protocol.js";

/**
 * @typedef {import("./transport.js").Transport} Transport
 */

/**
 * Connects an element to a transport.
 *
 * Anything the element exposes is optional: `descriptor`, `settings`, `capacity`, `state` and
 * `update(frame)` are set/called only when present, so the same function serves every component.
 *
 * @param {HTMLElement & Record<string, any>} element
 * @param {Transport} transport
 * @returns {() => void} a dispose function
 */
export function bind(element, transport) {
  const onMessage = (/** @type {any} */ message) => {
    if (!message || !message.type) return;
    if (message.type === TYPE.DESCRIPTOR) {
      if ("descriptor" in element) element.descriptor = message;
      if ("settings" in element) element.settings = message.settings || [];
      if ("capacity" in element && message.capture) element.capacity = message.capture.capacity;
      if (message.state && "state" in element) element.state = message.state;
    } else if (message.type === TYPE.STATE) {
      if ("state" in element) element.state = message;
    } else if (message.type === TYPE.ERROR) {
      console.error("gui4us:", message.message);
      element.dispatchEvent(new CustomEvent("g4u-error", {
        detail: message, bubbles: true, composed: true,
      }));
    }
  };

  const onFrame = (/** @type {any} */ frame) => {
    if (typeof element.update === "function") element.update(frame);
  };

  const onAction = (/** @type {any} */ event) => {
    transport.send({ type: TYPE.ACTION, ...event.detail });
  };

  const onSetSetting = (/** @type {any} */ event) => {
    transport.send({ type: TYPE.SET_SETTING, ...event.detail });
  };

  transport.onMessage(onMessage);
  transport.onFrame(onFrame);
  element.addEventListener("action", onAction);
  element.addEventListener("set-setting", onSetSetting);

  return () => {
    element.removeEventListener("action", onAction);
    element.removeEventListener("set-setting", onSetSetting);
  };
}

/**
 * Binds several elements to one transport.
 * @param {Array<HTMLElement & Record<string, any>>} elements
 * @param {Transport} transport
 * @returns {() => void}
 */
export function bindAll(elements, transport) {
  const disposers = elements.map((element) => bind(element, transport));
  return () => disposers.forEach((dispose) => dispose());
}
