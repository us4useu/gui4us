// @ts-check
/**
 * Shared anywidget bootstrap.
 *
 * Every widget entry point is the same three lines: create the element, connect it to the
 * notebook's model through ModelTransport, append it. The components are the ones the web app
 * uses -- this file is the only Jupyter-specific glue.
 */

import { bind } from "../core/bind.js";
import { ModelTransport } from "../core/transport.js";

/**
 * @param {string} tagName
 * @param {(element: any, model: any) => void} [configure]
 * @returns {{render: (context: {model: any, el: HTMLElement}) => (() => void)}}
 */
export function widgetFor(tagName, configure) {
  return {
    render({ model, el }) {
      const element = /** @type {any} */ (document.createElement(tagName));
      const transport = new ModelTransport(model);
      const dispose = bind(element, transport);
      if (configure) configure(element, model);
      el.classList.add("gui4us-widget");
      el.appendChild(element);
      return () => {
        dispose();
        element.remove();
      };
    },
  };
}
