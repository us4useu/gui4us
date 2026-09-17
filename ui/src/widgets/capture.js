// @ts-check
/** anywidget entry point for <g4u-capture-panel> (see gui4us/view/jupyter/widgets.py). */
import "../components/capture-panel.js";
import { widgetFor } from "./_widget.js";

export default widgetFor("g4u-capture-panel", (element) => {
  // In a notebook the captured arrays are already available as `view.captured`; "Save" asks
  // Python for a path-based save rather than a browser download.
  element.askForPath = true;
});
